from __future__ import annotations

_commands: dict[str, str] = {
    "/info": "monitor system resources in real-time",
    "/search": "search the web from your terminal!",
}


def get_matches(prefix: str) -> list[tuple[str, str]]:
    if not prefix.startswith("/"):
        return []
    lower = prefix.lower()
    return [(cmd, desc) for cmd, desc in _commands.items() if cmd.startswith(lower)]
