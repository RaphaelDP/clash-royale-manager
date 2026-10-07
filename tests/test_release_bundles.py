"""
Filename: test_release_bundles.py
Description: Verify complete downloads, source identity and launcher permissions.
Author: Raphael Smilet
Date Created: 2026-10-07
Last Modified: 2026-10-07
Version: 0.1.0
"""

import io
from pathlib import Path
import tarfile
from zipfile import ZipFile, ZipInfo
import pytest

from app import __version__
from scripts.bundle_release import build_bundles, safe_name


def test_complete_bundles_include_guides_and_executable_modes(tmp_path, monkeypatch):
    """Assemble synthetic native artifacts with source and both PDF guides.

    Args:
        tmp_path: Isolated build directory.
        monkeypatch: Working-directory override fixture.

    Returns:
        None. Verifies archive layout, permissions and checksums.
    """
    root = Path(__file__).resolve().parents[1]
    (tmp_path / "app").mkdir()
    (tmp_path / "app/__init__.py").write_bytes((root / "app/__init__.py").read_bytes())
    monkeypatch.chdir(tmp_path)
    artifacts = tmp_path / "artifacts"
    source = artifacts / "project-source/project.zip"
    source.parent.mkdir(parents=True)
    with ZipFile(source, "w") as archive:
        archive.write("app/__init__.py")
        archive.writestr("docker-compose.yml", "services: {}")
        for lang in ("en", "fr"):
            archive.writestr(f"docs/user-guide-{lang}.pdf", b"%PDF-fixture")
    windows = artifacts / "launcher-windows-2022/windows_launcher.exe"
    windows.parent.mkdir(parents=True)
    windows.write_bytes(b"Windows fixture")
    for platform in ("macos-15", "macos-15-intel"):
        path = artifacts / f"launcher-{platform}/macos_launcher.app.zip"
        path.parent.mkdir(parents=True)
        with ZipFile(path, "w") as archive:
            entry = ZipInfo("macos_launcher.app/Contents/MacOS/macos_launcher")
            entry.create_system = 3
            entry.external_attr = 0o100755 << 16
            archive.writestr(entry, b"Mac fixture")
    linux = artifacts / "launcher-ubuntu-22.04/linux_launcher.AppImage.tar.gz"
    linux.parent.mkdir(parents=True)
    with tarfile.open(linux, "w:gz") as archive:
        entry = tarfile.TarInfo("linux_launcher.AppImage")
        entry.size = 5
        entry.mode = 0o755
        archive.addfile(entry, io.BytesIO(b"Linux"))
    bundles = build_bundles(artifacts, tmp_path / "output", __version__)
    assert len(bundles) == 4
    for path in bundles:
        with ZipFile(path) as archive:
            assert "docker-compose.yml" in archive.namelist()
            assert "docs/user-guide-en.pdf" in archive.namelist()
            assert "docs/user-guide-fr.pdf" in archive.namelist()
            native = next(
                name for name in archive.namelist() if name.startswith("launch/")
            )
            if "windows" not in path.name:
                assert (archive.getinfo(native).external_attr >> 16) & 0o111
    assert len((tmp_path / "output/SHA256SUMS.txt").read_text().splitlines()) == 6
    with pytest.raises(ValueError, match="empty"):
        build_bundles(artifacts, tmp_path / "output", __version__)


@pytest.mark.parametrize(
    "name", ["../outside", "/absolute", "C:/escape", "dir/../../escape"]
)
def test_bundle_rejects_unsafe_paths(name):
    """Reject archive members that could escape the extracted application.

    Args:
        name: Unsafe archive path.

    Returns:
        None. The path is rejected.
    """
    with pytest.raises(ValueError, match="Unsafe"):
        safe_name(name)
