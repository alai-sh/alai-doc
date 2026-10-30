# Copyright: (c) 2026, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""alai-doc's command and its Markdown, with a stand-in alai (``doc_data.World``)."""

from __future__ import annotations

import pytest
from doc_data import World

from alai_doc._alai import Alai
from alai_doc._cli import main
from alai_doc._common import EXIT_ERROR, EXIT_NOT_FOUND
from alai_doc._doc import _code, _escape, _paragraph
from alai_doc._doc_model import split_arguments, usage
from alai_doc._markup import markup


def doc(*args: str) -> int:
    return main([*args, "--output-format", "markdown"])


def out(capsys: pytest.CaptureFixture[str]) -> list[str]:
    return capsys.readouterr().out.splitlines()


def test_module(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    assert doc("-t", "module", "ns.coll.thing") == 0
    assert out(capsys) == [
        "# ns.coll.thing",
        "",
        "Manage things.",
        "",
        "- Type: module",
        "- Version: ns.coll 2.0.0, from the cache; 3.0.0 is the latest.",
        "- Authors: Someone (@someone)",
        "- Added in: ns.coll 1.0.0",
        "",
        "| Attribute | Support | Details |",
        "|---|---|---|",
        "| check_mode | full |  |",
        "| diff_mode | partial | Not for rules. |",
        "| platform | posix |  |",
        "",
        "Manages a `thing` on the host.",
        "",
        "See **name** for which, and `ansible.builtin.copy` for copying.",
        "",
        "## Usage",
        "",
        "In a task:",
        "",
        "```yaml",
        "- ns.coll.thing:",
        "    name: <str>",
        "```",
        "",
        "## Options",
        "",
        # From ansible.builtin's files fragment.
        "- **mode** · `raw`",
        "",
        "  The permissions.",
        "",
        "- **mode_kind** · `str` · default `slow`",
        "",
        "  How it's done.",
        "",
        "  Choices:",
        "",
        "  - `fast`: Quickly.",
        "  - `slow` (default): Carefully.",
        "",
        "- **name** · `str` · required",
        "",
        # Escaped where Markdown would read it as emphasis.
        "  Name of the \\*\\_thing\\*.",
        "",
        "  Aliases: `thing_name`.",
        "",
        "- **old** · `bool`",
        "",
        "  Not used any more.",
        "",
        "  Added in 1.1.0.",
        "",
        "  **Deprecated**, to be removed in 3.0.0. Replaced. Alternative: Use **state**.",
        "",
        "- **rules** · `list[dict]`",
        "",
        "  Rules to apply.",
        "",
        "  - **match** · `dict`",
        "",
        "    What a rule matches.",
        "",
        "    - **conditions** · `list[dict]`",
        "",
        "      Conditions.",
        "",
        "      - **field** · `str` · required when **conditions** is given",
        "",
        "        The field.",
        "",
        "  - **port** · `int` · required when **rules** is given",
        "",
        "    The port.",
        "",
        "- **state** · `str` · default `present`",
        "",
        "  What to do.",
        "",
        "  Choices: `present` (default), `absent`.",
        "",
        # From the collection's own fragment, and other.coll's, downloaded into the cache for it.
        "- **timeout** · `int` · default `30`",
        "",
        "  How long to wait.",
        "",
        "- **token** · `str`",
        "",
        "  The token to sign in with.",
        "",
        "## Notes",
        "",
        "- Only one at a time.",
        "",
        "## See also",
        "",
        "- `ansible.builtin.copy` module",
        "- `ns.coll.thing` lookup",
        "- [The thing's site](https://example.com/thing): All about it.",
        "",
        "## Examples",
        "",
        "```yaml",
        "- name: Make a thing",
        "  ns.coll.thing:",
        '    name: "{{ item }}"',
        "```",
        "",
        "## Return values",
        "",
        "- **changed_things** · `list[str]` · returned always",
        "",
        "  The things changed.",
        "",
        '  Sample: `["a", "b"]`',
        "",
        "- **details** · `dict` · returned success",
        "",
        "  About the thing.",
        "",
        "  - **size** · `int` · returned always",
        "",
        "    How big.",
    ]


def test_lookup(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    assert doc("-t", "lookup", "ns.coll.thing") == 0
    text = "\n".join(out(capsys))
    assert "```jinja\n{{ lookup('ns.coll.thing', <terms>, endpoint=<str>) }}\n```" in text
    # A lookup's terms are its positional arguments; its one return value has no name.
    assert "## Positional\n\n- **terms** · `str` · required\n\n  The keys." in text
    assert "## Options\n\n- **endpoint** · `str` · required" in text
    # Where an option can be set, highest precedence first, and within a kind the last listed first.
    assert (
        "  var: `thing_endpoint`\n\n  env: `THING_ENDPOINT`, `OLD_THING_ENDPOINT` (deprecated, removed in 3.0.0)"
        in text
    )
    assert "  ini: `[thing] endpoint`" in text
    assert text.endswith("## Returns\n\n`list[str]` · The values found.")


def test_filter(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    assert doc("ns.coll.double") == 0
    text = "\n".join(out(capsys))
    assert "{{ <input> | ns.coll.double(<times>, sep=<str>) }}" in text
    assert "## Input\n\n- **input** · `raw` · required" in text
    assert "## Positional\n\n- **times** · `int` · required" in text
    assert "## Options\n\n- **sep** · `str` · required" in text
    assert text.endswith("## Returns\n\n`str` · The value repeated.")


def test_connection_usage(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    assert doc("ns.coll.tunnel") == 0
    text = "\n".join(out(capsys))
    assert "On a play or task:\n\n```yaml\nconnection: ns.coll.tunnel\n```" in text
    assert "As a host or group variable:\n\n```yaml\nansible_connection: ns.coll.tunnel\n```" in text
    assert "```shell\nansible-playbook --connection ns.coll.tunnel playbook.yml\n```" in text
    assert "```ini\n[defaults]\ntransport = ns.coll.tunnel\n```" in text


def test_not_shown_yet(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    assert doc("ns.coll.setup") == EXIT_ERROR
    assert capsys.readouterr().err == "error: ns.coll.setup is a role, and alai-doc doesn't show roles yet\n"


def test_more_than_one_type(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    """A name that's more than one type of plugin is an error listing each, and the -t that picks it."""
    assert doc("ns.coll.thing") == EXIT_ERROR
    assert capsys.readouterr().err == (
        "error: ns.coll.thing is more than one type of plugin, so say which with -t:\n"
        + "  alai-doc ns.coll.thing -t module  manage things\n"
        + "  alai-doc ns.coll.thing -t lookup  look things up\n"
    )


def test_short_name(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    """A short name is ansible.legacy's: ansible-core's own plugin, or where its routing leads."""
    assert doc("copy") == 0
    lines = out(capsys)
    assert lines[0] == "# ansible.builtin.copy"
    assert "- Version: ansible-core 2.99.0, the latest release." in lines
    assert doc("thing", "-t", "module") == 0
    lines = out(capsys)
    assert lines[0] == "# ns.coll.thing"
    assert "- Redirected from: `thing`" in lines


def test_short_name_not_found(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    # Ranked as alai find ranks them, without the removed one.
    assert doc("tunnel") == EXIT_NOT_FOUND
    assert capsys.readouterr().err == (
        "warning: ansible.builtin has no plugin tunnel; did you mean 'ns.coll.tunnel' or 'fork.coll.tunnel'?\n"
    )


def test_short_name_in_a_collection_project(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    """In a collection project, a short name is looked for in its own collection first, as a playbook in it would."""
    world.project = "ns.coll"
    world.save()
    assert doc("tunnel") == 0
    assert out(capsys)[0] == "# ns.coll.tunnel"


def test_tombstone(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    assert doc("gone") == EXIT_NOT_FOUND
    assert capsys.readouterr().err == "warning: ansible.builtin.gone was removed: Use ns.coll.thing instead.\n"


def test_checked_before_downloading(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    """A collection alai doesn't have yet is checked against the plugin index first: a typo isn't worth a download."""
    world.on_disk.discard("ns.coll")
    world.save()
    assert doc("ns.coll.thingy") == EXIT_NOT_FOUND
    assert capsys.readouterr().err == "warning: no index has a plugin ns.coll.thingy; did you mean 'ns.coll.thing'?\n"
    # Asked whether it's on disk, then the plugin index; never told to download it.
    runs = world.runs()
    assert [r[0] for r in runs] == ["collection", "find", "find"]
    assert "--no-download" in runs[0]


def test_fragment_not_found(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    del world.collections["other.coll"]
    world.on_disk.discard("other.coll")
    world.save()
    assert doc("-t", "module", "ns.coll.thing") == 0
    assert (
        "- Not shown: what the doc fragment `other.coll.auth` adds, which couldn't be found or read without running "
        + "code"
    ) in out(capsys)


def test_fragment_built_at_runtime_or_missing(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    """A fragment only running Python makes, as amazon.aws's boto3 is, and one its collection doesn't have, are each
    said not to be shown, and the plugin's own docs are."""
    assert doc("ns.coll.gaps") == 0
    lines = out(capsys)
    assert (
        "- Not shown: what the doc fragments `ns.coll.built` and `ns.coll.nowhere` add, which couldn't be found or "
        + "read without running code"
    ) in lines
    assert "- **name** · `str`" in lines


def test_return_fragment(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    """A fragment's RETURN adds return values, after the plugin's own, and says nothing is missing."""
    assert doc("ns.coll.gaps") == 0
    text = "\n".join(out(capsys))
    assert "## Return values\n\n- **id** · `str` · returned always" in text
    assert "- **stdout** · `str` · returned success\n\n  What it printed." in text
    assert "ns.coll.results" not in text


def test_one_run_for_the_fragments(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    assert doc("-t", "module", "ns.coll.thing") == 0
    paths = [r for r in world.runs() if r[:2] == ["collection", "path"]]
    assert paths[-1][-2:] == ["ansible.builtin", "other.coll"]


def test_settings_passed_on(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    assert doc("copy", "--offline", "--project", "/somewhere", "--index", "a=https://a.example/") == 0
    run = world.runs()[0]
    for flags in (["--offline"], ["--project", "/somewhere"], ["--index", "a=https://a.example/"]):
        at = run.index(flags[0])
        assert run[at : at + len(flags)] == flags


def test_alai_fails(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    world.fail = "error: no alai.toml found"
    world.save()
    assert doc("copy") == EXIT_ERROR
    assert capsys.readouterr().err == (
        "error: alai collection path failed with exit code 2\nerror: no alai.toml found\n"
    )


def test_installed_alai(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """Without the stand-in, the alai installed with alai-doc runs, rather than any on PATH."""
    import subprocess
    import sys

    monkeypatch.delenv("ALAI_DOC_ALAI")
    ran: list[list[str]] = []

    def run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        ran.append(command)
        return subprocess.CompletedProcess(command, 0, '{"project": null, "collections": {}}', "")

    monkeypatch.setattr(subprocess, "run", run)
    assert Alai().project_collection() is None
    assert ran[0][:5] == [sys.executable, "-m", "alai", "collection", "path"]


def test_not_a_plugin_name(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    assert doc("ns.coll") == EXIT_ERROR
    assert "isn't a plugin's name" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("text", "escaped"),
    [
        ("check_mode", "check_mode"),
        ("*_info", "\\*\\_info"),
        ("a <b> c", "a \\<b> c"),
        ("x >= 1", "x >= 1"),
        ("_private and name_", "\\_private and name\\_"),
        ("[x](y)", "\\[x](y)"),
        ("C:\\path", "C:\\\\path"),
    ],
)
def test_escape(text: str, escaped: str) -> None:
    assert _escape(text) == escaped


def test_code_spans() -> None:
    assert _code("") == '`""`'
    assert _code("a`b") == "``a`b``"
    assert _code("`a") == "`` `a ``"


def test_paragraph_start_is_not_markdown() -> None:
    assert _paragraph("# not a heading") == "\\# not a heading"
    assert _paragraph("- not a list") == "\\- not a list"
    assert _paragraph("1. not a list") == "1\\. not a list"


@pytest.mark.parametrize(
    ("kind", "documentation", "expected"),
    [
        (
            "inventory",
            {"options": {"plugin": {"required": True}, "region": {"required": True}}},
            [
                ("In an inventory source", "yaml", "plugin: ns.c.x\nregion: <str>"),
            ],
        ),
        (
            "callback",
            {"type": "stdout"},
            [
                ("In ansible.cfg", "ini", "[defaults]\nstdout_callback = ns.c.x"),
                ("As an environment variable", "shell", "ANSIBLE_STDOUT_CALLBACK=ns.c.x"),
            ],
        ),
        (
            "callback",
            {"type": "notification"},
            [
                ("In ansible.cfg", "ini", "[defaults]\ncallbacks_enabled = ns.c.x"),
                ("As an environment variable", "shell", "ANSIBLE_CALLBACKS_ENABLED=ns.c.x"),
            ],
        ),
        (
            "become",
            {},
            [
                ("On a play or task", "yaml", "become: true\nbecome_method: ns.c.x"),
                ("As a host or group variable", "yaml", "ansible_become: true\nansible_become_method: ns.c.x"),
                ("On the command line", "shell", "ansible-playbook --become --become-method ns.c.x playbook.yml"),
                ("In ansible.cfg", "ini", "[privilege_escalation]\nbecome_method = ns.c.x"),
            ],
        ),
        (
            "cache",
            {},
            [
                ("In ansible.cfg", "ini", "[defaults]\nfact_caching = ns.c.x"),
                ("As an environment variable", "shell", "ANSIBLE_CACHE_PLUGIN=ns.c.x"),
            ],
        ),
        (
            "strategy",
            {},
            [
                ("On a play", "yaml", "strategy: ns.c.x"),
                ("In ansible.cfg, for every play", "ini", "[defaults]\nstrategy = ns.c.x"),
                ("As an environment variable", "shell", "ANSIBLE_STRATEGY=ns.c.x"),
            ],
        ),
        ("vars", {}, [("In ansible.cfg", "ini", "[defaults]\nvars_plugins_enabled = host_group_vars, ns.c.x")]),
        ("shell", {}, [("As a host or group variable", "yaml", "ansible_shell_type: ns.c.x")]),
        (
            "httpapi",
            {},
            [
                (
                    "As host or group variables",
                    "yaml",
                    "ansible_connection: ansible.netcommon.httpapi\nansible_network_os: ns.c.x",
                ),
            ],
        ),
        (
            "test",
            {"options": {"_input": {}, "other": {"required": True}}},
            [
                ("In a template or expression", "jinja", "{{ <input> is ns.c.x(other=<str>) }}"),
            ],
        ),
        ("playbook", {}, []),
    ],
)
def test_usage(kind: str, documentation: dict[str, object], expected: list[tuple[str, str, str]]) -> None:

    assert usage("ns.c.x", kind, documentation) == expected


def test_host_group_vars_isnt_listed_twice() -> None:

    assert usage("ansible.builtin.host_group_vars", "vars", {})[0][2].endswith("= ansible.builtin.host_group_vars")


def test_positional_as_a_list() -> None:

    options: dict[str, object] = {"_input": {}, "a": {}, "b": {}, "c": {}}
    inputs, positional, rest = split_arguments("filter", {"options": options, "positional": ["b", "a"]})
    assert (list(inputs), list(positional), list(rest)) == (["input"], ["b", "a"], ["c"])


def test_markup() -> None:
    """alai-core's parts as the page and the viewer take them: the markup's letter, and what a link goes to."""
    assert markup(
        "See O(ns.coll.thing#lookup:endpoint=x), RV(out), O(ignore:old), M(ns.coll.thing), "
        + "P(ns.coll.thing#lookup), L(site,https://e.com), U(ftp://e.com), V(1), E(HOME), C(c).HORIZONTALLINE"
    ) == [
        ("See ", None, None),
        ("endpoint=x", "option_name", "ns.coll.thing#lookup:endpoint"),
        (", ", None, None),
        ("out", "return_value", "out"),
        (", ", None, None),
        ("old", "option_name", None),
        (", ", None, None),
        ("ns.coll.thing", "module", "ns.coll.thing"),
        (", ", None, None),
        ("ns.coll.thing", "plugin", "ns.coll.thing#lookup"),
        (", ", None, None),
        ("site", "link", "https://e.com"),
        (", ", None, None),
        ("ftp://e.com", "url", None),
        (", ", None, None),
        ("1", "option_value", None),
        (", ", None, None),
        ("HOME", "env_var", None),
        (", ", None, None),
        ("c", "code", None),
        (".", None, None),
    ]
    assert markup("O(main:name)", role=True) == [("name", "option_name", "main:name")]
    assert markup("broken C(here") == [("broken ", None, None), ("C(here", None, None)]
