"""
Filename: configuration.py
Description: Template-based private launcher configuration and graphical editing.
Author: Raphael Smilet
Date Created: 2026-10-06
Last Modified: 2026-10-06
Version: 0.1.0
"""

import os
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from dotenv import dotenv_values, set_key

OPTIONAL = {"DISCORD_WEBHOOK_URL"}
SECRETS = {"CR_API_TOKEN", "DISCORD_WEBHOOK_URL"}


def read_configuration(root):
    """Create an exact private template copy if absent, then read without interpolation.

    Args:
        root: Application folder containing the example configuration.

    Returns:
        tuple: Template defaults and existing local values, without environment expansion.
    """
    template = root / ".env.example"
    target = root / ".env"
    contents = template.read_bytes()
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(descriptor, "wb") as output:
            output.write(contents)
    return (
        dict(dotenv_values(template, interpolate=False)),
        dict(dotenv_values(target, interpolate=False)),
    )


def missing_fields(defaults, values):
    """Identify required template fields absent or blank in the local configuration.

    Args:
        defaults: Template fields, including defaults and empty placeholders.
        values: Existing or edited configuration values.

    Returns:
        list: Required field names; optional Discord configuration may remain blank.
    """
    return [
        key
        for key in defaults
        if key not in OPTIONAL and not (values.get(key) or "").strip()
    ]


def save_configuration(root, values, original):
    """Atomically update edited fields while preserving other settings and comments.

    Args:
        root: Selected application folder.
        values: Validated edited template fields.
        original: File bytes captured when editing began, for concurrent-edit detection.

    Returns:
        bool: Whether any configuration values changed.

    Raises:
        ValueError: Input contains a newline or the file changed during editing.
    """
    if any(any(char in value for char in "\r\n\0") for value in values.values()):
        raise ValueError("Settings must contain single-line values.")
    target = root / ".env"
    if target.read_bytes() != original:
        raise ValueError(
            "Settings changed outside the launcher. Reopen Application settings."
        )
    previous = dotenv_values(target, interpolate=False)
    changes = {
        key: value for key, value in values.items() if previous.get(key) != value
    }
    if not changes:
        return False
    descriptor, filename = tempfile.mkstemp(prefix=".launcher-settings-", dir=root)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(original)
        for key, value in changes.items():
            set_key(filename, key, value, quote_mode="always")
        if target.read_bytes() != original:
            raise ValueError(
                "Settings changed outside the launcher. Reopen Application settings."
            )
        os.replace(filename, target)
    finally:
        Path(filename).unlink(missing_ok=True)
    return True


class ConfigurationDialog(simpledialog.Dialog):
    """Edit template fields locally with masked secrets and explicit Save/Cancel."""

    def __init__(self, parent, root):
        """Load local settings and open the modal editor.

        Args:
            parent: Launcher window owning the dialog.
            root: Application directory.

        Returns:
            None. The result is True only when saved settings changed.
        """
        self.root = root
        self.defaults, self.values = read_configuration(root)
        self.original = (root / ".env").read_bytes()
        self.fields = {}
        self.changed = False
        super().__init__(parent, title="Application settings")

    def body(self, master):
        """Display required fields, defaults and password-masked secret entries.

        Args:
            master: Dialog content frame.

        Returns:
            None.
        """
        ttk.Label(
            master,
            text=(
                "Complete required fields. Discord is optional.\n"
                "API token: developer.clashroyale.com (allow your public IP)."
            ),
        ).grid(row=0, columnspan=2, pady=8)
        for row, (key, default) in enumerate(self.defaults.items(), start=1):
            label = key + (" (optional)" if key in OPTIONAL else " *")
            ttk.Label(master, text=label).grid(row=row, column=0, sticky="w", padx=6)
            self.fields[key] = tk.StringVar(value=self.values.get(key) or default or "")
            ttk.Entry(
                master,
                textvariable=self.fields[key],
                width=48,
                show="*" if key in SECRETS else "",
            ).grid(row=row, column=1, padx=6, pady=4)

    def validate(self):
        """Require complete mandatory fields and save only after validation succeeds.

        Args:
            None.

        Returns:
            bool: True on successful save; False keeps the dialog open for correction.
        """
        values = {key: variable.get().strip() for key, variable in self.fields.items()}
        missing = missing_fields(self.defaults, values)
        if missing:
            messagebox.showerror(
                "Missing settings", "Complete: " + ", ".join(missing), parent=self
            )
            return False
        try:
            self.changed = save_configuration(self.root, values, self.original)
        except (OSError, ValueError) as error:
            messagebox.showerror("Settings", str(error), parent=self)
            return False
        return True
