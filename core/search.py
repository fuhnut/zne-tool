from __future__ import annotations

from asyncio import to_thread

from msgspec import Struct


class textresult(Struct, frozen=True):
    title: str
    href: str
    body: str


def _ddgs_text(query: str, max_results: int) -> list[dict[str, str]]:
    from ddgs import DDGS

    with DDGS() as ddgs:
        return ddgs.text(query, max_results=max_results)


async def search_text(query: str, max_results: int = 10) -> tuple[textresult, ...]:
    raw = await to_thread(_ddgs_text, query, max_results)
    return tuple(
        textresult(
            title=r.get("title", ""), href=r.get("href", ""), body=r.get("body", "")
        )
        for r in raw
    )
