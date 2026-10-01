"""
================================================================================
Filename: package_release.py
Description: Build fresh distribution archives without runtime or private files.
Author: Raphael Smilet
Date Created: 2026-09-30
Last Modified: 2026-10-01
Version: 0.1.1
Python Version: 3.12
================================================================================
"""

import argparse
import os
from pathlib import Path
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

SOURCE_DIRS = {"app", "dashboard", "scripts", "tests", "docs", "launch"}
ROOT_FILES = {
    "README.md",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "makefile",
    "Dockerfile",
    "docker-compose.yml",
    "alembic.ini",
    ".env.example",
    ".gitignore",
    ".dockerignore",
    ".pylintrc",
}
EXCLUDED_DIRS = {
    "__pycache__",
    ".pytest_cache",
    "cache",
    "data",
    "logs",
    "backups",
    "secrets",
    ".git",
    ".venv",
}


def source_files(root: Path):
    """
    Allow only source roots; never follow links into runtime/private data.

    Args:
        root: Project root from which allowed source files are collected.

    Returns:
        Iterator[Path]: Iterator over allowed source files without following symlinks.

    Yields:
        Path: Source file eligible for inclusion in the distribution archive.
    """
    for name in sorted(ROOT_FILES):
        path = root / name
        if path.is_file() and not path.is_symlink():
            yield path
    for name in sorted(SOURCE_DIRS):
        base = root / name
        if not base.is_dir() or base.is_symlink():
            continue
        for directory, dirs, files in os.walk(base, followlinks=False):
            dirs[:] = sorted(
                d
                for d in dirs
                if d not in EXCLUDED_DIRS and not (Path(directory) / d).is_symlink()
            )
            for filename in sorted(files):
                path = Path(directory) / filename
                if path.is_symlink() or filename.startswith(".env"):
                    continue
                if path.suffix.lower() in {
                    ".pyc",
                    ".db",
                    ".sqlite",
                    ".sqlite3",
                    ".zip",
                    ".log",
                    ".pem",
                    ".key",
                }:
                    continue
                yield path


def build_archive(root: Path, destination: Path) -> Path:
    """
    Build from scratch and replace the destination only after success.

    Args:
        root: Project root from which allowed source files are collected.
        destination: Output path for the generated archive or restored database.

    Returns:
        Path: Destination of the completed, atomically installed source archive.
    """
    root, destination = root.resolve(), destination.absolute()
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".release-", suffix=".zip", dir=destination.parent
    )
    os.close(descriptor)
    try:
        with ZipFile(temporary, "w", ZIP_DEFLATED) as archive:
            for path in source_files(root):
                if path.absolute() != destination:
                    archive.write(path, path.relative_to(root))
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return destination


def main():
    """
    Build the requested source-only distribution ZIP.

    Args:
        None.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(description="Build a source-only release archive.")
    parser.add_argument("--output", type=Path, default=Path("clash_royale_manager.zip"))
    args = parser.parse_args()
    print(build_archive(Path(__file__).resolve().parents[1], args.output))


if __name__ == "__main__":
    main()
