# Copyright: (c) 2026, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""A plugin's documentation for alai-doc: finding the plugin in its collection, following redirects, applying its
doc fragments, and reading the YAML it's written in, for both the printed page (``_doc``) and the viewer
(``_doc_view``).
"""

from __future__ import annotations

import collections.abc as _c
import difflib
import json
import re
import typing as _t
from pathlib import Path

from ._alai import BUILTIN, DOWNLOADED, EDA_BUILTIN, INSTALLED, LEGACY, LOCKED, PROJECT, Alai, Located
from ._common import Error, Record
from ._markup import Segment, markup, or_list
from ._output import debug, home_path

if _t.TYPE_CHECKING:
    from alai_core import extract as ape

_UNDOCUMENTED = frozenset(("action", "terminal"))
"""The types extraction finds that ansible-doc has no ``-t`` for: an action plugin backs a module of the same name, and
a terminal plugin is used through a cliconf one."""
_MAX_REDIRECTS = 10
"""How many redirects are followed before giving up; the plugin index has none longer than two (2026-10-21)."""
SUPPORT_MARKS = {"full": "✓", "partial": "◐", "none": "✗", "N/A": "n/a"}
"""How an attribute's ``support`` is shown in its badge."""
NBSP = "\u00a0"
"""Joins pieces of a line that wrapping mustn't split, such as a choice and its ``(default)``; shown as a space."""
SOURCE_ORDER = ("vars", "keyword", "cli", "env", "ini")
"""Where a plugin option can be set, highest precedence first, as ansible-core's
``ConfigManager.get_config_value_and_origin`` reads them, after a task's own arguments."""


class NotFound(Error):
    """The plugin couldn't be found: no index has its collection, the collection doesn't have it, or it was removed."""


class Loaded(Record):
    """A plugin's docs, ready to show, with its doc fragments applied."""

    __slots__ = ("collection", "located", "others", "plugins", "redirects")

    def __init__(
        self,
        collection: str,
        plugins: list[tuple[ape.Plugin, ape.PluginDocs | None]],
        located: Located,
        redirects: list[str],
        others: list[tuple[str, str]] | None = None,
    ) -> None:
        self.collection = collection
        self.plugins = plugins
        """The plugin, as a one-item list."""
        self.located = located
        self.redirects = redirects
        """The names asked for that redirected here, in order."""
        self.others = others or []
        """The other types of plugin the name asked for is, and the name for each, for the viewer to link to."""


class _Hop(Record):
    """A collection on the way to a plugin: where its files are, and what was read from them."""

    __slots__ = ("extracted", "legacy", "located", "name")

    def __init__(self, name: str, located: Located, extracted: ape.Collection, *, legacy: bool = False) -> None:
        self.name = name
        self.located = located
        self.extracted = extracted
        self.legacy = legacy
        """Reached as ``ansible.legacy``, which finds a plugin's file before reading its routing; a FQCN reads routing
        first."""


def load(alai: Alai, name: str, types: _c.Sequence[str] = ()) -> Loaded:
    """The plugin ``name``, following redirects, with its doc fragments applied. ``name`` is a FQCN, or a short name,
    found as a play would find it: in the collection project's own collection, if there is one, then as
    ``ansible.legacy``, which is ansible-core's own plugins and their routing (``win_copy`` leads to
    ``ansible.windows.win_copy``). A name more than one type of plugin has needs ``types`` to say which. Raises
    NotFound for one that isn't there, and Error for one alai can't show."""
    parts = name.split(".")
    short = parts[-1] if len(parts) == 1 else ".".join(parts[2:])
    if len(parts) == 1:
        # As ansible-core's CollectionSearch: a playbook's or role's own collection first, then ansible.legacy.
        own = alai.project_collection()
        search = [*([own] if own else []), LEGACY]
    else:
        search = [".".join(parts[:2])]

    found: dict[str, tuple[_Hop, str]] = {}
    last: _Hop | None = None
    for candidate in search:
        collection = BUILTIN if candidate == LEGACY else candidate
        if len(parts) > 1 and not alai.has_version(collection):
            # Before downloading a collection, whether it has the plugin at all, and of which types.
            _check_index(alai, name, types)
        located = alai.locate(collection)
        if located is None:
            if len(search) == 1:
                raise NotFound(f"no index has the collection {collection}")
            continue
        last = _Hop(collection, located, alai.read(located), legacy=candidate == LEGACY)
        # Each type from the first collection with that name, as ansible-core looks one type up at a time.
        for kind, description in _types_named(last.extracted, short).items():
            found.setdefault(kind, (last, description))

    asked = name if len(parts) > 1 else short
    chosen = {k: v for k, v in found.items() if not types or k in types}
    if not chosen:
        if len(parts) > 1 and last is not None:
            raise NotFound(_not_found(asked, last, list(types)))
        # A short name is only ansible-core's, or the project's: anything else is found by its full name.
        kind = f" of type {', '.join(types)}" if types else ""
        searched = " or ".join(BUILTIN if c == LEGACY else c for c in search)
        if names := _suggestions(alai, asked, types):
            raise NotFound(f"{searched} has no plugin {asked}{kind}; did you mean {or_list(names)}?")
        raise NotFound(f"{searched} has no plugin {asked}{kind}; alai find {asked} searches every collection for one")
    if len(chosen) > 1:
        raise Error(_conflict(asked, {k: (h.name, d) for k, (h, d) in chosen.items()}))
    [(kind, (hop, _))] = chosen.items()
    others = [(k, f"{h.name}.{short}") for k, (h, _) in found.items() if k != kind]
    return _follow(alai, hop, short, kind, others)


