# Copyright: (c) 2026, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""alai-doc's viewer, driven by Textual's test pilot."""

from __future__ import annotations

import asyncio
import collections.abc as _c
import os
import sys
import types
import typing as _t

import pytest
from doc_data import World

from alai_doc import _output

if _t.TYPE_CHECKING:
    from textual.pilot import Pilot

    from alai_doc._doc_view import DocViewer


@pytest.fixture
def project(world: World, monkeypatch: pytest.MonkeyPatch) -> World:
    # Textual's themes, dark, unless a test says otherwise.
    monkeypatch.setenv("COLORTERM", "truecolor")
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("COLORFGBG", raising=False)
    monkeypatch.setattr(_output, "_light", None)
    monkeypatch.setattr(_output, "terminal_background", lambda: None)
    return world


def run(
    name: str, steps: _c.Callable[[DocViewer, Pilot[None]], _c.Awaitable[None]], *, types: tuple[str, ...] = ()
) -> None:
    """Open ``name`` in the viewer, 100 by 45, and run ``steps`` on it."""
    from alai_doc._alai import Alai
    from alai_doc._doc_model import load
    from alai_doc._doc_view import DocViewer, _Place

    alai = Alai(quiet=True)

    async def main() -> None:
        loaded = load(alai, name, types)
        plugin = loaded.plugins[0][0]
        place = _Place(f"{loaded.collection}.{plugin.name}", (plugin.type,))
        app = DocViewer(alai, loaded, None, place)
        async with app.run_test(size=(100, 45)) as pilot:
            await pilot.pause()
            await steps(app, pilot)

    asyncio.run(main())


def screen(app: DocViewer) -> str:
    return "\n".join(strip.text.rstrip() for strip in app.screen._compositor.render_strips())


def focused(app: DocViewer) -> str:
    from alai_doc._doc_view import Entry, Section

    widget = app.focused
    if isinstance(widget, Entry):
        return ".".join(widget.path)
    if isinstance(widget, Section):
        return f"[{widget.title}]"
    return repr(widget)


def opened(app: DocViewer) -> set[str]:
    from alai_doc._doc_view import Entry

    return {".".join(e.path) for e in app.query(Entry) if e.is_open}


async def settle(pilot: Pilot[None], *keys: str) -> None:
    for key in keys:
        await pilot.press(key)
    await pilot.pause()


def test_page(project: World) -> None:
    async def steps(app: DocViewer, pilot: Pilot[None]) -> None:
        text = screen(app)
        assert "╭─ ns.coll.thing ─" in text
        assert "│ Manage things." in text
        assert "│ By Someone (@someone)." in text
        # The other type of plugin with this name, to follow.
        assert "│ Also a lookup" in text
        assert "check_mode ✓   diff_mode ◐   platform posix" in text
        assert "▾ Usage" in text
        assert "In a task:" in text
        assert "- ns.coll.thing:" in text
        # The first option has the cursor; each is a line, with required and the default in words.
        assert focused(app) == "mode"
        assert "▸ name       str         required" in text
        assert "▸ state      str         = present" in text
        assert app.theme == "textual-dark"
        assert app.sub_title == "ns.coll.thing"
        assert "⏎ Open/close {} Section q Quit [] Back/forward e/c Open/close all" in text

    run("ns.coll.thing", steps, types=("module",))


def test_open_and_close(project: World) -> None:
    async def steps(app: DocViewer, pilot: Pilot[None]) -> None:
        await settle(pilot, "down", "enter")
        assert focused(app) == "mode_kind"
        text = screen(app)
        # Open, it has all of it: the default whole, choices with descriptions.
        assert "▾ mode_kind" in text
        assert "Default: slow" in text
        assert "• fast: Quickly." in text
        await settle(pilot, "left")
        assert "▸ mode_kind" in screen(app)
        await settle(pilot, "down", "down", "down", "right", "down")
        # rules' children are mounted when it's opened, and the cursor goes into them.
        assert focused(app) == "rules.match"
        assert "required in rules" in screen(app)
        await settle(pilot, "left", "left")
        assert focused(app) == "rules"
        assert "▸ rules" in screen(app)
        await settle(pilot, "e")
        assert opened(app) >= {"rules", "rules.match", "rules.match.conditions", "rules.match.conditions.field"}
        await settle(pilot, "c")
        assert opened(app) == set()

    run("ns.coll.thing", steps, types=("module",))


def test_opened_comes_into_view(project: World) -> None:
    """Opening an option at the bottom of the screen brings what opened into view, its default whole."""

    async def steps(app: DocViewer, pilot: Pilot[None]) -> None:
        await pilot.resize_terminal(60, 20)
        await app.run_action("goto('state')")
        await settle(pilot, "enter")
        await pilot.pause(0.2)
        assert "Default: present" in screen(app)

    run("ns.coll.thing", steps, types=("module",))


