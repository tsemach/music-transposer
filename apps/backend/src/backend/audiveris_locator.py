from pathlib import Path

from .errors import AudiverisNotFoundError
from .executables import find_executable

ENV_VAR = "AUDIVERIS_PATH"
EXECUTABLE_NAMES = ("Audiveris", "audiveris")


def known_install_dirs() -> list[Path]:
    return [
        Path.home() / ".local" / "opt" / "audiveris" / "opt" / "audiveris" / "bin",
        Path("/opt/audiveris/bin"),
        Path("C:/Program Files/Audiveris"),
    ]


def find_audiveris(override: Path | None = None) -> Path:
    return find_executable(
        "Audiveris", ENV_VAR, EXECUTABLE_NAMES, known_install_dirs(), AudiverisNotFoundError, override
    )
