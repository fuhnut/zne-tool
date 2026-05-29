from __future__ import annotations

import argparse
import base64
import hashlib
import marshal
import os
import secrets
import uuid
import zlib
from pathlib import Path

_PH = {
    "uid": "__ZNE_UID__",
    "payload": "__ZNE_PAYLOAD__",
    "mk": "__ZNE_MK__",
    "pxk": "__ZNE_PXK__",
    "hmk": "__ZNE_HMK__",
    "hmac": "__ZNE_HMAC__",
    "expire": "__ZNE_EXPIRE__",
    "bind": "__ZNE_BIND__",
    "junk": "__ZNE_JUNK__",
    "strdec": "__ZNE_STRDEC__",
}


def _minify(source: str) -> str:
    b = base64.b64encode(source.encode("utf-8")).decode("ascii")
    return f"exec(__import__('base64').b64decode('{b}'))"


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _keystream_encrypt(data: bytes, enc_key: bytes) -> bytes:
    ks = bytearray()
    ctr = 0
    while len(ks) < len(data):
        ks.extend(hashlib.sha256(enc_key + ctr.to_bytes(8, "big")).digest())
        ctr += 1
    return bytes(b ^ ks[i] for i, b in enumerate(data))


def _walk_consts(consts, key: bytes) -> list:
    out = []
    for c in consts:
        if isinstance(c, str):
            if len(c) > 0:
                out.append(("__enc_str__", _xor_bytes(c.encode("utf-8"), key)))
            else:
                out.append(c)
        elif isinstance(c, bytes):
            if len(c) > 0:
                out.append(("__enc_bytes__", _xor_bytes(c, key)))
            else:
                out.append(c)
        elif isinstance(c, tuple):
            out.append(tuple(_walk_consts(c, key)))
        elif isinstance(c, frozenset):
            out.append(frozenset(_walk_consts(c, key)))
        elif hasattr(c, "co_consts"):
            out.append(_encrypt_consts(c, key))
        else:
            out.append(c)
    return out


def _encrypt_consts(code, key: bytes):
    new_consts = tuple(_walk_consts(code.co_consts, key))
    return code.replace(co_consts=new_consts)


def _decrypt_stub(key_hex: str) -> str:
    return (
        f"_ck=bytes.fromhex('{key_hex}')\n"
        "def _rd(c):\n"
        " if isinstance(c,tuple):\n"
        "  if len(c)==2 and c[0]=='__enc_str__':return bytes(b^_ck[i%len(_ck)]for i,b in enumerate(c[1])).decode('utf-8')\n"
        "  if len(c)==2 and c[0]=='__enc_bytes__':return bytes(b^_ck[i%len(_ck)]for i,b in enumerate(c[1]))\n"
        "  return tuple(_rd(x)for x in c)\n"
        " if isinstance(c,frozenset):return frozenset(_rd(x)for x in c)\n"
        " return c\n"
        "def _fx(c):\n"
        " nc=tuple(_rd(x)for x in c.co_consts)\n"
        " cc=c.replace(co_consts=nc)\n"
        " return cc\n"
        "_code=_fx(_code)\n"
    )


def _junk_lines(n: int) -> list[str]:
    rng = secrets.SystemRandom()
    lines: list[str] = []
    for _ in range(n):
        kind = rng.randint(0, 2)
        if kind == 0:
            v = rng.randbytes(8).hex()
            lines.append(f"_{v}=None;del _{v}")
        elif kind == 1:
            v = rng.randbytes(6).hex()
            lines.append(f"if _{v}:=0:pass")
        else:
            v = rng.randbytes(5).hex()
            lines.append(f"while _j_{v}:=0:break")
    return lines