def _check_index(alai: Alai, name: str, types: _c.Sequence[str]) -> None:
    """Fail as ``load`` would, without downloading the collection: if no index's plugin index has ``name``, or none
    of ``types``, or more than one type and no ``types`` to choose. Nothing, if
    there's no plugin index to tell. Only to check a name before downloading, as what a page shows comes from the
    collection itself."""
    lines = alai.find(name, exact=True)
    if lines is None:
        return
    found: dict[str, tuple[str, str]] = {}
    for line in lines:
        if line.get("fqcn") != name:
            continue
        redirect = as_map(line.get("routing")).get("redirect")
        description = line.get("short_description") or (f"redirects to {redirect}" if isinstance(redirect, str) else "")
        found[line["type"]] = (line["collection"], description)
    chosen = {k: v for k, v in found.items() if not types or k in types}
    kind = f" of type {', '.join(types)}" if types else ""
    if not chosen:
        collection, short = ".".join(name.split(".")[:2]), ".".join(name.split(".")[2:])
        names = {p["name"] for p in alai.find(f"{collection}.*", types=types) or ()}
        if not names and not types:
            raise NotFound(f"no index has the collection {collection}")
        # Close names in the same collection, as a mistyped name usually is.
        close = [f"{collection}.{n}" for n in difflib.get_close_matches(short, sorted(names), n=3)]
        also = f"; did you mean {or_list(close)}?" if close else ""
        raise NotFound(f"no index has a plugin {name}{kind}{also}")
    if len(chosen) > 1:
        raise Error(_conflict(name, chosen))


def _suggestions(alai: Alai, short: str, types: _c.Sequence[str], most: int = 3) -> list[str]:
    """The likeliest plugins of a short name, ranked as ``alai find`` ranks them, leaving out removed ones and those
    whose redirects don't lead to a plugin: what to suggest when a short name isn't ansible-core's or the project's."""
    lines = alai.find(short, exact=True, types=types) or []
    by_name = {(p["type"], p["fqcn"]): p for p in lines}
    # Not ansible.builtin's, which it would have found.
    names = [
        line["fqcn"]
        for line in lines
        if line.get("matched") and line["collection"] != BUILTIN and _usable(line, by_name)
    ]
    return list(dict.fromkeys(names))[:most]


def _usable(line: dict[str, _t.Any], by_name: dict[tuple[str, str], dict[str, _t.Any]]) -> bool:
    """Whether a plugin index line, following its redirects through ``by_name``, the lines ``alai find`` gave with
    it, ends at a plugin that isn't removed."""
    for _ in range(_MAX_REDIRECTS):
        routing = as_map(line.get("routing"))
        if routing.get("tombstone") is not None:
            return False
        redirect = routing.get("redirect")
        if not isinstance(redirect, str):
            return True
        target = by_name.get(
            (line["type"], BUILTIN + redirect[len(LEGACY) :] if redirect.startswith(LEGACY + ".") else redirect)
        )
        if target is None:
            return False
        line = target
    return False


