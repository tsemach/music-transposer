import zipfile
from pathlib import Path
from xml.etree import ElementTree

from .errors import InvalidInputError

CONTAINER_PATH = "META-INF/container.xml"


def extract_musicxml(mxl: Path, dest_dir: Path) -> Path:
    try:
        with zipfile.ZipFile(mxl) as archive:
            root_member = _root_member(archive)
            dest_dir.mkdir(parents=True, exist_ok=True)
            output = dest_dir / f"{mxl.stem}.musicxml"
            output.write_bytes(archive.read(root_member))
            return output
    except zipfile.BadZipFile as error:
        raise InvalidInputError(f"{mxl} is not a valid .mxl archive") from error


def _root_member(archive: zipfile.ZipFile) -> str:
    if CONTAINER_PATH not in archive.namelist():
        raise InvalidInputError(f"{CONTAINER_PATH} missing from .mxl archive")
    container = ElementTree.fromstring(archive.read(CONTAINER_PATH))
    rootfile = container.find(".//rootfile")
    if rootfile is None or not rootfile.get("full-path"):
        raise InvalidInputError("container.xml names no rootfile")
    return rootfile.get("full-path")
