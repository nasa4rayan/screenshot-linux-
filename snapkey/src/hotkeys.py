from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .record import capture_short_gif


HotkeyHandler = Callable[[], Any]


class HotkeyRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, HotkeyHandler] = {}
        self.last_selection: dict[str, int] | None = None

    def register(self, hotkey: str, handler: HotkeyHandler) -> None:
        self._handlers[hotkey] = handler

    def trigger(self, hotkey: str) -> Any:
        handler = self._handlers[hotkey]
        return handler()

    def register_defaults(self) -> None:
        self.register("SUPER+SHIFT+G", self.capture_short_gif)

    def capture_short_gif(self) -> None:
        capture_short_gif(last_selection=self.last_selection)
