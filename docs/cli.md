---
description: alai-doc's command line and the options it takes.
---

<!-- Written by python -m cli_recorder reference from alai-doc's argument parser. Edit the help there, not here. -->

# CLI reference

alai-doc's command line, with what it does and the options it takes, as
`alai-doc --help` shows them. The recordings were made when these docs were
built, so their output is alai-doc's own, though the collections are only
examples.

## alai-doc

Show a plugin's documentation, with its options, examples and return values, as ansible-doc does. It opens in a viewer on a terminal, and is printed as Markdown otherwise. The docs are read from the copy of the collection alai finds, as alai collection path does, so a collection that isn't on disk yet is downloaded into alai's cache. ansible.builtin comes from the latest ansible-core release.

```console
$ alai-doc [OPTIONS] NAME
```

### Arguments

| Argument | Description |
|---|---|
| `NAME` | The plugin's full name, such as ansible.windows.win_copy, or its short name, win_copy, found as a play would find it |

### Options

| Option | Description |
|---|---|
| `-t`, `--type TYPE` | The plugin's type, as ansible-doc `-t` names them (module, lookup, filter...), for a name more than one type has |
| `--output-format {markdown}` | Markdown to print the docs as Markdown rather than open the viewer, which is otherwise used on a terminal |
| `-v`, `--verbose` | Say more, and `-vv` for every step |
| `-q`, `--quiet` | Only show errors |
| `--color {auto,always,never}` | Color output |
| `--no-progress` | Don't show alai's progress |

### Alai's settings

| Option | Description |
|---|---|
| `--project DIR` | Find the project from DIR |
| `--offline` | Use only what's cached |
| `--index NAME=URL` | An index, which can be repeated |
