from __future__ import annotations

import mmap
from pathlib import Path

from msgspec import Struct

from core.serializer import jdecode, jencode

_store = Path.home() / ".config" / "zne" / "api_store.json"


class apientry(Struct, frozen=True):
    name: str
    method: str
    url: str
    headers: dict[str, str]
    body: str
    auth_type: str
    auth_value: str


def _ensure_store() -> None:
    _store.parent.mkdir(parents=True, exist_ok=True)
    if not _store.exists():
        _store.write_bytes(b"[]")


def load_entries() -> list[apientry]:
    _ensure_store()
    with _store.open("rb") as fh:
        with mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as m:
            return jdecode(m, type=list[apientry])


def save_entry(entry: apientry) -> None:
    entries = load_entries()
    for i, e in enumerate(entries):
        if e.name == entry.name:
            entries[i] = entry
            _write_entries(entries)
            return
    entries.append(entry)
    _write_entries(entries)


def delete_entry(name: str) -> bool:
    entries = load_entries()
    before = len(entries)
    entries = [e for e in entries if e.name != name]
    if len(entries) == before:
        return False
    _write_entries(entries)
    return True


def _write_entries(entries: list[apientry]) -> None:
    _ensure_store()
    _store.write_bytes(jencode(entries))


def parse_response(raw: bytes) -> dict:
    try:
        return jdecode(raw)
    except Exception:
        return {"raw": raw.decode("utf-8", errors="replace")}
