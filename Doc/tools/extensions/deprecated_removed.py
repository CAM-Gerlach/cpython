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

    _deprecated_label = "Deprecated since version {deprecated}, will be removed in version {removed}"
    _removed_label = "Deprecated since version {deprecated}, removed in version {removed}"

    def run(self):
        # Create and set up target doctree node
        node = addnodes.versionmodified()
        node.document = self.state.document
        self.set_source_info(node)
        node["type"] = self.name
        node["version"] = tuple(self.arguments[:2])

        # Parse versions and generate label from them
        current_version = tuple(int(e) for e in self.config.version.split("."))
        removed_version = tuple(int(e) for e in self.arguments[1].split("."))
        if current_version < removed_version:
            label = self._deprecated_label
        else:
            label = self._removed_label
        label = sphinx_gettext(label)
        text = label.format(
            deprecated=self.arguments[0], removed=self.arguments[1])

        # Parse inline and content body text
        if len(self.arguments) == 3:
            inodes, messages = self.state.inline_text(
                self.arguments[2], self.lineno + 1)
            para = nodes.paragraph(
                self.arguments[2], "", *inodes, translatable=False)
            self.set_source_info(para)
            node.append(para)
        else:
            messages = []
        if self.content:
            self.state.nested_parse(self.content, self.content_offset, node)

        # Transform content to a single paragraph with inline nodes
        classes = ["versionmodified", "deprecated", "removed"]
        if len(node) > 0 and isinstance(node[0], nodes.paragraph):
            # If the contents start with a paragraph, make it translatable
            if node[0].rawsource:
                content = nodes.inline(node[0].rawsource, translatable=True)
                content.source = node[0].source
                content.line = node[0].line
                content += node[0].children
                node[0].replace_self(
                    nodes.paragraph("", "", content, translatable=False))
            node[0].insert(
                0, nodes.inline("", f"{text}: ", classes=classes))
        elif len(node) > 0:
            para = nodes.paragraph(
                "",
                "",
                nodes.inline("", f"{text}: ", classes=classes),
                translatable=False,
            )
            node.insert(0, para)
        else:
            para = nodes.paragraph(
                "",
                "",
                nodes.inline("", f"{text}.", classes=classes),
                translatable=False,
            )
            node.append(para)

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
