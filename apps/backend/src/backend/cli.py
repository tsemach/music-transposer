import argparse
import sys
from pathlib import Path

from .convert import convert_pdf
from .errors import BackendError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="backend")
    commands = parser.add_subparsers(dest="command", required=True)
    convert = commands.add_parser("convert", help="convert a PDF to MusicXML")
    convert.add_argument("pdf", type=Path)
    convert.add_argument("--out", type=Path, default=None)
    convert.add_argument("--audiveris", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out_dir = args.out or args.pdf.parent / args.pdf.stem
    try:
        outputs = convert_pdf(args.pdf, out_dir, args.audiveris)
    except BackendError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    for output in outputs:
        print(output)
    return 0
