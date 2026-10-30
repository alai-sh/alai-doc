# Copyright: (c) 2026, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""Messages to stderr: warnings unless ``-q``, debug lines with ``-v``, trace lines with ``-vv``; and the terminal's
background, light or dark, for the viewer's theme."""

from __future__ import annotations

import os
import sys

verbosity = 0
"""-1 with ``-q``, else how many times ``-v`` was given (at most 2)."""
color = "auto"
"""``--color``: ``auto``, ``always`` or ``never``."""

BOLD = "1"
DIM = "2"
ITALIC = "3"
UNDERLINE = "4"
RED = "31"
GREEN = "32"
YELLOW = "33"
BLUE = "34"
MAGENTA = "35"
CYAN = "36"
WHITE = "37"


def color_enabled(*, stdout: bool = False) -> bool:
    """Whether to colour stderr, or stdout with ``stdout``: ``--color always`` or ``never`` if given; else not with
    ``NO_COLOR``, and always with ``FORCE_COLOR`` (``NO_COLOR`` winning if both are set), and otherwise on a terminal
    that isn't ``TERM=dumb``."""
    if color != "auto":
        return color == "always"
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return (sys.stdout if stdout else sys.stderr).isatty() and os.environ.get("TERM") != "dumb"


_light: bool | None = None
"""What ``light_background`` found, once it's asked the terminal."""


def light_background(*, ask: bool = False) -> bool:
    """Whether the terminal's background is light: from ``COLORFGBG`` where the terminal sets it (``15;0`` is light
    text on black), as rxvt and Konsole do; else, with ``ask``, by asking the terminal (``terminal_background``);
    else dark. Only choices between colours depend on it, so a wrong guess still reads."""
    global _light
    background = os.environ.get("COLORFGBG", "").rsplit(";", 1)[-1]
    if background.isdigit():
        return background in ("7", "15")
    if ask and _light is None:
        _light = terminal_background()
    return bool(_light)


def terminal_background() -> bool | None:
    """Ask the terminal for its background colour with OSC 11, as Neovim does: whether it's light, or None if the
    terminal doesn't say. A device attributes request (DA1) follows it, which every terminal answers, so one that
    doesn't know OSC 11 costs no wait; half a second at most if nothing answers at all."""
    import re
    import select
    import termios
    import time
    import tty

    try:
        fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
    except OSError:
        return None
    data = b""
    try:
        saved = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            os.write(fd, b"\x1b]11;?\x1b\\\x1b[c")
            deadline = time.monotonic() + 0.5
            while not re.search(rb"\x1b\[\?[0-9;]*c", data):
                left = deadline - time.monotonic()
                if left <= 0 or not select.select([fd], [], [], left)[0]:
                    break
                data += os.read(fd, 1024)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, saved)
    except (OSError, termios.error):
        return None
    finally:
        os.close(fd)
    match = re.search(rb"\]11;rgb:([0-9a-fA-F]+)/([0-9a-fA-F]+)/([0-9a-fA-F]+)", data)
    if match is None:
        return None
    red, green, blue = (int(part, 16) / (16 ** len(part) - 1) for part in match.groups())
    # Relative luminance, as WCAG defines it, without the gamma: enough to tell light from dark.
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue > 0.5


def styled(text: str, *codes: str, stdout: bool = False) -> str:
    """``text`` in the given styles (``BOLD``, ``GREEN``…), when colour is on for stderr, or stdout with ``stdout``."""
    if not text or not codes or not color_enabled(stdout=stdout):
        return text
    return f"\x1b[{';'.join(codes)}m{text}\x1b[0m"


def _write(text: str) -> None:
    print(text, file=sys.stderr, flush=True)


def error(message: str) -> None:
    _write(f"{styled('error', RED, BOLD)}: {message}")


def warn(message: str) -> None:
    if verbosity >= 0:
        _write(f"{styled('warning', YELLOW, BOLD)}: {message}")


def debug(message: str) -> None:
    """What alai decided and why."""
    if verbosity >= 1:
        _write(f"debug: {message}")


def trace(message: str) -> None:
    """Each request and file operation."""
    if verbosity >= 2:
        _write(f"trace: {message}")


def home_path(path: str) -> str:
    """``path`` with a leading home directory shortened to ``~``, for display."""
    home = os.path.expanduser("~")
    if home != "~" and (path == home or path.startswith(home + os.sep)):
        return "~" + path[len(home) :]
    return path
