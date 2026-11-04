---
description: Moving around alai-doc's viewer, and printing a plugin's docs as Markdown for another program.
---

# Reading the docs

On a terminal, alai-doc opens the docs in a viewer. Anywhere else, such as
when stdout is piped to another program, the docs are printed as Markdown.

## The viewer

The viewer shows each option and return value folded to a single line, with
its type and whether it's required. Opening one shows its description,
choices and default, and the options nested under it.

[Reading a module's docs in the viewer](casts/viewer.cast){ .cli-cast }

Names of other plugins and options in the docs are links. Clicking one goes
to that plugin or option, and the viewer keeps a history to go back and
forward through, as a browser does.

| Key | What it does |
|---|---|
| `Down` or `j`, `Up` or `k` | Move to the next or previous option |
| `Enter` or `Space` | Open or close the option or section |
| `Right` or `l`, `Left` or `h` | Open or close the option |
| `e`, `c` | Open or close every option |
| `PageDown` or `}`, `PageUp` or `{` | Move to the next or previous section |
| `Home` or `g`, `End` or `G` | Move to the top or bottom |
| `/` or `Ctrl+F` | Find text on the page |
| `n`, `N` | Move to the next or previous match |
| `[` or `Backspace`, `]` | Go back or forward through the history |
| `?` | Show every key |
| `Esc` | Close the find box, or quit |
| `q` | Quit |

Finding text searches every option, including the ones that are closed, and
opens the option each match is in. `Alt+Left` and `Alt+Right` also go
back and forward, but macOS terminals often send something else for them,
which is why `[` and `]` do the same.

The viewer's colors follow the terminal's background, light or dark.

## Markdown

When the docs are read by another program, or saved to a file,
`--output-format markdown` prints them as Markdown even on a terminal. The
viewer also isn't used when `TERM` is `dumb`. The Markdown isn't wrapped,
so whatever reads it can wrap or render it.

[Printing a plugin's docs](casts/markdown.cast){ .cli-cast }

stdout is only ever the docs. alai's progress, warnings and errors go to
stderr, and `--quiet` or `--no-progress` keeps them out of a script's
output.

When a plugin isn't found, alai-doc prints an error and exits with code 1.
Any other error exits with code 2, so a script can tell a missing plugin
from a failure.
