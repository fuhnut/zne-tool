import asyncio
from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Label

from ui.components.home import _searchbar

_COLOURS = (
    "#ff1111",
    "#ff2244",
    "#ff1166",
    "#ff0088",
    "#dd2299",
    "#bb33aa",
    "#9922bb",
    "#8822cc",
    "#7722dd",
    "#6622ee",
    "#5522ff",
    "#4422ff",
    "#3322ff",
    "#4422ff",
    "#5522ff",
    "#6622ff",
    "#7722ff",
    "#8822ee",
    "#9922dd",
    "#bb22cc",
    "#dd22aa",
    "#ff1199",
    "#ff2277",
    "#ff1155",
    "#ff1133",
    "#ff1111",
)


class zneapp(App):
    CSS_PATH = [
        str(Path(__file__).parent.parent / "styles" / "main.css"),
        str(Path(__file__).parent.parent / "styles" / "home.css"),
    ]
    BINDINGS = (("ctrl+q", "quit", "Quit"),)
    _quit_text = "press ctrl+q to quit"
    _logo_lines = (
        "███████╗███╗░░██╗███████╗",
        "╚════██║████╗░██║██╔════╝",
        "░░███╔═╝██╔██╗██║█████╗░░",
        "██╔══╝░░██║╚████║██╔══╝░░",
        "███████╗██║░╚███║███████╗",
        "╚══════╝╚═╝░░╚══╝╚══════╝",
    )

    def compose(self) -> ComposeResult:
        with Vertical(id="logo-area"):
            for i, line in enumerate(self._logo_lines):
                yield Label(Text(line), id=f"logo-{i}")
        with Vertical(id="search-area"):
            yield _searchbar()
            with Vertical(id="suggestion-list"):
                pass
        with Vertical(id="quit-area"):
            yield Label(self._quit_text, id="quit-hint")

    def _gradient_text(self, line: str, offset: int) -> Text:
        text = Text()
        for k, char in enumerate(line):
            colour = _COLOURS[(k + offset) % 26]
            text.append(char, style=colour)
        return text

    async def on_mount(self) -> None:
        self.run_worker(self._animate_logo_colours())
        self.query_one("#suggestion-list").display = False

    async def _animate_logo_colours(self) -> None:
        offset = 0
        quit_label = self.query_one("#quit-hint", Label)
        logo_labels = tuple(
            self.query_one(f"#logo-{i}", Label) for i in range(len(self._logo_lines))
        )
        while True:
            for i, line in enumerate(self._logo_lines):
                logo_labels[i].update(self._gradient_text(line, offset))
            quit_label.update(self._gradient_text(self._quit_text, offset))
            offset = (offset + 1) % 26
            await asyncio.sleep(0.08)

    def execute_command(self, cmd: str) -> None:
        raw = cmd.strip().lower()
        if not raw.startswith("/"):
            self._clear_search()
            return
        if raw == "/info":
            from ui.screens.system_screen import _systemscreen

            self.push_screen(_systemscreen())
        elif raw == "/search":
            from ui.screens.search_screen import _searchscreen

            self.push_screen(_searchscreen())
        else:
            from ui.components.error_modal import _commanderrormodal

            self.push_screen(_commanderrormodal(raw))
        self._clear_search()

    def _clear_search(self) -> None:
        search = self.query_one(_searchbar)
        search.value = ""
        suggestions = self.query_one("#suggestion-list", Vertical)
        suggestions.remove_children()
        suggestions.display = False

    def on_input_changed(self, event: _searchbar.Changed) -> None:
        value = event.value
        suggestions = self.query_one("#suggestion-list", Vertical)
        suggestions.remove_children()
        if not value.startswith("/"):
            suggestions.display = False
            return
        from ui.commands import get_matches

        matches = get_matches(value)
        if not matches:
            suggestions.display = False
            return
        for cmd, desc in matches:
            suggestions.mount(
                Button(
                    f"{cmd}  —  {desc}",
                    name=cmd,
                    classes="suggestion-btn",
                )
            )
        suggestions.display = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if "suggestion-btn" in event.button.classes:
            self.execute_command(event.button.name)
