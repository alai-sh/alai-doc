# Copyright: (c) 2026, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""The flags alai-doc gives alai, checked against the alai installed with it, so a rename in alai fails here."""

from __future__ import annotations

import re
import subprocess
import sys

import pytest

from alai_doc._cli import _alai_args, _parser

COMMANDS: dict[tuple[str, ...], tuple[str, ...]] = {
    ("collection", "path"): ("--no-download", "--output-format"),
    ("find",): ("--exact", "--type", "--output-format"),
}
"""Each command alai-doc runs (``_alai.py``), with the flags it adds of its own."""


def forwarded() -> set[str]:
    """Every flag ``_alai_args`` gives, with each option alai-doc has set. -q and -v can't be given together."""
    flags: set[str] = set()
    for argv in (
        ["x", "--project", "p", "--offline", "--index", "a=b", "-q", "--no-progress", "--color", "never"],
        ["x", "-vv"],
    ):
        flags.update(a for a in _alai_args(_parser().parse_args(argv)) if a.startswith("-"))
    return flags


@pytest.mark.parametrize("command", list(COMMANDS), ids=" ".join)
def test_alai_has_the_flags(command: tuple[str, ...]) -> None:
    done = subprocess.run(  # noqa: S603 - alai from this environment, with fixed arguments
        [sys.executable, "-m", "alai", *command, "--help"], capture_output=True, text=True, check=True
    )
    listed = set(re.findall(r"-{1,2}[a-z][a-z-]*", done.stdout))
    missing = (forwarded() | set(COMMANDS[command])) - listed
    assert not missing, f"alai {' '.join(command)} has no {', '.join(sorted(missing))}"
