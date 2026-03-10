"""SnapKey daemon entrypoint.

Responsibilities:
- Startup and environment detection (Wayland vs X11)
- Global hotkey registration strategy selection
- Idle, event-driven lifecycle (signal + control FIFO)
"""

from __future__ import annotations

import argparse
import os
import selectors
import signal
from pathlib import Path

from hotkeys import HotkeyRegistrar
from record import stop_recording, toggle_recording
from screenshot import capture_screenshot
from ui import notify


class SnapKeyDaemon:
    def __init__(self) -> None:
        self.session_type = self._detect_session_type()
        self.running = True
        self.selector = selectors.DefaultSelector()
        self.control_fifo = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "snapkeyd.fifo"
        self._hotkeys = HotkeyRegistrar(
            self.session_type,
            on_screenshot=lambda _: self.handle_command("screenshot"),
            on_record=lambda _: self.handle_command("record"),
            on_quit=lambda _: self.handle_command("quit"),
            on_optional_gif=lambda _: self.handle_command("gif"),
        )

    @staticmethod
    def _detect_session_type() -> str:
        if os.environ.get("XDG_SESSION_TYPE") == "wayland" or os.environ.get("WAYLAND_DISPLAY"):
            return "wayland"
        return "x11"

    def start(self) -> None:
        strategy = self._hotkeys.register()
        self._setup_signals()
        self._setup_fifo()
        notify("SnapKey started", f"Session: {self.session_type}, strategy: {strategy}")
        self._event_loop()

    def stop(self) -> None:
        self.running = False
        self._hotkeys.unregister()
        stop_recording()
        if self.control_fifo.exists():
            self.control_fifo.unlink(missing_ok=True)
        notify("SnapKey stopped")

    def _setup_signals(self) -> None:
        signal.signal(signal.SIGTERM, lambda *_: self.handle_command("quit"))
        signal.signal(signal.SIGINT, lambda *_: self.handle_command("quit"))

    def _setup_fifo(self) -> None:
        self.control_fifo.unlink(missing_ok=True)
        os.mkfifo(self.control_fifo)
        fifo_fd = os.open(self.control_fifo, os.O_RDWR | os.O_NONBLOCK)
        self.selector.register(fifo_fd, selectors.EVENT_READ)

    def _event_loop(self) -> None:
        while self.running:
            for key, _ in self.selector.select(timeout=None):
                payload = os.read(key.fd, 1024).decode().strip().lower()
                if payload:
                    self.handle_command(payload)

    def handle_command(self, command: str) -> None:
        if command == "screenshot":
            output = capture_screenshot(self.session_type)
            notify("Screenshot", str(output) if output else "No compatible tool found")
            return

        if command == "record":
            state = toggle_recording(self.session_type)
            notify("Recording", state)
            return

        if command == "gif":
            notify("GIF capture", "Optional action not yet implemented")
            return

        if command == "quit":
            self.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="SnapKey daemon")
    parser.add_argument("--command", help="Send single command to running daemon", default=None)
    args = parser.parse_args()

    fifo = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "snapkeyd.fifo"
    if args.command:
        if not fifo.exists():
            raise SystemExit("snapkey daemon is not running")
        with fifo.open("w", encoding="utf-8") as handle:
            handle.write(args.command)
        return

    daemon = SnapKeyDaemon()
    daemon.start()


if __name__ == "__main__":
    main()
