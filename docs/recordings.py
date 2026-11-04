# Copyright: (c) 2026, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""The fixture for the docs' terminal recordings in ``docs/recordings.toml``, loaded by ``python -m cli_recorder``.

The recordings read the tests' collections through the tests' stand-in for alai, so the docs build never reaches the
network.
"""

from __future__ import annotations

import collections.abc as _c
import contextlib
import pathlib
import sys

sys.path.insert(0, "tests")

from doc_data import World, _write, ansible_core, collection, other_collection

WEBSERVER_SPEC = b"""
argument_specs:
  main:
    short_description: Install and start a web server.
    description:
      - Installs the web server package and starts its service.
    options:
      webserver_port:
        type: int
        default: 80
        description: The port the server listens on.
      webserver_packages:
        type: list
        elements: str
        default: [nginx]
        description: The packages to install.
  configure:
    short_description: Write the web server's configuration.
    options:
      webserver_sites:
        type: list
        elements: dict
        required: true
        description: The sites to serve.
        options:
          name:
            type: str
            required: true
            description: The site's host name.
          root:
            type: path
            description: The directory the site is served from.
"""

WEBSERVER_README = b"""# ns.coll.webserver

Installs a web server and serves one or more sites from it.

## Example playbook

```yaml
- hosts: web
  roles:
    - role: ns.coll.webserver
      webserver_port: 8080
```

## Notes

The `configure` entry point can be run on its own to change the sites
without reinstalling anything.
"""


@contextlib.contextmanager
def environment(root: pathlib.Path, _scenarios: dict[str, object]) -> _c.Generator[dict[str, str]]:
    """A stand-in alai with ns.coll 2.0.0 cached, 3.0.0 the latest, other.coll and ansible-core 2.99.0. ns.coll has
    the role webserver too."""
    world = World(root)
    coll = collection(root / "ns.coll", "2.0.0")
    # A role with entry points as well as a README, which the tests' collection doesn't have.
    _write(
        coll / "roles" / "webserver",
        {
            "meta/argument_specs.yml": WEBSERVER_SPEC,
            "tasks/main.yml": b"- ansible.builtin.debug: {}\n",
            "tasks/configure.yml": b"- ansible.builtin.debug: {}\n",
            "README.md": WEBSERVER_README,
        },
    )
    world.add("ns.coll", coll, "2.0.0", latest="3.0.0")
    world.add("other.coll", other_collection(root / "other.coll"), "1.0.0")
    world.add("ansible.builtin", ansible_core(root / "core"), "2.99.0")
    world.save()
    # cli-recorder sets only TERM=xterm-256color, which squeezes the viewer's theme into 256 colors. The player shows
    # 24-bit color, as most terminals do.
    yield {"ALAI_DOC_ALAI": str(world.executable()), "COLORTERM": "truecolor"}
