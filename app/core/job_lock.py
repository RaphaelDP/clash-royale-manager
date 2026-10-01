"""
================================================================================
Filename: job_lock.py
Description: Serialize scheduler and dashboard jobs without leaving stale locks.
Author: Raphael Smilet
Date Created: 2026-09-30
Last Modified: 2026-10-01
Version: 0.1.1
Python Version: 3.12
================================================================================
"""

from contextlib import contextmanager
from pathlib import Path
import os

if os.name == "nt":
    import msvcrt  # pylint: disable=import-error
else:
    import fcntl


@contextmanager
def job_lock(name):
    """
    Non-blocking process lock, released by the OS after a crash. If the lock is already
    held, the context manager yields False. Otherwise, it yields True and holds the lock
    until the context exits. Purpose: Prevent multiple instances of the same job from
    running concurrently.

    Args:
        name: Internal lock identifier used as a filename under JOB_LOCK_DIR.

    Returns:
        AbstractContextManager[bool]: Context manager holding an acquired lock until
        exit.

    Yields:
        bool: True when the process lock is held; False when another process holds it.
    """
    directory = Path(os.getenv("JOB_LOCK_DIR", "data/locks"))
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / (name + ".lock")).open("a+b") as file:
        locked = False
        try:
            if os.name == "nt":
                file.seek(0)
                if not file.read(1):
                    file.write(b"0")
                    file.flush()
                file.seek(0)
                try:
                    msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
                    locked = True
                except OSError:
                    pass
            else:
                try:
                    fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                except BlockingIOError:
                    pass
            yield locked
        finally:
            if locked:
                if os.name == "nt":
                    file.seek(0)
                    msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(file, fcntl.LOCK_UN)
