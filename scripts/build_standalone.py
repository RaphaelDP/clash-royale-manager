"""
Filename: build_standalone.py
Description: Build a native GUI plus relocatable Python application directory.
Author: Raphael Smilet
Date Created: 2026-10-07
Last Modified: 2026-10-07
Version: 0.1.0
"""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

from scripts.package_release import source_files


def main():
    """Package a native launcher, managed Python runtime, and reviewed source files.

    Args:
        None. CLI requires a relocatable Python installation directory.

    Returns:
        None. Writes a standalone directory; never reads personal configuration.
    """
    parser = argparse.ArgumentParser(
        description="Build a Docker-free desktop application."
    )
    parser.add_argument("--python-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("dist/ClanManager"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if output.exists():
        raise ValueError("Choose an output directory that does not already exist.")
    runtime = args.python_dir.resolve()
    python = runtime / ("python.exe" if sys.platform == "win32" else "bin/python3")
    if not python.is_file():
        raise ValueError(
            "The selected directory must contain a relocatable Python runtime."
        )
    icon = root / (
        "launch/windows/clan-manager.ico"
        if sys.platform == "win32"
        else "launch/clan-manager.png"
    )
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--paths",
        str(root),
        "--name",
        "ClanManager",
        "--distpath",
        str(output.parent),
        "--workpath",
        str(root / "build/standalone-work"),
        "--specpath",
        str(root / "build"),
        "--add-data",
        f"{root / 'launch/clan-manager.png'}:launch",
    ]
    if sys.platform == "win32":
        command.extend(["--icon", str(icon)])
    command.append(str(root / "launch/desktop.py"))
    subprocess.run(command, check=True, cwd=root)
    generated = output.parent / "ClanManager"
    if output != generated:
        generated.rename(output)
    shutil.copytree(runtime, output / "python", symlinks=False)
    for path in source_files(root):
        destination = output / "application" / path.relative_to(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    for language in ("en", "fr"):
        guide = root / f"docs/user-guide-{language}.pdf"
        if guide.exists():
            shutil.copy2(guide, output / guide.name)
    (output / "START-HERE.txt").write_text(
        "Clash Royale Clan Manager — standalone\n\n"
        "Open ClanManager.exe (Windows) or ClanManager (Linux).\n"
        "Keep every file in this folder together. No Docker or Python installation is needed.\n"
        "Settings, data and backups are stored separately in your user-data folder.\n"
        "The launcher displays that location. Enter your API key and clan tag on first start.\n"
        "Stop all before replacing this program folder with a newer version.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
