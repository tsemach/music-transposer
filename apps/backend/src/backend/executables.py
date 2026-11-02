import os
import shutil
from pathlib import Path

from .errors import ExecutableNotFoundError


def find_executable(
    label: str,
    env_var: str,
    names: tuple[str, ...],
    known_dirs: list[Path],
    error: type[ExecutableNotFoundError],
    override: Path | None = None,
) -> Path:
    if override is not None:
        return _require_file(override, "override", label, error)

    from_env = os.environ.get(env_var)
    if from_env:
        return _require_file(Path(from_env), env_var, label, error)

    found = _search(names, None) or next(
        (hit for directory in known_dirs if (hit := _search(names, directory))),
        None,
    )
    if found:
        return found

    searched = [env_var, "PATH", *map(str, known_dirs)]
    raise error(f"{label} not found. Searched: " + ", ".join(searched))


def _search(names: tuple[str, ...], directory: Path | None) -> Path | None:
    search_path = str(directory) if directory else None
    for name in names:
        hit = shutil.which(name, path=search_path)
        if hit:
            return Path(hit)
    return None


def _require_file(path: Path, source: str, label: str, error: type[ExecutableNotFoundError]) -> Path:
    if not path.is_file():
        raise error(f"{label} path from {source} does not exist: {path}")
    return path
