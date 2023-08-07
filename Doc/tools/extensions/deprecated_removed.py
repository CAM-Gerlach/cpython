"""Sphinx extension adding a deprecated directive listing removal version."""

from docutils import nodes
from sphinx import addnodes
from sphinx.locale import _ as sphinx_gettext
from sphinx.util.docutils import SphinxDirective


class DeprecatedRemoved(SphinxDirective):
    """Document deprecations and removals using structured data."""

    has_content = True
    required_arguments = 2
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {}

    _deprecated_label = "Deprecated since version {deprecated}"
    _removed_label = "removed in version {removed}"

    def _generate_label_text(self, deprecated_arg, removed_arg):
        """Parse versions and generate label from them."""
        current_version = tuple(int(e) for e in self.config.version.split("."))
        removed_version = tuple(int(e) for e in removed_arg.split("."))
        is_removed = current_version >= removed_version
        will_be = "" if is_removed else "will be "
        label = f"{self._deprecated_label}, {will_be}{self._removed_label}"
        label = sphinx_gettext(label)
        text = label.format(deprecated=deprecated_arg, removed=removed_arg)
        return text

    def _create_node(self, *, deprecated_arg):
        """Create and set up target doctree node."""
        node = addnodes.versionmodified()
        node.document = self.state.document
        self.set_source_info(node)
        node["type"] = self.name
        node["version"] = deprecated_arg
        return node

    def _parse_content_arg(self, content_arg, *, node):
        """Parse inline directive content argument into the node."""
        if not content_arg:
            return []

        inodes, messages = self.state.inline_text(content_arg, self.lineno + 1)
        para = nodes.paragraph(content_arg, "", *inodes, translatable=False)
        self.set_source_info(para)
        node.append(para)
        return messages

    def _add_label_node(self, label_text, *, node):
        """Add generated label to node content and restructure accordingly."""
        classes = ["versionmodified", "deprecated", "removed"]
        label_text = f"{label_text}: " if len(node) > 0 else f"{label_text}."
        label_node = nodes.inline("", label_text, classes=classes)
        label_para = nodes.paragraph("", "", label_node, translatable=False)
        if len(node) > 0 and isinstance(node[0], nodes.paragraph):
            # If the contents already start with a paragraph
            para = node[0]
            if para.rawsource:
                # Make it translatable
                content = nodes.inline(para.rawsource, translatable=True)
                content.source = para.source
                content.line = para.line
                content += para.children
                para.replace_self(
                    nodes.paragraph("", "", content, translatable=False)
                )
                para = node[0]
                self.set_source_info(para)
            para.insert(0, label_node)
        else:
            node.insert(0, label_para)

    def run(self):
        # Parse arguments
        args = self.arguments.copy()
        args = args + [None] if len(args) == 2 else args
        deprecated_arg, removed_arg, content_arg = args

        # Generate the label text
        label_text = self._generate_label_text(deprecated_arg, removed_arg)

        # Create node and parse inline and body content into it
        node = self._create_node(deprecated_arg=deprecated_arg)
        messages = self._parse_content_arg(content_arg=content_arg, node=node)
        if self.content:
            self.state.nested_parse(self.content, self.content_offset, node)

        # Add label text to doctree node
        self._add_label_node(label_text=label_text, node=node)

        # Note changes and return parsed node
        self.env.get_domain("changeset").note_changeset(node)
        return [node] + messages


def setup(app):
    app.add_directive("deprecated-removed", DeprecatedRemoved)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
