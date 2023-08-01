"""Sphinx extension adding a deprecated directive listing removal version."""

from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx import addnodes
from sphinx.locale import _ as sphinx_gettext


class DeprecatedRemoved(Directive):
    """Document deprecations and removals using structured data."""

    has_content = True
    required_arguments = 2
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {}

    _deprecated_label = "Deprecated since version {deprecated}, will be removed in version {removed}"
    _removed_label = "Deprecated since version {deprecated}, removed in version {removed}"

    def run(self):
        node = addnodes.versionmodified()
        node.document = self.state.document
        node["type"] = "deprecated-removed"
        version = (self.arguments[0], self.arguments[1])
        node["version"] = version
        env = self.state.document.settings.env
        current_version = tuple(int(e) for e in env.config.version.split("."))
        removed_version = tuple(int(e) for e in self.arguments[1].split("."))
        if current_version < removed_version:
            label = self._deprecated_label
        else:
            label = self._removed_label

        label = sphinx_gettext(label)
        text = label.format(
            deprecated=self.arguments[0], removed=self.arguments[1])
        if len(self.arguments) == 3:
            inodes, messages = self.state.inline_text(
                self.arguments[2], self.lineno + 1)
            para = nodes.paragraph(
                self.arguments[2], "", *inodes, translatable=False)
            node.append(para)
        else:
            messages = []
        if self.content:
            self.state.nested_parse(self.content, self.content_offset, node)
        if len(node):
            if isinstance(node[0], nodes.paragraph) and node[0].rawsource:
                content = nodes.inline(node[0].rawsource, translatable=True)
                content.source = node[0].source
                content.line = node[0].line
                content += node[0].children
                node[0].replace_self(
                    nodes.paragraph("", "", content, translatable=False))
            node[0].insert(
                0, nodes.inline("", "%s: " % text, classes=["versionmodified"]))
        else:
            para = nodes.paragraph(
                "",
                "",
                nodes.inline("", "%s." % text, classes=["versionmodified"]),
                translatable=False,
            )
            node.append(para)
        env = self.state.document.settings.env
        env.get_domain("changeset").note_changeset(node)
        return [node] + messages


def setup(app):
    app.add_directive("deprecated-removed", DeprecatedRemoved)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
