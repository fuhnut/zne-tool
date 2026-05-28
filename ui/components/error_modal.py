from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class _commanderrormodal(ModalScreen):
    BINDINGS = (
        ("escape", "close", "Close"),
        ("ctrl+q", "close", "Close"),
    )

    def __init__(self, command: str, **kwargs) -> None:
        self._command = command
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        with Vertical(id="error-modal"):
            yield Button("✕", id="error-close-btn", variant="error")
            yield Label(
                f"⚠  command {self._command} doesn't exist :c",
                id="error-msg",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "error-close-btn":
            self.app.pop_screen()

    def action_close(self) -> None:
        self.app.pop_screen()
