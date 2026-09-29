from __future__ import annotations

import os
import signal
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


def streaming_pager(
  lines: Iterable[str],
  pager_command: str | Sequence[str] = "less",
) -> None:
    """This function takes a stream of text lines, and pipes them into a pager of choice."""
    int_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)

    try:
        env = dict(os.environ)
        env["LESSSECURE"] = "1"
        proc = subprocess.Popen(  # noqa: S603 input is controlled by configuration, not user input
            pager_command,
            env=env,
            encoding="utf-8",
            stdin=subprocess.PIPE,
        )

        try:
            assert proc.stdin is not None

            try:
                for line in lines:
                    proc.stdin.write(line)
            except BrokenPipeError:
                pass
            finally:
                # If `lines` is a generator, it may have a `close()`
                # method that should be called to clean up resources.
                close = getattr(lines, "close", None)
                if close is not None:
                    close()

            try:
                proc.stdin.close()
            except BrokenPipeError:
                pass

        finally:
            proc.wait()
    finally:
        signal.signal(signal.SIGINT, int_handler)
