from pathlib import Path

from .errors import MuseScoreNotFoundError
from .executables import find_executable

ENV_VAR = "MUSESCORE_PATH"
EXECUTABLE_NAMES = ("MuseScore4", "mscore4", "mscore", "musescore", "MuseScore.AppImage")


def known_install_dirs() -> list[Path]:
    return [
        Path.home() / ".local" / "opt" / "musescore",
        Path("/opt/musescore"),
        Path("/usr/local/bin"),
        Path("C:/Program Files/MuseScore 4/bin"),
        Path("/Applications/MuseScore 4.app/Contents/MacOS"),
    ]


def find_musescore(override: Path | None = None) -> Path:
    return find_executable(
        "MuseScore", ENV_VAR, EXECUTABLE_NAMES, known_install_dirs(), MuseScoreNotFoundError, override
    )
