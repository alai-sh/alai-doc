# Copyright: (c) 2026, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""Ansible's documentation markup, parsed by alai-core (``alai_core.markup``), as the pieces the page and the viewer
show, and the sentences and lists they're written in."""

from __future__ import annotations

import re

Segment = tuple[str, "str | None", "str | None"]
"""A piece of a description: its text, its kind, and what it refers to. The kind is alai-core's for markup (``code``,
``option_name``…), a style of the page's own (``dim``), or None for plain text. What it refers to is the URL for
``link`` and ``url``, the plugin for ``module`` and ``plugin`` (``fqcn#type`` for ``plugin``), and for
``option_name`` and ``return_value`` the option or return value as written, plugin and entry point included, without
``=value``."""

_MARKUP = frozenset(
    (
        "bold",
        "italic",
        "code",
        "module",
        "plugin",
        "url",
        "link",
        "rst_ref",
        "env_var",
        "option_value",
        "option_name",
        "return_value",
    )
)
"""alai-core's kinds that are markup, rather than plain text, an error's text or a horizontal line."""


def markup(text: str) -> list[Segment]:
    """A description split at Ansible's documentation markup, each piece the text it shows: ``C()``, ``B()`` and
    ``I()`` their text, ``M(fqcn)`` and ``P(fqcn#type)`` the name, ``L(text,url)`` and ``R(text,anchor)`` the text,
    ``U(url)`` the URL, ``O()`` and ``RV()`` the option or return value (and ``=value``) without the plugin, entry
    point or ``ignore:`` before it, and ``V()`` and ``E()`` their value. ``HORIZONTALLINE`` is dropped, and markup
    that isn't well formed is left as written."""
    from alai_core.markup import parse

    out: list[Segment] = []
    # As a role's, as O(entrypoint:name) is an error anywhere else.
    for part in parse(text, role=True):
        kind = part.kind
        if kind not in _MARKUP:
            # text, or an error's markup as written. horizontal_line has no text.
            if part.text:
                out.append((part.text, None, None))
        elif kind in ("module", "plugin"):
            fqcn = part.fqcn or ""
            out.append((fqcn, kind, fqcn if kind == "module" else f"{fqcn}#{part.plugin_type}"))
        elif kind in ("url", "link"):
            url = part.url or ""
            shown = url if kind == "url" else part.text or url
            out.append((shown, kind, url if url.startswith(("http://", "https://")) else None))
        elif kind in ("option_name", "return_value"):
            name = part.name or ""
            shown = name + (f"={part.value}" if part.value is not None else "")
            out.append(
                (shown, kind, None if part.ignore else _reference(part.fqcn, part.plugin_type, part.entrypoint, name))
            )
        else:
            shown = part.name if kind == "env_var" else part.value if kind == "option_value" else part.text
            out.append((shown or "", kind, None))
    return out


def _reference(fqcn: str | None, plugin_type: str | None, entrypoint: str | None, name: str) -> str:
    """An ``O()`` or ``RV()`` as the viewer goes to it: ``name``, ``entrypoint:name`` or ``fqcn#type:name``."""
    where = f"{fqcn}#{plugin_type}:" if fqcn else ""
    return f"{where}{entrypoint}:{name}" if entrypoint else f"{where}{name}"


def as_sentence(segments: list[Segment]) -> list[Segment]:
    """A description's pieces as a sentence: the first capitalised if it's plain text, a full stop added."""
    segments = [s for s in segments if s[0]]
    if segments:
        segments[0] = (segments[0][0].lstrip(), *segments[0][1:])
        segments[-1] = (segments[-1][0].rstrip(), *segments[-1][1:])
    segments = [s for s in segments if s[0]]
    if not segments:
        return segments
    first, kind, url = segments[0]
    if kind is None:
        segments[0] = (_capitalise(first), kind, url)
    if segments[-1][0][-1] not in ".!?":
        segments.append((".", None, None))
    return segments


def _capitalise(text: str) -> str:
    """``text`` with its first letter upper case, unless its first word is a name rather than a word: anything but
    lowercase letters (``oVirt``, ``floating_ips``, ``tasks/main.yml``)."""
    first = text.split()[0].rstrip(",:;") if text.split() else ""
    if re.fullmatch(r"[a-z]+(?:[-/][a-z]+)*", first):
        return text[0].upper() + text[1:]
    return text


def and_list(items: list[str]) -> str:
    """``a``, ``a and b``, ``a, b and c``."""
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def or_list(items: list[str]) -> str:
    """``'a'``, ``'a' or 'b'``, ``'a', 'b' or 'c'``."""
    quoted = [f"'{i}'" for i in items]
    return quoted[0] if len(quoted) == 1 else f"{', '.join(quoted[:-1])} or {quoted[-1]}"
