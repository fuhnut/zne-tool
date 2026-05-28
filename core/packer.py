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


def _minify(source: str) -> str:
    b = base64.b64encode(source.encode("utf-8")).decode("ascii")
    return f"exec(__import__('base64').b64decode('{b}'))"


def _build(source_path: Path) -> tuple[str, str, str, str, dict]:
    build_uuid = str(uuid.uuid4())
    source = source_path.read_text(encoding="utf-8")

    # Compile to a real Python code object -- this supports *everything* CPython supports
    code = compile(source, source_path.name, "exec")

    # Marshal to raw bytes
    marshaled = marshal.dumps(code)

    # Compress
    compressed = zlib.compress(marshaled, level=9)

    # Encrypt with custom keystream
    master_key = secrets.token_bytes(32)
    uuid_salt = hashlib.sha256(build_uuid.encode()).digest()[:16]
    enc_key = hashlib.sha256(master_key + b"enc" + uuid_salt).digest()
    keystream = bytearray()
    ctr = 0
    while len(keystream) < len(compressed):
        block = hashlib.sha256(enc_key + ctr.to_bytes(8, "big")).digest()
        keystream.extend(block)
        ctr += 1
    encrypted = bytes(b ^ keystream[i] for i, b in enumerate(compressed))

    # XOR layer
    payload_xor_key = secrets.token_bytes(16)
    xored = bytes(
        b ^ payload_xor_key[i % len(payload_xor_key)] for i, b in enumerate(encrypted)
    )

    return (
        base64.b64encode(xored).decode("ascii"),
        base64.b64encode(master_key).decode("ascii"),
        base64.b64encode(payload_xor_key).decode("ascii"),
        build_uuid,
        {},
    )


VM_TEMPLATE = r"""import sys as _sys,hashlib as _hl,zlib as _zl,base64 as _b64,gc as _gc,time as _tm,marshal as _ma
if _sys.gettrace()is not None:_sys.exit(1)
_sys.settrace(None)
_t0=_tm.monotonic()
for _ in range(1000):pass
if _tm.monotonic()-_t0>0.05:_sys.exit(1)
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
_d=_zl.decompress(_d)
del _zl
_code=_ma.loads(_d)
del _d,_ma
_gl={'__name__':'__main__','__file__':_sys.argv[0],'__builtins__':__builtins__}
exec(_code,_gl)
"""


def run(source: Path, output: Path | None) -> None:
    if not source.exists():
        raise FileNotFoundError(source)

    if output is None:
        output = source.parent / f"{source.stem}_packed.py"

    payload_b64, mk_b64, pxk_b64, buid, _ = _build(source)
    content = VM_TEMPLATE.replace("{build_uuid}", buid)
    content = content.replace("{payload}", payload_b64)
    content = content.replace("{master_key}", mk_b64)
    content = content.replace("{payload_xor_key}", pxk_b64)

    minified = _minify(content)
    output.write_text(minified, encoding="utf-8")
    os.chmod(output, 0o755)
    print(f"built -> {output}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="zne-pack")
    parser.add_argument("source", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()

    if args.output is None:
        stem = args.source.stem
        args.output = args.source.parent / f"{stem}_packed.py"

    run(args.source, args.output)
