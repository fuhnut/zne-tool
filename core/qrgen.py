from __future__ import annotations


def generate(data, box_size: int = 2) -> list[str]:
    import qrcode

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image()
    pixels = img.convert("1").load()
    w, h = img.size

    rows = []
    for y in range(0, h, box_size):
        line = ""
        for x in range(0, w, box_size):
            is_dark = pixels[x, y] == 0
            line += "██" if is_dark else "  "
        rows.append(line)
    return rows
