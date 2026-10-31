# Copyright: (c) 2026, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""Collections with plugin docs, an ansible-core source tree, and a stand-in for alai that says where they are, for
the alai-doc tests."""

from __future__ import annotations

import json
import stat
import sys
import typing as _t
from pathlib import Path

MODULE = '''
DOCUMENTATION = r"""
module: thing
short_description: manage things
version_added: 1.0.0
author:
  - Someone (@someone)
description:
  - Manages a C(thing) on the host.
  - See O(name) for which, and M(ansible.builtin.copy) for copying.
extends_documentation_fragment:
  - files
  - ns.coll.common
  - other.coll.auth
options:
  name:
    description: Name of the *_thing*.
    type: str
    required: true
    aliases: [thing_name]
  state:
    description: What to do.
    type: str
    choices: [present, absent]
    default: present
  mode_kind:
    description: How it's done.
    type: str
    choices:
      fast: Quickly.
      slow: Carefully.
    default: slow
  rules:
    description: Rules to apply.
    type: list
    elements: dict
    suboptions:
      port:
        description: The port.
        type: int
        required: true
      match:
        description: What a rule matches.
        type: dict
        suboptions:
          conditions:
            description: Conditions.
            type: list
            elements: dict
            suboptions:
              field:
                description: The field.
                type: str
                required: true
  old:
    description: Not used any more.
    type: bool
    version_added: 1.1.0
    deprecated:
      why: Replaced.
      alternative: Use O(state).
      removed_in: 3.0.0
attributes:
  check_mode:
    support: full
    description: Can run in check mode.
  diff_mode:
    support: partial
    description: Shows some differences.
    details: Not for rules.
  platform:
    platforms: posix
    description: Where it runs.
notes:
  - Only one at a time.
seealso:
  - module: ansible.builtin.copy
  - plugin: ns.coll.thing
    plugin_type: lookup
  - link: https://example.com/thing
    name: The thing's site
    description: All about it.
"""

EXAMPLES = r"""
- name: Make a thing
  ns.coll.thing:
    name: "{{ item }}"
"""

RETURN = r"""
changed_things:
  description: The things changed.
  type: list
  elements: str
  returned: always
  sample: [a, b]
details:
  description: About the thing.
  type: dict
  returned: success
  contains:
    size:
      description: How big.
      type: int
      returned: always
"""
'''

FRAGMENT = '''
class ModuleDocFragment:
    DOCUMENTATION = r"""
options:
  timeout:
    description: How long to wait.
    type: int
    default: 30
"""
'''

AUTH_FRAGMENT = '''
class ModuleDocFragment:
    DOCUMENTATION = r"""
options:
  token:
    description: The token to sign in with.
    type: str
"""
'''

GAPS = '''
DOCUMENTATION = r"""
module: gaps
short_description: show what fragments miss
description: Uses fragments that can't all be read.
extends_documentation_fragment:
  - ns.coll.built
  - ns.coll.nowhere
options:
  name:
    description: The name.
    type: str
"""

RETURN = r"""
extends_documentation_fragment: ns.coll.results
id:
  description: Its ID.
  type: str
  returned: always
"""
'''

BUILT_FRAGMENT = '''
from ansible_collections.ns.coll.plugins.module_utils import versions


class ModuleDocFragment:
    # Built when the class is made, as amazon.aws's boto3 fragment is, so only running it gives the text.
    def __init__(self):
        self.DOCUMENTATION = f"""
requirements:
  - thing >= {versions.MINIMUM}
"""
'''

RESULTS_FRAGMENT = '''
class ModuleDocFragment:
    DOCUMENTATION = r"""
options: {}
"""

    RETURN = r"""
stdout:
  description: What it printed.
  type: str
  returned: success
"""
'''

LOOKUP = '''
DOCUMENTATION = r"""
name: thing
short_description: look things up
description: Looks things up.
options:
  _terms:
    description: The keys.
    required: true
  endpoint:
    description: Where to look.
    type: string
    required: true
    env:
      - name: OLD_THING_ENDPOINT
        deprecated:
          why: renamed
          version: "3.0.0"
      - name: THING_ENDPOINT
    ini:
      - section: thing
        key: endpoint
    vars:
      - name: thing_endpoint
"""

RETURN = r"""
_raw:
  description: The values found.
  type: list
  elements: str
"""
'''

FILTER = """
def double(value, times=2):
    return value * times


class FilterModule:
    def filters(self):
        return {"double": double}
"""

FILTER_DOCS = """
DOCUMENTATION:
  name: double
  short_description: double a value
  description: Repeats a value.
  positional: _input, times
  options:
    _input:
      description: The value.
      type: raw
      required: true
    times:
      description: How many times.
      type: int
      required: true
    sep:
      description: Between each.
      type: str
      required: true
