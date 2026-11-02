from pathlib import Path
from xml.etree import ElementTree

from .markup import add_hairpins, add_tempo
from .pdf_layout import read_pdf_layout
from .tempo import find_tempo

READ_ERRORS = (RuntimeError, ValueError, OSError, ElementTree.ParseError)


def enrich_musicxml(pdf: Path, musicxml: Path) -> list[str]:
    try:
        pages = read_pdf_layout(pdf)
        tree = ElementTree.parse(musicxml)
    except READ_ERRORS as error:
        return [f"Could not read the tempo and hairpins from the PDF: {error}"]
    root = tree.getroot()
    wedges_before = len(list(root.iter("wedge")))
    changed = False
    tempo = find_tempo(pages[0]) if pages else None
    if tempo:
        changed = add_tempo(root, tempo)
    warnings = add_hairpins(root, pages)
    changed = changed or len(list(root.iter("wedge"))) > wedges_before
    if changed:
        tree.write(musicxml, encoding="utf-8", xml_declaration=True)
    return warnings
