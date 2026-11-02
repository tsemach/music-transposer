import os
import shutil
from pathlib import Path

from .errors import AudiverisNotFoundError

ENV_VAR = "AUDIVERIS_PATH"
EXECUTABLE_NAMES = ("Audiveris", "audiveris")


def known_install_dirs() -> list[Path]:
    return [
        Path.home() / ".local" / "opt" / "audiveris" / "opt" / "audiveris" / "bin",
        Path("/opt/audiveris/bin"),
        Path("C:/Program Files/Audiveris"),
    ]


def find_audiveris(override: Path | None = None) -> Path:
    if override is not None:
        return _require_file(override, "override")

    from_env = os.environ.get(ENV_VAR)
    if from_env:
        return _require_file(Path(from_env), ENV_VAR)

    found = _search_directories(None) or next(
        (hit for directory in known_install_dirs() if (hit := _search_directories(directory))),
        None,
    )
    if found:
        return found

    searched = [f"{ENV_VAR}", "PATH", *map(str, known_install_dirs())]
    raise AudiverisNotFoundError("Audiveris not found. Searched: " + ", ".join(searched))


def _search_directories(directory: Path | None) -> Path | None:
    search_path = str(directory) if directory else None
    for name in EXECUTABLE_NAMES:
        hit = shutil.which(name, path=search_path)
        if hit:
            return Path(hit)
    return None


def _require_file(path: Path, source: str) -> Path:
    if not path.is_file():
        raise AudiverisNotFoundError(f"Audiveris path from {source} does not exist: {path}")
    return path
