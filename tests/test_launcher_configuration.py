"""
Filename: test_launcher_configuration.py
Description: Check template copying, missing settings and safe private configuration updates.
Author: Raphael Smilet
Date Created: 2026-10-06
Last Modified: 2026-10-19
Version: 0.1.1
"""

from pathlib import Path
import os
import subprocess
import sys
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


@pytest.mark.parametrize("disabled", [False, True])
def test_saved_standalone_settings_are_loaded_on_restart(tmp_path, disabled):
    """Load edited user settings instead of an unrelated file or stale environment.

    Args:
        tmp_path: Isolated synthetic configuration files.
        disabled: Whether the smoke-test dotenv opt-out is active.

    Returns:
        None. Fresh runtimes observe saved changes while smoke tests stay isolated.
    """
    root = tmp_path / "user"
    root.mkdir()
    (root / ".env.example").write_text(
        "CR_API_TOKEN=\nCLAN_TAG=\nDISCORD_WEBHOOK_URL=\n", encoding="utf-8"
    )
    read_configuration(root)
    target = root / ".env"
    # A conflicting working-directory file must never win over the selected file.
    (tmp_path / ".env").write_text("CLAN_TAG=wrong-file\n", encoding="utf-8")
    for tag in ("#FIRST", "#EDITED"):
        assert save_configuration(
            root,
            {"CR_API_TOKEN": "dummy", "CLAN_TAG": tag, "DISCORD_WEBHOOK_URL": ""},
            target.read_bytes(),
        )
        env = dict(os.environ)
        env.update(
            PYTHONPATH=str(Path(__file__).resolve().parents[1]),
            CLAN_ENV_FILE=str(target),
            CLAN_TAG="inherited",
            CR_API_TOKEN="inherited",
            DISCORD_WEBHOOK_URL="inherited",
            PYTHON_DOTENV_DISABLED="1" if disabled else "0",
            EXPECTED_TAG="inherited" if disabled else tag,
        )
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import os; from app.core.config import settings; "
                    "assert settings.CLAN_TAG == os.environ['EXPECTED_TAG']; "
                    "assert settings.CR_API_TOKEN == "
                    "('inherited' if os.environ['PYTHON_DOTENV_DISABLED']=='1' else 'dummy'); "
                    "assert settings.DISCORD_WEBHOOK_URL == "
                    "('inherited' if os.environ['PYTHON_DOTENV_DISABLED']=='1' else '')"
                ),
            ],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