def _types_named(extracted: ape.Collection, short: str) -> dict[str, str]:
    """The types of plugin or routing ``short`` is in a collection, each with what it is: its short description, or
    where it redirects."""
    types: dict[str, str] = {}
    for plugin in extracted.plugins:
        if plugin.name == short and plugin.type not in _UNDOCUMENTED:
            types[plugin.type] = plugin.short_description or ""
    for routing in extracted.routing:
        if routing.name == short and routing.type not in types and routing.type not in _UNDOCUMENTED:
            redirect = routing.entry.get("redirect")
            types[routing.type] = f"redirects to {redirect}" if isinstance(redirect, str) else ""
    return types


def _conflict(asked: str, found: dict[str, tuple[str, str]]) -> str:
    """The error for a name more than one type of plugin has: each, by type, with the collection it's in and what it
    is, and the -t that picks it."""
    width = max(len(kind) for kind in found)
    lines = [f"{asked} is more than one type of plugin, so say which with -t:"]
    for kind, (collection, description) in sorted(found.items(), key=lambda i: (i[0] != "module", i[0])):
        line = f"  alai-doc {asked} -t {kind.ljust(width)}"
        name = f"{collection}.{asked.rsplit('.', 1)[-1]}" if "." not in asked else ""
        if name and name != asked:
            line += f"  ({name})"
        lines.append((line + (f"  {description}" if description else "")).rstrip())
    return "\n".join(lines)


def _follow(alai: Alai, hop: _Hop, short: str, kind: str, others: list[tuple[str, str]]) -> Loaded:
    """Plugin ``short`` of type ``kind`` from ``hop``, following its routing as ansible-core's ``PluginLoader`` does:
    a redirect to another FQCN, a tombstone failing it, and routing read before the plugin's file, except as
    ``ansible.legacy``, which finds the file first."""
    from alai_core import extract as ape

    seen: list[str] = []
    while True:
        fqcn = f"{hop.name}.{short}"
        plugin = next((p for p in hop.extracted.plugins if p.name == short and p.type == kind), None)
        entries = (r.entry for r in hop.extracted.routing if r.name == short and r.type == kind)
        routing = _t.cast("_c.Mapping[str, object]", next(entries, {}))
        if plugin is not None and (hop.legacy or (not routing.get("redirect") and not routing.get("tombstone"))):
            break
        if tombstone := routing.get("tombstone"):
            text = as_text(as_map(tombstone).get("warning_text")).strip()
            raise NotFound(f"{fqcn} was removed" + (f": {text}" if text else ""))
        redirect = routing.get("redirect")
        if not isinstance(redirect, str) or redirect.count(".") < 2:
            raise NotFound(_not_found(fqcn, hop, [kind]))
        seen.append(fqcn if not hop.legacy else short)
        if redirect in seen or len(seen) > _MAX_REDIRECTS:
            raise Error(f"{seen[0]} redirects in a loop: {' → '.join([*seen, redirect])}")
        parts = redirect.split(".")
        collection = BUILTIN if ".".join(parts[:2]) == LEGACY else ".".join(parts[:2])
        if not alai.has_version(collection) and alai.find(redirect, exact=True, types=(kind,)) == []:
            raise NotFound(f"{seen[-1]} redirects to {redirect}, which no index's plugin index has")
        located = alai.locate(collection)
        if located is None:
            raise NotFound(f"{seen[-1]} redirects to {redirect}, and no index has the collection {collection}")
        hop = _Hop(collection, located, alai.read(located), legacy=".".join(parts[:2]) == LEGACY)
        short = ".".join(parts[2:])

    lookup = ape.fragment_lookup(_fragment_sources(alai, hop.extracted, [plugin]))
    return Loaded(hop.name, [(plugin, _applied(plugin, lookup))], hop.located, seen, others)


def _applied(plugin: ape.Plugin, lookup: ape.FragmentLookup) -> ape.PluginDocs | None:
    """The plugin's docs with every fragment ``lookup`` has applied, labelled with the collection and, for a module,
    shaped as extraction says (``PluginDocs.collection`` and ``module``)."""
    return plugin.docs.apply_fragments(lookup) if plugin.docs is not None else None


