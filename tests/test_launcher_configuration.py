"""
Filename: test_launcher_configuration.py
Description: Check template copying, missing settings and safe private configuration updates.
Author: Raphael Smilet
Date Created: 2026-10-06
Last Modified: 2026-10-06
Version: 0.1.0
"""

from pathlib import Path
import pytest
from dotenv import dotenv_values
from launch.configuration import read_configuration, missing_fields, save_configuration


def test_template_copy_is_exact_and_existing_file_is_preserved(tmp_path):
    """Create the complete example file and never replace existing configuration on read.

    Args:
        tmp_path: Isolated application directory.

    Returns:
        None. Assertions verify byte equality, optional fields and preservation.
    """
    template = Path(__file__).resolve().parents[1] / ".env.example"
    (tmp_path / ".env.example").write_bytes(template.read_bytes())
    defaults, values = read_configuration(tmp_path)
    assert (tmp_path / ".env").read_bytes() == template.read_bytes()
    assert missing_fields(defaults, values) == ["CR_API_TOKEN", "CLAN_TAG"]
    original = b'# custom\nCR_API_TOKEN=existing\nCLAN_TAG="#TEST"\nCUSTOM=value\n'
    (tmp_path / ".env").write_bytes(original)
    read_configuration(tmp_path)
    assert (tmp_path / ".env").read_bytes() == original


def test_save_preserves_comments_and_unedited_secrets(tmp_path):
    """Update only edited keys and preserve optional blanks and custom configuration.

    Args:
        tmp_path: Isolated directory with synthetic private values.

    Returns:
        None. Assertions verify round-trip quoting and preservation.
    """
    original = b"# keep comment\nCR_API_TOKEN=synthetic\nCUSTOM=keep\n"
    target = tmp_path / ".env"
    target.write_bytes(original)
    assert save_configuration(
        tmp_path,
        {"CR_API_TOKEN": "synthetic", "CLAN_TAG": "#TEST", "DISCORD_WEBHOOK_URL": ""},
        original,
    )
    assert target.read_bytes().startswith(original)
    values = dotenv_values(target)
    assert values["CLAN_TAG"] == "#TEST"
    assert values["CR_API_TOKEN"] == "synthetic"
    assert values["CUSTOM"] == "keep"
    assert values["DISCORD_WEBHOOK_URL"] == ""
    assert not save_configuration(tmp_path, dict(values), target.read_bytes())


def test_save_refuses_external_edits_and_multiline_values(tmp_path):
    """Reject stale editor writes and injected extra environment assignments.

    Args:
        tmp_path: Temporary application directory.

    Returns:
        None. Assertions check no data is overwritten after validation failures.
    """
    target = tmp_path / ".env"
    target.write_bytes(b"CLAN_TAG=new\n")
    with pytest.raises(ValueError, match="outside"):
        save_configuration(tmp_path, {"CLAN_TAG": "#TEST"}, b"CLAN_TAG=old\n")
    with pytest.raises(ValueError, match="single-line"):
        save_configuration(
            tmp_path, {"CLAN_TAG": "#TEST\nOTHER=bad"}, target.read_bytes()
        )
    assert target.read_bytes() == b"CLAN_TAG=new\n"
