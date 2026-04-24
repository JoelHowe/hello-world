"""Substack Notes source adapter — STUB.

Substack Notes has no official public API at time of writing. Options:

1. Scraping the public Notes feed at `substack.com/api/v1/reader/feed/...`
   endpoints that the web app uses (unofficial; may change without notice;
   check ToS).
2. RSS per-publication (gives posts, not Notes; partial coverage).
3. Wait for an official API.

Login model differs from Bluesky: Substack auth is email-magic-link or
Google. For v2 the likely shape is a browser-cookie paste flow similar to
some newsreader integrations, or an API token if one appears.

Leave unimplemented until a viable path exists.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterator

from . import SharedPost, SourceCredentials


class SubstackNotesAdapter:
    name = "substack_notes"

    def login(self, handle: str, secret: str) -> tuple[SourceCredentials, dict]:
        raise NotImplementedError("Substack Notes adapter not yet implemented.")

    def recent_self_timeline(
        self,
        creds: SourceCredentials,
        since: datetime,
        max_posts: int,
    ) -> Iterator[SharedPost]:
        raise NotImplementedError("Substack Notes adapter not yet implemented.")
        yield  # pragma: no cover
