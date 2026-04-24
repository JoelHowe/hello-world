"""URL canonicalization.

Why this matters: the *same* article gets shared as `bit.ly/xyz`,
`example.com/story?utm_source=twitter`, `example.com/story?ref=bsky`, and
the bare `https://example.com/story/`. Nuzzle's whole value proposition
depends on collapsing those to one canonical URL so we can count distinct
sharers correctly.

Strategy:
  1. Normalize (lower-case host, strip default ports, unify trailing slash)
  2. Drop known tracking params (utm_*, fbclid, gclid, ...)
  3. For known URL shorteners, follow redirects (HEAD, then GET fallback)
     and re-canonicalize the expanded URL.

Pure function for (1) + (2) so it's easy to unit-test. (3) takes an httpx
client injected by the caller so tests can mock redirects with respx.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from url_normalize import url_normalize

# Tracking params we always strip. Mix of exact names and prefixes.
_TRACKING_PARAM_PREFIXES: tuple[str, ...] = (
    "utm_",
    "mc_",
    "_hsenc",
    "_hsmi",
    "hsa_",
    "vero_",
)
_TRACKING_PARAM_EXACT: frozenset[str] = frozenset(
    {
        "fbclid",
        "gclid",
        "gbraid",
        "wbraid",
        "yclid",
        "dclid",
        "msclkid",
        "igshid",
        "twclid",
        "ref",
        "ref_src",
        "ref_url",
        "s",  # twitter share param ("?s=20")
        "t",  # twitter share param ("?t=abc")
        "si",  # youtube/spotify share param
        "feature",  # youtube
        "source",  # common tracking alias
    }
)

_KNOWN_SHORTENERS: frozenset[str] = frozenset(
    {
        "bit.ly",
        "buff.ly",
        "t.co",
        "tinyurl.com",
        "ow.ly",
        "dlvr.it",
        "lnkd.in",
        "trib.al",
        "ift.tt",
        "is.gd",
        "goo.gl",
        "shar.es",
        "j.mp",
        "rebrand.ly",
        "tiny.cc",
        "bsky.app",  # bsky link wrapper (rare)
    }
)


def _is_tracking_param(name: str) -> bool:
    if name in _TRACKING_PARAM_EXACT:
        return True
    return any(name.startswith(p) for p in _TRACKING_PARAM_PREFIXES)


def _strip_tracking_query(query: str) -> str:
    if not query:
        return ""
    kept = [(k, v) for k, v in parse_qsl(query, keep_blank_values=True) if not _is_tracking_param(k)]
    return urlencode(kept, doseq=True)


def _normalize_once(url: str) -> str:
    """Scheme/host normalization + tracking-param stripping. No network."""
    try:
        normalized = url_normalize(url)
    except Exception:
        normalized = url

    parts = urlsplit(normalized)
    # Drop fragment entirely — it never identifies an article.
    cleaned_query = _strip_tracking_query(parts.query)
    # Lower-case host (url_normalize does this, belt-and-braces)
    netloc = parts.netloc.lower()

    return urlunsplit((parts.scheme.lower(), netloc, parts.path, cleaned_query, ""))


def _host_of(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")


def domain_of(url: str) -> str:
    return _host_of(url)


def canonicalize(url: str) -> str:
    """Pure-function canonicalization (no network). Use `expand_and_canonicalize`
    when you want shortener resolution."""
    return _normalize_once(url)


@dataclass
class _ExpandCache:
    """Per-run memoization of shortener expansions."""

    _data: dict[str, str]

    def get(self, url: str) -> str | None:
        return self._data.get(url)

    def set(self, url: str, expanded: str) -> None:
        self._data[url] = expanded


def new_expand_cache() -> _ExpandCache:
    return _ExpandCache(_data={})


_MAX_HOPS = 5
_TIMEOUT = 5.0


def expand_and_canonicalize(
    url: str,
    client: httpx.Client,
    cache: _ExpandCache | None = None,
) -> str:
    """Canonicalize, then resolve known shorteners via HEAD redirects, then
    canonicalize the final URL. Safe: caps hops, swallows errors (returns
    the best URL we reached)."""
    cache = cache or new_expand_cache()

    current = _normalize_once(url)
    hops = 0
    while hops < _MAX_HOPS and _host_of(current) in _KNOWN_SHORTENERS:
        if cached := cache.get(current):
            current = cached
            break
        try:
            resp = client.head(current, follow_redirects=False, timeout=_TIMEOUT)
            # Some shorteners reject HEAD; retry with GET stream.
            if resp.status_code >= 400:
                resp = client.get(
                    current, follow_redirects=False, timeout=_TIMEOUT
                )
        except httpx.HTTPError:
            break

        location = resp.headers.get("location")
        if not location or resp.status_code not in (301, 302, 303, 307, 308):
            break

        # Relative redirects → resolve against current
        if location.startswith("/"):
            parts = urlsplit(current)
            location = urlunsplit((parts.scheme, parts.netloc, location, "", ""))

        next_url = _normalize_once(location)
        cache.set(current, next_url)
        current = next_url
        hops += 1

    return current
