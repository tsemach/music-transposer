import subprocess
import threading
from pathlib import Path

from .errors import InvalidInputError, NoOutputError, OmrFailedError
from .process import run_process


def run_omr(
    pdf: Path,
    out_dir: Path,
    audiveris: Path,
    timeout_s: int = 600,
    cancel: threading.Event | None = None,
) -> list[Path]:
    _require_pdf(pdf)
    out_dir.mkdir(parents=True, exist_ok=True)
    before = _snapshot_mxl(out_dir)
    command = [str(audiveris), "-batch", "-export", "-output", str(out_dir), "--", str(pdf)]

    try:
        completed = run_process(command, timeout_s, cancel)
    except subprocess.TimeoutExpired as error:
        raise OmrFailedError(-1, f"timed out after {timeout_s}s") from error

    if completed.returncode != 0:
        raise OmrFailedError(completed.returncode, completed.stderr)

    after = _snapshot_mxl(out_dir)
    produced = sorted(path for path, mtime in after.items() if before.get(path) != mtime)
    if not produced:
        raise NoOutputError(f"Audiveris exited 0 but wrote no .mxl in {out_dir}")
    return produced


def _require_pdf(pdf: Path) -> None:
    if pdf.suffix.lower() != ".pdf":
        raise InvalidInputError(f"Not a PDF file: {pdf}")
    if not pdf.is_file():
        raise InvalidInputError(f"PDF not found: {pdf}")


def _snapshot_mxl(directory: Path) -> dict[Path, int]:
    return {path: path.stat().st_mtime_ns for path in directory.glob("*.mxl")}
