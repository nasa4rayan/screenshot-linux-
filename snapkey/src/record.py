from __future__ import annotations

import datetime as dt
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Mapping


DEFAULT_DURATION_SECONDS = 3
DEFAULT_FPS = 12
DEFAULT_OUTPUT_DIR = Path.home() / "Videos" / "SnapKey"


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def _selection_to_geometry(selection: Mapping[str, int] | None) -> str | None:
    if not selection:
        return None

    required_keys = {"x", "y", "width", "height"}
    if not required_keys.issubset(selection.keys()):
        return None

    x = int(selection["x"])
    y = int(selection["y"])
    width = int(selection["width"])
    height = int(selection["height"])

    if width <= 0 or height <= 0:
        return None

    return f"{x},{y} {width}x{height}"


def _timestamped_gif_path() -> Path:
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUTPUT_DIR / f"snapkey-{timestamp}.gif"


def _record_with_wf_recorder(video_path: Path, duration_seconds: int, geometry: str | None) -> None:
    command = [
        "wf-recorder",
        "-f",
        str(video_path),
        "-t",
        str(duration_seconds),
    ]
    if geometry:
        command.extend(["-g", geometry])

    _run(command)


def _record_with_ffmpeg(video_path: Path, duration_seconds: int, geometry: str | None) -> None:
    display = os.environ.get("DISPLAY", ":0.0")
    command = [
        "ffmpeg",
        "-y",
        "-video_size",
        "1920x1080",
        "-framerate",
        "30",
        "-f",
        "x11grab",
        "-i",
        display,
        "-t",
        str(duration_seconds),
        str(video_path),
    ]

    if geometry:
        origin, size = geometry.split(" ")
        x, y = origin.split(",")
        command = [
            "ffmpeg",
            "-y",
            "-video_size",
            size,
            "-framerate",
            "30",
            "-f",
            "x11grab",
            "-i",
            f"{display}+{x},{y}",
            "-t",
            str(duration_seconds),
            str(video_path),
        ]

    _run(command)


def _transcode_to_gif(source_video: Path, target_gif: Path) -> None:
    palette = source_video.with_name("palette.png")
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source_video),
            "-vf",
            f"fps={DEFAULT_FPS},scale=iw:-1:flags=lanczos,palettegen",
            str(palette),
        ]
    )
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source_video),
            "-i",
            str(palette),
            "-lavfi",
            f"fps={DEFAULT_FPS},scale=iw:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=sierra2_4a",
            str(target_gif),
        ]
    )


def _notify_completed(path: Path) -> None:
    if shutil.which("notify-send") is None:
        return

    _run(["notify-send", "SnapKey", f"Short GIF saved: {path.name}\n{path}"])


def capture_short_gif(last_selection: Mapping[str, int] | None = None, duration_seconds: int = DEFAULT_DURATION_SECONDS) -> Path:
    """Record a short clip and transcode it to GIF.

    If `last_selection` is provided and has x/y/width/height values, capture is limited to
    that region. Otherwise the capture defaults to fullscreen.
    """

    geometry = _selection_to_geometry(last_selection)
    gif_path = _timestamped_gif_path()

    with tempfile.TemporaryDirectory(prefix="snapkey-gif-") as temp_dir:
        temp_video = Path(temp_dir) / "capture.mkv"

        if shutil.which("wf-recorder"):
            _record_with_wf_recorder(temp_video, duration_seconds, geometry)
        elif shutil.which("ffmpeg"):
            _record_with_ffmpeg(temp_video, duration_seconds, geometry)
        else:
            raise RuntimeError("No supported recorder found. Install wf-recorder or ffmpeg.")

        _transcode_to_gif(temp_video, gif_path)

    _notify_completed(gif_path)
    return gif_path
