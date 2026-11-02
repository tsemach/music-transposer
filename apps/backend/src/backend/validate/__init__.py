from pathlib import Path
from xml.etree import ElementTree

from ..errors import InvalidInputError
from .durations import check_durations
from .report import ValidationReport
from .structure import check_structure


def validate_musicxml(path: Path) -> ValidationReport:
    try:
        root = ElementTree.parse(path).getroot()
    except (OSError, ElementTree.ParseError) as error:
        raise InvalidInputError(f"Cannot read MusicXML {path}: {error}") from error
    return ValidationReport(check_structure(root) + check_durations(path))
