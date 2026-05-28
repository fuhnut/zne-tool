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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# String encryption  –  walk code-object constants, encrypt str/bytes literals
# ---------------------------------------------------------------------------


def _encrypt_consts(code, key: bytes):
    """Recursively encrypt string/bytes constants inside a code object."""
    new_consts = []
    for c in code.co_consts:
        if isinstance(c, str) and len(c) > 0:
            enc = _xor_bytes(c.encode("utf-8"), key)
            new_consts.append(("__enc_str__", enc))
        elif isinstance(c, bytes) and len(c) > 0:
            enc = _xor_bytes(c, key)
            new_consts.append(("__enc_bytes__", enc))
        elif hasattr(c, "co_consts"):  # nested code object
            new_consts.append(_encrypt_consts(c, key))
        else:
            new_consts.append(c)
    return code.replace(co_consts=tuple(new_consts))


def _decrypt_stub(key_hex: str) -> str:
    """Returns a snippet that patches every code-object's co_consts at load."""
    return (
        f"_ck=bytes.fromhex('{key_hex}')\n"
        "def _dec(c):\n"
        " if isinstance(c,tuple)and len(c)==2:\n"
        "  if c[0]=='__enc_str__':return bytes(b^_ck[i%len(_ck)]for i,b in enumerate(c[1])).decode('utf-8')\n"
        "  if c[0]=='__enc_bytes__':return bytes(b^_ck[i%len(_ck)]for i,b in enumerate(c[1]))\n"
        " return c\n"
        "def _fix(c):\n"
        " nc=tuple(_dec(x)if isinstance(x,tuple)and len(x)==2 and x[0]in('__enc_str__','__enc_bytes__')else _fix(x)if hasattr(x,'co_consts')else x for x in c.co_consts)\n"
        " return c.replace(co_consts=nc)\n"
        "_code=_fix(_code)\n"
    )


# ---------------------------------------------------------------------------
# Junk code generator for the loader stub
# ---------------------------------------------------------------------------


def _junk_lines(n: int) -> list[str]:
    rng = secrets.SystemRandom()
    lines: list[str] = []
    for _ in range(n):
        kind = rng.randint(0, 3)
        if kind == 0:
            v = rng.randbytes(8).hex()
            lines.append(f"_{v}=None;del _{v}")
        elif kind == 1:
            v = rng.randbytes(6).hex()
            lines.append(f"if _{v}:=0:pass")
        elif kind == 2:
            a, b = rng.randbytes(4).hex(), rng.randbytes(4).hex()
            lines.append(f"_l_{a}=[_l_{b} for _l_{b} in [0]];del _l_{a}")
        else:
            v = rng.randbytes(5).hex()
            lines.append(f"while _j_{v}:=0:break")
    return lines


# ---------------------------------------------------------------------------
# Core build  –  compile → marshal → encrypt → pack into loader
# ---------------------------------------------------------------------------


def _build(
    source_path: Path,
    *,
    encrypt_strings: bool = False,
    expire: str | None = None,
    bind_host: str | None = None,
) -> tuple[str, str, str, str, str, str, str, str, str]:
    build_uuid = str(uuid.uuid4())
    source = source_path.read_text(encoding="utf-8")

    code = compile(source, source_path.name, "exec")

    # -- string encryption --------------------------------------------------
    str_key_hex = ""
    if encrypt_strings:
        str_key = secrets.token_bytes(16)
        str_key_hex = str_key.hex()
        code = _encrypt_consts(code, str_key)

    marshaled = marshal.dumps(code)
    compressed = zlib.compress(marshaled, level=9)

    # -- HMAC integrity -----------------------------------------------------
    hmac_key = secrets.token_bytes(32)
    payload_hmac = hashlib.sha256(hmac_key + compressed).hexdigest()

    # -- encrypt payload ----------------------------------------------------
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


# ---------------------------------------------------------------------------
# Loader template
# ---------------------------------------------------------------------------

VM_TEMPLATE = r"""import sys as _sys,hashlib as _hl,zlib as _zl,base64 as _b64,gc as _gc,time as _tm,marshal as _ma
if _sys.gettrace()is not None:_sys.settrace(None)
_t0=_tm.monotonic()
for _ in range(1000):pass
if _tm.monotonic()-_t0>2.0:_sys.exit(1)
{expire_check}
{bind_check}
{junk}
_uid="{build_uuid}"
_raw=_b64.b64decode("{payload}")
_mk=_b64.b64decode("{master_key}")
_ek=_hl.sha256(_mk+b"enc"+_hl.sha256(_uid.encode()).digest()[:16]).digest()
_pxk=_b64.b64decode("{payload_xor_key}")
_d=bytes(b^_pxk[i%len(_pxk)]for i,b in enumerate(_raw))
del _raw,_pxk
_ks=bytearray();_c=0
while len(_ks)<len(_d):
 _ks.extend(_hl.sha256(_ek+_c.to_bytes(8,"big")).digest())
 _c+=1
_d=bytes(b^_ks[i]for i,b in enumerate(_d))
del _ek,_mk,_ks
_hmk=_b64.b64decode("{hmac_key}")
if _hl.sha256(_hmk+_d).hexdigest()!="{payload_hmac}":raise RuntimeError("integrity check failed")
del _hmk
_d=_zl.decompress(_d)
del _zl
_code=_ma.loads(_d)
del _d,_ma
{str_decrypt}
_gl={'__name__':'__main__','__file__':_sys.argv[0],'__builtins__':__builtins__}
exec(_code,_gl)
"""


