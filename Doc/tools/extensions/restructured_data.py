"""Sphinx extension to read, process and ouput structured data."""

from __future__ import annotations

import collections.abc
import copy
import dataclasses
import functools
import json
from pathlib import Path
from typing import TYPE_CHECKING, cast

import sphinx.util.logging
from docutils import nodes
from sphinx import addnodes
from sphinx.domains import Domain
from sphinx.domains.c import ASTDeclaration
from sphinx.transforms import SphinxTransform

if TYPE_CHECKING:
    from typing import Any

    from docutils.nodes import Node
    from docutils.parsers.rst import Directive
    from docutils.parsers.rst.states import RSTState
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment


# ---- Module-level constants ----


RSD_RUN_ATTRIBUTE = "_rsd_run_original"
RSD_OUT_DIR = Path("_restructured_data")
ANNOTATIONS_JSON_PATH = RSD_OUT_DIR / "annotations.json"

logger = sphinx.util.logging.getLogger(__name__)

__version__ = "0.1.0"


# ---- Node classes----


class rsdannotation(nodes.Element):
    pass


# ---- Dataclasses ----


@dataclasses.dataclass
class AnnotationAttributes:
    domain: str | None
    module: str | None
    objclass: str | None
    objtype: str | None
    objname: str | None
    fullname: str | None
    parentid: str | None


@dataclasses.dataclass
class DocAnnotation:
    directive: str
    docname: str
    line: int
    arguments: list[str]
    options: dict[str, float | int | bool | str | None]
    content: str | None
    version: str | None
    attributes: AnnotationAttributes


# ---- Helpers ----


def get_rsd_domain(env: BuildEnvironment) -> ReStructuredDataDomain:
    """Helper to get the live reStructured Data domain object from Sphinx."""
    domain = env.get_domain("rsd")
    assert isinstance(domain, ReStructuredDataDomain)
    return domain


def convert_object_name_to_string(obj: object) -> str | None:
    """Convert a Sphinx "object" record to a string with its name."""
    if obj is None or isinstance(obj, str):
        return obj
    # Handle C domain objects
    if isinstance(obj, ASTDeclaration):
        return obj.name.get_display_string()
    # Handle Python domain objects
    if isinstance(obj, collections.abc.Sequence) and len(obj):
        obj_name = obj[0]
        if isinstance(obj_name, str):
            return obj_name
    return None


class DataclassJSONEncoder(json.JSONEncoder):
    """A JSON encoder that knows how to serialize dataclasses."""

    def default(self, o: object) -> dict[str, Any] | Any:
        """Prepare dataclasses for JSON serialization."""
        if dataclasses.is_dataclass(o) and not isinstance(o, type):
            return dataclasses.asdict(o)
        return super().default(o)


# ---- Class decorator hook ----


def restructured_data_class_hook(
    directive_class: type[Directive],
) -> type[Directive]:
    """Class decorator to wrap the Directive.run() method for RSD support."""
    if hasattr(directive_class, RSD_RUN_ATTRIBUTE):
        return directive_class

    original_run = directive_class.run  # type: ignore[attr-defined]

    @functools.wraps(original_run)
    def run(self: Directive) -> list[rsdannotation]:
        # Execute original run method
        output_nodes = getattr(self, RSD_RUN_ATTRIBUTE)()

        # Store directive information in environment
        domain = get_rsd_domain(self.state.document.settings.env)
        node_id = domain.note_annotation(
            output_nodes=output_nodes, directive=self, state=self.state
        )

        # Wrap output nodes in new custom node
        wrapper_node = rsdannotation("", *output_nodes, ids=[node_id])
        wrapper_node.document = self.state.document
        source_and_line = self.state_machine.get_source_and_line(self.lineno)
        wrapper_node.source, wrapper_node.line = source_and_line

        return [wrapper_node]

    setattr(directive_class, RSD_RUN_ATTRIBUTE, original_run)
    directive_class.run = run  # type: ignore[attr-defined]

    return directive_class


# ---- Transforms ----


class UnwrapRSDNodeClass(SphinxTransform):
    """Remove RSD-added nodes and unwrap their children."""

    default_priority = 890

    def apply(self, **kwargs: Any) -> None:
        """Remove RSD-added nodes and unwrap their children."""
        for wrapper in self.document.findall(rsdannotation):
            wrapper.replace_self(wrapper.children)


# ---- Domain ----


