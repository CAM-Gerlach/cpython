from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Literal


@dataclass
class MessageText:
    raw: str
    plain: str


@dataclass(order=True)
class Version:
    major: int
    minor: int = 0
    micro: int = 0
    nano: int = 0
    phasen: int = 0
    phase: Literal["dev", "alpha", "beta", "rc", "final", "post"] = "final"
    serial: int = 0


@dataclass
class VersionInfo:
    string: str
    parts: list[str]
    release: list[int]
    asnumeric: list[int] | None
    parsed: Version | None


@dataclass
class XRefInfo:
    id: str
    role: str
    ref: str
    title: str


@dataclass
class SourceInfo:
    docpath: str
    repopath: str
    uri: str
    permalink: str
    line: int | None


@dataclass
class Location:
    raw: str
    kind: Literal["object", "label", "uri", "other"]
    uri: str | None = None
    xref: XRefInfo | None = None
    source: SourceInfo | None = None


@dataclass
class DocObject:
    name: str
    shortname: str
    ids: list[str]
    location: Location
    domain: str
    kind: str
    module: str | None
    classname: str | None
    exists: bool | None = None


@dataclass
class QualifierValue:
    equals: str | None = None


@dataclass
class Qualifiers:
    param: str | None = None
    type: DocObject | None = None
    value: QualifierValue | None = None
    behavior: MessageText | True | False | None = None


@dataclass
class DirectiveArguments:
    values: list[str]
    required: int
    optional: int
    whitespace: bool


@dataclass
class DirectiveOption:
    name: str
    value: str | float | int | bool | None
    native: bool
    spec: str


@dataclass
class DirectiveContent:
    raw: str
    block: str | None
    inline: str | None
    inferred: str | None


@dataclass
class DirectiveInfo:
    name: str
    arguments: DirectiveArguments
    options: dict[str, DirectiveOption]
    content: DirectiveContent


@dataclass
class AnnotationParents:
    physical: DocObject | None = None
    logical: DocObject | None = None


@dataclass
class AnnotationChildren:
    raw: list[str]
    full: list[str]
    physical: list[str]
    logical: list[str]


@dataclass
class AnnotationTarget:
    id: str
    location: Location
    obj: DocObject
    text: MessageText
    message: MessageText | None = None


@dataclass
class DocAnnotation:
    id: str
    kind: str
    location: Location
    directive: DirectiveInfo
    text: MessageText
    message: MessageText | None = None
    description: MessageText | None = None
    domain: str | None = None
    parent: AnnotationParents | None = None
    children: AnnotationChildren | None = None
    targets: dict[str, AnnotationTarget] | None = None
    display: Literal["parent", "target", "both", "none"] | None = None
    qualifiers: Qualifiers | None = None
    granularity: Literal["object", "param", "type", "value"] | None = None
    version: VersionInfo | None = None
    moreinfo: Location | None = None
    attrs: dataclass | None = None


# Deprecation-specific dataclasses

@dataclass
class RemovalInfo:
    raw: str
    state: Literal["tbd", "notplanned", "notscheduled", "scheduled"]
    removed: bool
    scheduled: bool
    planned: bool | None
    version: VersionInfo | None = None


@dataclass
class ReasonInfo:
    names: list[str]
    message: MessageText
    description: MessageText | None


@dataclass
class ReplaceInfo:
    raw: str
    text: str
    granularity: Literal["object", "param", "type", "value"] | None
    message: MessageText
    description: MessageText | None
    obj: DocObject | None
    qualifiers: Qualifiers | None
    uri: str | None
    dropin: bool | None
    external: bool | None
    version: VersionInfo | False | None


@dataclass
class DeprecationAttributes:
    removal: RemovalInfo | None = None
    reason: ReasonInfo | None = None
    replace: ReplaceInfo | False | None = None
    warning: DocObject | False | None = None
    warnversion: VersionInfo | None = None
    error: DocObject | False | None = None
