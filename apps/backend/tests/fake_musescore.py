#!/usr/bin/env python3
import os
import sys
import time
from pathlib import Path

args = sys.argv[1:]
output = Path(args[args.index("-o") + 1])
mode = os.environ.get("FAKE_MODE", "ok")

args_file = os.environ.get("FAKE_ARGS_FILE")
if args_file:
    Path(args_file).write_text("\n".join(args), encoding="utf-8")

if mode == "fail":
    print("bad score", file=sys.stderr)
    sys.exit(4)
if mode == "sleep":
    time.sleep(30)
if mode == "ok":
    output.write_bytes(b"%PDF-1.4 fake")
