# Copyright: (c) 2026, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""The viewer alai-doc opens on a terminal: a plugin's documentation with its options collapsed to a line each,
links to other plugins and options to follow, and back and forward through what's been read, as a browser has.

Textual is imported only here, so the Markdown output never pays for it.
"""

from __future__ import annotations

import collections.abc as _c
import json
import re
import typing as _t

from textual import events, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.content import Content
from textual.geometry import Region
from textual.style import Style
from textual.widget import Widget
from textual.widgets import Footer, HelpPanel, Input, Static

from . import _output
from ._alai import BUILTIN
from ._common import Error, Record
from ._doc_model import (
    NBSP,
    SOURCE_ORDER,
    SUPPORT_MARKS,
    Loaded,
    as_list,
    as_map,
    as_text,
    bare,
    deprecation_text,
    entries_under,
    input_label,
    load,
    nested_entries,
    origin_text,
    paragraphs_of,
    path_segment,
    rich_text,
    split_arguments,
    type_name,
    unnamed_return,
    usage,
    yaml_value,
)
from ._markup import and_list, as_sentence, markup

if _t.TYPE_CHECKING:
    from alai_core import extract as ape

    from ._alai import Alai
    from ._markup import Segment

_STYLES = {
    "bold": "bold",
    "italic": "italic",
    "code": "cyan",
    "option_value": "cyan",
    "env_var": "cyan",
    "option_name": "bold",
    "return_value": "bold",
    "module": "blue",
    "plugin": "blue",
    "link": "blue",
    "url": "blue",
    "dim": "dim",
    "warn": "yellow",
    "support-full": "green",
    "support-partial": "yellow",
    "support-none": "red",
    "support-N/A": "dim",
}
"""How each piece of a line is styled, as the plain page styles it."""
_MAX_COLUMN = 28
"""The widest the names in a group of options make their column; a longer name pushes its own line along."""
_MAX_FLAG = 24
"""The widest a default is shown on a collapsed line; the whole of it is in the detail."""
_MARK = "reverse"
"""How what's being found is marked on the page."""


class _Place(Record):
    """Somewhere in the viewer's history: a plugin, and the option or return value to show in it, if any."""

    __slots__ = ("fqcn", "path", "returns", "types")

    def __init__(self, fqcn: str, types: tuple[str, ...], path: tuple[str, ...] = (), *, returns: bool = False) -> None:
        self.fqcn = fqcn
        self.types = types
        self.path = path
        self.returns = returns


def view(alai: Alai, loaded: Loaded) -> int:
    """Show ``loaded`` in the viewer until it's closed."""
    plugin = loaded.plugins[0][0]
    place = _Place(f"{loaded.collection}.{plugin.name}", (plugin.type,))
    app = DocViewer(alai, loaded, loaded.located.latest, place)
    # Nothing may write to the terminal while the viewer is drawn on it: messages, and alai's progress, are the
    # viewer's.
    verbosity, quiet = _output.verbosity, alai.quiet
    _output.verbosity, alai.quiet = -1, True
    try:
        app.run()
    finally:
        _output.verbosity, alai.quiet = verbosity, quiet
    return 0


def _content(segments: _c.Iterable[Segment]) -> Content:
    """A line's pieces as Textual content: markup styled, and links to plugins, options and URLs clickable."""
    parts: list[tuple[str, Style]] = []
    for text, kind, target in segments:
        style = Style.parse(_STYLES[kind]) if kind in _STYLES else Style()
        action = None
        if target and kind in ("option_name", "return_value"):
            action = f"app.goto({target!r}, {kind == 'return_value'})"
        elif target and kind in ("module", "plugin"):
            # M() is a module, P() says its type after a #.
            action = f"app.open_plugin({(target if kind == 'plugin' else target + '#module')!r})"
        elif target and kind in ("link", "url"):
            action = f"app.open_link({target!r})"
        if action:
            style = style + Style(underline=True) + Style.from_meta({"@click": action})
        parts.append((text.replace(NBSP, " "), style))
    return Content.assemble(*parts)


def _join(*lines: Content | None, gap: str = "\n") -> Content:
    return Content(gap).join([line for line in lines if line is not None and line.plain])


class _Text(Static):
    """Text on the page, with what's being found marked in it."""

    def __init__(self, text: Content, *, classes: str | None = None, id: str | None = None) -> None:  # noqa: A002
        super().__init__(text, classes=classes, id=id)
        self.text = text

    def on_mount(self) -> None:
        # Mounted while something's being found, as an option's children are when it opens.
        if _t.cast("DocViewer", self.app).found is not None:
            self.mark()

    def show(self, text: Content) -> None:
        self.text = text
        self.mark()

    def mark(self) -> None:
        found = _t.cast("DocViewer", self.app).found
        self.update(self.text.highlight_regex(found, style=_MARK) if found is not None else self.text)


