from __future__ import annotations

import asyncio
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Input,
    Label,
    Select,
    Static,
)

from core.theme import (
    _configs,
    get_config,
    gradient_colours,
    load_theme,
    save_custom,
    save_theme,
    themecfg,
)

_TITLE_LINES = (
    "███████╗███╗░░██╗███████╗",
    "╚════██║████╗░██║██╔════╝",
    "░░███╔═╝██╔██╗██║█████╗░░",
    "██╔══╝░░██║╚████║██╔══╝░░",
    "███████╗██║░╚███║███████╗",
    "╚══════╝╚═╝░░╚══╝╚══════╝",
)

_THEME_OPTIONS = [(name.title(), name) for name in _configs.keys()]
_CUSTOM_OPTION = [("Custom", "custom")]


class _themescreen(Screen):
    CSS_PATH = str(Path(__file__).parent.parent.parent / "styles" / "theme.css")
    BINDINGS = (("escape", "back", "back"),)

    def action_back(self) -> None:
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        with Vertical(id="theme-header"):
            for i, line in enumerate(_TITLE_LINES):
                yield Label(Text(line), id=f"theme-logo-{i}")
            yield Label("THEME", id="theme-subtitle")
        with VerticalScroll(id="theme-body"):
            with Horizontal(id="theme-select-row"):
                yield Select(
                    _THEME_OPTIONS + _CUSTOM_OPTION,
                    value=load_theme(),
                    id="theme-select",
                )
            with Horizontal(id="theme-preview-row"):
                yield Static("Preview Text", id="theme-preview-box")
            with Horizontal(id="theme-custom-bg-row"):
                yield Input(placeholder="background hex (e.g. #0e0e1a)", id="inp-bg")
            with Horizontal(id="theme-custom-fg-row"):
                yield Input(placeholder="foreground hex (e.g. #ccccee)", id="inp-fg")
            with Horizontal(id="theme-custom-accent-row"):
                yield Input(placeholder="accent hex (e.g. #7755cc)", id="inp-accent")
            with Horizontal(id="theme-btn-row"):
                yield Button("APPLY CUSTOM", id="theme-custom-apply", variant="success")
                yield Button("RESET", id="theme-reset")
            yield Label("", id="theme-status")
        with Vertical(id="theme-footer"):
            yield Label("press esc to go back", id="theme-back-hint")

    def _gradient_text(self, line: str, offset: int) -> Text:
        text = Text()
        colours = gradient_colours()
        n = len(colours)
        for k, char in enumerate(line):
            colour = colours[(k + offset) % n]
            text.append(char, style=colour)
        return text

    def _current_cfg(self):
        theme_name = self.query_one("#theme-select", Select).value
        if isinstance(theme_name, str):
            return get_config(theme_name)
        return _configs["midnight"]

    def _update_preview(self) -> None:
        cfg = self._current_cfg()
        box = self.query_one("#theme-preview-box", Static)
        box.styles.background = cfg.bg
        box.styles.color = cfg.fg
        box.update("Preview Text")

    async def on_mount(self) -> None:
        self._logo_labels = tuple(
            self.query_one(f"#theme-logo-{i}", Label) for i in range(len(_TITLE_LINES))
        )
        self._back_hint = self.query_one("#theme-back-hint", Label)
        self._update_preview()
        self._sync_inputs()
        self.run_worker(self._animate_header())

    async def _animate_header(self) -> None:
        colours = gradient_colours()
        n = len(colours)
        offset = 0
        while True:
            for i, line in enumerate(_TITLE_LINES):
                self._logo_labels[i].update(self._gradient_text(line, offset))
            self._back_hint.update(
                self._gradient_text("press esc to go back", offset=offset)
            )
            offset = (offset + 1) % n
            await asyncio.sleep(0.08)

    def _sync_inputs(self) -> None:
        cfg = self._current_cfg()
        self.query_one("#inp-bg", Input).value = cfg.bg
        self.query_one("#inp-fg", Input).value = cfg.fg
        self.query_one("#inp-accent", Input).value = cfg.accent

    def _set_status(self, msg: str, colour: str) -> None:
        self.query_one("#theme-status", Label).update(Text(f" {msg}", style=colour))

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "theme-select":
            name = event.select.value
            if isinstance(name, str) and (name in _configs or name == "custom"):
                save_theme(name)
                self.app.theme = name
                self._update_preview()
                self._sync_inputs()
                self._set_status("theme applied", "#44ff88")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "theme-reset":
            name = load_theme()
            if name in _configs:
                self.app.theme = name
                self._update_preview()
                self._sync_inputs()
                self._set_status("reset to theme defaults", "#44ff88")
        elif event.button.id == "theme-custom-apply":
            bg = self.query_one("#inp-bg", Input).value.strip()
            fg = self.query_one("#inp-fg", Input).value.strip()
            accent = self.query_one("#inp-accent", Input).value.strip()
            if not bg and not fg and not accent:
                self._set_status("enter at least one colour value", "#ff4444")
                return
            current = get_config(load_theme())
            cfg = themecfg(
                name="custom",
                bg=bg or current.bg,
                fg=fg or current.fg,
                accent=accent or current.accent,
                accent2=current.accent2,
                border=current.border,
                border_focus=current.border_focus,
                input_bg=current.input_bg,
                input_bg_focus=current.input_bg_focus,
                hover=current.hover,
                btn_green=current.btn_green,
                btn_red=current.btn_red,
                btn_text=current.btn_text,
                muted=current.muted,
                muted_2=current.muted_2,
                output_text=current.output_text,
            )
            save_custom(cfg)
            save_theme("custom")
            from core.theme import to_theme

            theme = to_theme(cfg)
            self.app.register_theme(theme)
            self.app.theme = "custom"
            box = self.query_one("#theme-preview-box", Static)
            box.styles.background = cfg.bg
            box.styles.color = cfg.fg
            box.update("Preview Text")
            self._set_status("custom theme saved", "#44ff88")
