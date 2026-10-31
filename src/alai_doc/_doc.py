# Copyright: (c) 2026, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""alai-doc: a plugin's full documentation, from its collection wherever alai finds it (``_alai``), in the viewer on a
terminal (``_doc_view``) and as Markdown anywhere else.

The Markdown goes to stdout, unwrapped, for whatever reads it to wrap or render. Everything else goes to stderr.
"""

from __future__ import annotations

import os
import re
import sys
import typing as _t

from ._alai import BUILTIN, Alai
from ._common import EXIT_NOT_FOUND, Error
from ._doc_model import (
    NBSP,
    SOURCE_ORDER,
    Loaded,
    NotFound,
    as_list,
    as_map,
    as_text,
    bare,
    deprecation_text,
    entries_under,
    entry_points,
    load,
    nested_entries,
    origin_text,
    paragraphs_of,
    readme,
    rich_text,
    split_arguments,
    summary,
    type_name,
    unnamed_return,
    usage,
    yaml_value,
)
from ._markup import Segment, and_list, as_sentence, markup
from ._output import home_path, warn

if _t.TYPE_CHECKING:
    from alai_core import extract as ape


def doc(alai: Alai, name: str, *, types: list[str], output_format: str | None = None) -> int:
    """Show plugin ``name``'s docs: in ``output_format``, ``markdown``, or with none, in the viewer on a terminal and
    as Markdown otherwise."""
    parts = name.split(".")
    if not all(parts) or len(parts) == 2:
        raise Error(
            f"'{name}' isn't a plugin's name, such as ansible.builtin.copy or copy; alai find searches by part of one"
        )
    # A full-screen viewer needs a terminal that can draw one.
    viewer = output_format is None and sys.stdout.isatty() and sys.stdin.isatty() and os.environ.get("TERM") != "dumb"
    try:
        loaded = load(alai, name, types)
    except NotFound as e:
        warn(str(e))
        return EXIT_NOT_FOUND
    if viewer:
        from ._doc_view import view

        return view(alai, loaded)

    sys.stdout.write(markdown(loaded, loaded.located.latest))
    sys.stdout.flush()
    return 0


def markdown(loaded: Loaded, latest: str | None) -> str:
    """The docs of each plugin ``loaded`` has, as Markdown: each option a list item, its suboptions a list in it, and
    each paragraph a line of its own, unwrapped."""
    out: list[str] = []
    for plugin, docs in loaded.plugins:
        out += _plugin(loaded, plugin, docs, latest)
    return "\n".join(out).rstrip("\n") + "\n"


def _plugin(loaded: Loaded, plugin: ape.Plugin, docs: ape.PluginDocs | None, latest: str | None) -> list[str]:
    collection = loaded.collection
    parts = entry_points(plugin, docs, loaded.located) if docs is not None else []
    # A role's header is its main entry point's, and a role without one has only its name.
    documentation = as_map(parts[0][1].documentation) if parts and parts[0][0] in (None, "main") else {}
    short = as_text(documentation.get("short_description")) or plugin.short_description
    out = [f"# {_escape(f'{collection}.{plugin.name}')}", ""]
    if short:
        out += [_inline(as_sentence(markup(short))), ""]

    origin = origin_text(loaded.located)
    if latest:
        origin = f"{origin.rstrip('.')}; {latest} is the latest."
    kind = plugin.type
    if plugin.type == "callback" and (callback := as_text(documentation.get("type"))):
        kind = f"{callback} callback"
    facts = [f"Type: {kind}", f"Version: {_escape(origin)}"]
    if loaded.redirects:
        facts.append(f"Redirected from: {', '.join(f'`{r}`' for r in loaded.redirects)}")
    if authors := paragraphs_of(documentation.get("author")):
        facts.append(f"Authors: {_escape(and_list(authors))}")
    if (added := documentation.get("version_added")) and as_text(added) != "historical":
        facts.append(f"Added in: {'' if collection == BUILTIN else collection + ' '}{_escape(as_text(added))}")
    if deprecated := deprecation_text(documentation.get("deprecated")):
        facts.append(_deprecated(deprecated))
    if docs is not None and (missing := sorted({*docs.fragments, *docs.return_fragments})):
        what = "fragment" if len(missing) == 1 else "fragments"
        verb = "adds" if len(missing) == 1 else "add"
        names = and_list([f"`{m}`" for m in missing])
        facts.append(
            f"Not shown: what the doc {what} {names} {verb}, which couldn't be found or read without running code"
        )
    found = readme(loaded)
    if found is not None and docs is not None:
        facts.append(f"README: {_escape(home_path(str(found[0])))}")
    out += [f"- {fact}" for fact in facts] + [""]
    if docs is None:
        # A role without argument specs has its README, as Markdown already.
        return [*out, found[1].strip("\n") if found is not None else "No documentation.", ""]
    # Any other entry point is under its name, as include_role needs it.
    if len(parts) == 1 and parts[0][0] in (None, "main"):
        return out + _body(f"{collection}.{plugin.name}", plugin.type, *parts[0], short, "##")
    # Without links, as each renderer makes a heading's anchor its own way.
    out += ["## Entry points", ""]
    for entry, part, usable in parts:
        said = summary(as_map(part.documentation))
        line = f"- `{entry}`" + (f" · {_inline(as_sentence(markup(said)))}" if said else "")
        out.append(line + ("" if usable else " (documentation only)"))
    out.append("")
    for entry, part, usable in parts:
        part_short = as_text(as_map(part.documentation).get("short_description"))
        out += [f"## Entry point `{entry}`" if usable else f"## `{entry}`, documentation only", ""]
        if part_short:
            out += [_inline(as_sentence(markup(part_short))), ""]
        out += _body(f"{collection}.{plugin.name}", plugin.type, entry, part, usable, part_short, "###")
    return out


def _body(
    fqcn: str,
    plugin_type: str,
    entry: str | None,
    docs: ape.PluginDocs,
    usable: bool,
    short: str | None,
    level: str,
) -> list[str]:
    """What's under a plugin's header, or a role entry point's, its sections' headings at ``level``, with no usage for
    one that can't be used."""
    documentation = as_map(docs.documentation)
    out = _attributes(documentation.get("attributes"))
    paragraphs = paragraphs_of(documentation.get("description"))
    # Many plugins repeat the short description as the whole description.
    if [bare(p) for p in paragraphs] != [bare(short or "")]:
        for paragraph in paragraphs:
            out += [_paragraph(paragraph), ""]

    snippets = usage(fqcn, plugin_type, documentation, entry) if usable else []
    if snippets:
        out += [f"{level} Usage", ""]
        for caption, language, code in snippets:
            out += [f"{_escape(caption)}:", "", f"```{language}", code, "```", ""]
    inputs, positional, options = split_arguments(plugin_type, documentation)
    for title, entries in (("Input", inputs), ("Positional", positional), ("Options", options)):
        if entries:
            out += [f"{level} {title}", "", *_entries(entries, 0, None, returns=False)]
    for title, key in (("Notes", "notes"), ("Requirements", "requirements")):
        if items := paragraphs_of(documentation.get(key)):
            out += [f"{level} {title}", "", *[f"- {_paragraph(i)}" for i in items], ""]
    if seealso := _seealso(documentation.get("seealso")):
        out += [f"{level} See also", "", *seealso, ""]
    if docs.examples and docs.examples.strip():
        code = "\n".join(line.rstrip() for line in docs.examples.strip("\n").splitlines())
        fence = "```" if "```" not in code else "~~~~"
        out += [f"{level} Examples", "", f"{fence}yaml", code, fence, ""]
    returns = entries_under({"returns": docs.returns}, "returns")
    if (value := unnamed_return(plugin_type, returns)) is not None:
        # The type, then what it is, as the first paragraph's start.
        described = paragraphs_of(value.get("description")) or [""]
        first = f"`{type_name(value)}`" + (f" · {_paragraph(described[0])}" if described[0] else "")
        out += [f"{level} Returns", "", first, ""]
        for paragraph in described[1:]:
            out += [_paragraph(paragraph), ""]
        out += _returned(value)
    elif returns:
        out += [f"{level} Return values", "", *_entries(returns, 0, None, returns=True)]
    return out


