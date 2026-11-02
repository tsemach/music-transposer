import subprocess
import sys
import threading
from pathlib import Path

from .errors import InvalidInputError, RenderFailedError
from .process import run_process


def render_pdf(
    musicxml: Path,
    out_pdf: Path,
    musescore: Path,
    timeout_s: int = 120,
    cancel: threading.Event | None = None,
) -> Path:
    _require_paths(musicxml, out_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    out_pdf.unlink(missing_ok=True)

    command = [str(musescore)]
    if musescore.name.lower().endswith(".appimage"):
        command.append("--appimage-extract-and-run")
    command += ["-o", str(out_pdf), str(musicxml)]
    env = {"QT_QPA_PLATFORM": "offscreen"} if sys.platform.startswith("linux") else None

    try:
        completed = run_process(command, timeout_s, cancel, env)
    except subprocess.TimeoutExpired as error:
        raise RenderFailedError(-1, f"timed out after {timeout_s}s") from error

    if completed.returncode != 0:
        raise RenderFailedError(completed.returncode, completed.stderr)
    if not out_pdf.is_file():
        raise RenderFailedError(0, "MuseScore exited 0 but wrote no PDF")
    return out_pdf


def _require_paths(musicxml: Path, out_pdf: Path) -> None:
    if not musicxml.is_file():
        raise InvalidInputError(f"MusicXML not found: {musicxml}")
    if out_pdf.suffix.lower() != ".pdf":
        raise InvalidInputError(f"Output must be a .pdf file: {out_pdf}")
