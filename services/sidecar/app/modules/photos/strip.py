"""Remove metadata from JPEG and PNG files without decoding the image.

JPEG: every APPn segment except APP0 (JFIF) and APP14 (Adobe colour transform) goes,
and so does every COM segment: that drops EXIF (camera, serial, GPS, date), XMP, ICC
and IPTC. PNG: only the chunks needed to draw the picture are kept. The renderer already
re-encodes photos through a canvas (which writes no metadata); this is the sidecar's own
guarantee for anything that reaches it another way.
"""

from __future__ import annotations

import struct
import zlib

JPEG_SOI = b"\xff\xd8"
PNG_SIG = b"\x89PNG\r\n\x1a\n"
PNG_KEEP = {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"gAMA", b"sRGB", b"cHRM", b"sBIT"}


class NotAnImage(ValueError):
    pass


def kind(data: bytes) -> str:
    if data.startswith(JPEG_SOI):
        return "image/jpeg"
    if data.startswith(PNG_SIG):
        return "image/png"
    raise NotAnImage("only JPEG and PNG photos are supported")


def strip_jpeg(data: bytes) -> bytes:
    if not data.startswith(JPEG_SOI):
        raise NotAnImage("not a JPEG")
    out = bytearray(JPEG_SOI)
    i = 2
    n = len(data)
    while i < n:
        if data[i] != 0xFF:
            raise NotAnImage("damaged JPEG")
        marker = data[i + 1] if i + 1 < n else 0
        if marker == 0xFF:  # fill byte
            i += 1
            continue
        if marker == 0xDA:  # start of scan: the rest is image data
            out += data[i:]
            return bytes(out)
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            out += data[i : i + 2]
            i += 2
            continue
        if marker == 0xD9:
            out += data[i : i + 2]
            return bytes(out)
        if i + 4 > n:
            raise NotAnImage("damaged JPEG")
        (length,) = struct.unpack(">H", data[i + 2 : i + 4])
        seg = data[i : i + 2 + length]
        if len(seg) < 2 + length:
            raise NotAnImage("damaged JPEG")
        is_app = 0xE0 <= marker <= 0xEF
        if (not is_app or marker in (0xE0, 0xEE)) and marker != 0xFE:
            out += seg
        i += 2 + length
    raise NotAnImage("damaged JPEG")


def strip_png(data: bytes) -> bytes:
    if not data.startswith(PNG_SIG):
        raise NotAnImage("not a PNG")
    out = bytearray(PNG_SIG)
    i = len(PNG_SIG)
    while i + 8 <= len(data):
        (length,) = struct.unpack(">I", data[i : i + 4])
        ctype = data[i + 4 : i + 8]
        end = i + 12 + length
        if end > len(data):
            raise NotAnImage("damaged PNG")
        chunk = data[i:end]
        crc = struct.unpack(">I", chunk[-4:])[0]
        if zlib.crc32(chunk[4:-4]) & 0xFFFFFFFF != crc:
            raise NotAnImage("damaged PNG")
        if ctype in PNG_KEEP:
            out += chunk
        i = end
        if ctype == b"IEND":
            return bytes(out)
    raise NotAnImage("damaged PNG")


def strip(data: bytes) -> tuple[bytes, str]:
    """(clean bytes, mime type)."""
    mime = kind(data)
    return (strip_jpeg(data) if mime == "image/jpeg" else strip_png(data)), mime
