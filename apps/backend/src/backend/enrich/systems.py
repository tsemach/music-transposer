from dataclasses import dataclass
from xml.etree.ElementTree import Element

from .pdf_layout import Staff

NEW_LAYOUT_ATTRIBUTES = ("new-system", "new-page")


@dataclass(frozen=True)
class XmlSystem:
    measures: list[Element]
    staff: Staff

    @property
    def scale(self) -> float:
        widths = sum(float(measure.get("width", 0)) for measure in self.measures)
        return (self.staff.x_right - self.staff.x_left) / widths if widths else 0.0

    def measure_left(self, index: int) -> float:
        preceding = sum(float(measure.get("width", 0)) for measure in self.measures[:index])
        return self.staff.x_left + preceding * self.scale

    def measure_right(self, index: int) -> float:
        return self.measure_left(index) + float(self.measures[index].get("width", 0)) * self.scale

    def measure_index_at(self, x: float) -> int:
        containing = [i for i in range(len(self.measures)) if self.measure_left(i) <= x]
        return containing[-1] if containing else 0


def split_into_systems(measures: list[Element]) -> list[list[Element]]:
    systems: list[list[Element]] = []
    for measure in measures:
        prints = measure.findall("print")
        starts_system = any(print_.get(name) == "yes" for print_ in prints for name in NEW_LAYOUT_ATTRIBUTES)
        if starts_system or not systems:
            systems.append([])
        systems[-1].append(measure)
    return systems


def positioned_notes(system: XmlSystem, index: int) -> list[tuple[float, Element]] | None:
    left = system.measure_left(index)
    result = []
    for note in system.measures[index].findall("note"):
        if note.find("chord") is not None or note.find("grace") is not None:
            continue
        default_x = note.get("default-x")
        if default_x is None:
            return None
        result.append((left + float(default_x) * system.scale, note))
    return result
