import sys
from typing import TextIO

from .handlers import HANDLERS, Handler
from .protocol import MessageWriter
from .server import serve


def run_server(stdin: TextIO, stdout: TextIO, handlers: dict[str, Handler] = HANDLERS) -> int:
    for stream in (stdin, stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    previous_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        serve(stdin, MessageWriter(stdout), handlers)
    finally:
        sys.stdout = previous_stdout
    return 0