# ---------------------------------------------------------------------------
# Multi-layer: pack the packed output again with fresh keys
# ---------------------------------------------------------------------------


def _pack_layer(source_code: str) -> str:
    """Take Python source and wrap it in a single encrypted layer."""
    build_uuid = str(uuid.uuid4())
    raw = source_code.encode("utf-8")
    compressed = zlib.compress(raw, level=9)

    master_key = secrets.token_bytes(32)
    uuid_salt = hashlib.sha256(build_uuid.encode()).digest()[:16]
    enc_key = hashlib.sha256(master_key + b"enc" + uuid_salt).digest()
    encrypted = _keystream_encrypt(compressed, enc_key)

    xor_key = secrets.token_bytes(16)
    xored = _xor_bytes(encrypted, xor_key)

    layer = (
        "import sys as _s,hashlib as _h,zlib as _z,base64 as _b\n"
        f"_u='{build_uuid}'\n"
        f"_r=_b.b64decode('{base64.b64encode(xored).decode()}')\n"
        f"_m=_b.b64decode('{base64.b64encode(master_key).decode()}')\n"
        f"_k=_h.sha256(_m+b'enc'+_h.sha256(_u.encode()).digest()[:16]).digest()\n"
        f"_x=_b.b64decode('{base64.b64encode(xor_key).decode()}')\n"
        "_d=bytes(b^_x[i%len(_x)]for i,b in enumerate(_r))\n"
        "_ks=bytearray();_c=0\n"
        "while len(_ks)<len(_d):\n"
        " _ks.extend(_h.sha256(_k+_c.to_bytes(8,'big')).digest());_c+=1\n"
        "_d=bytes(b^_ks[i]for i,b in enumerate(_d))\n"
        "_d=_z.decompress(_d).decode()\n"
        "del _s,_h,_z,_b,_u,_r,_m,_k,_x,_ks,_c\n"
        "exec(_d)\n"
    )
    return _minify(layer)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


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

    # -- expire check snippet -----------------------------------------------
    expire_snippet = ""
    if expire_val:
        expire_snippet = f"if _tm.time()>float('{expire_val}'):_sys.exit(1)\n"

    # -- bind-host check snippet --------------------------------------------
    bind_snippet = ""
    if bind_host_val:
        bind_snippet = (
            f"if __import__('socket').gethostname()!='{bind_host_val}':_sys.exit(1)\n"
        )

    # -- string-decrypt snippet ---------------------------------------------
    str_decrypt = ""
    if str_key_hex:
        str_decrypt = _decrypt_stub(str_key_hex)

    # -- junk code ----------------------------------------------------------
    junk_code = "\n".join(_junk_lines(junk)) if junk else ""

    content = VM_TEMPLATE
    content = content.replace("{build_uuid}", buid)
    content = content.replace("{payload}", payload_b64)
    content = content.replace("{master_key}", mk_b64)
    content = content.replace("{payload_xor_key}", pxk_b64)
    content = content.replace("{hmac_key}", hmac_key_b64)
    content = content.replace("{payload_hmac}", payload_hmac)
    content = content.replace("{expire_check}", expire_snippet)
    content = content.replace("{bind_check}", bind_snippet)
    content = content.replace("{junk}", junk_code)
    content = content.replace("{str_decrypt}", str_decrypt)

    # -- multi-layer packing ------------------------------------------------
    for _ in range(layers - 1):
        content = _pack_layer(content)

    if layers <= 1:
        content = _minify(content)

    output.write_text(content, encoding="utf-8")
    os.chmod(output, 0o755)
    print(f"built -> {output}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="zne-pack",
        description="Obfuscate & encrypt a Python script",
    )
    parser.add_argument("source", type=Path, help="Input .py file")
    parser.add_argument("-o", "--output", type=Path, help="Output path")
    parser.add_argument(
        "--strings",
        action="store_true",
        help="Encrypt string/bytes literals in the payload",
    )
    parser.add_argument(
        "--expire",
        type=str,
        default=None,
        help="Unix timestamp after which the script refuses to run",
    )
    parser.add_argument(
        "--bind-host",
        type=str,
        default=None,
        help="Lock execution to a specific hostname",
    )
    parser.add_argument(
        "--layers",
        type=int,
        default=1,
        help="Number of encryption layers (default: 1)",
    )
    parser.add_argument(
        "--junk",
        type=int,
        default=8,
        help="Number of junk-code lines in the loader (default: 8, 0 to disable)",
    )

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
