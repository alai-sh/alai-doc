# Copyright: (c) 2026, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""alai, run as a command for what needs its settings, project, lock and cache: where a collection's files are
(``alai collection path``) and which plugins the indexes have (``alai find``). The collection's files are read here,
with alai-core's extractor."""

from __future__ import annotations

import collections.abc as _c
import json
import os
import subprocess
import sys
import typing as _t

from ._common import Error, Record
from ._output import debug, trace

if _t.TYPE_CHECKING:
    from alai_core import extract as ape

BUILTIN = "ansible.builtin"
EDA_BUILTIN = "eda.builtin"
LEGACY = "ansible.legacy"
"""ansible.builtin, as a play finds a short name: a plugin's file before its routing."""

PROJECT = "project"
"""The collection project's own collection, read from its checkout."""
INSTALLED = "installed"
LOCKED = "locked"
CACHED = "cached"
DOWNLOADED = "downloaded"

ALAI_ENV = "ALAI_DOC_ALAI"
"""An alai executable to run instead of the one installed with alai-doc, as the tests' stand-in."""


class Located(Record):
    """A collection's files on disk, as ``alai collection path`` gives them."""

    __slots__ = ("latest", "name", "origin", "path", "version")

    def __init__(self, name: str, version: str | None, path: str, origin: str, latest: str | None = None) -> None:
        self.name = name
        self.version = version
        self.path = path
        self.origin = origin
        """``PROJECT``, ``INSTALLED``, ``LOCKED``, ``CACHED`` or ``DOWNLOADED``."""
        self.latest = latest
        """For a ``CACHED`` collection, the latest version on the indexes when it's newer; else None."""


class Alai:
    """alai, run with ``args``, the settings flags alai-doc was given (``--project``, ``--offline``...). Each answer is
    kept for the rest of the run, as the viewer asks again on every page. With ``quiet``, as under the viewer, alai's
    messages and progress are kept off the screen."""

    def __init__(self, args: _c.Sequence[str] = (), *, quiet: bool = False) -> None:
        self.args = list(args)
        self.quiet = quiet
        self._project: tuple[str | None] | None = None
        self._located: dict[str, Located | str | None] = {}
        self._on_disk: dict[str, bool] = {}
        self._read: dict[str, ape.Collection] = {}

    def project_collection(self) -> str | None:
        """The collection the collection project is, or None outside one."""
        if self._project is None:
            self._collection_path([])
        return self._project[0] if self._project is not None else None

    def locate(self, name: str) -> Located | None:
        """Collection ``name``'s files, downloading it into alai's cache if it has to; None if no index has it."""
        if name not in self._located:
            self.prefetch([name])
        found = self._located[name]
        if isinstance(found, str):
            raise Error(found)
        return found

    def prefetch(self, names: _c.Iterable[str]) -> None:
        """Locate each of ``names`` not already located, in one run of alai."""
        wanted = [n for n in dict.fromkeys(names) if n not in self._located]
        if wanted:
            self._located.update(self._collection_path(wanted))

    def has_version(self, name: str) -> bool:
        """Whether alai has a version of ``name`` on disk, or has decided on one, so ``locate`` won't download the
        latest: only for the latest is the plugin index a check on what it has."""
        if isinstance(self._located.get(name), Located):
            return True
        if name not in self._on_disk:
            found = self._collection_path([name], download=False).get(name)
            self._on_disk[name] = isinstance(found, Located)
        return self._on_disk[name]

    def read(self, located: Located) -> ape.Collection:
        """The collection's plugins with their docs, as alai-core's extractor reads them: ``ansible.builtin`` and
        ``eda.builtin`` from ansible-core's and ansible-rulebook's source."""
        if located.path not in self._read:
            from alai_core import extract

            reader = {BUILTIN: extract.ansible_core, EDA_BUILTIN: extract.ansible_rulebook}.get(
                located.name, extract.extract
            )
            try:
                collection = reader(located.path, docs=True)
            except (OSError, ValueError) as e:
                raise Error(f"can't read the docs of {located.name} at {located.path} because {e}") from None
            for issue in collection.issues:
                trace(f"{located.name}: {issue.path}: {issue.kind} {issue.detail}".rstrip())
            self._read[located.path] = collection
        return self._read[located.path]

    def find(self, query: str, *, exact: bool = False, types: _c.Sequence[str] = ()) -> list[dict[str, _t.Any]] | None:
        """The plugins ``alai find`` lists for ``query``, ranked, each a plugin index line with its ``fqcn``; None if
        it can't search, as with no plugin index configured."""
        argv = ["find", *(["--exact"] if exact else []), *(a for t in types for a in ("--type", t))]
        code, out, err = self._run([*argv, "--", query], capture=True)
        if code == 1 and not out.strip():
            return []
        try:
            plugins = json.loads(out)["plugins"]
        except (ValueError, KeyError, TypeError):
            debug(f"alai find {query} gave nothing to check names against: {err.strip() or f'exit code {code}'}")
            return None
        return [p for p in plugins if isinstance(p, dict)]

    def _collection_path(self, names: list[str], *, download: bool = True) -> dict[str, Located | str | None]:
        argv = ["collection", "path", *([] if download else ["--no-download"])]
        # Only a download has progress worth showing.
        code, out, err = self._run([*argv, "--", *names], capture=self.quiet or not download or not names)
        try:
            result = json.loads(out)
            self._project = (result["project"],)
            found = result["collections"]
            return {name: _located(name, found[name]) for name in names}
        except (ValueError, KeyError, TypeError):
            # Without err, alai's own message was shown.
            said = f"\n{err.strip()}" if err.strip() else ", as it says above"
            raise Error(f"alai collection path failed with exit code {code}{said}") from None

    def _run(self, argv: list[str], *, capture: bool) -> tuple[int, str, str]:
        """alai's exit code, stdout and stderr. stderr is only captured with ``capture``, to quote when alai fails:
        otherwise its progress and messages show."""
        # The alai alai-doc depends on, in its own environment, whatever else is on PATH.
        alai = [os.environ[ALAI_ENV]] if os.environ.get(ALAI_ENV) else [sys.executable, "-m", "alai"]
        command = [
            *alai,
            *argv[: argv.index("--")],
            *self.args,
            "--output-format",
            "json",
            *argv[argv.index("--") :],
        ]
        trace(f"running {' '.join(command)}")
        try:
            done = subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE if capture else None, text=True, check=False
            )
        except OSError as e:
            raise Error(f"can't run {alai[0]} ({e.strerror or e})") from None
        return done.returncode, done.stdout, done.stderr or ""


def _located(name: str, entry: object) -> Located | str | None:
    """A collection from ``alai collection path``'s JSON: where it is, None if it isn't found, or why it failed."""
    if entry is None:
        return None
    if not isinstance(entry, dict):
        raise TypeError(name)
    entry = _t.cast("dict[str, _t.Any]", entry)
    if "error" in entry:
        return str(entry["error"])
    return Located(name, entry["version"], entry["path"], entry["origin"], entry.get("latest"))