def _not_found(asked: str, hop: _Hop, types: list[str]) -> str:
    located = hop.located
    shown = f"{located.name} {located.version}" if located.version else located.name
    kind = f" of type {', '.join(types)}" if types else ""
    names = sorted({p.name for p in hop.extracted.plugins if not types or p.type in types})
    close = difflib.get_close_matches(asked.rsplit(".", 1)[-1], names, n=3)
    prefix = f"{hop.name}." if "." in asked else ""
    also = f"; did you mean {', '.join(repr(prefix + n) for n in close)}?" if close else ""
    return f"{shown} has no plugin {asked}{kind}{also}"


def _fragment_sources(alai: Alai, extracted: ape.Collection, plugins: list[ape.Plugin]) -> list[ape.Collection]:
    """The collections the plugins' doc fragments can come from: their own, ansible.builtin, and any other collection
    they name, found as the plugin's own is: installed, locked, cached, or else downloaded into the cache, as a
    plugin's docs aren't whole without them. One that can't be found, or fetched offline, is left out, and the page
    says what isn't shown."""
    sources = [extracted]
    if not any(p.docs is not None and (p.docs.fragments or p.docs.return_fragments) for p in plugins):
        # Nothing to apply, so no collection to find, as roles and many plugins have none.
        return sources
    own = f"{extracted.namespace}.{extracted.name}"
    wanted = {
        ".".join(f.split(".")[:2])
        for p in plugins
        if p.docs is not None
        for f in (*p.docs.fragments, *p.docs.return_fragments)
        if f.count(".") >= 2
    } - {own, BUILTIN}
    # ansible.builtin's are the ones a short name such as files means.
    names = [*([BUILTIN] if own != BUILTIN else []), *sorted(wanted)]
    alai.prefetch(names)

    def read(name: str) -> ape.Collection | None:
        try:
            located = alai.locate(name)
            return alai.read(located) if located is not None else None
        except Error as e:
            debug(f"doc fragments from {name} aren't shown: {e}")
            return None

    return sources + [c for c in map(read, names) if c is not None]


def as_map(value: object) -> dict[str, object]:
    """A mapping read from YAML, or an empty one for anything else, with its keys as strings."""
    if not isinstance(value, dict):
        return {}
    return {str(k): v for k, v in _t.cast("dict[object, object]", value).items()}


def as_list(value: object) -> list[object]:
    """A list read from YAML, or an empty one for anything else."""
    return list(_t.cast("list[object]", value)) if isinstance(value, list) else []


def as_text(value: object) -> str:
    return value if isinstance(value, str) else json.dumps(value) if value is not None else ""


def paragraphs_of(value: object) -> list[str]:
    """A description, which may be one string or a list of paragraphs."""
    values = as_list(value) if isinstance(value, list) else [value] if value is not None else []
    return [as_text(v) for v in values if as_text(v).strip()]


_TYPE_NAMES = {"string": "str", "boolean": "bool", "integer": "int", "dictionary": "dict"}
"""The long type names plugin options may use (ansible-core's config takes both), shown as modules name them."""


def type_name(option: dict[str, object]) -> str:
    """``type`` and ``elements`` together: ``list`` of ``dict`` is ``list[dict]``."""
    kind = as_text(option.get("type")) or "str"
    kind = _TYPE_NAMES.get(kind, kind)
    elements = as_text(option.get("elements"))
    return f"{kind}[{_TYPE_NAMES.get(elements, elements)}]" if kind == "list" and elements else kind


def entries_under(option: dict[str, object], key: str) -> dict[str, dict[str, object]]:
    """The options, suboptions or return values under ``key``, sorted by name as ansible-doc lists them."""
    return {k: as_map(v) for k, v in sorted(as_map(option.get(key)).items()) if isinstance(v, dict)}


def suboptions_of(option: dict[str, object]) -> dict[str, dict[str, object]]:
    """A module option's ``suboptions``, or a role's ``options``."""
    return entries_under(option, "suboptions") or entries_under(option, "options")


def origin_text(located: Located) -> str:
    """Where the docs came from, for the header."""
    shown = f"{located.name} {located.version}" if located.version else located.name
    if located.name in (BUILTIN, EDA_BUILTIN):
        tool = "ansible-core" if located.name == BUILTIN else "ansible-rulebook"
        fetched = ", downloaded into the cache" if located.origin == DOWNLOADED else ""
        return f"{tool} {located.version}, the latest release{fetched}."
    if located.origin == INSTALLED:
        return f"{shown}, installed at {home_path(located.path)}."
    if located.origin == PROJECT:
        return f"{shown}, the collection project at {home_path(located.path)}."
    if located.origin == LOCKED:
        return f"{shown}, the locked version, from the cache."
    if located.origin == DOWNLOADED:
        return f"{shown}, downloaded into the cache."
    return f"{shown}, from the cache."


