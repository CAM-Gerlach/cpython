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

    def run(self):
        # Parse arguments
        args = self.arguments.copy()
        args = args + [None] if len(args) == 2 else args
        deprecated_arg, removed_arg, content_arg = args

        # Create and set up target doctree node
        node = addnodes.versionmodified()
        node.document = self.state.document
        self.set_source_info(node)
        node["type"] = self.name
        node["version"] = (deprecated_arg, removed_arg)

        # Parse versions and generate label from them
        current_version = tuple(int(e) for e in self.config.version.split("."))
        removed_version = tuple(int(e) for e in removed_arg.split("."))
        is_removed = current_version >= removed_version
        will_be = '' if is_removed else "will be "
        label = f"{self._deprecated_label}, {will_be}{self._removed_label}"
        label = sphinx_gettext(label)
        text = label.format(deprecated=deprecated_arg, removed=removed_arg)

        # Parse inline and content body text
        if content_arg:
            inodes, messages = self.state.inline_text(
                content_arg, self.lineno + 1)
            para = nodes.paragraph(
                content_arg, "", *inodes, translatable=False)
            self.set_source_info(para)
            node.append(para)
        else:
            messages = []
        if self.content:
            self.state.nested_parse(self.content, self.content_offset, node)

        # Transform content to a single paragraph with inline nodes
        classes = ["versionmodified", "deprecated", "removed"]
        label_text = f"{text}: " if len(node) > 0 else f"{text}."
        label_node = nodes.inline("", label_text, classes=classes)
        label_para = nodes.paragraph("", "", label_node, translatable=False)
        if len(node) > 0 and isinstance(node[0], nodes.paragraph):
            # If the contents start with a paragraph, make it translatable
            if node[0].rawsource:
                content = nodes.inline(node[0].rawsource, translatable=True)
                content.source = node[0].source
                content.line = node[0].line
                content += node[0].children
                node[0].replace_self(
                    nodes.paragraph("", "", content, translatable=False))
            node[0].insert(0, label_node)
        elif len(node) > 0:
            node.insert(0, label_para)
        else:
            node.append(label_para)

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
