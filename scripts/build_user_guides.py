"""
Filename: build_user_guides.py
Description: Build English and French PDF guides from the maintained Markdown source.
Author: Raphael Smilet
Date Created: 2026-10-07
Last Modified: 2026-10-07
Version: 0.1.0
"""

import argparse
from html import escape
from pathlib import Path
import re

# Documentation build dependencies; not application runtime dependencies.
# pylint: disable=import-error
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)


def inline(text):
    """Convert inline Markdown to safe PDF paragraph markup.

    Args:
        text: Markdown text without block syntax.

    Returns:
        str: Escaped text with links and emphasis.
    """
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r"<font color='#24486b'>\1</font>", text)

    def link(match):
        """Expand repository-relative links for offline PDF readers.

        Args:
            match: Markdown link match.

        Returns:
            str: Clickable PDF link markup.
        """
        label, target = match.groups()
        if not target.startswith(("https://", "http://")):
            target = "https://github.com/RaphaelDP/clash-royale-manager/blob/main/" + (
                target[3:] if target.startswith("../") else "docs/" + target
            )
        return f'<a href="{target}" color="#17639b">{label}</a>'

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)


def build_guide(source, output, language, font_dir):
    """Render one language as a paginated PDF with tables and real screenshots.

    Args:
        source: Path to bilingual Markdown.
        output: Destination PDF.
        language: en or fr.
        font_dir: Directory containing DejaVu Sans font files.

    Returns:
        None. Writes a PDF file.
    """
    for name, filename in (
        ("Guide", "DejaVuSans.ttf"),
        ("GuideBold", "DejaVuSans-Bold.ttf"),
    ):
        pdfmetrics.registerFont(TTFont(name, str(font_dir / filename)))
    pdfmetrics.registerFontFamily("Guide", normal="Guide", bold="GuideBold")
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = "Guide"
        style.fontSize = 9
        style.leading = 14
    for name, size in (
        ("Heading1", 22),
        ("Heading2", 17),
        ("Heading3", 13),
        ("Heading4", 11),
    ):
        styles[name].fontName = "GuideBold"
        styles[name].fontSize = size
        styles[name].leading = size + 5
        styles[name].textColor = colors.HexColor("#17324d")
    styles.add(
        ParagraphStyle(
            "Cell",
            parent=styles["BodyText"],
            fontSize=8,
            leading=11,
            alignment=TA_LEFT,
            wordWrap="CJK",
        )
    )
    text = source.read_text(encoding="utf-8")
    english, french = text.split('<a id="english"></a>', 1)[1].split(
        '<a id="francais"></a>'
    )
    text = english if language == "en" else french
    story = [
        Paragraph("Clash Royale Clan Manager", styles["Heading1"]),
        Paragraph(
            (
                "User guide · English"
                if language == "en"
                else "Guide utilisateur · Français"
            ),
            styles["Heading2"],
        ),
        Paragraph("2026-10-07", styles["BodyText"]),
        Spacer(1, 14),
    ]
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line or line.startswith("<a "):
            continue
        if line.startswith("|"):
            rows = [line]
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(lines[index].strip())
                index += 1
            cells = [
                [
                    Paragraph(inline(cell.strip()), styles["Cell"])
                    for cell in row.strip("|").split("|")
                ]
                for row in rows
                if not re.fullmatch(r"[| :\-]+", row)
            ]
            table = Table(
                cells, colWidths=[475 / len(cells[0])] * len(cells[0]), repeatRows=1
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5edf5")),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c3ccd5")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.extend([table, Spacer(1, 10)])
        elif line.startswith("!["):
            match = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", line)
            if match:
                path = source.parent / match[2]
                width, height = ImageReader(str(path)).getSize()
                story.extend(
                    [
                        Image(str(path), width=475, height=475 * height / width),
                        Paragraph(inline(match[1]), styles["Cell"]),
                        Spacer(1, 12),
                    ]
                )
        elif line.startswith("#"):
            level = min(len(line) - len(line.lstrip("#")), 4)
            story.append(
                Paragraph(inline(line.lstrip("# ")), styles[f"Heading{level}"])
            )
        else:
            paragraph = [line]
            while (
                index < len(lines)
                and lines[index].strip()
                and not re.match(r"^(#|\||!\[|\d+\. |[-*] )", lines[index].strip())
            ):
                paragraph.append(lines[index].strip())
                index += 1
            story.append(Paragraph(inline(" ".join(paragraph)), styles["BodyText"]))
            story.append(Spacer(1, 5))
    output.parent.mkdir(parents=True, exist_ok=True)

    def footer(canvas, document):
        """Add page numbers to each generated page.

        Args:
            canvas: ReportLab drawing canvas.
            document: Current document.

        Returns:
            None.
        """
        canvas.setFont("Guide", 8)
        canvas.drawString(60, 28, "Clash Royale Clan Manager")
        canvas.drawRightString(535, 28, str(document.page))

    SimpleDocTemplate(
        str(output),
        pagesize=(595, 842),
        leftMargin=60,
        rightMargin=60,
        topMargin=40,
        bottomMargin=45,
        title="Clash Royale Clan Manager",
        author="Raphael Smilet",
    ).build(story, onFirstPage=footer, onLaterPages=footer)


def main():
    """Build both PDF guides with optional source, output and font paths.

    Args:
        None. Reads command-line arguments.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(
        description="Build English and French PDF user guides."
    )
    parser.add_argument("--source", type=Path, default=Path("docs/user-guide.md"))
    parser.add_argument("--output-dir", type=Path, default=Path("docs"))
    parser.add_argument(
        "--font-dir", type=Path, default=Path("/usr/share/fonts/truetype/dejavu")
    )
    args = parser.parse_args()
    for language in ("en", "fr"):
        build_guide(
            args.source,
            args.output_dir / f"user-guide-{language}.pdf",
            language,
            args.font_dir,
        )


if __name__ == "__main__":
    main()
