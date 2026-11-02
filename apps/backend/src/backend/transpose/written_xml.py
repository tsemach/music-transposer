from pathlib import Path
from xml.etree import ElementTree
from xml.etree.ElementTree import Element


def fix_for_musescore(path: Path) -> None:
    tree = ElementTree.parse(path)
    changed = _drop_wedge_spread(tree) | _merge_tempo_words(tree) | _hide_staff_labels(tree)
    if changed:
        tree.write(path, encoding="utf-8", xml_declaration=True)


def _drop_wedge_spread(tree: ElementTree.ElementTree) -> bool:
    # music21 hard-codes spread="0" on crescendo starts, which MuseScore draws as a flat line
    wedges = [wedge for wedge in tree.iter("wedge") if "spread" in wedge.attrib]
    for wedge in wedges:
        del wedge.attrib["spread"]
    return bool(wedges)


def _merge_tempo_words(tree: ElementTree.ElementTree) -> bool:
    # music21 writes a tempo's words and metronome as two directions, which MuseScore stacks on two lines
    merged = False
    for parent in list(tree.iter()):
        children = list(parent)
        for words, metronome in zip(children, children[1:]):
            if _is_words_only(words) and _has_metronome(metronome):
                metronome.insert(0, words.find("direction-type"))
                parent.remove(words)
                merged = True
    return merged


def _hide_staff_labels(tree: ElementTree.ElementTree) -> bool:
    # the instrument is named in the title instead of beside every staff
    labels = [*tree.iter("part-name"), *tree.iter("part-abbreviation")]
    for label in labels:
        label.set("print-object", "no")
    return bool(labels)


def _is_words_only(direction: Element) -> bool:
    types = direction.findall("direction-type")
    return direction.tag == "direction" and len(types) == 1 and [child.tag for child in types[0]] == ["words"]


def _has_metronome(direction: Element) -> bool:
    return direction.tag == "direction" and direction.find("direction-type/metronome") is not None