def _build(
    source_path: Path,
    *,
    encrypt_strings: bool = False,
    expire: str | None = None,
    bind_host: str | None = None,
) -> tuple[str, str, str, str, str, str, str, str, str]:
    build_uuid = str(uuid.uuid4())
    source = source_path.read_text(encoding="utf-8")
    code = compile(source, str(source_path), "exec")

    str_key_hex = ""
    if encrypt_strings:
        str_key = secrets.token_bytes(16)
        str_key_hex = str_key.hex()
        code = _encrypt_consts(code, str_key)

    marshaled = marshal.dumps(code)
    compressed = zlib.compress(marshaled, level=9)

    hmac_key = secrets.token_bytes(32)
    payload_hmac = hashlib.sha256(hmac_key + compressed).hexdigest()

    master_key = secrets.token_bytes(32)
    uuid_salt = hashlib.sha256(build_uuid.encode()).digest()[:16]
    enc_key = hashlib.sha256(master_key + b"enc" + uuid_salt).digest()
    encrypted = _keystream_encrypt(compressed, enc_key)

    xor_key = secrets.token_bytes(16)
    xored = _xor_bytes(encrypted, xor_key)

    return (
        base64.b64encode(xored).decode("ascii"),
        base64.b64encode(master_key).decode("ascii"),
        base64.b64encode(xor_key).decode("ascii"),
        build_uuid,
        base64.b64encode(hmac_key).decode("ascii"),
        payload_hmac,
        str_key_hex,
        expire or "",
        bind_host or "",
    )


VM_TEMPLATE = r"""import sys as _sys,hashlib as _hl,zlib as _zl,base64 as _b64,gc as _gc,time as _tm,marshal as _ma
if _sys.gettrace()is not None:_sys.settrace(None)
_t0=_tm.monotonic()
for _ in range(1000):pass
if _tm.monotonic()-_t0>2.0:_sys.exit(1)
__ZNE_EXPIRE__
__ZNE_BIND__
__ZNE_JUNK__
_uid="__ZNE_UID__"
_raw=_b64.b64decode("__ZNE_PAYLOAD__")
_mk=_b64.b64decode("__ZNE_MK__")
_ek=_hl.sha256(_mk+b"enc"+_hl.sha256(_uid.encode()).digest()[:16]).digest()
_pxk=_b64.b64decode("__ZNE_PXK__")
_d=bytes(b^_pxk[i%len(_pxk)]for i,b in enumerate(_raw))
del _raw,_pxk
_ks=bytearray();_c=0
while len(_ks)<len(_d):
 _ks.extend(_hl.sha256(_ek+_c.to_bytes(8,"big")).digest())
 _c+=1
_d=bytes(b^_ks[i]for i,b in enumerate(_d))
del _ek,_mk,_ks
_hmk=_b64.b64decode("__ZNE_HMK__")
if _hl.sha256(_hmk+_d).hexdigest()!="__ZNE_HMAC__":raise RuntimeError("integrity check failed")
del _hmk
_d=_zl.decompress(_d)
del _zl
_code=_ma.loads(_d)
del _d,_ma
__ZNE_STRDEC__
_gl={'__name__':'__main__','__file__':_sys.argv[0],'__builtins__':__builtins__}
exec(_code,_gl)
"""


