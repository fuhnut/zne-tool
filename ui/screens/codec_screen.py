from __future__ import annotations
import asyncio
from pathlib import Path
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, DirectoryTree, Input, Label, Select

from core.codec import (
    base64_decode,
    base64_encode,
    entropy_score,
    generate_password,
    hash_file,
    hash_text,
    hex_decode,
    hex_encode,
    url_decode,
    url_encode,
)
from core.theme import gradient_colours

_TITLE_LINES = (
    "███████╗███╗░░██╗███████╗",
    "╚════██║████╗░██║██╔════╝",
    "░░███╔═╝██╔██╗██║█████╗░░",
    "██╔══╝░░██║╚████║██╔══╝░░",
    "███████╗██║░╚███║███████╗",
    "╚══════╝╚═╝░░╚══╝╚══════╝",
)

_MODE_OPTIONS = [
    ("Base64 Encode", "b64_enc"),
    ("Base64 Decode", "b64_dec"),
    ("Hex Encode", "hex_enc"),
    ("Hex Decode", "hex_dec"),
    ("URL Encode", "url_enc"),
    ("URL Decode", "url_dec"),
]

_HASH_OPTIONS = [
    ("MD5", "md5"),
    ("SHA-1", "sha1"),
    ("SHA-256", "sha256"),
    ("SHA-512", "sha512"),
    ("BLAKE2b", "blake2b"),
    ("BLAKE2s", "blake2s"),
]

_PWD_SYMBOL_OPTIONS = [
    ("Letters + Numbers", "letters"),
    ("All Characters", "symbols"),
]


class _pyfiltertree(DirectoryTree):
    def filter_paths(self, paths) -> list:
        return [
            p
            for p in paths
            if (p.is_dir() and not p.name.startswith("."))
            or str(p).endswith(".py")
            or str(p).endswith(".txt")
            or str(p).endswith(".json")
            or str(p).endswith(".yaml")
            or str(p).endswith(".yml")
            or str(p).endswith(".md")
            or str(p).endswith(".log")
            or str(p).endswith(".sh")
            or str(p).endswith(".bat")
            or str(p).endswith(".ps1")
            or str(p).endswith(".xml")
            or str(p).endswith(".toml")
            or str(p).endswith(".cfg")
            or str(p).endswith(".conf")
            or str(p).endswith(".ini")
            or str(p).endswith(".zip")
            or str(p).endswith(".tar")
            or str(p).endswith(".gz")
            or str(p).endswith(".rar")
            or str(p).endswith(".7z")
            or str(p).endswith(".pdf")
            or str(p).endswith(".doc")
            or str(p).endswith(".docx")
            or str(p).endswith(".xls")
            or str(p).endswith(".xlsx")
            or str(p).endswith(".png")
            or str(p).endswith(".jpg")
            or str(p).endswith(".jpeg")
            or str(p).endswith(".gif")
            or str(p).endswith(".bmp")
            or str(p).endswith(".ico")
            or str(p).endswith(".svg")
            or str(p).endswith(".webp")
            or str(p).endswith(".mp3")
            or str(p).endswith(".wav")
            or str(p).endswith(".ogg")
            or str(p).endswith(".mp4")
            or str(p).endswith(".avi")
            or str(p).endswith(".mkv")
            or str(p).endswith(".mov")
            or str(p).endswith(".flac")
            or str(p).endswith(".aac")
            or str(p).endswith(".iso")
            or str(p).endswith(".dmg")
            or str(p).endswith(".exe")
            or str(p).endswith(".dll")
            or str(p).endswith(".so")
            or str(p).endswith(".dylib")
        ]