def deprecation_text(deprecated: object) -> str | None:
    """A ``deprecated`` entry as a sentence or two, or None if there isn't one."""
    if not isinstance(deprecated, dict):
        return None
    value = as_map(deprecated)
    removed = value.get("removed_in") or value.get("version") or value.get("removed_at_date") or value.get("date")
    parts = ["Deprecated" + (f", to be removed in {as_text(removed)}" if removed else "") + "."]
    why = as_text(value.get("why")).strip()
    alternative = as_text(value.get("alternative") or value.get("alternatives")).strip()
    parts += [*([why] if why else []), *([f"Alternative: {alternative}"] if alternative else [])]
    return " ".join(parts)


def nested_entries(entry: dict[str, object], *, returns: bool) -> dict[str, dict[str, object]]:
    """A return value's ``contains``, or an option's ``suboptions`` (a role's ``options``)."""
    return entries_under(entry, "contains") if returns else suboptions_of(entry)


_RST_CODE_RE = re.compile(r"``(.+?)``")


def rich_text(text: str) -> list[Segment]:
    """``markup``, with reStructuredText's ````code```` as code too, which some descriptions use."""
    out: list[Segment] = []
    for piece, kind, url in markup(text):
        if kind is not None or "``" not in piece:
            out.append((piece, kind, url))
            continue
        at = 0
        for match in _RST_CODE_RE.finditer(piece):
            out += [(piece[at : match.start()], None, None), (match.group(1), "code", None)]
            at = match.end()
        out.append((piece[at:], None, None))
    return [s for s in out if s[0]]


def entry_points(
    plugin: ape.Plugin, docs: ape.PluginDocs, located: Located
) -> list[tuple[str | None, ape.PluginDocs, bool]]:
    """What a page shows: for a role, each entry point's argument spec as docs of its own, ``main`` first and the rest
    as the role lists them, and for anything else its docs, with no entry point. Each says whether it can be used,
    which an entry point can't if its role has no task file for it. Those come last, as they're shared options or
    notes rather than something to run."""
    if plugin.type != "role" or not docs.entry_points:
        return [(None, docs, True)]
    from alai_core import extract as ape

    specs = as_map(docs.entry_points)
    # meta/argument_specs.yml, so tasks is beside meta.
    tasks = Path(located.path, docs.path).parent.parent / "tasks" if docs.path else None

    def usable(name: str) -> bool:
        # As include_role finds tasks_from, with or without an extension. Some roles document things other than
        # task files as entry points, such as __examples__.
        return name == "main" or tasks is None or any(tasks.joinpath(name + e).exists() for e in _TASK_EXTENSIONS)

    parts = [(name, ape.PluginDocs(documentation=as_map(specs[name])), usable(name)) for name in specs]
    return sorted(parts, key=lambda p: (p[0] != "main", not p[2]))


_TASK_EXTENSIONS = ("", ".yml", ".yaml", ".json")
"""What ansible-core's ``Role._load_role_yaml`` tries after a task file's name."""


def readme(loaded: Loaded) -> tuple[Path, str] | None:
    """A role's ``README.md`` and what's in it, which Galaxy shows for a role and alai-core doesn't read: for most
    roles their only docs. None for anything else, or if it can't be read."""
    plugin = loaded.plugins[0][0]
    if plugin.type != "role":
        return None
    path = Path(loaded.located.path, "roles", plugin.name, "README.md")
    try:
        return path, path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def summary(documentation: dict[str, object]) -> str:
    """What a role entry point does, for the list of them: its short description, else its description's first
    paragraph, as a few roles give only that."""
    return as_text(documentation.get("short_description")) or next(
        iter(paragraphs_of(documentation.get("description"))), ""
    )


def bare(text: str) -> str:
    """Text to compare, without case, surrounding space or a full stop."""
    return text.strip().rstrip(".").lower()


