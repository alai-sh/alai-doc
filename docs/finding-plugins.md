---
description: How alai-doc finds a plugin from its full or short name, and which copy of a collection the docs are read from.
---

# Finding a plugin

alai-doc takes the name of one plugin or role. A full name, such as
`ansible.windows.win_copy`, names the collection the docs are read from. A
short name, such as `win_copy`, is found as a play running in the current
project would find it.

## Short names

When a task uses a short name, Ansible looks for it in ansible-core's own
plugins and follows ansible-core's routing to the collection the plugin
moved to. alai-doc does the same, so `alai-doc win_copy` shows
`ansible.windows.win_copy`, and the header says which name it was
redirected from. Inside a collection project, alai-doc looks in
the project's own collection first, as a play in one of its roles would.

When a short name is neither in ansible-core's routing nor in the project's
own collection, alai-doc stops with an error. The error suggests the
collections that have a plugin by that name, from the plugin index alai
searches.

[Finding a plugin by its short name](casts/short-names.cast){ .cli-cast }

When the plugin's collection isn't known, `alai find` searches every
collection on the index by part of a name, as
[Finding plugins](https://docs.alai.sh/finding-plugins/) in alai's docs
describes.

## Choosing a type

A collection can have plugins of different types with the same name, such
as a module and a lookup both called `thing`. When more than one type has
the name, alai-doc stops with an error that lists each type, and `-t` picks
the one to show.

[Choosing a plugin's type](casts/types.cast){ .cli-cast }

## Roles

A role is shown from its argument spec when it has one, with a section for
each entry point and the options it takes. A role that also has a
`README.md` has it in a tab after the docs. A role with no argument spec is
shown from its `README.md`, which is rendered as Markdown.

[A role with only a README](casts/role.cast){ .cli-cast }

## Which copy of a collection

alai-doc runs `alai collection path` to find the collection, so the docs
match the version a project uses. alai uses the first copy it finds, looking
in this order.

1. The collection project's own checkout, when using an alai collection project
2. The project's collections directory
3. The version in `alai.lock`, from alai's cache if not installed
4. The newest version in alai's cache
5. The latest version on the indexes, which alai downloads into its cache

The docs for `ansible.builtin` come from the latest ansible-core release,
and `eda.builtin` from the latest ansible-rulebook release.

The header of the docs says which copy they were read from. When the copy
in the cache is older than the latest version on the indexes, the header
names the latest version too.

alai's settings come from its own config files and `ALAI_` environment
variables, as [Configuration](https://docs.alai.sh/configuration/) in alai's
docs describes. When a setting is needed for a single run, alai-doc passes
these options on to alai.

| Option | When to use it |
|---|---|
| `--project DIR` | When the project isn't the one the current directory is in |
| `--offline` | When there's no network, so only collections already on disk or cached are read |
| `--index NAME=URL` | When the collection is on an index alai isn't set up to use, which can be repeated |
