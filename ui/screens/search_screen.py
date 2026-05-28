from __future__ import annotations

import asyncio
from pathlib import Path

from rich.style import Style
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Label

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

_TITLE_LINES = (
    "███████╗███╗░░██╗███████╗",
    "╚════██║████╗░██║██╔════╝",
    "░░███╔═╝██╔██╗██║█████╗░░",
    "██╔══╝░░██║╚████║██╔══╝░░",
    "███████╗██║░╚███║███████╗",
    "╚══════╝╚═╝░░╚══╝╚══════╝",
)


class _searchscreen(Screen):
    CSS_PATH = str(Path(__file__).parent.parent.parent / "styles" / "search.css")
    BINDINGS = (("escape", "back", "back"),)

    def action_back(self) -> None:
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        with Vertical(id="search-header"):
            for i, line in enumerate(_TITLE_LINES):
                yield Label(Text(line), id=f"search-logo-{i}")
            yield Label("WEB SEARCH", id="search-subtitle")
        with Vertical(id="search-input-area"):
            yield Input(
                placeholder="Type a query and press enter...",
                id="search-input",
            )
        with VerticalScroll(id="search-scroll"):
            yield Label("", id="search-data")
        with Vertical(id="search-footer"):
            yield Label("press esc to go back", id="search-back-hint")

    def _gradient_text(self, line: str, offset: int) -> Text:
        text = Text()
        for k, char in enumerate(line):
            colour = _COLOURS[(k + offset) % 26]
            text.append(char, style=colour)
        return text

    async def on_mount(self) -> None:
        self._logo_labels = tuple(
            self.query_one(f"#search-logo-{i}", Label) for i in range(len(_TITLE_LINES))
        )
        self._data_label = self.query_one("#search-data", Label)
        self._back_hint = self.query_one("#search-back-hint", Label)
        self._search_input = self.query_one("#search-input", Input)
        self.run_worker(self._animate_header())

    async def _animate_header(self) -> None:
        offset = 0
        while True:
            for i, line in enumerate(_TITLE_LINES):
                self._logo_labels[i].update(self._gradient_text(line, offset))
            self._back_hint.update(
                self._gradient_text("press esc to go back", offset=offset)
            )
            offset = (offset + 1) % 26
            await asyncio.sleep(0.08)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "search-input":
            return
        query = event.value.strip()
        if not query:
            return
        self._search_input.disabled = True
        self._data_label.update(Text(" Searching...", style="#7755aa"))
        try:
            from core.search import search_text

            results = await search_text(query)
        except Exception as e:
            self._data_label.update(Text(f" Error: {e}", style="#ff4444"))
            self._search_input.disabled = False
            return
        self._search_input.disabled = False
        content = Text()
        content.append(" Results for: ", style="#7755aa")
        content.append(f"{query}\n", style="#ccccee bold")
        content.append("─" * 60, style="#332244")
        content.append("\n")
        if not results:
            content.append(" No results found.", style="#554477")
            self._data_label.update(content)
            return
        for i, r in enumerate(results, 1):
            content.append(f" {i}. ", style="#7755cc")
            content.append(
                f"{r.title}\n",
                style=Style(link=r.href, color="#e0d0ff", bold=True),
            )
            content.append(
                f"    {r.href}\n",
                style=Style(link=r.href, color="#5599ff"),
            )
            content.append(f"    {r.body}\n", style="#9988bb")
            content.append("\n")
        self._data_label.update(content)