RETURN:
  _value:
    description: The value repeated.
    type: str
"""

CONNECTION = '''
DOCUMENTATION = r"""
name: tunnel
short_description: connect through a tunnel
description: Connects through a tunnel.
options:
  host:
    description: Where to.
    vars:
      - name: ansible_host
"""
'''

ROLE_SPEC = b"""
argument_specs:
  main:
    short_description: Set things up.
    author: Someone
    options:
      thing_name:
        type: str
        required: true
        description: The thing, or O(install:version) to install it.
  install:
    description:
      - Install the thing.
      - Then start it.
    options:
      thing_name:
        type: str
        description: The thing to install.
      version:
        type: str
        default: latest
        description: Which version.
"""

README = b"""Plain role
==========

Sets up the plain thing, see [the guide](https://e.com/guide) or [defaults](defaults/main.yml).

## Variables

| Variable | Default |
|---|---|
| `plain_name` | `plain` |
"""

TOOLS_SPEC = b"""
argument_specs:
  build:
    short_description: Build it.
  zap/all:
    short_description: Remove everything.
"""

SOLO_SPEC = b"""
argument_specs:
  main:
    short_description: Do one thing.
    options:
      count:
        type: int
        description: How many.
"""

EVENT_SOURCE = '''
DOCUMENTATION = r"""
short_description: Receive events from a hook.
description: Listens for events.
options:
  port:
    description: The port.
    type: int
    required: true
"""
'''

EVENT_FILTER = '''
DOCUMENTATION = r"""
short_description: Tidy event keys.
options:
  overwrite:
    description: Whether to replace a key.
    type: bool
    default: true
"""
'''

CORE_COPY = '''
DOCUMENTATION = r"""
module: copy
short_description: Copy files to remote locations
description: Copies files.
extends_documentation_fragment: files
options:
  dest:
    description: Where to.
    type: path
    required: true
"""
'''

CORE_FILES = '''
class ModuleDocFragment:
    DOCUMENTATION = r"""
options:
  mode:
    description: The permissions.
    type: raw
"""
'''

CORE_RUNTIME = b"""
plugin_routing:
  modules:
    thing:
      redirect: ns.coll.thing
    gone:
      tombstone:
        removal_version: "2.0"
        warning_text: Use ns.coll.thing instead.
"""


def _write(root: Path, files: dict[str, str | bytes]) -> Path:
    for name, data in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode())
    return root


def collection(root: Path, version: str, *, lookup: bool = True) -> Path:
    """ns.coll at ``version``, as a source checkout."""
    galaxy = f"namespace: ns\nname: coll\nversion: {version}\nreadme: README.md\nauthors: [me]\n"
    files: dict[str, str | bytes] = {
        "galaxy.yml": galaxy,
        "plugins/modules/thing.py": MODULE,
        "plugins/doc_fragments/common.py": FRAGMENT,
        "plugins/modules/gaps.py": GAPS,
        "plugins/doc_fragments/built.py": BUILT_FRAGMENT,
        "plugins/doc_fragments/results.py": RESULTS_FRAGMENT,
        "plugins/module_utils/versions.py": "MINIMUM = '1.0'\n",
        "plugins/filter/double.py": FILTER,
        "plugins/filter/double.yml": FILTER_DOCS,
        "plugins/connection/tunnel.py": CONNECTION,
        "roles/setup/meta/argument_specs.yml": ROLE_SPEC,
        "roles/setup/tasks/main.yml": b"- ansible.builtin.debug: {}\n",
        "roles/setup/tasks/install.yml": b"- ansible.builtin.debug: {}\n",
        "roles/solo/meta/argument_specs.yml": SOLO_SPEC,
        "roles/solo/tasks/main.yml": b"- ansible.builtin.debug: {}\n",
        "roles/solo/README.md": b"# Solo\n\nMore about solo.\n",
        "roles/plain/tasks/main.yml": b"- ansible.builtin.debug: {}\n",
        "roles/plain/README.md": README,
        "roles/tools/meta/argument_specs.yml": TOOLS_SPEC,
        "roles/tools/tasks/zap/all.yaml": b"- ansible.builtin.debug: {}\n",
        "extensions/eda/plugins/event_source/hook.py": EVENT_SOURCE,
        "extensions/eda/plugins/event_filter/tidy.py": EVENT_FILTER,
    }
    if lookup:
        files["plugins/lookup/thing.py"] = LOOKUP
    return _write(root, files)


def other_collection(root: Path) -> Path:
    galaxy = "namespace: other\nname: coll\nversion: 1.0.0\nreadme: README.md\nauthors: [me]\n"
    return _write(root, {"galaxy.yml": galaxy, "plugins/doc_fragments/auth.py": AUTH_FRAGMENT})


def ansible_core(root: Path, version: str = "2.99.0") -> Path:
    """ansible-core's source, as alai keeps it in its cache."""
    return _write(
        root,
        {
            "lib/ansible/release.py": f"__version__ = '{version}'\n",
            "lib/ansible/modules/copy.py": CORE_COPY,
            "lib/ansible/plugins/doc_fragments/files.py": CORE_FILES,
            "lib/ansible/config/ansible_builtin_runtime.yml": CORE_RUNTIME,
        },
    )


INDEX_PLUGINS: list[dict[str, _t.Any]] = [
    {"type": "module", "name": "thing", "collection": "ns.coll", "short_description": "manage things"},
    {"type": "lookup", "name": "thing", "collection": "ns.coll", "short_description": "look things up"},
    {"type": "filter", "name": "double", "collection": "ns.coll", "short_description": "double a value"},
    {"type": "connection", "name": "tunnel", "collection": "ns.coll", "short_description": "connect"},
    {"type": "event_source", "name": "hook", "collection": "ns.coll", "short_description": "Receive events."},
    # Somewhere else with a plugin by a name ansible-core doesn't have, to suggest, and one removed.
    {"type": "connection", "name": "tunnel", "collection": "fork.coll", "short_description": "a copy"},
    {"type": "connection", "name": "tunnel", "collection": "gone.coll", "routing": {"tombstone": {}}},
]
"""What the stand-in ``alai find`` searches, as plugin index lines."""


class World:
    """What the stand-in alai knows: where each collection is, whether it's already on disk, the collection project,
    and the plugin index ``alai find`` searches. Each run is logged, as its arguments."""

    def __init__(self, tmp_path: Path) -> None:
        self.root = tmp_path
        self.file = tmp_path / "world.json"
        self.log = tmp_path / "alai.log"
        self.project: str | None = None
        self.collections: dict[str, dict[str, _t.Any] | None] = {}
        self.on_disk: set[str] = set()
        self.plugins = [{**p, "fqcn": f"{p['collection']}.{p['name']}", "matched": True} for p in INDEX_PLUGINS]
        self.fail: str | None = None

    def add(
        self, name: str, path: Path, version: str | None, origin: str = "cached", latest: str | None = None
    ) -> None:
        self.collections[name] = {"version": version, "path": str(path), "origin": origin, "latest": latest}
        self.on_disk.add(name)

    def save(self) -> None:
        data: dict[str, object] = {
            "project": self.project,
            "collections": self.collections,
            "on_disk": sorted(self.on_disk),
            "plugins": self.plugins,
            "fail": self.fail,
        }
        self.file.write_text(json.dumps(data))

    def runs(self) -> list[list[str]]:
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def executable(self) -> Path:
        script = self.root / "alai"
        script.write_text(f"#!{sys.executable}\n" + _FAKE_ALAI.format(world=str(self.file), log=str(self.log)))
        script.chmod(script.stat().st_mode | stat.S_IXUSR)
        return script


_FAKE_ALAI = """
import fnmatch, json, sys

world = json.load(open({world!r}))
with open({log!r}, "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\\n")
if world["fail"]:
    sys.stderr.write(world["fail"] + "\\n")
    sys.exit(2)
args = sys.argv[1:]
cut = args.index("--")
options, names = args[:cut], args[cut + 1 :]
if args[:2] == ["collection", "path"]:
    download = "--no-download" not in options
    found = {{}}
    for name in names:
        entry = world["collections"].get(name)
        found[name] = entry if download or name in world["on_disk"] else None
    print(json.dumps({{"v": 1, "project": world["project"], "collections": found}}))
    sys.exit(1 if None in found.values() else 0)
if args[0] == "find":
    query = names[0]
    types = [options[i + 1] for i, a in enumerate(options) if a == "--type"]
    exact = "--exact" in options
    def matches(p):
        name = p["fqcn"] if "." in query else p["name"]
        hit = fnmatch.fnmatchcase(name, query) if "*" in query else name == query if exact else query in name
        return hit and (not types or p["type"] in types)
    plugins = [p for p in world["plugins"] if matches(p)]
    if not plugins:
        sys.stderr.write(f"warning: no plugin matches '{{query}}'\\n")
        sys.exit(1)
    print(json.dumps({{"v": 1, "plugins": plugins, "collections": {{}}, "omitted": 0}}))
    sys.exit(0)
sys.exit(2)
"""
