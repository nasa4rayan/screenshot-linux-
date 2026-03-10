"""Minimal UI notification helpers."""

from __future__ import annotations

import shutil
import subprocess


def notify(summary: str, body: str = "") -> None:
    """Send a desktop notification when available."""
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", summary, body], check=False)
