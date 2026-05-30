from __future__ import annotations

import base64
import hashlib
import mmap
import secrets
import string

from msgspec import Struct


class hashrequest(Struct, frozen=True):
    text: str
    algo: str


class filehashrequest(Struct, frozen=True):
    path: str
    algo: str
    chunk_size: int = 1048576


def base64_encode(raw: str) -> str:
    return base64.b64encode(raw.encode("utf-8")).decode("ascii")


def base64_decode(raw: str) -> str:
    return base64.b64decode(raw.strip().encode("ascii")).decode("utf-8")


def hex_encode(raw: str) -> str:
    return raw.encode("utf-8").hex()


def hex_decode(raw: str) -> str:
    return bytes.fromhex(raw.strip()).decode("utf-8")


def url_encode(raw: str) -> str:
    from urllib.parse import quote

    return quote(raw, safe="")


def url_decode(raw: str) -> str:
    from urllib.parse import unquote

    return unquote(raw)


def entropy_score(raw: str) -> float:
    import math

    if not raw:
        return 0.0
    pool = 0
    if any(c.islower() for c in raw):
        pool += 26
    if any(c.isupper() for c in raw):
        pool += 26
    if any(c.isdigit() for c in raw):
        pool += 10
    if any(c in string.punctuation for c in raw):
        pool += 32
    if pool == 0:
        return 0.0
    return len(raw) * math.log2(pool)


def generate_password(length: int, symbols: bool) -> str:
    chars = string.ascii_lowercase + string.ascii_uppercase + string.digits
    if symbols:
        chars += string.punctuation
    result = secrets.token_urlsafe(length)[:length]
    if not symbols:
        filt = set(string.ascii_letters + string.digits)
        result = "".join(c for c in result if c in filt)
    return result or secrets.token_hex(length // 2 + 1)[:length]


def hash_text(raw: str, algo: str) -> str:
    req = hashrequest(text=raw, algo=algo)
    h = hashlib.new(req.algo)
    h.update(req.text.encode("utf-8"))
    return h.hexdigest()


def hash_file(path: str, algo: str) -> tuple[str, int]:
    req = filehashrequest(path=path, algo=algo)
    h = hashlib.new(req.algo)
    size = 0
    with open(req.path, "rb") as fh:
        with mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as m:
            while True:
                chunk = m.read(req.chunk_size)
                if not chunk:
                    break
                h.update(chunk)
                size += len(chunk)
    return h.hexdigest(), size


_HASH_ALGOS = (
    "md5",
    "sha1",
    "sha256",
    "sha512",
    "blake2b",
    "blake2s",
)
