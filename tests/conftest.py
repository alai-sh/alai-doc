# Copyright: (c) 2026, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

from __future__ import annotations

from pathlib import Path

import pytest
from doc_data import World, ansible_core, collection, other_collection

from alai_doc import _output


@pytest.fixture(autouse=True)
def no_color(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_output, "color", "never")
    monkeypatch.setattr(_output, "verbosity", 0)


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> World:
    """A stand-in alai with ns.coll 2.0.0 in its cache, 3.0.0 being the latest, other.coll, whose doc fragment
    ns.coll's module uses, and ansible-core 2.99.0. The terminal is 80 columns wide."""
    world = World(tmp_path)
    world.add("ns.coll", collection(tmp_path / "ns.coll", "2.0.0"), "2.0.0", latest="3.0.0")
    world.add("other.coll", other_collection(tmp_path / "other.coll"), "1.0.0")
    world.add("ansible.builtin", ansible_core(tmp_path / "core"), "2.99.0")
    world.save()
    monkeypatch.setenv("ALAI_DOC_ALAI", str(world.executable()))
    monkeypatch.setenv("COLUMNS", "80")
    return world
