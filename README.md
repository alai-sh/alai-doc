# alai-doc

> **Warning** alai-doc is a proof of concept. Nothing is released, and
> anything can change.

Ansible plugin doc viewer that can be used to read plugin and role
documentation in a collection without a browser. Modules and other plugins
render the documentation from the provided doc file whereas roles will use
the argument spec definition or the role's `README.md` if present.

```console
$ alai-doc ansible.builtin.copy
$ alai-doc win_copy --output-format markdown
```

Using a short name without the namespace.name will attempt to find the plugin
like a normal Ansible play does, for example through the builtin routing
rules.

If the name provided matches more than one type of plugin in the collection,
use `-t` to specify which type to display.

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

- Finding a plugin from the viewer, keyboard links, picking from part of a
  name or a glob, and Tab completion.

## License

MIT, see [LICENSE](LICENSE).
