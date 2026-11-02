from dataclasses import dataclass
from typing import Literal

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class Finding:
    check: str
    severity: Severity
    measure: str | None
    message: str

    def format(self) -> str:
        location = f"bar {self.measure}" if self.measure is not None else "score"
        return f"{location}: {self.severity} {self.check}: {self.message}"


@dataclass
class ValidationReport:
    findings: list[Finding]

    @property
    def errors(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.severity == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.severity == "warning"]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    def passes(self, strict: bool = False) -> bool:
        return not self.findings if strict else not self.has_errors

    def format_lines(self) -> list[str]:
        return [finding.format() for finding in self.findings]
