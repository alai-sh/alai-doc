# Copyright: (c) 2026, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

from __future__ import annotations


class Error(Exception):
    """A failure to report to the user as ``error: <message>``, without a traceback."""


EXIT_ERROR = 2
"""An ``Error`` was reported, or the command line was wrong, as argparse exits."""
EXIT_NOT_FOUND = 1
"""The plugin wasn't found."""


class Record:
    """A value class with equality and repr from its ``__slots__``."""

    __slots__: tuple[str, ...] = ()

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and all(getattr(self, n) == getattr(other, n) for n in self.__slots__)

    def __repr__(self) -> str:
        fields = ", ".join(f"{n}={getattr(self, n)!r}" for n in self.__slots__)
        return f"{type(self).__name__}({fields})"