def test_moving_stops_at_the_ends(project: World) -> None:
    async def steps(app: DocViewer, pilot: Pilot[None]) -> None:
        await settle(pilot, "end")
        last = focused(app)
        await settle(pilot, "down")
        assert focused(app) == last
        await settle(pilot, "home")
        assert focused(app) == "[Description]"
        await settle(pilot, "up")
        assert focused(app) == "[Description]"
        assert "╭─ ns.coll.thing ─" in screen(app)

    run("ns.coll.thing", steps, types=("module",))


def test_sections_close(project: World) -> None:
    async def steps(app: DocViewer, pilot: Pilot[None]) -> None:
        await settle(pilot, "home", "enter")
        text = screen(app)
        assert "▸ Description" in text
        assert "Manages a thing on the host." not in text
        await pilot.click("Section .heading")
        await pilot.pause()
        assert "Manages a thing on the host." in screen(app)

    run("ns.coll.thing", steps, types=("module",))


def test_click_opens(project: World) -> None:
    async def steps(app: DocViewer, pilot: Pilot[None]) -> None:
        await pilot.click("Entry .line")
        await pilot.pause()
        assert "▾ mode" in screen(app)

    run("ns.coll.thing", steps, types=("module",))


def test_goto_option(project: World) -> None:
    async def steps(app: DocViewer, pilot: Pilot[None]) -> None:
        await app.run_action("goto('rules[].match.conditions[].field')")
        await pilot.pause()
        assert focused(app) == "rules.match.conditions.field"
        assert app.query_one("#status").render().plain == "rules[] › match › conditions[] › field"  # pyright: ignore[reportAttributeAccessIssue]  # noqa: RUF001
        await app.run_action("goto('nothing')")
        await pilot.pause()
        assert focused(app) == "rules.match.conditions.field"
        # Back to where it was before the jump.
        await settle(pilot, "left_square_bracket")
        await pilot.pause(0.5)
        assert focused(app) == "mode"

    run("ns.coll.thing", steps, types=("module",))


def test_links_and_history(project: World) -> None:
    async def steps(app: DocViewer, pilot: Pilot[None]) -> None:
        await app.run_action("open_plugin('ns.coll.thing#lookup')")
        await app.workers.wait_for_complete()
        await pilot.pause()
        text = screen(app)
        assert "lookup ─╯" in text
        assert "{{ lookup('ns.coll.thing', <terms>, endpoint=<str>) }}" in text
        assert "▾ Positional" in text
        assert "▾ Returns" in text
        await settle(pilot, "left_square_bracket")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert "module ─╯" in screen(app)
        await settle(pilot, "right_square_bracket")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert "lookup ─╯" in screen(app)
        # The input, shown without its _, is found by its name.
        await app.run_action("goto('_terms')")
        await pilot.pause()
        assert focused(app) == "terms"

    run("ns.coll.thing", steps, types=("module",))


def test_link_to_another_plugin_at_an_option(project: World) -> None:
    async def steps(app: DocViewer, pilot: Pilot[None]) -> None:
        await app.run_action("goto('ns.coll.thing#lookup:endpoint')")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert "lookup ─╯" in screen(app)
        assert focused(app) == "endpoint"

    run("ns.coll.thing", steps, types=("module",))


def test_link_that_fails(project: World) -> None:
    async def steps(app: DocViewer, pilot: Pilot[None]) -> None:
        await app.run_action("open_plugin('no.such.plugin')")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert [n.message for n in app._notifications] == ["no index has the collection no.such"]
        # Still where it was, with nothing in history to go forward to.
        assert app.history[app.at].fqcn == "ns.coll.thing"
        assert len(app.history) == 1

    run("ns.coll.thing", steps, types=("module",))


def test_filter(project: World) -> None:
    async def steps(app: DocViewer, pilot: Pilot[None]) -> None:
        text = screen(app)
        assert "{{ <input> | ns.coll.double(<times>, sep=<str>) }}" in text
        assert "▾ Input" in text
        assert "▸ input  raw  required" in text

    run("ns.coll.double", steps)


@pytest.mark.parametrize(
    ("environ", "theme"),
    [
        ({"COLORFGBG": "0;15"}, "textual-light"),
        ({"COLORTERM": "", "TERM": "linux"}, "ansi-dark"),
        ({"COLORTERM": "", "TERM": "linux", "COLORFGBG": "0;15"}, "ansi-light"),
    ],
)
def test_themes(project: World, monkeypatch: pytest.MonkeyPatch, environ: dict[str, str], theme: str) -> None:
    for name, value in environ.items():
        if value:
            monkeypatch.setenv(name, value)
        else:
            monkeypatch.delenv(name, raising=False)

    async def steps(app: DocViewer, pilot: Pilot[None]) -> None:
        assert app.theme == theme
        assert app.screen.has_class("-ansi") == theme.startswith("ansi")

    run("ns.coll.thing", steps, types=("module",))