class ReStructuredDataDomain(Domain):
    """Domain for structured data input, processing and output."""

    name = "rsd"
    label = "reStructuredData"

    initial_data: dict[str, dict[str, DocAnnotation]] = {
        "annotations": {},
    }

    @property
    def annotations(self) -> dict[str, dict[str, DocAnnotation]]:
        """A dict of directive name: (id: RSD annotation object)."""
        _annotations = self.data.setdefault("annotations", {})
        assert isinstance(_annotations, dict)
        return cast(dict[str, dict[str, DocAnnotation]], _annotations)

    def extract_annotation_attributes(
        self, *, state: RSTState
    ) -> AnnotationAttributes:
        """Extract attributes from an annotation context and store them."""
        # Get domain and object type from parent node via state
        node = state.parent
        while node and node.parent and not isinstance(node, addnodes.desc):
            node = node.parent
        parent = node or {}
        domain = parent.get("domain", None)
        objtype = parent.get("objtype", None)
        parentid = None
        if isinstance(parent, addnodes.desc):
            first_child = parent[0]
            if isinstance(first_child, addnodes.desc_signature):
                parentid = first_child.get("ids", [None])[0]

        # Get class and module from context
        module = self.env.ref_context.get("py:module", None)
        objclass = self.env.ref_context.get("py:class", None)
        program = self.env.ref_context.get("std:program", None)

        # Get current object name from environment
        objname = convert_object_name_to_string(
            self.env.temp_data.get("object")
        )
        fullname = objname
        if domain == "py" and module:
            fullname = f"{module}.{objname}"
        elif domain == "std" and objtype == "option" and program:
            fullname = f"{program} {objname}"
        elif not domain and not objname and module:
            fullname = module

        return AnnotationAttributes(
            domain=domain,
            module=module,
            objclass=objclass,
            objtype=objtype,
            objname=objname,
            fullname=fullname,
            parentid=parentid,
        )

    def note_annotation(
        self,
        *,
        output_nodes: list[Node],
        directive: Directive,
        state: RSTState,
    ) -> str:
        """Store annotation information in environment."""
        # Construct annotation ID
        normalized_docname = nodes.make_id(self.env.docname)
        id_prefix = f"rsd-{directive.name}-{normalized_docname}"
        id_serial = self.env.new_serialno(id_prefix) + 1
        annotation_id = f"{id_prefix}-{id_serial}"

        # Get content and version from output nodes
        content = None
        if output_nodes and len(output_nodes):
            node = output_nodes[0]
            content = node.astext().replace("\n", " ")
            version = None
            if isinstance(node, nodes.Element):
                version = node.attributes.get("version", None)

        # Build annotation object
        attributes = self.extract_annotation_attributes(state=state)
        annotation = DocAnnotation(
            directive=directive.name,
            docname=self.env.docname,
            line=directive.lineno,
            arguments=copy.deepcopy(directive.arguments),
            options=copy.deepcopy(directive.options),
            content=content,
            version=version,
            attributes=attributes,
        )

        # Store annotation data
        annotation_type = self.annotations.setdefault(directive.name, {})
        annotation_type[annotation_id] = annotation
        return annotation_id

    def clear_doc(self, docname: str) -> None:
        for annotations in self.annotations.values():
            annotation_keys = list(annotations.keys())
            for key in annotation_keys:
                if annotations[key].docname == docname:
                    del annotations[key]

    def merge_domaindata(
        self,
        docnames: list[str],
        otherdata: dict[str, dict[str, dict[str, DocAnnotation]]],
    ) -> None:
        """Handle merging annotation data collected from multiple workers."""
        all_other_annotations = otherdata.get("annotations", {})
        for directive, other_annotations in all_other_annotations.items():
            annotations = self.annotations.setdefault(directive, {})
            for annotation_id, annotation in other_annotations.items():
                if annotation.docname in docnames:
                    annotations[annotation_id] = annotation

    def process_doc(
        self,
        env: BuildEnvironment,
        docname: str,
        document: nodes.document,
    ) -> None:
        """Do nothing, as annotations are registered when calling directive."""

    def get_annotations_for(
        self, *, directive: str
    ) -> dict[str, DocAnnotation]:
        """Get the annotation records matching a given directive name."""
        return self.annotations.get(directive, {})


# ---- Output ----


def write_rsd(app: Sphinx, exception: Exception) -> None:
    """Write the collected reStructured Data as JSON."""
    if app.builder.format != "html":
        return
    annotations = get_rsd_domain(app.env).annotations
    if not annotations and exception:
        return

    logger.info(
        "Writing reStructured Data to %s", ANNOTATIONS_JSON_PATH.as_posix()
    )
    rsd_json = json.dumps(annotations, cls=DataclassJSONEncoder, indent=4)

    out_path = Path(app.outdir) / ANNOTATIONS_JSON_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rsd_json, encoding="UTF-8")


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_node(rsdannotation)
    app.add_domain(ReStructuredDataDomain)
    app.add_transform(UnwrapRSDNodeClass)
    app.connect("build-finished", write_rsd)

    return {
        "version": __version__,
        "env_version": 1,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