def _attributes(value: object) -> list[str]:
    """The attributes as a table: each one's support, or for ``platform`` and the like their values, and any
    details."""
    attributes = entries_under({"attributes": value}, "attributes")
    if not attributes:
        return []
    with_details = any(paragraphs_of(a.get("details")) for a in attributes.values())
    rows = (
        ["| Attribute | Support | Details |", "|---|---|---|"]
        if with_details
        else ["| Attribute | Support |", "|---|---|"]
    )
    for name, attribute in attributes.items():
        support = as_text(attribute.get("support"))
        for key in ("platforms", "membership"):
            if (values := attribute.get(key)) is not None:
                support = (
                    ", ".join(as_text(v) for v in as_list(values)) if isinstance(values, list) else as_text(values)
                )
        details = " ".join(paragraphs_of(attribute.get("details")))
        cells = [_escape(name), _escape(support), *([_inline(rich_text(details))] if with_details else [])]
        rows.append("| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |")
    return [*rows, ""]


def _entries(entries: dict[str, dict[str, object]], depth: int, parent: str | None, *, returns: bool) -> list[str]:
    """Options or return values as a list, each one's details as paragraphs indented under it, and its children as
    a list inside it, a level further in."""
    out: list[str] = []
    indent = "  " * depth
    for name, entry in entries.items():
        head = [f"**{_escape(name)}**", f"`{type_name(entry)}`"]
        if returns:
            if returned := as_text(entry.get("returned")):
                head.append(f"returned {_inline(rich_text(returned))}")
        else:
            if entry.get("required") is True:
                head.append("required" if parent is None else f"required when **{_escape(parent)}** is given")
            if "default" in entry and entry.get("default") is not None:
                head.append(f"default {_code(yaml_value(entry['default']))}")
        out += [f"{indent}- {' · '.join(head)}", ""]
        body = indent + "  "
        for paragraph in paragraphs_of(entry.get("description")):
            out += [body + _paragraph(paragraph), ""]
        lines = _returned(entry) if returns else _option(entry)
        out += [line if not line else body + line for line in lines]
        out += _entries(nested_entries(entry, returns=returns), depth + 1, name, returns=returns)
    return out