def test_view_quiets_alai(project: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """While the viewer is drawn, alai-doc's messages, and alai's, are off, and back once it's closed."""
    from textual.app import App

    from alai_doc import _doc_view
    from alai_doc._alai import Alai

    alai = Alai()
    seen: list[tuple[int, bool]] = []

    def run(_self: object) -> None:
        seen.append((_output.verbosity, alai.quiet))

    monkeypatch.setattr(App, "run", run)
    plugin = types.SimpleNamespace(name="thing", type="module")
    located = types.SimpleNamespace(latest=None)
    loaded = types.SimpleNamespace(collection="ns.coll", plugins=[(plugin, None)], located=located)
    assert _doc_view.view(alai, _t.cast("_t.Any", loaded)) == 0
    assert seen == [(-1, True)]
    assert (_output.verbosity, alai.quiet) == (0, False)


_ASK = """
import os, sys
os.setsid()
# Opened by a session leader, the pseudo-terminal becomes its controlling terminal, /dev/tty.
os.close(os.open(sys.argv[1], os.O_RDWR))
from alai_doc import _output
print("RESULT", _output.terminal_background(), flush=True)
"""


@pytest.mark.parametrize(
    ("reply", "light"),
    [
        (b"\x1b]11;rgb:ffff/ffff/ffff\x1b\\\x1b[?62;22c", True),
        (b"\x1b]11;rgb:1e1e/1e1e/2e2e\x07\x1b[?62c", False),
        (b"\x1b[?62;22c", None),
    ],
)
def test_terminal_background(reply: bytes, light: bool | None) -> None:
    """Asked on a pseudo-terminal that answers as a terminal would: OSC 11, if it knows it, then DA1. In a process of
    its own, which makes the pseudo-terminal its terminal, rather than forking this one, which has threads."""
    import select
    import subprocess

    master, slave = os.openpty()
    child = subprocess.Popen(  # noqa: S603 - this Python, running the script above
        [sys.executable, "-c", _ASK, os.ttyname(slave)], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    asked = b""
    try:
        while b"\x1b[c" not in asked and select.select([master], [], [], 10)[0]:
            asked += os.read(master, 1024)
        os.write(master, reply)
        stdout, stderr = child.communicate(timeout=10)
    finally:
        # Only now: with no end of it open here, reading the other gives EIO until the child has opened it.
        os.close(slave)
        os.close(master)
    assert stdout.decode().strip() == f"RESULT {light}", stderr.decode()


def test_light_background(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_output, "_light", None)
    monkeypatch.setattr(_output, "terminal_background", lambda: True)
    monkeypatch.setenv("COLORFGBG", "15;0")
    assert not _output.light_background(ask=True)
    monkeypatch.setenv("COLORFGBG", "0;15")
    assert _output.light_background()
    monkeypatch.delenv("COLORFGBG")
    assert not _output.light_background()
    assert _output.light_background(ask=True)


def test_no_terminal_to_ask(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_tty(*_args: object) -> int:
        raise OSError("no tty")

    monkeypatch.setattr(os, "open", no_tty)
    assert _output.terminal_background() is None


def test_page_keys_move_by_section(project: World) -> None:
    async def steps(app: DocViewer, pilot: Pilot[None]) -> None:
        # From an option, Page Down moves the cursor to the next heading, without scrolling to one on screen.
        assert focused(app) == "mode"
        await settle(pilot, "pagedown")
        assert focused(app) == "[Notes]"
        assert "╭─ ns.coll.thing ─" in screen(app)
        # The braces do the same.
        await settle(pilot, "right_curly_bracket", "pagedown", "pagedown", "pagedown")
        # It stops at the last.
        assert focused(app) == "[Return values]"
        # Page Up from inside a section goes to its own heading first, then the one before.
        await settle(pilot, "down", "down")
        assert focused(app) == "details"
        await settle(pilot, "pageup")
        assert focused(app) == "[Return values]"
        await settle(pilot, "left_curly_bracket")
        assert focused(app) == "[Examples]"
        await settle(pilot, "pageup")
        assert focused(app) == "[See also]"
        await settle(pilot, "pageup", "pageup", "pageup", "pageup", "pageup", "pageup")
        assert focused(app) == "[Description]"
        # At the first, the page is at its top, so the header shows.
        assert "╭─ ns.coll.thing ─" in screen(app)

    run("ns.coll.thing", steps, types=("module",))


def test_fragments_not_shown(project: World) -> None:
    async def steps(app: DocViewer, pilot: Pilot[None]) -> None:
        text = " ".join(screen(app).split())
        assert "Not shown: what the doc fragments ns.coll.built and ns.coll.nowhere add" in text

    run("ns.coll.gaps", steps)
