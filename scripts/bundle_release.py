"""
Filename: bundle_release.py
Description: Assemble complete platform downloads from matching CI artifacts.
Author: Raphael Smilet
Date Created: 2026-10-07
Last Modified: 2026-10-07
Version: 0.1.1
"""

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import tarfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from app import __version__


def artifact(root, group, filename):
    """Find exactly one nonempty artifact file.

    Args:
        root: Downloaded artifact directory.
        group: Workflow artifact name.
        filename: Expected file name.

    Returns:
        Path: Matching file.

    Raises:
        ValueError: Artifact is missing, ambiguous or empty.
    """
    matches = list((root / group).rglob(filename))
    if len(matches) != 1 or not matches[0].stat().st_size:
        raise ValueError(f"Expected one nonempty {group}/{filename}")
    return matches[0]


def safe_name(name):
    """Validate a relative archive path before copying its entry.

    Args:
        name: Archive member name.

    Returns:
        str: Validated relative path.

    Raises:
        ValueError: Path escapes the bundle.
    """
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
        raise ValueError(f"Unsafe archive path: {name}")
    return name


def build_bundles(artifacts, output, version):
    """Create four complete bundles, standalone PDFs and a checksum manifest.

    Args:
        artifacts: Same-run downloaded workflow artifacts.
        output: Empty destination directory.
        version: Version identifying all source and binary artifacts.

    Returns:
        list[Path]: Created platform ZIP files.

    Raises:
        ValueError: Source version, guides or artifacts do not match.
    """
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("Bundle output must be empty.")
    source = artifact(artifacts, "project-source", "project.zip")
    platforms = [
        ("windows", "launcher-windows-2022", "windows_launcher.exe", "windows"),
        (
            "linux-x86_64",
            "launcher-ubuntu-22.04",
            "linux_launcher.AppImage.tar.gz",
            "linux",
        ),
        ("macos-intel", "launcher-macos-15-intel", "macos_launcher.app.zip", "macos"),
        ("macos-apple-silicon", "launcher-macos-15", "macos_launcher.app.zip", "macos"),
    ]
    bundles = []
    with ZipFile(source) as project:
        # Exact source comparison prevents mixing a different revision's source archive.
        if project.read("app/__init__.py") != Path("app/__init__.py").read_bytes():
            raise ValueError("Source artifact does not match the checked-out release.")
        if version != __version__:
            raise ValueError("Requested version differs from the application version.")
        for language in ("en", "fr"):
            name = f"user-guide-{language}.pdf"
            data = project.read("docs/" + name)
            if not data.startswith(b"%PDF-"):
                raise ValueError("Missing or invalid PDF guide.")
            (output / name).write_bytes(data)
        for platform, group, filename, folder in platforms:
            launcher = artifact(artifacts, group, filename)
            destination = output / f"clan-manager-v{version}-docker-{platform}.zip"
            with ZipFile(destination, "w", ZIP_DEFLATED) as bundle:
                for entry in project.infolist():
                    safe_name(entry.filename)
                    bundle.writestr(entry, project.read(entry))
                if folder == "macos":
                    with ZipFile(launcher) as native:
                        for entry in native.infolist():
                            name = safe_name(entry.filename)
                            entry.filename = f"launch/macos/{name}"
                            bundle.writestr(entry, native.read(name))
                elif folder == "linux":
                    with tarfile.open(launcher) as native:
                        entry = native.getmember("linux_launcher.AppImage")
                        if not entry.isfile():
                            raise ValueError("Linux launcher must be a regular file.")
                        info = ZipInfo("launch/linux/linux_launcher.AppImage")
                        info.create_system = 3
                        info.external_attr = 0o100755 << 16
                        bundle.writestr(info, native.extractfile(entry).read())
                else:
                    bundle.write(launcher, "launch/windows/windows_launcher.exe")
            bundles.append(destination)
    checksum = "\n".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
        for path in sorted(output.iterdir())
    )
    (output / "SHA256SUMS.txt").write_text(checksum + "\n", encoding="utf-8")
    return bundles


def main():
    """Assemble release bundles from the current workflow's artifacts.

    Args:
        None. Reads artifact and output paths from CLI arguments.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(
        description="Build complete desktop download bundles."
    )
    parser.add_argument("--artifacts", type=Path, default=Path("release-artifacts"))
    parser.add_argument("--output", type=Path, default=Path("release-assets"))
    args = parser.parse_args()
    build_bundles(args.artifacts, args.output, __version__)


if __name__ == "__main__":
    main()
