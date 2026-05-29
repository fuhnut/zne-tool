from __future__ import annotations

_client = None
_methods = (
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "HEAD",
    "OPTIONS",
)


def _get_client():
    global _client
    if _client is None:
        from httpx import (
            AsyncClient,
            Limits,
            Timeout,
        )

        _client = AsyncClient(
            http2=True,
            timeout=Timeout(
                connect=5.0,
                read=30.0,
                write=10.0,
                pool=5.0,
            ),
            limits=Limits(
                max_connections=100,
                max_keepalive_connections=20,
            ),
            follow_redirects=True,
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def execute(entry) -> dict:
    from core.api_client import parse_response

    if entry.method not in _methods:
        return {
            "status": 0,
            "headers": {},
            "body": f"unsupported method: {entry.method}",
        }

    headers = dict(entry.headers)

    if entry.auth_type == "bearer" and entry.auth_value:
        headers["Authorization"] = f"Bearer {entry.auth_value}"
    elif entry.auth_type == "basic" and entry.auth_value:
        import base64

        encoded = base64.b64encode(entry.auth_value.encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"
    elif entry.auth_type == "custom" and entry.auth_value:
        headers["Authorization"] = entry.auth_value

    data = (
        entry.body if entry.body and entry.method in ("POST", "PUT", "PATCH") else None
    )

    client = _get_client()

    try:
        resp = await client.request(
            method=entry.method,
            url=entry.url,
            headers=headers,
            content=data,
        )
        status = resp.status_code
        resp_headers = dict(resp.headers)
        raw = resp.content
    except Exception as e:
        return {"status": 0, "headers": {}, "body": str(e)}

    content_type = resp_headers.get("content-type", "")
    if "json" in content_type:
        body = parse_response(raw)
    else:
        body = raw.decode("utf-8", errors="replace")

    return {"status": status, "headers": resp_headers, "body": body}