class Entry(Vertical, can_focus=True):
    """An option or return value: one line, which opens to show all of it and its children, each an Entry too."""

    DEFAULT_CSS = """
    Entry { height: auto; }
    Entry > .line { width: 1fr; height: 1; text-wrap: nowrap; text-overflow: ellipsis; border-left: blank; }
    Entry:focus > .line { border-left: outer $primary; text-style: bold; background: $boost; }
    Entry.-flash > .line { background: $warning 40%; }
    Screen.-ansi Entry.-flash > .line { background: ansi_yellow; color: ansi_black; }
    Entry > .detail { display: none; height: auto; max-width: 104; padding: 0 0 1 4; }
    Entry.-open > .detail { display: block; }
    Entry > .children { display: none; height: auto; padding-left: 2; }
    Entry.-open > .children { display: block; }
    """
    BINDINGS: _t.ClassVar = [
        Binding("down,j", "move(1)", "Next", show=False),
        # Here, not only on the app, as the page's scrolling has its own Home, End and page keys, which come first.
        Binding("home,g", "app.top", "Top", show=False),
        Binding("end,G", "app.bottom", "Bottom", show=False),
        Binding("up,k", "move(-1)", "Previous", show=False),
        Binding("enter,space", "flip", "Open/close"),
        Binding("pageup,left_curly_bracket", "app.section(-1)", "Previous section", show=False),
        Binding("pagedown,right_curly_bracket", "app.section(1)", "Next section", show=False),
        Binding("right,l", "open", "Open", show=False),
        Binding("left,h", "close", "Close", show=False),
    ]

    def __init__(
        self,
        name: str,
        entry: dict[str, object],
        path: tuple[str, ...],
        *,
        crumbs: tuple[str, ...] = (),
        column: tuple[int, int, int],
        returns: bool,
        parent: str | None,
    ) -> None:
        super().__init__()
        self.option = name
        self.entry = entry
        self.path = (*path, name)
        """The names from the top level down to this one."""
        self.crumbs: tuple[str, ...] = (*crumbs, path_segment(name, entry))
        """``path``, with ``[]`` after each that's a list, for the status line."""
        self.column = column
        """How wide the name, type and flags columns are, the same for its siblings."""
        self.returns = returns
        self.parent_name = parent
        self.kids = nested_entries(entry, returns=returns)
        self.mounted = False
        self.is_open = False

    def compose(self) -> ComposeResult:
        yield _Text(self._line(), classes="line")
        yield _Text(self._detail(), classes="detail")
        yield Vertical(classes="children")

    def _line(self) -> Content:
        """The collapsed line: name, type, whether it's required, the default, and the description's start."""
        expandable = bool(self.kids) or bool(self._detail().plain)
        marker = ("▾ " if self.is_open else "▸ ") if expandable else "  "
        names, types, flags = self.column
        parts: list[tuple[str, str | Style]] = [
            (marker, "dim"),
            (self.option.ljust(names), "bold"),
            ("  ", ""),
            (type_name(self.entry).ljust(types), "magenta"),
            ("  ", ""),
        ]
        flag = _flag(self.entry, self.parent_name, returns=self.returns)
        parts += [*flag, (" " * max(0, flags - sum(len(text) for text, _ in flag)), "")]
        line = Content.assemble(*parts)
        first = paragraphs_of(self.entry.get("description"))
        # Open, the detail has all of it.
        if first and not self.is_open:
            line = line + Content("  ") + _content([(p, k, None) for p, k, _ in rich_text(first[0])])
        return line

    def _detail(self) -> Content:
        """Everything about it, for when it's open: the whole description and the rest."""
        entry = self.entry
        blocks: list[Content | None] = [_content(rich_text(p)) for p in paragraphs_of(entry.get("description"))]
        if self.returns:
            if returned := as_text(entry.get("returned")):
                blocks.append(_content([("Returned: ", "dim", None), *rich_text(returned)]))
            if entry.get("sample") is not None:
                sample = entry["sample"]
                text = json.dumps(sample, indent=2) if isinstance(sample, (dict, list)) else yaml_value(sample)
                blocks.append(Content.assemble(("Sample: ", "dim"), (text, "cyan")))
        else:
            # The line may be cut short, or cut its default, so it's here whole.
            default = entry.get("default")
            if "default" in entry and default is not None:
                blocks.append(Content.assemble(("Default: ", "dim"), (yaml_value(default), "cyan")))
            blocks.append(_choices(entry))
            extra: list[str] = []
            if aliases := as_list(entry.get("aliases")):
                extra.append("aliases: " + ", ".join(as_text(a) for a in aliases))
            added = entry.get("version_added")
            if added and as_text(added) != "historical":
                extra.append(f"added in {as_text(added)}")
            if extra:
                blocks.append(Content.styled(" · ".join(extra), "dim"))
            if deprecated := deprecation_text(entry.get("deprecated")):
                blocks.append(_content(rich_text(deprecated)).stylize_before("yellow"))
            blocks.append(_sources(entry))
        return _join(*blocks, gap="\n\n")

    async def mount_kids(self) -> None:
        """Its children, mounted the first time it opens, or when the page is searched."""
        if not self.mounted:
            self.mounted = True
            parent = self.option
            column = _columns(self.kids, parent, returns=self.returns)
            await self.query_one(".children", Vertical).mount_all(
                Entry(n, e, self.path, crumbs=self.crumbs, column=column, returns=self.returns, parent=parent)
                for n, e in self.kids.items()
            )

    async def open(self) -> None:
        if not self.kids and not self._detail().plain:
            return
        await self.mount_kids()
        self.is_open = True
        self.add_class("-open")
        self.query_one(".line", _Text).show(self._line())
        # What opened is below the line, and may be below the screen: once it's laid out, bring it into view, its line
        # kept on screen if it's taller than the screen.
        self.call_after_refresh(self._show_opened)

    def _show_opened(self) -> None:
        page = self.screen.query_one("#page", VerticalScroll)
        self.scroll_visible(animate=False, top=self.region.height > page.region.height)

    def close(self) -> None:
        self.is_open = False
        self.remove_class("-open")
        self.query_one(".line", _Text).show(self._line())

    async def action_flip(self) -> None:
        if self.is_open:
            self.close()
        else:
            await self.open()

    async def action_open(self) -> None:
        await self.open()

    def action_close(self) -> None:
        if self.is_open:
            self.close()
        elif isinstance(parent := self.parent.parent if self.parent else None, Entry):
            parent.focus()
            parent.close()

    def action_move(self, step: int) -> None:
        _t.cast("DocViewer", self.app).move(step)

    async def on_click(self, event: events.Click) -> None:
        # A click on the line opens or closes it, unless it's on a link, which follows the link instead.
        if isinstance(event.widget, Static) and event.widget.has_class("line"):
            event.stop()
            if "@click" not in event.style.meta:
                self.focus()
                await self.action_flip()

    def on_focus(self) -> None:
        crumbs = " › ".join(self.crumbs)  # noqa: RUF001 - a breadcrumb, not a quote
        self.app.query_one("#status", Static).update(Content.styled(crumbs, "dim"))
        # Not animated, or a scroll this starts could undo one an Enter straight after starts.
        self.scroll_visible(animate=False)


