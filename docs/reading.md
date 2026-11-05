---
description: Moving around alai-doc's viewer, and printing a plugin's docs as Markdown for another program.
---

# Reading the docs

On a terminal, alai-doc opens the docs in a viewer. Anywhere else, such as
when stdout is piped to another program, the docs are printed as Markdown.

## The viewer

The viewer shows each option and return value folded to a single line, with
its type and whether it's required. Opening one shows its description,
choices and default, and the options nested under it. When a plugin's
options all fit on the screen with their descriptions, the viewer opens them
to start with.

A plugin's docs are split into tabs under its header. The Docs tab has the
description, options and notes. The Usage, Examples and Returns tabs each
have what they're named for, and a role with a README has it in a README tab.
`Tab` and `Shift+Tab` move between the tabs, as does clicking one.

[Reading a module's docs in the viewer](casts/viewer.cast){ .cli-cast .cli-cast-schemes }

Names of other plugins and options in the docs are links. Clicking one goes
to that plugin or option, and the viewer keeps a history to go back and
forward through, as a browser does. While a plugin in another collection
loads, the page says what alai is doing, such as downloading the collection
or reading its docs.

| Key | What it does |
|---|---|
| `Down` or `j`, `Up` or `k` | Move to the next or previous option, or scroll a line at either end |
| `Enter` or `Space` | Open or close the option or section |
| `Right` or `l`, `Left` or `h` | Open or close the option |
| `e`, `c` | Open or close every option |
| `Tab`, `Shift+Tab` | Move to the next or previous tab |
| `PageDown` or `}`, `PageUp` or `{` | Move to the next or previous section in the tab, or scroll a screen at either end |
| `Home` or `g`, `End` or `G` | Move to the top or bottom |
| `/` or `Ctrl+F` | Find text on the page |
| `n`, `N` | Move to the next or previous match |
| `[` or `Backspace`, `]` | Go back or forward through the history |
| `?` | Show every key |
| `Esc` | Close the find box, or quit |
| `q` | Quit |

Finding text searches every option, including the ones that are closed, and
opens the option each match is in. Matches on every tab are found, and
moving to one on another tab switches to that tab. `Alt+Left` and `Alt+Right` also go
back and forward, but macOS terminals often send something else for them,
which is why `[` and `]` do the same.

### Colors

The viewer's colors depend on the terminal. When the terminal shows 256
colors or more, the viewer uses Textual's themes. When the terminal only
shows 16 colors, the viewer uses the terminal's own colors instead. Textual's
themes are built from many shades of each color, and squeezing them into 16
colors would leave some text hard to read against its background. Either way,
the viewer picks a light or dark look to match the terminal's background.

A different theme can be picked while the viewer is open. `Ctrl+P` opens
Textual's command palette, and its Theme command lists every theme. The
page and its code change to the theme picked, which lasts until the viewer
is closed.

[Picking another theme](casts/themes.cast){ .cli-cast .cli-cast-schemes }

The palette's Theme command lists the themes, and typing `nord` picks it.
The page and the examples are then in nord's colors.
{: .cli-cast-description }

alai-doc works out how many colors the terminal shows from `COLORTERM`, then
`TERM`. The background comes from `COLORFGBG` when the terminal sets it, and
otherwise alai-doc asks the terminal. When checking how the viewer looks on
another terminal, these variables can be set to override what the terminal
says.

```console
$ COLORTERM= TERM=xterm-256color alai-doc ansible.builtin.copy
$ COLORTERM= TERM=xterm-16color alai-doc ansible.builtin.copy
$ COLORFGBG="0;15" alai-doc ansible.builtin.copy
```

The first shows the themes in 256 colors, and the second the 16 color look.
The third shows the light look, and the dark look is `COLORFGBG="15;0"`.
`TERM` is only read when `COLORTERM` is empty, so it has to be cleared to
pick fewer colors on a terminal that sets `COLORTERM=truecolor`.

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
