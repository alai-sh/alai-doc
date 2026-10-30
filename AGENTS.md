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
- What users read is US English, the CLI's help and output and
  `README.md`, without `;` or `:` in the text.
- Comments are sparse, in short plain sentences, without `;` or `:`.
- Every `.py` file starts with the two-line copyright and MIT header.
- Nothing is released, so no compatibility shims. Rename and replace
  outright.
- Checks are `uv run tox run -f sanity` and `uv run tox run -f py314` (any
  of `py310` to `py315`, `py314t`, `py315t`).