class Section(Vertical, can_focus=True):
    """A part of the page under a heading, open to start with, which closes to just its heading."""

    DEFAULT_CSS = """
    Section { height: auto; margin-top: 1; }
    Section > .heading { height: 1; width: 1fr; text-wrap: nowrap; text-overflow: clip; border-left: blank; }
    Section:focus > .heading { border-left: outer $primary; text-style: bold; background: $boost; }
    Section > .body { height: auto; }
    Section.-closed > .body { display: none; }
    """
    BINDINGS: _t.ClassVar = [
        Binding("down,j", "move(1)", "Next", show=False),
        # Here, not only on the app, as the page's scrolling has its own Home, End and page keys, which come first.
        Binding("home,g", "app.top", "Top", show=False),
        Binding("end,G", "app.bottom", "Bottom", show=False),
        Binding("up,k", "move(-1)", "Previous", show=False),
        Binding("enter,space", "flip", "Open/close"),
        Binding("pageup,left_curly_bracket", "app.section(-1)", "Previous section", show=False),
        Binding("pagedown,right_curly_bracket", "app.section(1)", "Next section", show=False),
        Binding("right,l", "open", "Open", show=False),
        Binding("left,h", "close", "Close", show=False),
    ]

    def __init__(self, title: str, *body: Widget) -> None:
        super().__init__()
        self.title = title
        self.body = body

    def compose(self) -> ComposeResult:
        yield Static(self._heading(), classes="heading")
        yield Vertical(*self.body, classes="body")

    def _heading(self) -> Content:
        marker = "▸ " if self.has_class("-closed") else "▾ "
        # As the printed page's rules; cut to the width.
        return Content.assemble((marker, "dim"), (self.title, "bold"), (" " + "─" * 400, "dim"))

    def _set(self, *, closed: bool) -> None:
        self.set_class(closed, "-closed")
        self.query_one(".heading", Static).update(self._heading())

    def action_flip(self) -> None:
        self._set(closed=not self.has_class("-closed"))

    def action_open(self) -> None:
        self._set(closed=False)

    def action_close(self) -> None:
        self._set(closed=True)

    def action_move(self, step: int) -> None:
        _t.cast("DocViewer", self.app).move(step)

    def on_click(self, event: events.Click) -> None:
        if isinstance(event.widget, Static) and event.widget.has_class("heading"):
            event.stop()
            self.focus()
            self.action_flip()

    def on_focus(self) -> None:
        self.app.query_one("#status", Static).update(Content.styled(self.title, "dim"))


def _colour_system() -> str | None:
    """How many colours the terminal shows, as Rich works it out from ``COLORTERM`` and ``TERM``, for Textual draws
    through Rich: ``truecolor``, ``256``, ``standard`` (16) or None."""
    from rich.console import Console

    # As if on a terminal, which the viewer is: only the environment then decides.
    return Console(force_terminal=True).color_system


class _Bullet(Horizontal):
    """A bullet point, its text indented under its first line."""

    DEFAULT_CSS = """
    _Bullet { height: auto; max-width: 104; margin-left: 1; }
    _Bullet > .mark { width: 2; color: $text-muted; }
    _Bullet > .text { width: 1fr; height: auto; }
    """

    def __init__(self, text: Content) -> None:
        super().__init__()
        self.text = text

    def compose(self) -> ComposeResult:
        yield Static("•", classes="mark")
        yield _Text(self.text, classes="text")


