"""Global hotkey registration for SnapKey.

This module uses compositor/desktop-specific commands on Wayland where generic
low-level key grabbing is intentionally restricted.
"""

from __future__ import annotations

import os
import shlex
import shutil
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ActionCallback = Callable[[str], None]
DAEMON_CMD = os.environ.get("SNAPKEY_DAEMON_CMD")
if DAEMON_CMD:
    CONTROL_CMD = DAEMON_CMD
else:
    CONTROL_CMD = f"python3 {shlex.quote(str(Path(__file__).with_name('daemon.py')))} --command"


@dataclass(frozen=True)
class HotkeyMap:
    screenshot: str = "SUPER+SHIFT+S"
    record: str = "SUPER+SHIFT+R"
    quit: str = "SUPER+SHIFT+Q"
    optional_gif: str = "SUPER+SHIFT+G"


class HotkeyRegistrar:
    """Register desktop global shortcuts with low CPU overhead."""

    def __init__(
        self,
        session_type: str,
        on_screenshot: ActionCallback,
        on_record: ActionCallback,
        on_quit: ActionCallback,
        on_optional_gif: ActionCallback | None = None,
    ) -> None:
        self.session_type = session_type
        self.on_screenshot = on_screenshot
        self.on_record = on_record
        self.on_quit = on_quit
        self.on_optional_gif = on_optional_gif
        self._bind_process: subprocess.Popen | None = None

    def dispatch(self, action: str) -> None:
        """Route an action into the daemon callbacks."""
        if action == "screenshot":
            self.on_screenshot(action)
        elif action == "record":
            self.on_record(action)
        elif action == "quit":
            self.on_quit(action)
        elif action == "gif" and self.on_optional_gif:
            self.on_optional_gif(action)

    def register(self) -> str:
        if self.session_type == "wayland":
            return self._register_wayland()
        return self._register_x11()

    def unregister(self) -> None:
        if self._bind_process and self._bind_process.poll() is None:
            self._bind_process.send_signal(signal.SIGTERM)
            self._bind_process.wait(timeout=2)

    def _register_wayland(self) -> str:
        if os.environ.get("SWAYSOCK") and shutil.which("swaymsg"):
            self._run("swaymsg", "bindsym", "Super+Shift+s", "exec", f"{CONTROL_CMD} screenshot")
            self._run("swaymsg", "bindsym", "Super+Shift+r", "exec", f"{CONTROL_CMD} record")
            self._run("swaymsg", "bindsym", "Super+Shift+q", "exec", f"{CONTROL_CMD} quit")
            self._run("swaymsg", "bindsym", "Super+Shift+g", "exec", f"{CONTROL_CMD} gif")
            return "wayland-sway"

        if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") and shutil.which("hyprctl"):
            self._run("hyprctl", "keyword", "bind", f",SUPER_SHIFT,S,exec,{CONTROL_CMD} screenshot")
            self._run("hyprctl", "keyword", "bind", f",SUPER_SHIFT,R,exec,{CONTROL_CMD} record")
            self._run("hyprctl", "keyword", "bind", f",SUPER_SHIFT,Q,exec,{CONTROL_CMD} quit")
            self._run("hyprctl", "keyword", "bind", f",SUPER_SHIFT,G,exec,{CONTROL_CMD} gif")
            return "wayland-hyprland"

        if shutil.which("gsettings"):
            return "wayland-gnome-manual"
        return "wayland-manual"

    def _register_x11(self) -> str:
        if shutil.which("sxhkd"):
            config = "\n".join(
                [
                    "super + shift + s",
                    f"\t{CONTROL_CMD} screenshot",
                    "super + shift + r",
                    f"\t{CONTROL_CMD} record",
                    "super + shift + q",
                    f"\t{CONTROL_CMD} quit",
                    "super + shift + g",
                    f"\t{CONTROL_CMD} gif",
                    "",
                ]
            )
            self._bind_process = subprocess.Popen(["sxhkd", "-c", "/dev/stdin"], stdin=subprocess.PIPE)
            assert self._bind_process.stdin is not None
            self._bind_process.stdin.write(config.encode())
            self._bind_process.stdin.close()
            return "x11-sxhkd"

        if shutil.which("xbindkeys"):
            return "x11-xbindkeys-manual"
        return "x11-manual"

    @staticmethod
    def _run(*cmd: str) -> None:
        subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