def _pack_layer(source_code: str) -> str:
    build_uuid = str(uuid.uuid4())
    raw = source_code.encode("utf-8")
    compressed = zlib.compress(raw, level=9)

    master_key = secrets.token_bytes(32)
    uuid_salt = hashlib.sha256(build_uuid.encode()).digest()[:16]
    enc_key = hashlib.sha256(master_key + b"enc" + uuid_salt).digest()
    encrypted = _keystream_encrypt(compressed, enc_key)

    xor_key = secrets.token_bytes(16)
    xored = _xor_bytes(encrypted, xor_key)

    payload_b64 = base64.b64encode(xored).decode()
    mk_b64 = base64.b64encode(master_key).decode()
    pxk_b64 = base64.b64encode(xor_key).decode()

    layer = (
        "import sys as _s,hashlib as _h,zlib as _z,base64 as _b,gc as _g,time as _t\n"
        "if _s.gettrace()is not None:_s.settrace(None)\n"
        "_t0=_t.monotonic()\n"
        "for _ in range(1000):pass\n"
        "if _t.monotonic()-_t0>2.0:_s.exit(1)\n"
        f"_u='{build_uuid}'\n"
        f"_r=_b.b64decode('{payload_b64}')\n"
        f"_m=_b.b64decode('{mk_b64}')\n"
        f"_k=_h.sha256(_m+b'enc'+_h.sha256(_u.encode()).digest()[:16]).digest()\n"
        f"_x=_b.b64decode('{pxk_b64}')\n"
        "_d=bytes(b^_x[i%len(_x)]for i,b in enumerate(_r))\n"
        "del _r,_x\n"
        "_ks=bytearray();_c=0\n"
        "while len(_ks)<len(_d):\n"
        " _ks.extend(_h.sha256(_k+_c.to_bytes(8,'big')).digest());_c+=1\n"
        "_d=bytes(b^_ks[i]for i,b in enumerate(_d))\n"
        "del _k,_m,_ks,_c\n"
        "_d=_z.decompress(_d).decode()\n"
        "del _s,_h,_z,_b,_g,_t,_u\n"
        "exec(_d)\n"
    )
    return _minify(layer)


def run(
    source: Path,
    output: Path | None,
    *,
    encrypt_strings: bool = False,
    expire: str | None = None,
    bind_host: str | None = None,
    layers: int = 1,
    junk: int = 8,
) -> None:
    if not source.exists():
        raise FileNotFoundError(source)

    if output is None:
        output = source.parent / f"{source.stem}_packed.py"

    (
        payload_b64,
        mk_b64,
        pxk_b64,
        buid,
        hmac_key_b64,
        payload_hmac,
        str_key_hex,
        expire_val,
        bind_host_val,
    ) = _build(
        source,
        encrypt_strings=encrypt_strings,
        expire=expire,
        bind_host=bind_host,
    )

    expire_snippet = ""
    if expire_val:
        expire_snippet = f"if _tm.time()>float('{expire_val}'):_sys.exit(1)\n"

    bind_snippet = ""
    if bind_host_val:
        bind_snippet = (
            f"if __import__('socket').gethostname()!='{bind_host_val}':_sys.exit(1)\n"
        )

    str_decrypt = ""
    if str_key_hex:
        str_decrypt = _decrypt_stub(str_key_hex)

    junk_code = "\n".join(_junk_lines(junk)) if junk else ""

    content = VM_TEMPLATE
    content = content.replace(_PH["uid"], buid)
    content = content.replace(_PH["payload"], payload_b64)
    content = content.replace(_PH["mk"], mk_b64)
    content = content.replace(_PH["pxk"], pxk_b64)
    content = content.replace(_PH["hmk"], hmac_key_b64)
    content = content.replace(_PH["hmac"], payload_hmac)
    content = content.replace(_PH["expire"], expire_snippet)
    content = content.replace(_PH["bind"], bind_snippet)
    content = content.replace(_PH["junk"], junk_code)
    content = content.replace(_PH["strdec"], str_decrypt)

    for _ in range(layers - 1):
        content = _pack_layer(content)

    if layers <= 1:
        content = _minify(content)

    output.write_text(content, encoding="utf-8")
    os.chmod(output, 0o755)
    print(f"built -> {output}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="zne-pack")
    parser.add_argument("source", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--strings", action="store_true")
    parser.add_argument("--expire", type=str, default=None)
    parser.add_argument("--bind-host", type=str, default=None)
    parser.add_argument("--layers", type=int, default=1)
    parser.add_argument("--junk", type=int, default=8)

    args = parser.parse_args()

    if args.output is None:
        stem = args.source.stem
        args.output = args.source.parent / f"{stem}_packed.py"

    run(
        args.source,
        args.output,
        encrypt_strings=args.strings,
        expire=args.expire,
        bind_host=args.bind_host,
        layers=args.layers,
        junk=args.junk,
    )
# print("done")