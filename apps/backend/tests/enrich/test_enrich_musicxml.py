from pathlib import Path
from xml.etree import ElementTree

import pymupdf
from xml_helpers import measure, note, score

from backend.enrich import enrich_musicxml

STAFF_TOP = 200.0
STAFF_SPACING = 5.0


def write_pdf(path: Path, with_tempo: bool = True, with_hairpin: bool = True) -> None:
    document = pymupdf.open()
    page = document.new_page()
    for index in range(5):
        y = STAFF_TOP + index * STAFF_SPACING
        page.draw_line((50, y), (550, y), width=0.6)
    if with_tempo:
        page.insert_text((80, 180), "With attitude!  q = 105", fontsize=11)
    if with_hairpin:
        page.draw_line((100, 240), (250, 237), width=0.6)
        page.draw_line((100, 240), (250, 243), width=0.6)
    document.save(path)
    document.close()


def write_musicxml(path: Path) -> None:
    root = score([measure(1, 250, [note(20), note(100), note(180)]), measure(2, 250, [note(20), note(100)])])
    ElementTree.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def test_tempo_and_hairpin_are_restored_from_the_pdf(tmp_path):
    pdf, xml = tmp_path / "song.pdf", tmp_path / "song.musicxml"
    write_pdf(pdf)
    write_musicxml(xml)

    warnings = enrich_musicxml(pdf, xml)

    root = ElementTree.parse(xml).getroot()
    assert warnings == []
    assert root.find(".//per-minute").text == "105"
    assert root.find(".//words").text.startswith("With attitude!")
    assert [w.get("type") for w in root.iter("wedge")] == ["crescendo", "stop"]


def test_pdf_without_extras_leaves_the_music_untouched(tmp_path):
    pdf, xml = tmp_path / "plain.pdf", tmp_path / "plain.musicxml"
    write_pdf(pdf, with_tempo=False, with_hairpin=False)
    write_musicxml(xml)
    before = xml.read_bytes()

    assert enrich_musicxml(pdf, xml) == []
    assert xml.read_bytes() == before


def test_unreadable_pdf_warns_and_keeps_the_music(tmp_path):
    pdf, xml = tmp_path / "broken.pdf", tmp_path / "broken.musicxml"
    pdf.write_bytes(b"not a pdf")
    write_musicxml(xml)
    before = xml.read_bytes()

    warnings = enrich_musicxml(pdf, xml)

    assert len(warnings) == 1 and "PDF" in warnings[0]
    assert xml.read_bytes() == before


def test_hebrew_file_names_work(tmp_path):
    pdf, xml = tmp_path / "שיר.pdf", tmp_path / "שיר.musicxml"
    write_pdf(pdf)
    write_musicxml(xml)

    assert enrich_musicxml(pdf, xml) == []
    assert ElementTree.parse(xml).getroot().find(".//per-minute") is not None
