"""Screen recording helpers used by hotkey callbacks."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
from datetime import datetime
from pathlib import Path

_RECORDER: subprocess.Popen | None = None


def _output_file(prefix: str = "recording", ext: str = "mkv") -> Path:
    target_dir = Path(os.environ.get("XDG_VIDEOS_DIR", Path.home() / "Videos"))
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.{ext}"


def toggle_recording(session_type: str) -> str:
    """Toggle screen recording process and return status string."""
    global _RECORDER

    if _RECORDER and _RECORDER.poll() is None:
        _RECORDER.send_signal(signal.SIGINT)
        _RECORDER.wait(timeout=5)
        _RECORDER = None
        return "recording-stopped"

    if session_type == "wayland" and shutil.which("wf-recorder"):
        output = _output_file("recording", "mp4")
        _RECORDER = subprocess.Popen(["wf-recorder", "-f", str(output)])
        return f"recording-started:{output}"

    if shutil.which("ffmpeg"):
        output = _output_file("recording", "mkv")
        display = os.environ.get("DISPLAY", ":0")
        _RECORDER = subprocess.Popen(
            [
                "ffmpeg",
                "-y",
                "-video_size",
                "1920x1080",
                "-f",
                "x11grab",
                "-i",
                display,
                str(output),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return f"recording-started:{output}"

    return "recording-unavailable"


def stop_recording() -> None:
    """Best-effort recording shutdown for service lifecycle events."""
    global _RECORDER
    if _RECORDER and _RECORDER.poll() is None:
        _RECORDER.send_signal(signal.SIGINT)
        _RECORDER.wait(timeout=5)
    _RECORDER = None
