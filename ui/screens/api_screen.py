from __future__ import annotations

import asyncio
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import (
    Horizontal,
    Vertical,
    VerticalScroll,
)
from textual.screen import Screen
from textual.widgets import (
    Button,
    Input,
    Label,
    Select,
    Static,
)

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

_METHODS = [
    ("GET", "GET"),
    ("POST", "POST"),
    ("PUT", "PUT"),
    ("PATCH", "PATCH"),
    ("DELETE", "DELETE"),
]

_AUTH_TYPES = [
    ("None", "none"),
    ("Bearer Token", "bearer"),
    ("Basic Auth", "basic"),
    ("Custom", "custom"),
]


class _apiscreen(Screen):
    CSS_PATH = str(Path(__file__).parent.parent.parent / "styles" / "api.css")
    BINDINGS = (("escape", "back", "back"),)

    def action_back(self) -> None:
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        with Vertical(id="api-header"):
            for i, line in enumerate(_TITLE_LINES):
                yield Label(Text(line), id=f"api-logo-{i}")
            yield Label("API CLIENT", id="api-subtitle")
        with VerticalScroll(id="api-body"):
            with Horizontal(id="api-method-row"):
                yield Select(_METHODS, value="GET", id="api-method")
                yield Input(
                    placeholder="https://api.example.com/endpoint", id="api-url"
                )
            yield Input(placeholder="request name (to save/load)", id="api-name")
            with Horizontal(id="api-auth-row"):
                yield Select(_AUTH_TYPES, value="none", id="api-auth-type")
                yield Input(placeholder="token or user:pass", id="api-auth-value")
            yield Input(
                placeholder="headers  key:value  (one per line, e.g.  Content-Type:application/json)",
                id="api-headers",
            )
            yield Input(
                placeholder="request body (JSON)",
                id="api-body-input",
            )
            with Horizontal(id="api-btn-row"):
                yield Button("SEND", id="api-send", variant="primary")
                yield Button("SAVE", id="api-save", variant="success")
                yield Button("LOAD", id="api-load")
                yield Button("DELETE", id="api-delete", variant="error")
            yield Label("", id="api-data")
        with Vertical(id="api-footer"):
            yield Label("press esc to go back", id="api-back-hint")

    def _gradient_text(self, line: str, offset: int) -> Text:
        text = Text()
        for k, char in enumerate(line):
            colour = _COLOURS[(k + offset) % 26]
            text.append(char, style=colour)
        return text

    async def on_mount(self) -> None:
        self._logo_labels = tuple(
            self.query_one(f"#api-logo-{i}", Label) for i in range(len(_TITLE_LINES))
        )
        self._back_hint = self.query_one("#api-back-hint", Label)
        self._data_label = self.query_one("#api-data", Label)
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

    def _build_entry(self) -> tuple[object, str]:
        from core.api_client import apientry

        method = self.query_one("#api-method", Select).value
        url = self.query_one("#api-url", Input).value.strip()
        name = self.query_one("#api-name", Input).value.strip()
        auth_type = self.query_one("#api-auth-type", Select).value
        auth_value = self.query_one("#api-auth-value", Input).value.strip()
        headers_raw = self.query_one("#api-headers", Input).value.strip()
        body = self.query_one("#api-body-input", Input).value.strip()

        if not url:
            return None, "url is required"

        headers = {}
        if headers_raw:
            for line in headers_raw.split("\n"):
                line = line.strip()
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.strip()] = v.strip()

        entry = apientry(
            name=name or url,
            method=method,
            url=url,
            headers=headers,
            body=body,
            auth_type=auth_type,
            auth_value=auth_value,
        )
        return entry, ""

    def _render_result(self, result: dict) -> Text:
        text = Text()
        status = result.get("status", 0)
        if 200 <= status < 300:
            status_style = "#44ff88"
        elif 300 <= status < 400:
            status_style = "#ffcc22"
        else:
            status_style = "#ff4444"

        text.append(f" Status: ", style="#9988bb")
        text.append(f"{status}", style=f"{status_style} bold")
        text.append("\n")

        resp_headers = result.get("headers", {})
        if resp_headers:
            text.append(" Headers:\n", style="#7755cc")
            for k, v in resp_headers.items():
                text.append(f"   {k}: ", style="#9988bb")
                text.append(f"{v}\n", style="#ccccee")

        text.append("─" * 50, style="#332244")
        text.append("\n")

        body = result.get("body", "")
        if isinstance(body, dict):
            from core.serializer import jencode

            formatted = jencode(body).decode("utf-8")
            text.append(formatted, style="#ccccee")
        else:
            text.append(str(body), style="#ccccee")

        return text

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "api-send":
            await self._do_send()
        elif btn_id == "api-save":
            self._do_save()
        elif btn_id == "api-load":
            self._do_load()
        elif btn_id == "api-delete":
            self._do_delete()

    async def _do_send(self) -> None:
        entry, err = self._build_entry()
        if err:
            self._data_label.update(Text(f" {err}", style="#ff4444"))
            return

        self._data_label.update(Text(" Sending...", style="#7755aa"))

        from core.api_runner import execute

        result = await execute(entry)
        self._data_label.update(self._render_result(result))

    def _do_save(self) -> None:
        entry, err = self._build_entry()
        if err:
            self._data_label.update(Text(f" {err}", style="#ff4444"))
            return

        from core.api_client import save_entry

        save_entry(entry)
        self._data_label.update(Text(f" Saved as '{entry.name}'", style="#44ff88"))

    def _do_load(self) -> None:
        name = self.query_one("#api-name", Input).value.strip()
        if not name:
            self._data_label.update(Text(" Enter a name to load", style="#ff4444"))
            return

        from core.api_client import load_entries

        entries = load_entries()
        match = None
        for e in entries:
            if e.name == name:
                match = e
                break

        if not match:
            self._data_label.update(Text(f" '{name}' not found", style="#ff4444"))
            return

        self.query_one("#api-method", Select).value = match.method
        self.query_one("#api-url", Input).value = match.url
        self.query_one("#api-auth-type", Select).value = match.auth_type
        self.query_one("#api-auth-value", Input).value = match.auth_value
        self.query_one("#api-body-input", Input).value = match.body

        headers_str = "\n".join(f"{k}:{v}" for k, v in match.headers.items())
        self.query_one("#api-headers", Input).value = headers_str

        self._data_label.update(Text(f" Loaded '{match.name}'", style="#44ff88"))

    def _do_delete(self) -> None:
        name = self.query_one("#api-name", Input).value.strip()
        if not name:
            self._data_label.update(Text(" Enter a name to delete", style="#ff4444"))
            return

        from core.api_client import delete_entry

        if delete_entry(name):
            self._data_label.update(Text(f" Deleted '{name}'", style="#ffcc22"))
        else:
            self._data_label.update(Text(f" '{name}' not found", style="#ff4444"))