def _option(option: dict[str, object]) -> list[str]:
    """What's known of an option besides its description: choices, aliases, version added, deprecation and, for
    plugins, where it can be set."""
    out: list[str] = []
    default = option.get("default")
    mark = yaml_value(default) if "default" in option and default is not None else None
    choices = option.get("choices")
    if isinstance(choices, dict):
        out += ["Choices:", ""]
        for value, description in as_map(choices).items():
            shown = _code(yaml_value(value)) + (" (default)" if yaml_value(value) == mark else "")
            text = " ".join(paragraphs_of(description))
            out.append(f"- {shown}" + (f": {_paragraph(text)}" if text else ""))
        out.append("")
    elif values := as_list(choices):
        shown = [_code(yaml_value(v)) + (" (default)" if yaml_value(v) == mark else "") for v in values]
        out += [f"Choices: {', '.join(shown)}.", ""]
    extra: list[str] = []
    if aliases := as_list(option.get("aliases")):
        extra.append("Aliases: " + ", ".join(f"`{as_text(a)}`" for a in aliases) + ".")
    added = option.get("version_added")
    if added and as_text(added) != "historical":
        extra.append(f"Added in {_escape(as_text(added))}.")
    if extra:
        out += [" ".join(extra), ""]
    if deprecated := deprecation_text(option.get("deprecated")):
        out += [_deprecated(deprecated), ""]
    for kind in SOURCE_ORDER:
        entries = [as_map(e) for e in as_list(option.get(kind)) if isinstance(e, dict)]
        if not entries:
            continue
        # Highest precedence first: within a kind, the last one listed wins.
        shown = []
        for entry in reversed(entries):
            if kind == "ini":
                where = f"[{as_text(entry.get('section') or 'defaults')}] {as_text(entry.get('key'))}"
            else:
                where = as_text(entry.get("name"))
            note = ""
            if isinstance(gone := entry.get("deprecated"), dict):
                removed = as_text(as_map(gone).get("removed_in") or as_map(gone).get("version"))
                note = " (deprecated" + (f", removed in {removed}" if removed else "") + ")"
            shown.append(f"`{where}`{note}")
        out += [f"{kind.removesuffix('s')}: {', '.join(shown)}", ""]
    return out


