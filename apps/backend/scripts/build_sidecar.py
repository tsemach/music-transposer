import shutil
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
BINARIES = BACKEND.parent / "desktop" / "src-tauri" / "binaries"
WORK = BACKEND / "build" / "pyinstaller"
EXECUTABLE_NAME = "backend"


def host_triple() -> str:
    output = subprocess.run(["rustc", "-vV"], capture_output=True, text=True, check=True).stdout
    return next(line.split(": ", 1)[1] for line in output.splitlines() if line.startswith("host:"))


def freeze() -> Path:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",
            "--noconfirm",
            "--name",
            EXECUTABLE_NAME,
            "--distpath",
            str(WORK / "dist"),
            "--workpath",
            str(WORK / "work"),
            "--specpath",
            str(WORK),
            "--paths",
            str(BACKEND / "src"),
            "--collect-submodules",
            "music21",
            str(BACKEND / "scripts" / "sidecar_entry.py"),
        ],
        check=True,
        cwd=BACKEND,
    )
    suffix = ".exe" if sys.platform == "win32" else ""
    return WORK / "dist" / f"{EXECUTABLE_NAME}{suffix}"


def main() -> None:
    built = freeze()
    suffix = ".exe" if sys.platform == "win32" else ""
    target = BINARIES / f"{EXECUTABLE_NAME}-{host_triple()}{suffix}"
    BINARIES.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built, target)
    print(f"sidecar written to {target}")


if __name__ == "__main__":
    main()
