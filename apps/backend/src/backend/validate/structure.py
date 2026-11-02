from xml.etree.ElementTree import Element

from .report import Finding

MAX_KEY_FLIP_SPAN = 8


def check_structure(root: Element) -> list[Finding]:
    parts = root.findall("part")
    findings = []
    if len(parts) != 1:
        findings.append(
            Finding("unexpected-part-count", "warning", None, f"expected 1 part, found {len(parts)}")
        )
    if not parts:
        return findings
    part = parts[0]
    findings += _missing_time_signature(part)
    measures = part.findall("measure")
    findings += _empty_measures(measures)
    findings += _key_signature_flips(measures)
    findings += _orphan_endings(part, measures)
    return findings


def _key_signature_flips(measures: list[Element]) -> list[Finding]:
    findings = []
    current = 0
    last_change: tuple[int, str | None, int] | None = None
    for index, measure in enumerate(measures):
        fifths = measure.findtext("attributes/key/fifths")
        if fifths is None:
            continue
        new = int(fifths)
        if index == 0:
            current = new
            continue
        if new == current:
            continue
        if last_change and new == last_change[2] and index - last_change[0] <= MAX_KEY_FLIP_SPAN:
            findings.append(_key_flip_finding(last_change, measure.get("number"), new))
            last_change = None
        else:
            last_change = (index, measure.get("number"), current)
        current = new
    return findings


def _key_flip_finding(change: tuple[int, str | None, int], return_label: str | None, original: int) -> Finding:
    _, label, _ = change
    return Finding(
        "key-signature-flip",
        "warning",
        label,
        f"key signature changes at bar {label} and returns to {original} sharps/flats at bar {return_label}",
    )


def _orphan_endings(part: Element, measures: list[Element]) -> list[Finding]:
    if part.find(".//repeat[@direction='backward']") is not None:
        return []
    return [
        Finding("orphan-ending", "warning", measure.get("number"), "ending bracket without any repeat sign")
        for measure in measures
        for ending in measure.findall("barline/ending")
        if ending.get("type") == "start"
    ]


def _missing_time_signature(part: Element) -> list[Finding]:
    if part.find(".//time") is not None:
        return []
    return [Finding("missing-time-signature", "error", None, "no time signature in the part")]


def _empty_measures(measures: list[Element]) -> list[Finding]:
    return [
        Finding("empty-measure", "error", measure.get("number"), "measure has no notes or rests")
        for measure in measures
        if measure.find("note") is None
        and measure.find("attributes/measure-style/multiple-rest") is None
    ]
