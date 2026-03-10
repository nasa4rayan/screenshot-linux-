"""Screenshot helpers used by hotkey callbacks."""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def _output_file(prefix: str = "screenshot", ext: str = "png") -> Path:
    target_dir = Path(os.environ.get("XDG_PICTURES_DIR", Path.home() / "Pictures"))
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.{ext}"


def _run_if_available(*cmd: str) -> bool:
    if not shutil.which(cmd[0]):
        return False
    subprocess.run(cmd, check=False)
    return True


def capture_screenshot(session_type: str) -> Path | None:
    """Capture the current screen to a timestamped file.

    Supports common Wayland and X11 tooling. Returns the generated path when
    a command was successfully started.
    """
    output = _output_file()
    if session_type == "wayland":
        if _run_if_available("grim", str(output)):
            return output
        if _run_if_available("gnome-screenshot", "-f", str(output)):
            return output
    else:
        if _run_if_available("maim", str(output)):
            return output
        if _run_if_available("scrot", str(output)):
            return output
        if _run_if_available("gnome-screenshot", "-f", str(output)):
            return output
    return None
