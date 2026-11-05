---
description: Reading the documentation of Ansible plugins and roles in the terminal, from collections found by alai.
---

# alai-doc

alai-doc is a command line tool that can be used to view the documentation of
Ansible plugins and roles in the terminal.

!!! warning "Preview"

    alai-doc is released in preview, as a 0.x version under
    [semantic versioning](https://semver.org/). The viewer and the command
    line can still change as they're worked out, so a release that breaks
    something bumps the minor version, from 0.1 to 0.2, and lists the change
    in the [changelog](https://github.com/alai-sh/alai-doc/blob/main/CHANGELOG.md).
    A patch release, such as 0.1.1, only fixes bugs.

```console
$ alai-doc ansible.builtin.copy
$ alai-doc win_copy
$ alai-doc community.general.json_query --output-format markdown
```

[Opening an option, then the other tabs](casts/overview.cast){ .cli-cast .cli-cast-schemes }

The viewer opens on a module with each option folded to a single line.
Pressing Enter on `name` opens it, and `Tab` moves through the usage,
examples and return values, which each have a tab of their own.
{: .cli-cast-description }

The recordings show a terminal with 24-bit color and a dark background. How
the viewer looks on another terminal depends on the colors it shows and its
background, as [Colors](reading.md#colors) covers.

alai-doc does not need the collection to be installed. It asks
[alai](https://docs.alai.sh/) where the collection is, which is the project
directory when it's installed there and alai's cache otherwise. A collection
that isn't on disk yet is downloaded into the cache first.

## Installing

alai-doc is published on [PyPI](https://pypi.org/project/alai-doc/), and
installs alai with it. When it's used often, [uv](https://docs.astral.sh/uv/)
can install it as a tool so `alai-doc` is on the `PATH`.

```console
$ uv tool install alai-doc
```

## What it shows

The documentation of modules and other plugins is generated from their
documentation strings. Doc fragments are applied automatically where possible,
but some doc fragments are generated at runtime and can't be read without
running Python code. The header names any doc fragment that couldn't be
applied.

Role documentation comes from the role's argument spec in
`meta/argument_specs.yml`, its `README.md`, or both. When a role has both, the
argument spec is shown first and the README is in a tab after it. When a role
has only a README, the README is shown. A role with neither is shown as having
no documentation.

[A role's entry points, then its README](casts/role-readme.cast){ .cli-cast .cli-cast-schemes }

The role's entry points are listed first, and pressing Enter on `configure`
goes to the options it takes. Pressing `Tab` shows the README, and pressing it
again goes back to the docs.
{: .cli-cast-description }

## Where to go next

- [Finding a plugin](finding-plugins.md) covers full and short names, picking
  a plugin's type, and which copy of a collection the docs come from.
- [Reading the docs](reading.md) covers the viewer's keys and printing the
  docs as Markdown.
- The [CLI reference](cli.md) lists every option alai-doc takes.