def _flag(entry: dict[str, object], parent: str | None, *, returns: bool) -> list[tuple[str, str]]:
    """What the collapsed line says after the type: that it's required, or its default."""
    if returns:
        return []
    if entry.get("required") is True:
        return [(f"required in {parent}" if parent else "required", "red")]
    default = entry.get("default")
    if "default" in entry and default is not None:
        shown = yaml_value(default)
        if len(shown) > _MAX_FLAG - 2:
            shown = shown[: _MAX_FLAG - 3] + "…"
        return [("= ", "dim"), (shown, "cyan")]
    return []


def _columns(entries: dict[str, dict[str, object]], parent: str | None, *, returns: bool) -> tuple[int, int, int]:
    """The widths of a group's name, type and flags columns."""
    names = min(max((len(n) for n in entries), default=0), _MAX_COLUMN)
    types = max((len(type_name(e)) for e in entries.values()), default=0)
    flags = max((sum(len(t) for t, _ in _flag(e, parent, returns=returns)) for e in entries.values()), default=0)
    return names, types, min(flags, _MAX_FLAG)


def _choices(entry: dict[str, object]) -> Content | None:
    choices = entry.get("choices")
    default = entry.get("default")
    mark = yaml_value(default) if "default" in entry and default is not None else None
    if isinstance(choices, dict):
        lines = []
        for value, description in as_map(choices).items():
            segments: list[Segment] = [("• ", "dim", None), (yaml_value(value), "option_value", None)]
            if yaml_value(value) == mark:
                segments.append((" (default)", "dim", None))
            if text := " ".join(paragraphs_of(description)):
                segments += [(": ", None, None), *rich_text(text)]
            lines.append(_content(segments))
        return _join(*lines)
    values = as_list(choices)
    if not values:
        return None
    segments = [("Choices: ", "dim", None)]
    for i, value in enumerate(values):
        segments.append((yaml_value(value), "option_value", None))
        if yaml_value(value) == mark:
            segments.append((" (default)", "dim", None))
        if i < len(values) - 1:
            segments.append((" · ", "dim", None))
    return _content(segments)


def _sources(option: dict[str, object]) -> Content | None:
    """Where a plugin's option can be set, a line per kind, highest precedence first."""
    lines = []
    for kind in SOURCE_ORDER:
        entries = [as_map(e) for e in as_list(option.get(kind)) if isinstance(e, dict)]
        if not entries:
            continue
        segments: list[Segment] = [(f"{kind.removesuffix('s'):<8}", "dim", None)]
        for i, entry in enumerate(reversed(entries)):
            if i:
                segments.append((", ", None, None))
            if kind == "ini":
                where = f"[{as_text(entry.get('section') or 'defaults')}] {as_text(entry.get('key'))}"
            else:
                where = as_text(entry.get("name"))
            deprecated = entry.get("deprecated")
            segments.append((where, "dim" if isinstance(deprecated, dict) else "option_value", None))
            if isinstance(deprecated, dict):
                removed = as_text(as_map(deprecated).get("removed_in") or as_map(deprecated).get("version"))
                segments.append((" (deprecated" + (f", removed in {removed}" if removed else "") + ")", "dim", None))
        lines.append(_content(segments))
    return _join(*lines) if lines else None


