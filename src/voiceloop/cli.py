"""The `voiceloop` command: one entry point for every step of the project.

    voiceloop doctor        check this machine can run the Phase 1 stack     (Step 00)

Each command only parses its options and calls a function in the package, so the real work
can be tested without the command line. Imports are inside the handlers on purpose: they keep
`voiceloop --help` instant once the audio and model libraries are installed.
"""

import argparse
import logging
import sys

from voiceloop.errors import UserError

log = logging.getLogger("voiceloop")


# ---- handlers: one small function per command ----------------------------------------------


def cmd_doctor(args: argparse.Namespace) -> None:
    from voiceloop.doctor import run_doctor

    for check, result in run_doctor():
        print(f"{check:<12} {result}")


# ---- parser ------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="voiceloop", description="A full-duplex voice agent.")
    parser.add_argument("-v", "--verbose", action="store_true", help="show debug logging")
    commands = parser.add_subparsers(dest="command", required=True)

    doctor = commands.add_parser("doctor", help="check this machine can run the Phase 1 stack")
    doctor.set_defaults(handler=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")
    try:
        args.handler(args)
    except UserError as error:
        log.error(f"error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
