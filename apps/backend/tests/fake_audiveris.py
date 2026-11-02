#!/usr/bin/env python3
import os
import sys
import time
from pathlib import Path

args = sys.argv[1:]
output_dir = Path(args[args.index("-output") + 1])
pdf = Path(args[args.index("--") + 1])
mode = os.environ.get("FAKE_MODE", "one")

args_file = os.environ.get("FAKE_ARGS_FILE")
if args_file:
    Path(args_file).write_text("\n".join(args), encoding="utf-8")

if mode == "fail":
    print("boom", file=sys.stderr)
    sys.exit(3)
if mode == "sleep":
    time.sleep(30)

output_dir.mkdir(parents=True, exist_ok=True)
(output_dir / f"{pdf.stem}.omr").write_bytes(b"omr")
(output_dir / f"{pdf.stem}.log").write_text("log")
if mode in ("one", "two"):
    (output_dir / f"{pdf.stem}.mxl").write_bytes(b"mxl")
if mode == "two":
    (output_dir / f"{pdf.stem}.mvt2.mxl").write_bytes(b"mxl2")
