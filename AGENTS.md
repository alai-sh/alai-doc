# Agent notes

- A plugin documentation viewer for Ansible collections. It reads docs
  with alai-core and finds collections by running alai.
- alai is a dependency but is only ever run, as `python -m alai`, never
  imported. Its `collection path` and `find` JSON are the interface, and
  `src/alai_doc/_alai.py` is the only module that runs it. What needs alai's
  settings, project, lock, cache or network belongs in alai, not here.
- alai-core isn't pinned here. alai pins it, so alai-doc reads docs with the
  same alai-core alai uses.
- Modules in `src/alai_doc/` are private (`_name.py`).
- Tests stand in for alai with `tests/doc_data.py`'s `World`, through
  `ALAI_DOC_ALAI`, and drive the viewer with Textual's test pilot.
- What users read is US English, the CLI's help and output, `README.md`
  and `docs/`, without `;` or `:` in the text.
- The docs are published at alai.sh/alai-doc. `docs/cli.md` is written
  from the parser by `python -m cli_recorder reference`, so edit the help
  instead. The recordings are in `docs/recordings.toml`, run against the
  tests' `World` by `docs/recordings.py`.
- How what users read is written:
  - Start with the situation the reader is in, then what happens or what to
    do. Describe an option by the problem it solves, such as "When syncing
    against a server with lots of collections and versions, `--limit N` can
    be used to perform the sync in smaller batches", not as a bare
    instruction.
  - Give each sentence one main idea. Join a second point to it with "and",
    "so", "as", "but", "when" or "which" only when it completes or explains
    the first, and start a new sentence for the next idea.
  - Keep a sentence to two commas or fewer. One that needs more is carrying
    more than one idea, so split it where the ideas change.
  - Don't write runs of very short sentences that only make sense together.
    When avoiding `;` or `:`, join the two halves with one of the words
    above rather than splitting them into separate sentences.
  - Don't push a phrase into the middle of a clause, between a subject and
    its verb or between "which" and what it says. A condition goes at the
    start or the end of a sentence.
  - Each sentence should make sense on its own, so name the thing rather
    than opening with "this", "that" or "it" pointing at the sentence before.
  - Don't drop words to shorten a phrase, such as "`sha256`, its artifact's"
    for "the artifact's sha256 checksum".
- Comments are sparse, in short plain sentences, without `;` or `:`.
- Every `.py` file starts with the two-line copyright and MIT header.
- Nothing is released, so no compatibility shims. Rename and replace
  outright.
- Checks are `uv run tox run -f sanity` and `uv run tox run -f py314` (any
  of `py310` to `py315`, `py314t`, `py315t`). The docs build is
  `uv run tox run -e docs`.
