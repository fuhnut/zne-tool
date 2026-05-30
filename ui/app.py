import asyncio
from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Button, Label

from core.theme import all_themes, gradient_colours, load_theme, variable_defaults
from ui.components.home import _searchbar


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

    def get_theme_variable_defaults(self) -> dict[str, str]:
        return variable_defaults()

    def compose(self) -> ComposeResult:
        with Vertical(id="logo-area"):
            for i, line in enumerate(self._logo_lines):
                yield Label(Text(line), id=f"logo-{i}")
        with Vertical(id="search-area"):
            yield _searchbar()
            with VerticalScroll(id="suggestion-list"):
                pass
        with Vertical(id="quit-area"):
            yield Label(self._quit_text, id="quit-hint")

    def _gradient_text(self, line: str, offset: int) -> Text:
        text = Text()
        colours = gradient_colours()
        n = len(colours)
        for k, char in enumerate(line):
            colour = colours[(k + offset) % n]
            text.append(char, style=colour)
        return text

    async def on_mount(self) -> None:
        for name, theme in all_themes().items():
            self.register_theme(theme)
        self.theme = load_theme()
        self.run_worker(self._animate_logo_colours())
        self.query_one("#suggestion-list").display = False

    async def _animate_logo_colours(self) -> None:
        offset = 0
        quit_label = self.query_one("#quit-hint", Label)
        logo_labels = tuple(
            self.query_one(f"#logo-{i}", Label) for i in range(len(self._logo_lines))
        )
        colours = gradient_colours()
        n = len(colours)
        while True:
            for i, line in enumerate(self._logo_lines):
                logo_labels[i].update(self._gradient_text(line, offset))
            quit_label.update(self._gradient_text(self._quit_text, offset))
            offset = (offset + 1) % n
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
        elif raw == "/obfuscate":
            from ui.screens.obfuscate_screen import _obfuscatescreen

            self.push_screen(_obfuscatescreen())
        elif raw == "/api":
            from ui.screens.api_screen import _apiscreen

            self.push_screen(_apiscreen())
        elif raw == "/codec":
            from ui.screens.codec_screen import _codecscreen

            self.push_screen(_codecscreen())
        elif raw == "/qr":
            from ui.screens.qr_screen import _qrscreen

            self.push_screen(_qrscreen())
        elif raw == "/theme":
            from ui.screens.theme_screen import _themescreen

            self.push_screen(_themescreen())
        else:
            from ui.components.error_modal import _commanderrormodal

            self.push_screen(_commanderrormodal(raw))
        self._clear_search()

    def _clear_search(self) -> None:
        search = self.query_one(_searchbar)
        search.value = ""
        suggestions = self.query_one("#suggestion-list", VerticalScroll)
        suggestions.remove_children()
        suggestions.display = False

    def on_input_changed(self, event: _searchbar.Changed) -> None:
        value = event.value
        suggestions = self.query_one("#suggestion-list", VerticalScroll)
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
