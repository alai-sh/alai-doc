# alai-doc

> **Warning** alai-doc is a proof of concept. Nothing is released, and
> anything can change.

Ansible plugin documentation without Ansible or the collection installed,
as `ansible-doc` shows it. On a terminal it opens in a viewer, with each
option collapsed to a line, links to other plugins and options to follow,
and back and forward through what's been read. Anywhere else it's printed
as Markdown.

```console
$ alai-doc ansible.builtin.copy
$ alai-doc win_copy --output-format markdown
```

A short name is found as a play finds one, in the collection project's own
collection and then as `ansible.legacy`. A name that's more than one type
of plugin needs `-t` to say which.

## Developing

Building it needs `cargo` as well as [uv](https://docs.astral.sh/uv/), as
alai and alai-core are built from source until they're on PyPI.

```console
$ uv sync
$ uv run tox run -f sanity
$ uv run tox run -f py314
```

alai is pinned to a commit of alai-cli in `[project] dependencies`, as
alai-cli pins alai-core. To work on both at once, point it at a local
checkout in `[tool.uv.sources]`.

```toml
alai = { path = "../alai-cli", editable = true }
```

## Not done yet

- Roles and Event-Driven Ansible's plugins are an error, though alai-core
  reads both.
- Finding a plugin from the viewer, keyboard links, picking from part of a
  name or a glob, and Tab completion.

## License

MIT, see [LICENSE](LICENSE).
