import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from .errors import InvalidInputError, RenderFailedError
from .process import run_process

# Without a cap MuseScore stretches the systems down the page to fill it.
SYSTEM_SPACING_STYLE = """<?xml version="1.0" encoding="UTF-8"?>
<museScore version="4.00">
  <Style>
    <enableVerticalSpread>0</enableVerticalSpread>
    <minSystemDistance>8.5</minSystemDistance>
    <maxSystemDistance>12</maxSystemDistance>
  </Style>
</museScore>
"""


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
    env = {"QT_QPA_PLATFORM": "offscreen"} if sys.platform.startswith("linux") else None

    with tempfile.TemporaryDirectory() as style_dir:
        style = Path(style_dir) / "ascurix.mss"
        style.write_text(SYSTEM_SPACING_STYLE, encoding="utf-8")
        command += ["-S", str(style), "-o", str(out_pdf), str(musicxml)]
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
