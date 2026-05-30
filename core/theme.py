from __future__ import annotations

from pathlib import Path

import msgspec
from textual.theme import Theme

from core.serializer import jdecode, jencode


class themecfg(msgspec.Struct, frozen=True):
    name: str
    bg: str
    fg: str
    accent: str
    accent2: str
    border: str
    border_focus: str
    input_bg: str
    input_bg_focus: str
    hover: str
    btn_green: str
    btn_red: str
    btn_text: str
    muted: str
    muted_2: str
    output_text: str


def _gradient_from(accent: str, accent2: str) -> tuple[str, ...]:
    try:
        r1 = int(accent[1:3], 16)
        g1 = int(accent[3:5], 16)
        b1 = int(accent[5:7], 16)
        r2 = int(accent2[1:3], 16)
        g2 = int(accent2[3:5], 16)
        b2 = int(accent2[5:7], 16)
    except (ValueError, IndexError):
        return (
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
    steps = 13
    colours = []
    for i in range(steps):
        t = i / max(steps - 1, 1)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        colours.append(f"#{r:02x}{g:02x}{b:02x}")
    return tuple(colours + list(reversed(colours[:-1])))


_configs: dict[str, themecfg] = {
    "midnight": themecfg(
        name="midnight",
        bg="#0e0e1a",
        fg="#ccccee",
        accent="#7755cc",
        accent2="#bb88ff",
        border="#332244",
        border_focus="#7755cc",
        input_bg="#1a1a2e",
        input_bg_focus="#1e1e36",
        hover="#2a2a4e",
        btn_green="#44ff88",
        btn_red="#ff4444",
        btn_text="#ffffff",
        muted="#554477",
        muted_2="#9988bb",
        output_text="#ccccee",
    ),
    "matrix": themecfg(
        name="matrix",
        bg="#000000",
        fg="#00ff41",
        accent="#00ff41",
        accent2="#00cc33",
        border="#003300",
        border_focus="#00ff41",
        input_bg="#001a00",
        input_bg_focus="#003300",
        hover="#002200",
        btn_green="#00ff41",
        btn_red="#ff3333",
        btn_text="#000000",
        muted="#006600",
        muted_2="#009900",
        output_text="#00ff41",
    ),
    "crimson": themecfg(
        name="crimson",
        bg="#1a0000",
        fg="#ffffff",
        accent="#ff2244",
        accent2="#ff6677",
        border="#440000",
        border_focus="#ff2244",
        input_bg="#2a0000",
        input_bg_focus="#3a0000",
        hover="#440000",
        btn_green="#44ff88",
        btn_red="#ff2244",
        btn_text="#ffffff",
        muted="#883333",
        muted_2="#cc6666",
        output_text="#ffcccc",
    ),
    "dracula": themecfg(
        name="dracula",
        bg="#282a36",
        fg="#f8f8f2",
        accent="#bd93f9",
        accent2="#ff79c6",
        border="#6272a4",
        border_focus="#bd93f9",
        input_bg="#21222c",
        input_bg_focus="#2a2b38",
        hover="#343746",
        btn_green="#50fa7b",
        btn_red="#ff5555",
        btn_text="#f8f8f2",
        muted="#6272a4",
        muted_2="#9099ac",
        output_text="#f8f8f2",
    ),
    "nord": themecfg(
        name="nord",
        bg="#2e3440",
        fg="#d8dee9",
        accent="#88c0d0",
        accent2="#b48ead",
        border="#4c566a",
        border_focus="#88c0d0",
        input_bg="#3b4252",
        input_bg_focus="#434c5e",
        hover="#434c5e",
        btn_green="#a3be8c",
        btn_red="#bf616a",
        btn_text="#eceff4",
        muted="#4c566a",
        muted_2="#7b88a1",
        output_text="#d8dee9",
    ),
    "tokyo": themecfg(
        name="tokyo",
        bg="#1a1b26",
        fg="#a9b1d6",
        accent="#7aa2f7",
        accent2="#bb9af7",
        border="#292e42",
        border_focus="#7aa2f7",
        input_bg="#1f2335",
        input_bg_focus="#24283b",
        hover="#292e42",
        btn_green="#9ece6a",
        btn_red="#f7768e",
        btn_text="#c0caf5",
        muted="#3b4261",
        muted_2="#565f89",
        output_text="#a9b1d6",
    ),
    "gruvbox": themecfg(
        name="gruvbox",
        bg="#282828",
        fg="#ebdbb2",
        accent="#fe8019",
        accent2="#d65d0e",
        border="#504945",
        border_focus="#fe8019",
        input_bg="#1d2021",
        input_bg_focus="#282828",
        hover="#3c3836",
        btn_green="#b8bb26",
        btn_red="#fb4934",
        btn_text="#ebdbb2",
        muted="#665c54",
        muted_2="#928374",
        output_text="#ebdbb2",
    ),
    "ocean": themecfg(
        name="ocean",
        bg="#0b1929",
        fg="#b2dfdb",
        accent="#00bcd4",
        accent2="#26c6da",
        border="#1a3a4a",
        border_focus="#00bcd4",
        input_bg="#0d2137",
        input_bg_focus="#112d4a",
        hover="#153a50",
        btn_green="#4caf50",
        btn_red="#ef5350",
        btn_text="#e0f7fa",
        muted="#2a5a6a",
        muted_2="#4a8a9a",
        output_text="#b2dfdb",
    ),
    "solarized": themecfg(
        name="solarized",
        bg="#002b36",
        fg="#839496",
        accent="#b58900",
        accent2="#cb4b16",
        border="#073642",
        border_focus="#b58900",
        input_bg="#073642",
        input_bg_focus="#0a4050",
        hover="#0a4050",
        btn_green="#859900",
        btn_red="#dc322f",
        btn_text="#eee8d5",
        muted="#586e75",
        muted_2="#657b83",
        output_text="#93a1a1",
    ),
    "rose": themecfg(
        name="rose",
        bg="#1a0a14",
        fg="#f5c6d0",
        accent="#e84393",
        accent2="#fd79a8",
        border="#3a1a2a",
        border_focus="#e84393",
        input_bg="#2a0a1a",
        input_bg_focus="#3a1a2a",
        hover="#4a1a3a",
        btn_green="#55efc4",
        btn_red="#ff6b81",
        btn_text="#ffffff",
        muted="#6a3a5a",
        muted_2="#9a5a8a",
        output_text="#f5c6d0",
    ),
}

_config_dir = Path.home() / ".config" / "zne"
_config_path = _config_dir / "theme.json"
_custom_path = _config_dir / "custom.json"

_default_name = "midnight"


def gradient_colours(name: str | None = None) -> tuple[str, ...]:
    cfg = get_config(name)
    return _gradient_from(cfg.accent, cfg.accent2)


def load_theme() -> str:
    try:
        raw = _config_path.read_text("utf-8")
        data = jdecode(raw)
        name = (
            data.get("theme", _default_name)
            if isinstance(data, dict)
            else _default_name
        )
        if name in _configs or name == "custom":
            return name
        return _default_name
    except (
        FileNotFoundError,
        PermissionError,
        Exception,
    ):
        return _default_name


def save_theme(name: str) -> None:
    _config_dir.mkdir(parents=True, exist_ok=True)
    data = {"theme": name}
    raw = jencode(data).decode("utf-8")
    _config_path.write_text(raw, "utf-8")


def load_custom() -> themecfg | None:
    try:
        raw = _custom_path.read_text("utf-8")
        data = jdecode(raw)
        if not isinstance(data, dict):
            return None
        return themecfg(**data)
    except (
        FileNotFoundError,
        PermissionError,
        Exception,
    ):
        return None


def save_custom(cfg: themecfg) -> None:
    _config_dir.mkdir(parents=True, exist_ok=True)
    raw = jencode(msgspec.structs.asdict(cfg)).decode("utf-8")
    _custom_path.write_text(raw, "utf-8")


def get_config(name: str | None = None) -> themecfg:
    key = name or load_theme()
    if key == "custom":
        saved = load_custom()
        if saved is not None:
            return saved
    return _configs.get(key, _configs[_default_name])


def to_theme(cfg: themecfg) -> Theme:
    return Theme(
        name=cfg.name,
        primary=cfg.accent,
        secondary=cfg.accent2,
        accent=cfg.accent2,
        foreground=cfg.fg,
        background=cfg.bg,
        surface=cfg.input_bg,
        panel=cfg.hover,
        dark=True,
        variables={
            "bg": cfg.bg,
            "fg": cfg.fg,
            "accent": cfg.accent,
            "accent2": cfg.accent2,
            "border": cfg.border,
            "border-focus": cfg.border_focus,
            "input-bg": cfg.input_bg,
            "input-bg-focus": cfg.input_bg_focus,
            "hover": cfg.hover,
            "btn-green": cfg.btn_green,
            "btn-red": cfg.btn_red,
            "btn-text": cfg.btn_text,
            "muted": cfg.muted,
            "muted-2": cfg.muted_2,
            "output-text": cfg.output_text,
        },
    )


def all_themes() -> dict[str, Theme]:
    result = {name: to_theme(cfg) for name, cfg in _configs.items()}
    custom = load_custom()
    if custom is not None:
        result["custom"] = to_theme(custom)
    return result


def variable_defaults() -> dict[str, str]:
    cfg = get_config()
    return {
        "bg": cfg.bg,
        "fg": cfg.fg,
        "accent": cfg.accent,
        "accent2": cfg.accent2,
        "border": cfg.border,
        "border-focus": cfg.border_focus,
        "input-bg": cfg.input_bg,
        "input-bg-focus": cfg.input_bg_focus,
        "hover": cfg.hover,
        "btn-green": cfg.btn_green,
        "btn-red": cfg.btn_red,
        "btn-text": cfg.btn_text,
        "muted": cfg.muted,
        "muted-2": cfg.muted_2,
        "output-text": cfg.output_text,
    }
