from xml.etree.ElementTree import Element

from .report import Finding


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
    findings += _empty_measures(part.findall("measure"))
    return findings


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
