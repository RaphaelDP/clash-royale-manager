"""
Filename: build_icons.py
Description: Generate platform and window icons from the shared launcher SVG.
Author: Raphael Smilet
Date Created: 2026-10-06
Last Modified: 2026-10-06
Version: 0.1.1
"""

from io import BytesIO
from pathlib import Path


def main():
    """Render the master SVG and write PNG, Windows ICO and macOS ICNS icons.

    Args:
        None. Paths are relative to this module, independent of the working directory.

    Returns:
        None. Writes derived icons beside their corresponding platform launchers.
    """
    # These dependencies belong to the build environment, not the application runtime.
    # resvg exposes svg_to_bytes through a compiled extension.
    # pylint: disable=import-outside-toplevel,import-error,no-member
    import resvg_py
    from PIL import Image

    root = Path(__file__).resolve().parent
    svg = (root / "clan-manager.svg").read_text(encoding="utf-8")
    svg = svg.replace('width="256" height="256"', 'width="1024" height="1024"')
    with Image.open(BytesIO(resvg_py.svg_to_bytes(svg_string=svg))) as icon:
        icon.save(root / "macos/clan-manager.icns", format="ICNS")
        icon.save(
            root / "windows/clan-manager.ico",
            format="ICO",
            sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )
        icon.resize((256, 256)).save(root / "clan-manager.png")


if __name__ == "__main__":
    main()