def path_segment(name: str, option: dict[str, object]) -> str:
    """An option's name in a path, with ``[]`` when it takes a list of dicts."""
    return f"{name}[]" if option.get("type") == "list" else name


def yaml_value(value: object) -> str:
    """A default, choice or sample as YAML would show it: booleans lowercase, an empty string quoted."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value if value.strip() else json.dumps(value)
    return json.dumps(value)


# What's particular to each type of plugin: how it's used, the input and positional arguments of lookups, filters and
# tests, and the one value they return.

_INPUTS = {"filter": "_input", "test": "_input"}
"""The value a filter or test is given, before the ``|`` or ``is``: not an argument it's called with."""
_LABELS = {"_terms": "terms", "_input": "input"}
_NETWORK_CONNECTIONS = {
    "cliconf": "ansible.netcommon.network_cli",
    "httpapi": "ansible.netcommon.httpapi",
    "netconf": "ansible.netcommon.netconf",
}
"""The connection each network plugin type is used through, with ``ansible_network_os`` naming the plugin."""

Snippet = tuple[str, str, str]
"""One way to use a plugin: what it is (``On a play``), the language (``yaml``, ``jinja``, ``ini`` or ``shell``) and
the code."""


def input_label(name: str) -> str:
    """What an input or positional argument is called on the page: ``terms`` and ``input`` rather than ``_terms`` and
    ``_input``, and others without the ``_`` that marks them as positional (``_regex_match``)."""
    return _LABELS.get(name, name.removeprefix("_") or name)


def split_arguments(
    plugin_type: str, documentation: dict[str, object]
) -> tuple[dict[str, dict[str, object]], dict[str, dict[str, object]], dict[str, dict[str, object]]]:
    """A filter's or test's input; the arguments a lookup, filter or test takes by position, in order; and the options
    it takes by name, each keyed by how it's shown. A lookup's positional arguments are its ``_terms``; a filter's or
    test's are those its ``positional`` names, a list or a comma-separated string. Other types have only options."""
    options = entries_under(documentation, "options")
    if plugin_type not in ("lookup", "filter", "test"):
        return {}, {}, options
    first = _INPUTS.get(plugin_type)
    if plugin_type == "lookup":
        names = ["_terms"]
    else:
        positional = documentation.get("positional")
        if isinstance(positional, str):
            names = [p.strip() for p in positional.split(",")]
        else:
            names = [as_text(p).strip() for p in as_list(positional)]
    names = [n for n in names if n and n != first and n in options]
    inputs = {input_label(first): options[first]} if first in options else {}
    positional = {input_label(n): options[n] for n in names}
    rest = {k: v for k, v in options.items() if k != first and k not in names}
    return inputs, positional, rest


def unnamed_return(plugin_type: str, returns: dict[str, dict[str, object]]) -> dict[str, object] | None:
    """The value a lookup, filter or test returns, when its docs describe one under a ``_`` name (``_raw``, ``_list``
    or ``_value``), rather than return values with names, as a module's are."""
    if plugin_type not in ("lookup", "filter", "test") or len(returns) != 1:
        return None
    name, value = next(iter(returns.items()))
    return value if name.startswith("_") else None


def _placeholder(option: dict[str, object]) -> str:
    """A required argument's value in a usage example: its type, ``<str>``, or ``<list>`` for any list."""
    kind = type_name(option)
    return "<list>" if kind.startswith("list") else f"<{kind}>"


