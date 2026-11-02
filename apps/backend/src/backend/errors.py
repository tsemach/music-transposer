from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .validate.report import ValidationReport


class BackendError(Exception):
    pass


class ExecutableNotFoundError(BackendError):
    pass


class AudiverisNotFoundError(ExecutableNotFoundError):
    pass


class MuseScoreNotFoundError(ExecutableNotFoundError):
    pass


class CancelledError(BackendError):
    pass


class InvalidInputError(BackendError):
    pass


class NoOutputError(BackendError):
    pass


class OmrFailedError(BackendError):
    def __init__(self, returncode: int, stderr: str):
        super().__init__(f"Audiveris failed with exit code {returncode}: {stderr}")
        self.returncode = returncode
        self.stderr = stderr


class ValidationFailedError(BackendError):
    def __init__(self, report: "ValidationReport"):
        findings = "; ".join(finding.format() for finding in report.errors)
        super().__init__(f"MusicXML has validation errors (use --force to convert anyway): {findings}")
        self.report = report


class RenderFailedError(BackendError):
    def __init__(self, returncode: int, stderr: str):
        super().__init__(f"MuseScore failed with exit code {returncode}: {stderr}")
        self.returncode = returncode
        self.stderr = stderr
