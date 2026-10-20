"""Pictures on cards: search free images, prepare a file for Anki's media folder, add it to a field with a credit.

The search only returns freely licensed images (public domain, CC0, CC BY, CC BY-SA). Images are stored in Anki
through AnkiConnect's storeMediaFile and shown with an <img> tag; CC BY and CC BY-SA images carry a credit line.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

MAX_BYTES = 2_000_000
TYPES = {b"\x89PNG": ".png", b"\xff\xd8\xff": ".jpg", b"GIF8": ".gif", b"RIFF": ".webp"}
FREE = ("cc0", "public domain", "pd", "cc by")
UA = {"User-Agent": "anki-librarian-mcp/0.2 (image search for flashcards)"}
COMMONS = "https://commons.wikimedia.org/w/api.php"


class MediaError(ValueError):
    pass


def http_get(url: str, timeout: float = 20.0) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read(MAX_BYTES + 1)


def _kind(data: bytes) -> str:
    for magic, ext in TYPES.items():
        if data.startswith(magic):
            return ext
    raise MediaError("not a PNG, JPEG, GIF or WebP image")


def prepare(image: dict, state_dir: Path, label: str, fetch=http_get) -> tuple[str, dict]:
    """Read the image (path or url), check it, keep a copy, and return (file name, storeMediaFile step)."""
    if image.get("path"):
        data = Path(image["path"]).read_bytes()
    elif image.get("url"):
        if not image["url"].startswith("https://"):
            raise MediaError("only https:// image links")
        data = fetch(image["url"])
    else:
        raise MediaError("give 'path' or 'url'")
    if len(data) > MAX_BYTES:
        raise MediaError(f"image larger than {MAX_BYTES // 1_000_000} MB")
    ext = _kind(data)
    slug = re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", " ", label).lower()).strip("-")[:30] or "image"
    name = f"img-{slug}-{hashlib.sha1(data).hexdigest()[:6]}{ext}"
    folder = Path(state_dir) / "media"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(data)
    step = {"action": "storeMediaFile", "params": {"filename": name, "data": base64.b64encode(data).decode()}}
    return name, step


def html(name: str, credit: str = "") -> str:
    out = f'<br><br><img src="{name}">'
    if credit:
        out += f"<br><i>Photo: {credit}</i>"
    return out


def is_free(licence: str) -> bool:
    words = licence.lower().replace("-", " ").split()
    if "nc" in words or "nd" in words:
        return False
    return " ".join(words).startswith(FREE)


def search_commons(term: str, n: int = 6, fetch=http_get) -> list[dict]:
    """Free images from Wikimedia Commons for a term, with licence and author for the credit line."""
    q = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": term,
        "gsrnamespace": 6,
        "gsrlimit": n * 3,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 800,
    }
    data = json.loads(fetch(f"{COMMONS}?{urllib.parse.urlencode(q)}"))
    out = []
    for page in (data.get("query") or {}).get("pages", {}).values():
        title = page.get("title", "")
        if re.search(r"(?i)\.(pdf|djvu|svg)$|diagram|map of", title):
            continue
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        licence = (meta.get("LicenseShortName") or {}).get("value", "")
        if not is_free(licence):
            continue
        author = re.sub(r"<[^>]+>", "", (meta.get("Artist") or {}).get("value", "")).strip() or "unknown author"
        out.append(
            {
                "title": title.removeprefix("File:"),
                "url": info.get("thumburl") or info.get("url"),
                "page": info.get("descriptionurl"),
                "licence": licence,
                "credit": f"{author} · {licence} · Wikimedia Commons",
                "credit_required": licence.upper().startswith("CC BY"),
            }
        )
        if len(out) == n:
            break
    return out
