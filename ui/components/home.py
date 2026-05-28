from __future__ import annotations

from textual.events import Key
from textual.widgets import Input


class _searchbar(Input):
    def __init__(self, placeholder: str = "enter a command. type '/' to get started.", **kwargs) -> None:
        super().__init__(
            placeholder=placeholder,
            id="search-bar",
            **kwargs,
        )

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        self.app.execute_command(self.value)

    def on_key(self, event: Key) -> None:
        if event.key != "tab" or not self.value.startswith("/"):
            return
        from ui.commands import get_matches

        matches = get_matches(self.value)
        if len(matches) == 1:
            self.value = matches[0][0]
            event.stop()
