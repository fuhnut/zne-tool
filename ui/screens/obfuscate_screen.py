from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    DirectoryTree,
    Input,
    Label,
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


def _default_root() -> str:
    if sys.platform == "win32":
        return "C:\\"
    if sys.platform == "darwin":
        return str(Path.home())
    return str(Path.home())


def _find_py_files(root: Path, query: str, limit: int = 50) -> list[Path]:
    query_lower = query.lower()
    results = []
    queue = [root]
    while queue:
        try:
            current = queue.pop(0)
        except IndexError:
            break
        try:
            for entry in current.iterdir():
                if entry.is_dir():
                    if entry.name.startswith("."):
                        continue
                    queue.append(entry)
                elif entry.is_file() and entry.name.endswith(".py"):
                    if entry.name.lower().find(query_lower) >= 0:
                        results.append(entry)
                        if len(results) >= limit:
                            return results
        except (PermissionError, OSError):
            continue
    return results


class _pyfiltertree(DirectoryTree):
    def filter_paths(self, paths) -> list:
        return [
            p
            for p in paths
            if (p.is_dir() and not p.name.endswith(".")) or str(p).endswith(".py")
        ]


class _obfuscatescreen(Screen):
    CSS_PATH = str(Path(__file__).parent.parent.parent / "styles" / "obfuscate.css")
    BINDINGS = (("escape", "back", "back"),)

    def action_back(self) -> None:
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        with Vertical(id="obf-header"):
            for i, line in enumerate(_TITLE_LINES):
                yield Label(Text(line), id=f"obf-logo-{i}")
            yield Label("PYTHON OBFUSCATOR", id="obf-subtitle")
        with Horizontal(id="obf-body"):
            with Vertical(id="obf-tree-area"):
                yield _pyfiltertree(_default_root(), id="obf-tree")
            with VerticalScroll(id="obf-controls"):
                yield Input(
                    placeholder="search .py files by name...",
                    id="obf-search",
                )
                yield Input(
                    placeholder="source file (click a .py file)",
                    id="obf-source",
                )
                yield Input(
                    placeholder="output path (optional)",
                    id="obf-output",
                )
                yield Button("BUILD", id="obf-build", variant="primary")
                yield Label("", id="obf-data")
        with Vertical(id="obf-footer"):
            yield Label("press esc to go back", id="obf-back-hint")

    def _gradient_text(self, line: str, offset: int) -> Text:
        text = Text()
        for k, char in enumerate(line):
            colour = _COLOURS[(k + offset) % 26]
            text.append(char, style=colour)
        return text

    async def on_mount(self) -> None:
        self._logo_labels = tuple(
            self.query_one(f"#obf-logo-{i}", Label) for i in range(len(_TITLE_LINES))
        )
        self._back_hint = self.query_one("#obf-back-hint", Label)
        self._build_btn = self.query_one("#obf-build", Button)
        self._data_label = self.query_one("#obf-data", Label)
        self._source_input = self.query_one("#obf-source", Input)
        self._output_input = self.query_one("#obf-output", Input)
        self._search_input = self.query_one("#obf-search", Input)
        self._tree = self.query_one(_pyfiltertree)
        self._search_worker = None
        self.run_worker(self._animate_header())

    async def _animate_header(self) -> None:
        offset = 0
        while True:
            for i, line in enumerate(_TITLE_LINES):
                self._logo_labels[i].update(
                    self._gradient_text(line, offset),
                )
            self._back_hint.update(
                self._gradient_text("press esc to go back", offset=offset),
            )
            offset = (offset + 1) % 26
            await asyncio.sleep(0.08)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "obf-search":
            return
        query = event.value.strip()
        if not query:
            return
        root = Path(str(self._tree.path))
        self._data_label.update(
            Text(f" searching {root}...", style="#7755aa"),
        )
        results = await asyncio.to_thread(_find_py_files, root, query)
        if not results:
            self._data_label.update(
                Text("no .py files found", style="#ff4444"),
            )
            return
        content = Text()
        content.append(f" {len(results)} results\n", style="#7755aa")
        content.append("─" * 40, style="#332244")
        content.append("\n")
        for p in results:
            content.append(f" {p.name}", style="#e0d0ff bold")
            content.append(f"  {p.parent}\n", style="#554477")
        self._data_label.update(content)

    def on_directory_tree_file_selected(
        self,
        event: DirectoryTree.FileSelected,
    ) -> None:
        path = event.path
        if not str(path).endswith(".py"):
            return
        self._source_input.value = str(path)
        self._output_input.value = str(
            path.parent / f"{path.stem}_packed.py",
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "obf-build":
            return

        source_path = self._source_input.value.strip()
        output_path = self._output_input.value.strip()

        if not source_path:
            self._data_label.update(
                Text(
                    "select a .py file from the tree",
                    style="#ff4444",
                ),
            )
            return

        src = Path(source_path)
        out = Path(output_path) if output_path else None

        self._build_btn.disabled = True
        self._data_label.update(Text(" building...", style="#7755aa"))

        try:
            from core.packer import run as pack_run

            pack_run(src, out)
        except FileNotFoundError:
            self._data_label.update(
                Text(f"file not found: {source_path}", style="#ff4444"),
            )
            self._build_btn.disabled = False
            return
        except Exception as e:
            self._data_label.update(
                Text(f"error: {e}", style="#ff4444"),
            )
            self._build_btn.disabled = False
            return

        out_name = out or src.parent / f"{src.stem}_packed.py"
        content = Text()
        content.append(" built -> ", style="#7755aa")
        content.append(str(out_name), style="#00ff88 bold")
        content.append("\n\n run: ", style="#9988bb")
        content.append(f"python {out_name}", style="#e0d0ff bold")
        self._data_label.update(content)
        self._build_btn.disabled = False