class _codecscreen(Screen):
    CSS_PATH = str(Path(__file__).parent.parent.parent / "styles" / "codec.css")
    BINDINGS = (("escape", "back", "back"),)

    def action_back(self) -> None:
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        with Vertical(id="codec-header"):
            for i, line in enumerate(_TITLE_LINES):
                yield Label(Text(line), id=f"codec-logo-{i}")
            yield Label("CODEC TOOLBOX", id="codec-subtitle")
        with VerticalScroll(id="codec-body"):
            with Horizontal(id="codec-opts-row"):
                yield Select(
                    _MODE_OPTIONS,
                    value="b64_enc",
                    id="codec-mode",
                )
            yield Input(
                placeholder="text to encode/decode",
                id="codec-input",
            )
            with Horizontal(id="codec-act-row"):
                yield Button("RUN", id="codec-run", variant="primary")
                yield Button("CLEAR", id="codec-clear")
            yield Label("", id="codec-output")

            with Horizontal(id="codec-divider-row"):
                yield Label("── PASSWORD GENERATOR ──", id="codec-divider-label")
            yield Input(
                placeholder="length (e.g. 24)",
                id="codec-pwlen",
            )
            yield Select(
                _PWD_SYMBOL_OPTIONS,
                value="letters",
                id="codec-pwsym",
            )
            yield Button("GENERATE PASSWORD", id="codec-gen-pw", variant="success")
            yield Label("", id="codec-pw-output")

            with Horizontal(id="codec-hash-divider-row"):
                yield Label("── HASH TEXT ──", id="codec-hash-divider-label")
            yield Input(
                placeholder="text to hash",
                id="codec-hash-input",
            )
            with Horizontal(id="codec-hash-row"):
                yield Select(
                    _HASH_OPTIONS,
                    value="sha256",
                    id="codec-hash-algo",
                )
                yield Button("HASH IT", id="codec-hash-run", variant="primary")
            yield Label("", id="codec-hash-output")

            with Horizontal(id="codec-file-divider-row"):
                yield Label("── HASH FILE ──", id="codec-file-divider-label")
            with Horizontal(id="codec-file-pick-row"):
                yield _pyfiltertree("/home", id="codec-file-tree")
            with Horizontal(id="codec-file-hash-row"):
                yield Select(
                    _HASH_OPTIONS,
                    value="sha256",
                    id="codec-file-hash-algo",
                )
                yield Button("HASH FILE", id="codec-file-hash-run", variant="primary")
            yield Label("", id="codec-file-hash-output")

        with Vertical(id="codec-footer"):
            yield Label("press esc to go back", id="codec-back-hint")

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
            self.query_one(f"#codec-logo-{i}", Label) for i in range(len(_TITLE_LINES))
        )
        self._back_hint = self.query_one("#codec-back-hint", Label)
        self._output = self.query_one("#codec-output", Label)
        self._pw_output = self.query_one("#codec-pw-output", Label)
        self._hash_output = self.query_one("#codec-hash-output", Label)
        self._file_hash_output = self.query_one("#codec-file-hash-output", Label)
        self._file_tree = self.query_one("#codec-file-tree", _pyfiltertree)
        self._file_input = self.query_one("#codec-file-input", Input)
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

    async def _do_codec(self) -> None:
        mode = self.query_one("#codec-mode", Select).value
        inp = self.query_one("#codec-input", Input).value
        if not inp:
            self._output.update(Text(" input required", style="#ff4444"))
            return
        try:
            if mode == "b64_enc":
                result = await asyncio.to_thread(base64_encode, inp)
            elif mode == "b64_dec":
                result = await asyncio.to_thread(base64_decode, inp)
            elif mode == "hex_enc":
                result = await asyncio.to_thread(hex_encode, inp)
            elif mode == "hex_dec":
                result = await asyncio.to_thread(hex_decode, inp)
            elif mode == "url_enc":
                result = await asyncio.to_thread(url_encode, inp)
            elif mode == "url_dec":
                result = await asyncio.to_thread(url_decode, inp)
            else:
                result = inp
            entropy = entropy_score(inp)
            text = Text()
            text.append(f" {result}\n", style="#44ff88")
            text.append(f" entropy: {entropy:.1f} bits", style="#7755aa")
            self._output.update(text)
        except Exception as e:
            self._output.update(Text(f" error: {e}", style="#ff4444"))

    async def _do_password(self) -> None:
        length_str = self.query_one("#codec-pwlen", Input).value.strip()
        sym_mode = self.query_one("#codec-pwsym", Select).value
        try:
            length = int(length_str) if length_str else 24
        except ValueError:
            self._pw_output.update(Text(" invalid length", style="#ff4444"))
            return
        length = max(4, min(length, 256))
        syms = sym_mode == "symbols"
        pwd = await asyncio.to_thread(generate_password, length, syms)
        ent = entropy_score(pwd)
        text = Text()
        text.append(f" {pwd}\n", style="#44ff88 bold")
        text.append(f" entropy: {ent:.1f} bits", style="#7755aa")
        self._pw_output.update(text)

    async def _do_hash(self) -> None:
        inp = self.query_one("#codec-hash-input", Input).value
        algo = self.query_one("#codec-hash-algo", Select).value
        if not inp:
            self._hash_output.update(Text(" input required", style="#ff4444"))
            return
        result = await asyncio.to_thread(hash_text, inp, algo)
        self._hash_output.update(Text(f" {result}", style="#44ff88"))

    def _on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        if event.path:
            self._file_input.value = str(event.path)

    async def _do_file_hash(self) -> None:
        path = self.query_one("#codec-file-input", Input).value.strip()
        algo = self.query_one("#codec-file-hash-algo", Select).value
        if not path:
            self._file_hash_output.update(
                Text(" pick or type a file path", style="#ff4444")
            )
            return
        try:
            digest, size = await asyncio.to_thread(hash_file, path, algo)
            text = Text()
            text.append(f" {digest}\n", style="#44ff88")
            text.append(f" size: {size:,} bytes", style="#7755aa")
            self._file_hash_output.update(text)
        except FileNotFoundError:
            self._file_hash_output.update(
                Text(f" file not found: {path}", style="#ff4444")
            )
        except Exception as e:
            self._file_hash_output.update(Text(f" error: {e}", style="#ff4444"))

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "codec-run":
            await self._do_codec()
        elif btn_id == "codec-clear":
            self.query_one("#codec-input", Input).value = ""
            self._output.update(Text(""))
        elif btn_id == "codec-gen-pw":
            await self._do_password()
        elif btn_id == "codec-hash-run":
            await self._do_hash()
        elif btn_id == "codec-file-hash-run":
            await self._do_file_hash()
