# Copyright: (c) 2026, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""``alai-doc NAME``: the command line. alai's settings flags are passed on to alai as given."""

from __future__ import annotations

import argparse
import collections.abc as _c

from . import _output
from ._common import EXIT_ERROR, Error

PLUGIN_TYPES = (
    "become",
    "cache",
    "callback",
    "cliconf",
    "connection",
    "filter",
    "httpapi",
    "inventory",
    "lookup",
    "module",
    "netconf",
    "shell",
    "strategy",
    "test",
    "vars",
)


def main(argv: _c.Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.quiet and args.verbose:
        args.parser.error("-q/--quiet and -v/--verbose can't be used together")
    _output.verbosity = -1 if args.quiet else min(args.verbose, 2)
    _output.color = args.color

    from ._alai import Alai
    from ._doc import doc

    alai = Alai(_alai_args(args))
    try:
        return doc(alai, args.name, types=args.types, output_format=args.output_format)
    except Error as e:
        _output.error(str(e))
        return EXIT_ERROR


def _alai_args(args: argparse.Namespace) -> list[str]:
    """The flags alai is run with: the settings people give by hand, and how it talks. Every other setting reaches
    alai through its ALAI_ environment variable or config files, which it reads itself."""
    out = ["--project", args.project] if args.project is not None else []
    if args.offline:
        out.append("--offline")
    out += [a for index in args.index for a in ("--index", index)]
    out += ["--color", args.color]
    if args.quiet:
        out.append("--quiet")
    if args.no_progress:
        out.append("--no-progress")
    return out + ["--verbose"] * min(args.verbose, 2)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alai-doc",
        description="Show a plugin's documentation, with its options, examples and return values, as ansible-doc "
        + "does. It opens in a viewer on a terminal, and is printed as Markdown otherwise. The docs are read from the "
        + "copy of the collection alai finds, as alai collection path does, so a collection that isn't on disk yet "
        + "is downloaded into alai's cache. ansible.builtin comes from the latest ansible-core release.",
    )
    parser.add_argument(
        "name",
        metavar="NAME",
        help="the plugin's full name, such as ansible.windows.win_copy, or its short name, win_copy, found as a play "
        + "would find it",
    )
    parser.add_argument(
        "-t",
        "--type",
        metavar="TYPE",
        dest="types",
        action="append",
        default=[],
        help="only this type, as ansible-doc -t names them (module, lookup, filter...), for a name more than one "
        + "type has, and can be repeated",
    )
    parser.add_argument(
        "--output-format",
        choices=("markdown",),
        help="markdown to print the docs as Markdown rather than open the viewer, which is otherwise used on a "
        + "terminal",
    )
    parser.add_argument("-v", "--verbose", action="count", default=0, help="say more, and -vv for every step")
    parser.add_argument("-q", "--quiet", action="store_true", help="only show errors")
    parser.add_argument("--color", choices=("auto", "always", "never"), default="auto", help="color output")
    parser.add_argument("--no-progress", action="store_true", help="don't show alai's progress")

    alai = parser.add_argument_group(
        "alai's settings",
        "passed on to alai, which finds the collections. Every alai setting can also be set with its ALAI_ "
        + "environment variable, such as ALAI_CACHE_DIR, or in alai's config files.",
    )
    alai.add_argument("--project", metavar="DIR", help="find the project from DIR")
    alai.add_argument("--offline", action="store_true", help="use only what's cached")
    alai.add_argument(
        "--index", metavar="NAME=URL", action="append", default=[], help="an index, which can be repeated"
    )
    parser.set_defaults(parser=parser)
    return parser
