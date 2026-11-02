from pathlib import Path

from .audiveris_locator import find_audiveris
from .mxl import extract_musicxml
from .omr import run_omr


def convert_pdf(pdf: Path, out_dir: Path, audiveris: Path | None = None) -> list[Path]:
    executable = find_audiveris(audiveris)
    mxl_files = run_omr(pdf, out_dir, executable)
    return [extract_musicxml(mxl, out_dir) for mxl in mxl_files]
