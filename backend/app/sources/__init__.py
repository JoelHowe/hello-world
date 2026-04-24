"""Pluggable data sources.

Adding a new network (X, Substack Notes, Mastodon, Farcaster, ...) means:
  1. Implement `SourceAdapter` in a new module here.
  2. Register it in `REGISTRY` below.
  3. Handle login in `routers/auth.py` (one branch per auth style).

Everything downstream (ingest, canonicalize, rank, API, UI) is source-agnostic
and keys objects by `{source}:{handle}` so multiple networks can coexist in
the same database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Protocol, runtime_checkable


@dataclass(frozen=True)
class SharedPost:
    """Source-agnostic record of one post that contained URLs."""

    source: str
    author_handle: str
    author_display_name: str | None
    author_avatar_url: str | None
    posted_at: datetime
    permalink: str
    post_uri: str  # stable per-source id used for dedup within a run
    urls: list[str]  # raw URLs, pre-canonicalization


@dataclass(frozen=True)
class SourceCredentials:
    """Credentials to hydrate into a live session before fetching.

    Opaque to the rest of the app — each adapter interprets its own fields.
    For Bluesky these are the AT-proto JWTs; for X they'd be an OAuth2
    bearer, etc.
    """

    access_token: str
    refresh_token: str | None = None
    extra: dict[str, str] | None = None


@runtime_checkable
class SourceAdapter(Protocol):
    """Contract every data source implements."""

    name: str  # e.g. "bluesky", "x", "substack_notes"

    def login(self, handle: str, secret: str) -> tuple[SourceCredentials, dict]:
        """Exchange handle + secret (password, OAuth code, ...) for durable
        credentials. Second return is a dict of profile fields (did, display
        name, avatar) to persist on the viewer's Account row."""
        ...

    def recent_self_timeline(
        self,
        creds: SourceCredentials,
        since: datetime,
        max_posts: int,
    ) -> Iterator[SharedPost]:
        """Yield the signed-in viewer's home timeline posts newer than
        `since`, oldest-last. Implementations should paginate and stop
        once `since` is crossed or `max_posts` is reached."""
        ...

    # v2 (arbitrary-user mode):
    # def recent_from_follows_of(
    #     self, creds: SourceCredentials, handle: str, since: datetime, max_posts: int,
    # ) -> Iterator[SharedPost]: ...


# Populated at import time below.
REGISTRY: dict[str, SourceAdapter] = {}


def register(adapter: SourceAdapter) -> SourceAdapter:
    REGISTRY[adapter.name] = adapter
    return adapter


# Import adapters so they self-register. Guarded because optional adapters
# (Twitter/Substack) may have missing deps until wired up.
from . import bluesky as _bluesky  # noqa: E402,F401

try:  # pragma: no cover  optional, stubbed for v1
    from . import twitter as _twitter  # noqa: F401
except Exception:
    pass

try:  # pragma: no cover  optional, stubbed for v1
    from . import substack_notes as _substack  # noqa: F401
except Exception:
    pass


def get_adapter(name: str) -> SourceAdapter:
    try:
        return REGISTRY[name]
    except KeyError as e:
        raise ValueError(
            f"Unknown source {name!r}. Available: {sorted(REGISTRY)}"
        ) from e