def _returned(value: dict[str, object]) -> list[str]:
    if value.get("sample") is None:
        return []
    return [f"Sample: {_code(yaml_value(value['sample']))}", ""]


def _seealso(value: object) -> list[str]:
    out: list[str] = []
    for item in (as_map(i) for i in as_list(value) if isinstance(i, dict)):
        if "module" in item:
            text = f"`{as_text(item['module'])}` module"
        elif "plugin" in item:
            text = f"`{as_text(item['plugin'])}` {_escape(as_text(item.get('plugin_type')))}"
        elif "link" in item:
            text = f"[{_escape(as_text(item.get('name') or item['link']))}]({as_text(item['link'])})"
        elif "ref" in item:
            text = _escape(as_text(item.get("name") or item["ref"]))
        else:
            continue
        if description := paragraphs_of(item.get("description")):
            text += ": " + _paragraph(" ".join(description))
        out.append(f"- {text}")
    return out


def _deprecated(text: str) -> str:
    """A deprecation, which may have markup in its reason or alternative, with its first word bold."""
    line = _inline(rich_text(text))
    return "**Deprecated**" + line.removeprefix("Deprecated")


def _paragraph(text: str) -> str:
    """A description's paragraph as one line of Markdown."""
    line = _inline(rich_text(text))
    # Something at its start that Markdown would read as a heading, list or quote, isn't: CommonMark escapes an ordered
    # list's number by the punctuation after it.
    line = re.sub(r"^(\s*)([#>+-])", r"\1\\\2", line)
    return re.sub(r"^(\s*\d+)([.)])", r"\1\\\2", line)


def _inline(segments: list[Segment]) -> str:
    """Ansible's markup as Markdown's: code for ``C()``, ``V()`` and ``E()``, bold for ``B()`` and options, italics for
    ``I()``, links for ``L()`` and ``U()``, and plugins as code."""
    out: list[str] = []
    for piece, kind, target in segments:
        text = " ".join(piece.replace(NBSP, " ").split("\n"))
        if kind in ("code", "option_value", "env_var", "module", "plugin"):
            out.append(_code(text))
        elif kind in ("bold", "option_name", "return_value"):
            out.append(f"**{_escape(text)}**")
        elif kind == "italic":
            out.append(f"*{_escape(text)}*")
        elif kind in ("link", "url") and target:
            out.append(f"[{_escape(text)}]({target})" if kind == "link" else f"<{target}>")
        else:
            out.append(_escape(text))
    return "".join(out)


_SPECIAL_RE = re.compile(r"[\\`*\[]|(?<!\w)_|_(?!\w)|<(?=[A-Za-z/!?])")
"""What Markdown could read as markup in plain text: backslashes, backticks, ``*``, ``[``, an ``_`` at a word's edge
(CommonMark never reads one inside a word as emphasis), and a ``<`` that could start a tag or autolink. Only those, so
the raw text stays readable."""


def _escape(text: str) -> str:
    """Text with what Markdown would read as markup escaped, so ``*_info`` isn't emphasis."""
    return _SPECIAL_RE.sub(lambda m: "\\" + m.group(0), text)


def _code(text: str) -> str:
    """A code span, with a longer fence when the text has a backtick in it."""
    if not text:
        return '`""`'
    fence = "``" if "`" in text else "`"
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{pad}{text}{pad}{fence}"