def usage(
    fqcn: str, plugin_type: str, documentation: dict[str, object], entry_point: str | None = None
) -> list[Snippet]:
    """How the plugin is used, each way a short example with its required arguments as placeholders; none for a type
    with no one way to use it. The settings and variables are ansible-core's, from ``config/base.yml``. A role's is
    for its ``entry_point``."""
    inputs, positional, options = split_arguments(plugin_type, documentation)
    required = {n: o for n, o in options.items() if o.get("required") is True}
    yaml_args = [f"{n}: {_placeholder(o)}" for n, o in required.items() if n != "plugin"]
    keywords = [f"{n}={_placeholder(o)}" for n, o in required.items()]
    if plugin_type == "module":
        return [("In a task", "yaml", "\n".join([f"- {fqcn}:", *[f"    {a}" for a in yaml_args]]))]
    if plugin_type == "role":
        tasks_from = [f"    tasks_from: {entry_point}"] if entry_point not in (None, "main") else []
        role_vars = ["  vars:", *[f"    {a}" for a in yaml_args]] if yaml_args else []
        code = "\n".join(["- ansible.builtin.include_role:", f"    name: {fqcn}", *tasks_from, *role_vars])
        return [("In a task", "yaml", code)]
    if plugin_type == "event_source":
        return [("In a rulebook", "yaml", "\n".join(["sources:", f"  - {fqcn}:", *[f"      {a}" for a in yaml_args]]))]
    if plugin_type == "event_filter":
        code = "\n".join(["sources:", "  - <source>:", "    filters:", f"      - {fqcn}:"])
        return [("In a rulebook", "yaml", "\n".join([code, *[f"          {a}" for a in yaml_args]]))]
    if plugin_type == "lookup":
        args = ", ".join([f"<{n}>" for n in positional] + keywords)
        return [("In a template or expression", "jinja", f"{{{{ lookup('{fqcn}'{', ' + args if args else ''}) }}}}")]
    if plugin_type in ("filter", "test"):
        first = f"<{next(iter(inputs))}>" if inputs else "<input>"
        args = ", ".join([f"<{n}>" for n in positional] + keywords)
        call = f"{fqcn}({args})" if args else fqcn
        operator = "|" if plugin_type == "filter" else "is"
        return [("In a template or expression", "jinja", f"{{{{ {first} {operator} {call} }}}}")]
    if plugin_type == "inventory":
        return [("In an inventory source", "yaml", "\n".join([f"plugin: {fqcn}", *yaml_args]))]
    if plugin_type == "callback":
        # A stdout callback is the one that writes the output; any other is enabled alongside it.
        stdout = as_text(documentation.get("type")) == "stdout"
        setting, variable = (
            ("stdout_callback", "STDOUT_CALLBACK") if stdout else ("callbacks_enabled", "CALLBACKS_ENABLED")
        )
        return [
            ("In ansible.cfg", "ini", f"[defaults]\n{setting} = {fqcn}"),
            ("As an environment variable", "shell", f"ANSIBLE_{variable}={fqcn}"),
        ]
    if plugin_type == "connection":
        return [
            ("On a play or task", "yaml", f"connection: {fqcn}"),
            ("As a host or group variable", "yaml", f"ansible_connection: {fqcn}"),
            ("On the command line", "shell", f"ansible-playbook --connection {fqcn} playbook.yml"),
            ("In ansible.cfg", "ini", f"[defaults]\ntransport = {fqcn}"),
        ]
    if plugin_type == "become":
        return [
            ("On a play or task", "yaml", f"become: true\nbecome_method: {fqcn}"),
            ("As a host or group variable", "yaml", f"ansible_become: true\nansible_become_method: {fqcn}"),
            ("On the command line", "shell", f"ansible-playbook --become --become-method {fqcn} playbook.yml"),
            ("In ansible.cfg", "ini", f"[privilege_escalation]\nbecome_method = {fqcn}"),
        ]
    if plugin_type == "cache":
        return [
            ("In ansible.cfg", "ini", f"[defaults]\nfact_caching = {fqcn}"),
            ("As an environment variable", "shell", f"ANSIBLE_CACHE_PLUGIN={fqcn}"),
        ]
    if plugin_type == "strategy":
        return [
            ("On a play", "yaml", f"strategy: {fqcn}"),
            ("In ansible.cfg, for every play", "ini", f"[defaults]\nstrategy = {fqcn}"),
            ("As an environment variable", "shell", f"ANSIBLE_STRATEGY={fqcn}"),
        ]
    if plugin_type == "vars":
        # host_group_vars is enabled by default, and stays so only if it's listed too.
        enabled = fqcn if fqcn == "ansible.builtin.host_group_vars" else f"host_group_vars, {fqcn}"
        return [("In ansible.cfg", "ini", f"[defaults]\nvars_plugins_enabled = {enabled}")]
    if plugin_type == "shell":
        return [("As a host or group variable", "yaml", f"ansible_shell_type: {fqcn}")]
    if plugin_type in _NETWORK_CONNECTIONS:
        connection = _NETWORK_CONNECTIONS[plugin_type]
        code = f"ansible_connection: {connection}\nansible_network_os: {fqcn}"
        return [("As host or group variables", "yaml", code)]
    return []
