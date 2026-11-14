# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""A one-page PDF of plain lines, standard library only.

The standard PDF fonts have no Vietnamese letters, so the text is written without diacritics
("Phieu xac nhan ky so"); the page is a receipt next to the signed document, not the document itself.
"""

from __future__ import annotations

import unicodedata


def ascii_fold(text: str) -> str:
    text = str(text).replace("đ", "d").replace("Đ", "D")
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return folded.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def one_page(title: str, lines: list[str]) -> bytes:
    """A4 page: a bold title then the lines (long ones wrapped at 95 characters)."""
    wrapped: list[str] = []
    for line in lines:
        line = ascii_fold(line)
        while len(line) > 95:
            cut = line.rfind(" ", 0, 95)
            cut = cut if cut > 40 else 95
            wrapped.append(line[:cut])
            line = line[cut:].lstrip()
        wrapped.append(line)
    content = ["BT", "/F2 16 Tf", "56 790 Td", f"({ascii_fold(title)}) Tj", "/F1 10 Tf", "0 -28 Td", "14 TL"]
    content += [f"({line}) Tj T*" for line in wrapped[:52]]
    content.append("ET")
    stream = "\n".join(content).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)
