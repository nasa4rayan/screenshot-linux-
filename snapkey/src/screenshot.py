from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path.home() / "Pictures" / "SnapKey"
NOTIFICATION_MESSAGE = "Screenshot saved and copied to clipboard"


def take_region_screenshot() -> dict[str, Any]:
    """Capture a user-selected screenshot region and copy it to clipboard.

    Returns:
        Structured status for daemon logging.
    """
    status: dict[str, Any] = {
        "success": False,
        "session_type": None,
        "backend": None,
        "file_path": None,
        "copied_to_clipboard": False,
        "notification_sent": False,
        "error": None,
    }

    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        status["error"] = f"failed_to_create_output_dir: {exc}"
        return status

    session_type = _detect_session_type()
    status["session_type"] = session_type

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = OUTPUT_DIR / f"snapkey-{timestamp}.png"

    capture_result = _capture_region(session_type, output_path)
    status.update(
        {
            "backend": capture_result.get("backend"),
            "error": capture_result.get("error"),
        }
    )
    if not capture_result.get("success"):
        return status

    status["file_path"] = str(output_path)

    clipboard_result = _copy_to_clipboard(session_type, output_path)
    status["copied_to_clipboard"] = clipboard_result["success"]
    if not clipboard_result["success"]:
        status["error"] = clipboard_result["error"]
        return status

    status["notification_sent"] = _send_notification(NOTIFICATION_MESSAGE)
    status["success"] = True
    status["error"] = None
    return status


def _capture_region(session_type: str, output_path: Path) -> dict[str, Any]:
    if session_type == "wayland":
        return _capture_wayland(output_path)
    if session_type == "x11":
        return _capture_x11(output_path)
    return {"success": False, "backend": None, "error": "unsupported_session_type"}


def _capture_wayland(output_path: Path) -> dict[str, Any]:
    if not _tool_exists("grim"):
        return {"success": False, "backend": "grim", "error": "grim_not_found"}

    geometry = None
    if _tool_exists("slurp"):
        selection = _run_command(["slurp"])
        if selection.returncode != 0:
            return {"success": False, "backend": "slurp+grim", "error": "region_selection_cancelled"}
        geometry = selection.stdout.strip()
    else:
        geometry = _get_geometry_from_ui()

    if not geometry:
        return {"success": False, "backend": "grim", "error": "no_region_selected"}

    capture = _run_command(["grim", "-g", geometry, str(output_path)])
    if capture.returncode != 0:
        return {
            "success": False,
            "backend": "grim",
            "error": f"grim_failed: {capture.stderr.strip() or 'unknown_error'}",
        }

    return {"success": True, "backend": "slurp+grim" if _tool_exists("slurp") else "ui+grim", "error": None}


def _capture_x11(output_path: Path) -> dict[str, Any]:
    if _tool_exists("maim"):
        capture = _run_command(["maim", "-s", str(output_path)])
        if capture.returncode == 0:
            return {"success": True, "backend": "maim", "error": None}

    if _tool_exists("scrot"):
        capture = _run_command(["scrot", "-s", str(output_path)])
        if capture.returncode == 0:
            return {"success": True, "backend": "scrot", "error": None}

    geometry = _normalize_geometry(_get_geometry_from_ui(), session_type="x11")
    if not geometry:
        return {
            "success": False,
            "backend": None,
            "error": "no_supported_x11_capture_tool_or_ui_selection",
        }

    if _tool_exists("maim"):
        x, y, w, h = geometry
        maim_geometry = f"{w}x{h}+{x}+{y}"
        capture = _run_command(["maim", "-g", maim_geometry, str(output_path)])
        if capture.returncode == 0:
            return {"success": True, "backend": "ui+maim", "error": None}

    if _tool_exists("scrot"):
        x, y, w, h = geometry
        scrot_geometry = f"{x},{y},{w},{h}"
        capture = _run_command(["scrot", "-a", scrot_geometry, str(output_path)])
        if capture.returncode == 0:
            return {"success": True, "backend": "ui+scrot", "error": None}

    return {
        "success": False,
        "backend": None,
        "error": "failed_to_capture_x11_region",
    }


def _copy_to_clipboard(session_type: str, file_path: Path) -> dict[str, Any]:
    if session_type == "wayland":
        if not _tool_exists("wl-copy"):
            return {"success": False, "error": "wl-copy_not_found"}
        with file_path.open("rb") as image_file:
            proc = subprocess.run(["wl-copy"], stdin=image_file, check=False)
        return {"success": proc.returncode == 0, "error": None if proc.returncode == 0 else "wl-copy_failed"}

    if session_type == "x11":
        if not _tool_exists("xclip"):
            return {"success": False, "error": "xclip_not_found"}
        proc = _run_command(
            ["xclip", "-selection", "clipboard", "-t", "image/png", "-i", str(file_path)]
        )
        return {
            "success": proc.returncode == 0,
            "error": None if proc.returncode == 0 else "xclip_failed",
        }

    return {"success": False, "error": "unsupported_session_type"}


def _send_notification(message: str) -> bool:
    if not _tool_exists("notify-send"):
        return False
    proc = _run_command(["notify-send", message])
    return proc.returncode == 0


def _get_geometry_from_ui() -> str | tuple[int, int, int, int] | None:
    """Try optional GTK selection helpers from ui.py when native tool UX is unavailable."""
    ui_module = None
    try:
        from . import ui as ui_module  # type: ignore
    except Exception:
        try:
            import ui as ui_module  # type: ignore
        except Exception:
            return None

    for attr in ("select_region", "select_capture_region", "get_selection_geometry"):
        func = getattr(ui_module, attr, None)
        if callable(func):
            try:
                return func()
            except Exception:
                return None
    return None


def _normalize_geometry(
    geometry: str | tuple[int, int, int, int] | dict[str, Any] | None,
    session_type: str,
) -> tuple[int, int, int, int] | None:
    if geometry is None:
        return None

    if isinstance(geometry, tuple) and len(geometry) == 4:
        return tuple(int(v) for v in geometry)

    if isinstance(geometry, dict):
        x = geometry.get("x")
        y = geometry.get("y")
        width = geometry.get("width")
        height = geometry.get("height")
        if all(v is not None for v in (x, y, width, height)):
            return int(x), int(y), int(width), int(height)

    if isinstance(geometry, str):
        raw = geometry.strip()
        if session_type == "x11":
            # Accept slurp-like: "x,y wxh"
            if "," in raw and " " in raw and "x" in raw:
                try:
                    xy, wh = raw.split(" ", 1)
                    x, y = (int(v) for v in xy.split(","))
                    w, h = (int(v) for v in wh.split("x"))
                    return x, y, w, h
                except ValueError:
                    return None
    return None


def _detect_session_type() -> str:
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session_type in {"wayland", "x11"}:
        return session_type
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return "unknown"


def _tool_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)
