---
description: Reading the documentation of Ansible plugins and roles in the terminal, from collections found by alai.
---

# alai-doc

!!! warning "Proof of concept"

    alai-doc is a proof of concept. Nothing is released, and anything can
    change.

alai-doc is a command line tool that can be used to view the documentation of
Ansible plugins and roles in the terminal.

```console
$ alai-doc ansible.builtin.copy
$ alai-doc win_copy
$ alai-doc community.general.json_query --output-format markdown
```

[Opening an option, then the examples and return values](casts/overview.cast){ .cli-cast }

The viewer opens on a module with each option folded to a single line.
Pressing Enter on `name` opens it, and `}` jumps from section to section
through to the examples and return values.
{: .cli-cast-description }

alai-doc does not need the collection to be installed. It asks
[alai](https://docs.alai.sh/) where the collection is, which is the project
directory when it's installed there and alai's cache otherwise. A collection
that isn't on disk yet is downloaded into the cache first.

## Installing

alai-doc isn't on PyPI yet, so it's installed from its repository. alai is
built from source as part of the install, which needs
[cargo](https://www.rust-lang.org/tools/install).

```console
$ uv tool install git+https://github.com/alai-sh/alai-doc
```

## What it shows

The documentation of modules and other plugins is generated from their
documentation strings. Doc fragments are applied automatically where possible,
but some doc fragments are generated at runtime and can't be read without
running Python code. The header names any doc fragment that couldn't be
applied.

Role documentation comes from the role's argument spec in
`meta/argument_specs.yml`, its `README.md`, or both. When a role has both, the
argument spec is shown first with a link to the README. When a role has only a
README, the README is shown. A role with neither is shown as having no
documentation.

[A role's entry points, then its README](casts/role-readme.cast){ .cli-cast }

The role's entry points are listed first, and pressing Enter on `configure`
goes to the options it takes. Clicking "See the README" in the header opens
the README, and `[` goes back to where the docs were left.
{: .cli-cast-description }

## Where to go next

- [Finding a plugin](finding-plugins.md) covers full and short names, picking
  a plugin's type, and which copy of a collection the docs come from.
- [Reading the docs](reading.md) covers the viewer's keys and printing the
  docs as Markdown.
- The [CLI reference](cli.md) lists every option alai-doc takes.
