# alai-doc

[![PyPI](https://img.shields.io/pypi/v/alai-doc)](https://pypi.org/project/alai-doc/)
[![CI](https://github.com/alai-sh/alai-doc/actions/workflows/ci.yml/badge.svg)](https://github.com/alai-sh/alai-doc/actions/workflows/ci.yml)

alai-doc shows the documentation of a plugin or role in an Ansible
collection without a browser. The docs open in a viewer on a terminal, and
are printed as Markdown anywhere else.

> **Preview:** alai-doc is released in preview, as a 0.x version under
> [semantic versioning](https://semver.org/). The viewer and the command line
> can still change as they're worked out, so a release that breaks something
> bumps the minor version, from 0.1 to 0.2, and lists the change in the
> [changelog](https://github.com/alai-sh/alai-doc/blob/main/CHANGELOG.md). A
> patch release, such as 0.1.1, only fixes bugs.

```console
$ alai-doc ansible.builtin.copy
$ alai-doc win_copy --output-format markdown
```

## Installing

alai-doc is published on [PyPI](https://pypi.org/project/alai-doc/), and
installs alai with it. When it's used often, [uv](https://docs.astral.sh/uv/)
can install it as a tool so `alai-doc` is on the `PATH`.

```console
$ uv tool install alai-doc
```

The [documentation](https://alai.sh/alai-doc/) covers
[finding a plugin](https://alai.sh/alai-doc/finding-plugins/), the
[viewer's keys](https://alai.sh/alai-doc/reading/) and
[every option](https://alai.sh/alai-doc/cli/).

## Developing

It is built and checked with [uv](https://docs.astral.sh/uv/).

```console
$ uv sync
$ uv run tox run -f sanity
$ uv run tox run -f py314
```

The docs at [alai.sh/alai-doc](https://alai.sh/alai-doc/) are built from
`docs/` with `uv run tox run -e docs`. The build also writes the CLI
reference and records the terminal recordings with
[cli-recorder](https://github.com/alai-sh/cli-recorder), so it needs Linux
or macOS.

## Not done yet

- Finding a plugin from the viewer, keyboard links, picking from part of a
  name or a glob, and Tab completion.

## License

MIT, see [LICENSE](https://github.com/alai-sh/alai-doc/blob/main/LICENSE).
