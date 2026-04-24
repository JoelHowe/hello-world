"""Best-effort OpenGraph metadata fetch for a URL.

Keep this cheap and failure-tolerant: the ranking works even when every
metadata call fails — the UI just falls back to showing the domain.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from selectolax.parser import HTMLParser


@dataclass
class LinkMetadata:
    title: str | None = None
    description: str | None = None
    image_url: str | None = None


_MAX_BYTES = 256 * 1024  # 256 KB is plenty for <head>
_TIMEOUT = 6.0

_USER_AGENT = (
    "Mozilla/5.0 (compatible; NuzzleClone/0.1; +https://github.com/joelhowe/hello-world)"
)


def _meta(tree: HTMLParser, prop: str) -> str | None:
    node = tree.css_first(f'meta[property="{prop}"]') or tree.css_first(
        f'meta[name="{prop}"]'
    )
    if node is None:
        return None
    content = node.attributes.get("content")
    return content.strip() if content else None


def fetch_metadata(url: str, client: httpx.Client) -> LinkMetadata:
    headers = {"User-Agent": _USER_AGENT, "Accept": "text/html,*/*;q=0.1"}
    try:
        with client.stream(
            "GET", url, headers=headers, follow_redirects=True, timeout=_TIMEOUT
        ) as resp:
            if resp.status_code >= 400:
                return LinkMetadata()
            ctype = resp.headers.get("content-type", "")
            if "html" not in ctype:
                return LinkMetadata()

            chunks: list[bytes] = []
            total = 0
            for chunk in resp.iter_bytes(chunk_size=16 * 1024):
                chunks.append(chunk)
                total += len(chunk)
                if total >= _MAX_BYTES:
                    break
            body = b"".join(chunks)
    except httpx.HTTPError:
        return LinkMetadata()

    try:
        html = body.decode(
            resp.encoding or "utf-8", errors="replace"
        )
    except Exception:
        html = body.decode("utf-8", errors="replace")

    tree = HTMLParser(html)

    title = (
        _meta(tree, "og:title")
        or _meta(tree, "twitter:title")
        or (tree.css_first("title").text(strip=True) if tree.css_first("title") else None)
    )
    description = _meta(tree, "og:description") or _meta(tree, "twitter:description") or _meta(tree, "description")
    image = _meta(tree, "og:image") or _meta(tree, "twitter:image")

    return LinkMetadata(title=title, description=description, image_url=image)