class DocViewer(App[None]):
    """One plugin's documentation at a time, with history."""

    TITLE = "alai-doc"
    CSS = """
    #page { height: 1fr; padding: 0 1; }
    #head { height: auto; border: round $foreground 50%; padding: 0 1; max-width: 108; }
    Screen.-ansi #head { border: round ansi_bright_black; }
    .prose { height: auto; max-width: 104; margin: 1 0 0 1; }
    .caption { height: auto; max-width: 104; margin: 1 0 0 1; }
    .under-caption { height: auto; max-width: 104; margin: 0 0 0 3; }
    .entries { height: auto; }
    #status { height: 1; padding: 0 1; }
    #find { height: 1; display: none; }
    #find.-on { display: block; }
    #find > Input { width: 1fr; height: 1; border: none; padding: 0 1; }
    #found { width: auto; padding: 0 1; color: $text-muted; }
    """
    BINDINGS: _t.ClassVar = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "dismiss", "Close, or quit", show=False),
        Binding("slash,ctrl+f", "find", "Find", key_display="/"),
        Binding("n", "next_hit(1)", "Match", key_display="n/N"),
        Binding("N", "next_hit(-1)", "Previous match", show=False),
        Binding("question_mark", "keys", "Keys", key_display="?"),
        # [ and ] as well as Alt+arrows, which macOS terminals often send as something else.
        Binding("left_square_bracket,alt+left,backspace", "history_back", "Back/forward", key_display="[]"),
        Binding("right_square_bracket,alt+right", "history_forward", "Forward", show=False),
        Binding("e,E", "expand_all", "Open all", show=False),
        Binding("c,C", "collapse_all", "Close all", show=False),
        Binding("home,g", "top", "Top", show=False),
        Binding("end,G", "bottom", "Bottom", show=False),
        Binding("pageup,left_curly_bracket", "section(-1)", "Previous section", show=False),
        Binding("pagedown,right_curly_bracket", "section(1)", "Next section", show=False),
    ]

    def __init__(self, alai: Alai, loaded: Loaded, latest: str | None, place: _Place) -> None:
        # Textual's themes, light or dark as the terminal is, where it shows 256 colours or more; with only 16, which
        # the themes' colours would be squeezed into badly, the terminal's own colours and an ANSI theme.
        self.ansi = _colour_system() not in ("truecolor", "256")
        super().__init__(ansi_color=self.ansi)
        self.light = _output.light_background(ask=True)
        if self.ansi:
            self.theme = "ansi-light" if self.light else "ansi-dark"
        else:
            self.theme = "textual-light" if self.light else "textual-dark"
        self.alai = alai
        self.loaded = loaded
        self.latest = latest
        self.history = [place]
        self.at = 0
        self.found: re.Pattern[str] | None = None
        """What's being found on the page, if anything."""
        self.hit = -1
        """Which of what's found the cursor was last taken to."""
        self.before: Widget | None = None

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="page")
        yield Static(id="status")
        with Horizontal(id="find"):
            yield Input(placeholder="Find on the page", id="find-text")
            yield Static(id="found")
        yield Footer(compact=True)

    async def on_mount(self) -> None:
        self.screen.set_class(self.ansi, "-ansi")
        await self._show(self.loaded, self.latest, self.history[self.at])

    # Building a page.

    async def _show(self, loaded: Loaded, latest: str | None, place: _Place) -> None:
        self.loaded, self.latest = loaded, latest
        # The type asked for, else the module, as ansible-doc defaults to, else the first.
        plugin, docs = next(
            (pd for pd in loaded.plugins if pd[0].type in place.types),
            next((pd for pd in loaded.plugins if pd[0].type == "module"), loaded.plugins[0]),
        )
        page = self.query_one("#page", VerticalScroll)
        await page.remove_children()
        await page.mount_all(self._widgets(loaded, plugin, docs, latest))
        self.sub_title = f"{loaded.collection}.{plugin.name}"
        page.scroll_home(animate=False)
        if place.path:
            await self._jump(place.path, returns=place.returns, remember=False)
        elif first := next(iter(self.query(Entry)), None) or next(iter(self.query(Section)), None):
            first.focus(scroll_visible=False)
        if self.found is not None:
            await self._mount_all()
        self.hit = -1
        self._count()

    def _widgets(
        self, loaded: Loaded, plugin: ape.Plugin, docs: ape.PluginDocs | None, latest: str | None
    ) -> list[Static | Vertical | Horizontal]:
        collection = loaded.collection
        documentation = as_map(docs.documentation) if docs is not None else {}
        short = as_text(documentation.get("short_description")) or plugin.short_description
        widgets: list[Static | Vertical | Horizontal] = [self._head(loaded, plugin, docs, documentation, short, latest)]
        if docs is None:
            widgets.append(_Text(Content("No documentation."), classes="prose"))
            return widgets
        if badges := self._badges(documentation.get("attributes")):
            widgets.append(_Text(badges, classes="prose"))
        paragraphs = paragraphs_of(documentation.get("description"))
        if [bare(p) for p in paragraphs] == [bare(short or "")]:
            paragraphs = []
        if paragraphs:
            text = _join(*[_content(rich_text(p)) for p in paragraphs], gap="\n\n")
            widgets.append(Section("Description", _Text(text, classes="prose")))

        if snippets := usage(f"{collection}.{plugin.name}", plugin.type, documentation):
            parts: list[Widget] = []
            for caption, language, code in snippets:
                caption_line = _Text(Content.styled(f"{caption}:", "dim"), classes="caption")
                parts += [caption_line, self._code(language, code, classes="under-caption")]
            widgets.append(Section("Usage", *parts))
        inputs, positional, options = split_arguments(plugin.type, documentation)
        for title, entries in (("Input", inputs), ("Positional", positional), ("Options", options)):
            if entries:
                widgets.append(Section(title, self._entries(entries, returns=False, section=title.lower())))
        for title, key in (("Notes", "notes"), ("Requirements", "requirements")):
            if items := paragraphs_of(documentation.get(key)):
                widgets.append(Section(title, *[_Bullet(_content(rich_text(i))) for i in items]))
        if seealso := self._seealso(documentation.get("seealso")):
            widgets.append(Section("See also", *[_Bullet(line) for line in seealso]))
        if docs.examples and docs.examples.strip():
            widgets.append(Section("Examples", self._code("yaml", docs.examples)))
        returns = entries_under({"returns": docs.returns}, "returns")
        if (value := unnamed_return(plugin.type, returns)) is not None:
            described = [_content(rich_text(p)) for p in paragraphs_of(value.get("description"))]
            text = _join(Content.styled(type_name(value), "magenta"), *described, gap="\n\n")
            if value.get("sample") is not None:
                text = _join(
                    text, Content.assemble(("Sample: ", "dim"), (yaml_value(value["sample"]), "cyan")), gap="\n\n"
                )
            widgets.append(Section("Returns", _Text(text, classes="prose")))
        elif returns:
            widgets.append(Section("Return values", self._entries(returns, returns=True, section="returns")))
        return widgets

    def _code(self, language: str, code: str, *, classes: str = "prose") -> _Text:
        """Code highlighted with Textual's own highlighting, in the theme's colours and on its background, which
        Rich's Syntax isn't: ``yaml`` examples, ``jinja`` expressions or ``ini`` settings."""
        from textual.highlight import ANSIDarkHighlightTheme, ANSILightHighlightTheme, HighlightTheme, highlight

        text = "\n".join(line.rstrip() for line in code.strip("\n").splitlines())
        ansi = ANSILightHighlightTheme if self.light else ANSIDarkHighlightTheme
        lexer = {"yaml": "yaml+jinja", "jinja": "jinja", "shell": "bash"}.get(language, language)
        return _Text(highlight(text, language=lexer, theme=ansi if self.ansi else HighlightTheme), classes=classes)

    def _head(
        self,
        loaded: Loaded,
        plugin: ape.Plugin,
        docs: ape.PluginDocs | None,
        documentation: dict[str, object],
        short: str | None,
        latest: str | None,
    ) -> _Text:
        collection = loaded.collection
        lines: list[Content | None] = []
        if short:
            lines.append(_content([(p, k or "bold", t) for p, k, t in as_sentence(markup(short))]))
        # Next to what it does, as the name in the border is the one it redirected to.
        if loaded.redirects:
            lines.append(Content(f"Redirected from {and_list(loaded.redirects)}."))
        origin = origin_text(loaded.located)
        if latest:
            origin = f"{origin.rstrip('.')}; {latest} is the latest."
        lines.append(Content.styled(origin, "dim"))
        if authors := paragraphs_of(documentation.get("author")):
            lines.append(Content.styled(f"By {and_list(authors)}.", "dim"))
        if (added := documentation.get("version_added")) and as_text(added) != "historical":
            where = "version" if collection == BUILTIN else collection
            lines.append(Content.styled(f"Added in {where} {as_text(added)}.", "dim"))
        if deprecated := deprecation_text(documentation.get("deprecated")):
            lines.append(_content(rich_text(deprecated)).stylize_before("yellow"))
        if docs is not None and (missing := sorted({*docs.fragments, *docs.return_fragments})):
            what = "fragment" if len(missing) == 1 else "fragments"
            verb = "adds" if len(missing) == 1 else "add"
            lines.append(
                Content.styled(
                    f"Not shown: what the doc {what} {and_list(missing)} {verb}, which couldn't be found or read without "
                    + "running code.",
                    "yellow",
                )
            )
        # The other types of plugin the name asked for is: a lookup as well as a module, say.
        if loaded.others:
            links: list[Segment] = [("Also a ", "dim", None)]
            for i, (other, name) in enumerate(loaded.others):
                if i:
                    links.append((", ", "dim", None))
                links.append((other, "plugin", f"{name}#{other}"))
            lines.append(_content(links))
        head = _Text(_join(*lines), id="head")
        head.border_title = Content.styled(f"{collection}.{plugin.name}", "bold blue")
        kind = plugin.type
        if plugin.type == "callback" and (callback := as_text(documentation.get("type"))):
            kind = f"{callback} callback"
        head.border_subtitle = Content.styled(kind, "magenta")
        return head

    def _badges(self, value: object) -> Content | None:
        attributes = entries_under({"attributes": value}, "attributes")
        if not attributes:
            return None
        parts: list[Segment] = []
        for name, attribute in attributes.items():
            if parts:
                parts.append(("   ", None, None))
            support = as_text(attribute.get("support"))
            platforms = attribute.get("platforms")
            membership = attribute.get("membership")
            if name == "platform" or platforms is not None:
                shown = (
                    ", ".join(as_text(p) for p in as_list(platforms))
                    if isinstance(platforms, list)
                    else as_text(platforms)
                )
                parts += [(name, None, None), (f" {shown or support}", "option_value", None)]
            elif membership is not None:
                shown = (
                    ", ".join(as_text(m) for m in as_list(membership))
                    if isinstance(membership, list)
                    else as_text(membership)
                )
                parts += [(name, None, None), (f" {shown}", "option_value", None)]
            else:
                parts += [
                    (name, None, None),
                    (f" {SUPPORT_MARKS.get(support, support or '?')}", f"support-{support}", None),
                ]
        return _content(parts)

    def _seealso(self, value: object) -> list[Content]:
        lines: list[Content] = []
        for item in (as_map(i) for i in as_list(value) if isinstance(i, dict)):
            segments: list[Segment] = []
            if "module" in item:
                segments += [(as_text(item["module"]), "module", as_text(item["module"])), (" module", "dim", None)]
            elif "plugin" in item:
                kind = as_text(item.get("plugin_type"))
                segments += [
                    (as_text(item["plugin"]), "plugin", f"{as_text(item['plugin'])}#{kind}"),
                    (f" {kind}", "dim", None),
                ]
            elif "link" in item:
                segments.append((as_text(item.get("name") or item["link"]), "link", as_text(item["link"])))
            elif "ref" in item:
                segments.append((as_text(item.get("name") or item["ref"]), None, None))
            else:
                continue
            if description := paragraphs_of(item.get("description")):
                segments += [(": ", None, None), *rich_text(" ".join(description))]
            lines.append(_content(segments))
        return lines

    def _entries(self, entries: dict[str, dict[str, object]], *, returns: bool, section: str) -> Vertical:
        column = _columns(entries, None, returns=returns)
        box = Vertical(
            *[Entry(n, e, (), column=column, returns=returns, parent=None) for n, e in entries.items()],
            classes="entries",
            id=re.sub(r"[^a-z0-9_-]", "-", f"section-{section}"),
        )
        box.section = section  # pyright: ignore[reportAttributeAccessIssue]
        return box

    # Following links.

    async def action_goto(self, target: str, returns: bool = False) -> None:
        """Go to the option or return value an ``O()`` or ``RV()`` names: ``name``, ``a.b[].c``, with an entry point
        (``main:name``), or in another plugin (``ns.coll.plugin#module:name``)."""
        fqcn, kind = None, ""
        if "#" in target:
            fqcn, _, rest = target.partition("#")
            kind, _, target = rest.partition(":")
            if not target:
                target, kind = kind, ""
        elif ":" in target:
            target = target.rsplit(":", 1)[1]
        path = tuple(part.removesuffix("[]") for part in target.split(".") if part)
        current = self.history[self.at]
        if fqcn is not None and (fqcn != current.fqcn or (kind and kind not in current.types)):
            self._visit(_Place(fqcn, (kind,) if kind else (), path, returns=returns))
            return
        await self._jump(path, returns=returns)

    def action_open_plugin(self, target: str) -> None:
        fqcn, _, kind = target.partition("#")
        self._visit(_Place(fqcn, (kind,) if kind else ()))

    def action_open_link(self, url: str) -> None:
        self.open_url(url)

    async def _jump(self, path: tuple[str, ...], *, returns: bool, remember: bool = True) -> None:
        """Open every option on ``path`` and focus the last, briefly highlighted."""
        sections = [w for w in self.query(".entries") if (getattr(w, "section", "") == "returns") == returns]
        entries = [c for s in sections for c in s.children if isinstance(c, Entry)]
        found: Entry | None = None
        for i, name in enumerate(path):
            # An input or positional argument is shown without its _, as terms rather than _terms.
            found = next((e for e in entries if e.option == name), None)
            if found is None and i == 0:
                found = next((e for e in entries if e.option == input_label(name)), None)
            if found is None:
                self.notify(f"no {'return value' if returns else 'option'} {'.'.join(path)}", severity="warning")
                return
            if i < len(path) - 1:
                await found.open()
                entries = [c for c in found.query_one(".children").children if isinstance(c, Entry)]
        if found is None:
            return
        for ancestor in found.ancestors:
            if isinstance(ancestor, Section):
                ancestor.action_open()
        if remember:
            current = self.history[self.at]
            self.history[self.at + 1 :] = [_Place(current.fqcn, current.types, path, returns=returns)]
            self.at += 1
        found.focus()
        found.add_class("-flash")
        self.set_timer(1.0, lambda: found.remove_class("-flash"))

    # History.

    def _visit(self, place: _Place) -> None:
        self.history[self.at + 1 :] = [place]
        self.at += 1
        self._load(place)

    def action_history_back(self) -> None:
        if self.at > 0:
            self.at -= 1
            self._load(self.history[self.at])

    def action_history_forward(self) -> None:
        if self.at < len(self.history) - 1:
            self.at += 1
            self._load(self.history[self.at])

    @work(thread=True, exclusive=True)
    def _load(self, place: _Place) -> None:
        page = self.query_one("#page", VerticalScroll)
        self.call_from_thread(setattr, page, "loading", True)
        try:
            loaded = load(self.alai, place.fqcn, place.types)
            latest = loaded.located.latest
        except Error as e:
            self.call_from_thread(self._failed, str(e), place)
            return
        finally:
            self.call_from_thread(setattr, page, "loading", False)
        self.call_from_thread(self._show, loaded, latest, place)

    def _failed(self, message: str, place: _Place) -> None:
        self.notify(message, title=place.fqcn, severity="error")
        if self.history[self.at] is place and self.at > 0:
            del self.history[self.at]
            self.at -= 1

    # Opening and closing everything, and scrolling.

    async def action_expand_all(self) -> None:
        for section in self.query(Section):
            section.action_open()
        # Children are only mounted once open, so a level at a time.
        while closed := [e for e in self.query(Entry) if not e.is_open and (e.kids or e._detail().plain)]:
            for entry in closed:
                await entry.open()

    def action_collapse_all(self) -> None:
        for entry in self.query(Entry):
            if entry.is_open:
                entry.close()

    def action_top(self) -> None:
        if chain := self._chain():
            chain[0].focus(scroll_visible=False)
        self.query_one("#page", VerticalScroll).scroll_home()

    def action_bottom(self) -> None:
        if chain := self._chain():
            chain[-1].focus(scroll_visible=False)
        self.query_one("#page", VerticalScroll).scroll_end()

    def _chain(self) -> list[Widget]:
        """What up and down move between, in order: the sections' headings and the options they show."""
        return [w for w in self.screen.focus_chain if isinstance(w, (Entry, Section))]

    def action_section(self, step: int) -> None:
        """Move to the next section's heading, or back to the heading of the section the cursor is in, then the one
        before it, stopping at the ends. The page only scrolls to keep the heading on screen, as up and down do."""
        chain = self._chain()
        at = chain.index(self.focused) if self.focused in chain else -1
        headings = [i for i, w in enumerate(chain) if isinstance(w, Section)]
        found = [i for i in headings if i > at] if step > 0 else [i for i in headings if i < at][::-1]
        if not found:
            return
        chain[found[0]].focus()
        if found[0] == 0:
            self.query_one("#page", VerticalScroll).scroll_home()

    def move(self, step: int) -> None:
        """Move to the next or previous heading or option, stopping at the ends rather than going round; at the
        first, the page goes to its top, so the header shows."""
        chain = self._chain()
        focused = self.focused
        at = chain.index(focused) if focused in chain else -1
        target = max(0, min(len(chain) - 1, at + step))
        if chain and target != at:
            chain[target].focus()
        if chain and target == 0:
            self.query_one("#page", VerticalScroll).scroll_home()

    # Finding on the page, and closing what's open.

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        # n and N are only in the footer while something's being found.
        return self.found is not None if action == "next_hit" else True

    def action_find(self) -> None:
        box = self.query_one("#find-text", Input)
        if self.focused is not box:
            self.before = self.focused
        self.query_one("#find").add_class("-on")
        box.focus()

    async def on_input_changed(self, event: Input.Changed) -> None:
        text = event.value
        # Without case unless what's typed has a capital, as less's and vim's smartcase.
        self.found = re.compile(re.escape(text), 0 if text != text.lower() else re.IGNORECASE) if text else None
        self.hit = -1
        if self.found is not None:
            await self._mount_all()
        for widget in self.query(_Text):
            widget.mark()
        self._count()
        self.refresh_bindings()

    async def on_input_submitted(self, _: Input.Submitted) -> None:
        self._refocus()
        await self.action_next_hit(1)

    def action_dismiss(self) -> None:
        """Close the keys, else what's being found, else the viewer."""
        if self.screen.query(HelpPanel):
            self.action_hide_help_panel()
        elif self.query_one("#find").has_class("-on"):
            self.query_one("#find").remove_class("-on")
            box = self.query_one("#find-text", Input)
            if self.focused is box:
                self._refocus()
            # Its change clears the marks.
            box.value = ""
        else:
            self.exit()

    def action_keys(self) -> None:
        if self.screen.query(HelpPanel):
            self.action_hide_help_panel()
        else:
            self.action_show_help_panel()

    def _refocus(self) -> None:
        chain = self._chain()
        if self.before is not None and self.before in chain:
            self.before.focus(scroll_visible=False)
        elif chain:
            chain[0].focus(scroll_visible=False)

    async def _mount_all(self) -> None:
        """Every option, though not opened, so what's in closed ones can be found."""
        while unmounted := [e for e in self.query(Entry) if not e.mounted and e.kids]:
            for entry in unmounted:
                await entry.mount_kids()

    def _hits(self) -> list[tuple[_Text | Entry, int]]:
        """Where what's being found is, in order, each option it's in, or text and the line of it."""
        if self.found is None:
            return []
        hits: list[tuple[_Text | Entry, int]] = []
        for text in self.query_one("#page").query(_Text):
            plain = text.text.plain
            if isinstance(entry := text.parent, Entry):
                # Once for the option, whether open or not, as its line loses the description when it opens.
                if self.found.search(plain) and (not hits or hits[-1][0] is not entry):
                    hits.append((entry, 0))
                continue
            lines = sorted({plain.count("\n", 0, m.start()) for m in self.found.finditer(plain)})
            hits += [(text, line) for line in lines]
        return hits

    def _count(self) -> None:
        count = len(self._hits())
        if self.found is None:
            shown = ""
        elif not count:
            shown = "no match"
        elif self.hit >= 0:
            shown = f"{self.hit + 1}/{count}"
        else:
            shown = f"{count} {'match' if count == 1 else 'matches'}"
        self.query_one("#found", Static).update(shown)

    async def action_next_hit(self, step: int) -> None:
        """Go to the next or previous place what's being found is, round from the last to the first, opening what
        it's in."""
        hits = self._hits()
        if not hits:
            self._count()
            return
        self.hit = (self.hit + step) % len(hits) if self.hit >= 0 else (0 if step > 0 else len(hits) - 1)
        hit, line = hits[self.hit]
        for entry in reversed([a for a in hit.ancestors if isinstance(a, Entry)]):
            await entry.open()
        for section in (a for a in hit.ancestors if isinstance(a, Section)):
            section.action_open()
        if isinstance(hit, Entry):
            # Opened if it's only in what opening shows.
            if not _t.cast("re.Pattern[str]", self.found).search(hit.query_one(".line", _Text).text.plain):
                await hit.open()
            hit.focus()
        else:
            if owner := next((a for a in hit.ancestors if isinstance(a, (Entry, Section))), None):
                owner.focus(scroll_visible=False)
            self.call_after_refresh(self._show_hit, hit, line)
        self._count()

    def _show_hit(self, text: _Text, line: int) -> None:
        page = self.query_one("#page", VerticalScroll)
        # shortcut: counts lines as written, not wrapped, so a match far down a long wrapped paragraph may be a few
        # lines off the middle. Count wrapped lines if that's ever a bother.
        y = line
        widget: Widget = text
        while widget is not page:
            y += widget.virtual_region.y
            widget = _t.cast("Widget", widget.parent)
        page.scroll_to_region(Region(0, y, 1, 1), center=True, animate=False)
