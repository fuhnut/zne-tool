from __future__ import annotations

from msgspec import json, msgpack

_jenc = json.Encoder()
_jdec = json.Decoder()
_menc = msgpack.Encoder()
_mdec = msgpack.Decoder()


def jencode(value) -> bytes:
    return _jenc.encode(value)


def jdecode(raw: bytes | str, type=None):
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if type is None:
        return _jdec.decode(raw)
    return json.decode(raw, type=type)


def mencode(value) -> bytes:
    return _menc.encode(value)


def mdecode(raw: bytes, type=None):
    if type is None:
        return _mdec.decode(raw)
    return msgpack.decode(raw, type=type)
