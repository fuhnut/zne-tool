from __future__ import annotations

import asyncio
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Static

from core.qrgen import generate
from core.theme import gradient_colours

_TITLE_LINES = (
    "███████╗███╗░░██╗███████╗",
    "╚════██║████╗░██║██╔════╝",
    "░░███╔═╝██╔██╗██║█████╗░░",
    "██╔══╝░░██║╚████║██╔══╝░░",
    "███████╗██║░╚███║███████╗",
    "╚══════╝╚═╝░░╚══╝╚══════╝",
)


class _qrscreen(Screen):
    CSS_PATH = str(Path(__file__).parent.parent.parent / "styles" / "qr.css")
    BINDINGS = (("escape", "back", "back"),)

    def action_back(self) -> None:
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        with Vertical(id="qr-header"):
            for i, line in enumerate(_TITLE_LINES):
                yield Label(Text(line), id=f"qr-logo-{i}")
            yield Label("QR GENERATOR", id="qr-subtitle")
        with Vertical(id="qr-input-area"):
            yield Input(
                placeholder="enter text or URL for QR code",
                id="qr-input",
            )
            with Vertical(id="qr-btn-row"):
                yield Button("GENERATE", id="qr-generate", variant="primary")
                yield Button("CLEAR", id="qr-clear")
        with VerticalScroll(id="qr-scroll"):
            yield Static("", id="qr-output")
        with Vertical(id="qr-footer"):
            yield Label("press esc to go back", id="qr-back-hint")

    def _gradient_text(self, line: str, offset: int) -> Text:
        text = Text()
        colours = gradient_colours()
        n = len(colours)
        for k, char in enumerate(line):
            colour = colours[(k + offset) % n]
            text.append(char, style=colour)
        return text

    async def on_mount(self) -> None:
        self._logo_labels = tuple(
            self.query_one(f"#qr-logo-{i}", Label) for i in range(len(_TITLE_LINES))
        )
        self._back_hint = self.query_one("#qr-back-hint", Label)
        self._output = self.query_one("#qr-output", Static)
        self._input = self.query_one("#qr-input", Input)
        self.run_worker(self._animate_header())

    async def _animate_header(self) -> None:
        offset = 0
        colours = gradient_colours()
        n = len(colours)
        while True:
            for i, line in enumerate(_TITLE_LINES):
                self._logo_labels[i].update(self._gradient_text(line, offset))
            self._back_hint.update(
                self._gradient_text("press esc to go back", offset=offset)
            )
            offset = (offset + 1) % n
            await asyncio.sleep(0.08)

    async def _do_generate(self) -> None:
        data = self._input.value.strip()
        if not data:
            self._output.update(Text(" input required", style="#ff4444"))
            return
        try:
            rows = generate(data)
            text = Text()
            text.append("\n")
            for row in rows:
                text.append(f" {row}\n", style="#e0d0ff")
            text.append(f"\n {data}", style="#554477")
            self._output.update(text)
        except Exception as e:
            self._output.update(Text(f" error: {e}", style="#ff4444"))

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "qr-generate":
            await self._do_generate()
        elif event.button.id == "qr-clear":
            self._input.value = ""
            self._output.update(Text(""))

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "qr-input":
            await self._do_generate()
