from pathlib import Path


def make_executable(directory: Path, name: str = "Audiveris") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text("#!/bin/sh\n")
    path.chmod(0o755)
    return path
