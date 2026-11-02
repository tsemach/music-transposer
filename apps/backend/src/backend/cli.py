import argparse
import sys
from pathlib import Path

from .convert import convert_pdf
from .errors import BackendError
from .transpose import transpose_musicxml
from .transpose.saxophones import target_of
from .validate import validate_musicxml


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="backend")
    commands = parser.add_subparsers(dest="command", required=True)
    convert = commands.add_parser("convert", help="convert a PDF to MusicXML")
    convert.add_argument("pdf", type=Path)
    convert.add_argument("--out", type=Path, default=None)
    convert.add_argument("--audiveris", type=Path, default=None)
    validate = commands.add_parser("validate", help="check a MusicXML file for OMR errors")
    validate.add_argument("musicxml", type=Path)
    validate.add_argument("--strict", action="store_true")
    transpose = commands.add_parser("transpose", help="convert a part between alto and tenor saxophone")
    transpose.add_argument("musicxml", type=Path)
    transpose.add_argument("--from", dest="source", choices=["alto", "tenor"], required=True)
    transpose.add_argument("--register", choices=["auto", "same", "shifted"], default="auto")
    transpose.add_argument("--out", type=Path, default=None)
    transpose.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            return _validate(args)
        if args.command == "transpose":
            return _transpose(args)
        return _convert(args)
    except BackendError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


def _convert(args: argparse.Namespace) -> int:
    out_dir = args.out or args.pdf.parent / args.pdf.stem
    outputs = convert_pdf(args.pdf, out_dir, args.audiveris)
    for output in outputs:
        print(output)
        _print_validation(output)
    return 0


def _print_validation(musicxml: Path) -> None:
    try:
        lines = validate_musicxml(musicxml).format_lines()
    except BackendError as error:
        print(f"{musicxml.name}: could not validate: {error}", file=sys.stderr)
        return
    for line in lines:
        print(f"{musicxml.name}: {line}", file=sys.stderr)


def _validate(args: argparse.Namespace) -> int:
    report = validate_musicxml(args.musicxml)
    for line in report.format_lines():
        print(line)
    return 0 if report.passes(args.strict) else 1


def _transpose(args: argparse.Namespace) -> int:
    default_name = f"{args.musicxml.stem}.{target_of(args.source)}.musicxml"
    out_path = args.out or args.musicxml.with_name(default_name)
    outcome = transpose_musicxml(args.musicxml, out_path, args.source, args.register, args.force)
    print(outcome.out_path)
    print(f"interval: {outcome.interval.name} ({outcome.interval.register} register)", file=sys.stderr)
    for warning in outcome.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    for line in outcome.report.format_lines():
        print(f"{args.musicxml.name}: {line}", file=sys.stderr)
    return 0
