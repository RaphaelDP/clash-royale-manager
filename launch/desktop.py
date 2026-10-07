"""
Filename: desktop.py
Description: Native graphical entry point for the standalone desktop distribution.
Author: Raphael Smilet
Date Created: 2026-10-07
Last Modified: 2026-10-07
Version: 0.1.0
"""

import argparse
import ctypes
from pathlib import Path
import sys
import tkinter as tk

from launch.launcher import Launcher
from launch.native_backend import NativeBackend


def main():
    """Run the standalone GUI with optional isolated smoke-test paths.

    Args:
        None. Reads bundle and data paths from CLI arguments.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(
        description="Clash Royale Clan Manager — standalone"
    )
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    if sys.platform == "win32" and getattr(sys, "frozen", False):
        ctypes.windll.kernel32.SetDllDirectoryW(None)  # pylint: disable=no-member
    bundle = args.bundle or Path(sys.executable).resolve().parent
    backend = NativeBackend(bundle, args.data_dir)
    window = tk.Tk()
    Launcher(window, configure=not args.smoke_test, backend=backend)
    if args.smoke_test:
        window.after(250, window.destroy)
    window.mainloop()


if __name__ == "__main__":
    main()
