# alai-doc

> **Warning** alai-doc is a proof of concept. Nothing is released, and
> anything can change.

alai-doc shows the documentation of a plugin or role in an Ansible
collection without a browser. The docs open in a viewer on a terminal, and
are printed as Markdown anywhere else.

```console
$ alai-doc ansible.builtin.copy
$ alai-doc win_copy --output-format markdown
```

The [documentation](https://alai.sh/alai-doc/) covers
[finding a plugin](https://alai.sh/alai-doc/finding-plugins/), the
[viewer's keys](https://alai.sh/alai-doc/reading/) and
[every option](https://alai.sh/alai-doc/cli/).

## Developing

Building it needs `cargo` as well as [uv](https://docs.astral.sh/uv/), as
alai and alai-core are built from source until they're on PyPI.

```console
$ uv sync
$ uv run tox run -f sanity
$ uv run tox run -f py314
```

alai is pinned to a commit of alai in `[project] dependencies`, as
alai pins alai-core. To work on both at once, point it at a local
checkout in `[tool.uv.sources]`.

```toml
alai-sh = { path = "../alai", editable = true }
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
