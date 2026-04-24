"""X (Twitter) source adapter — STUB.

Not wired into v1 because the X API is gated behind a paid plan
(Basic ~$200/mo for 10k reads, Pro ~$5k/mo for 1M). The file exists to
pin down the exact shape a future adapter would take.

Fill in when a paid plan is available:
- Login: OAuth 2.0 PKCE flow → exchange code for access/refresh tokens.
- `recent_self_timeline`: paginate `GET /2/users/:id/timelines/reverse_chronological`
  with `expansions=author_id,attachments.media_keys&tweet.fields=entities,created_at`.
  URLs come from `entities.urls[].expanded_url`.
- v2 `recent_from_follows_of(handle)`: `GET /2/users/by/username/:handle`
  → `GET /2/users/:id/following` (paginate) → fan out to
  `GET /2/users/:id/tweets` per followee.

Do NOT register this adapter until implemented — the REGISTRY lookup in
`routers/auth.py` would otherwise expose a broken login path to the UI.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterator

from . import SharedPost, SourceCredentials


class TwitterAdapter:
    name = "x"

    def login(self, handle: str, secret: str) -> tuple[SourceCredentials, dict]:
        raise NotImplementedError("X adapter requires a paid API plan; not wired in v1.")

    def recent_self_timeline(
        self,
        creds: SourceCredentials,
        since: datetime,
        max_posts: int,
    ) -> Iterator[SharedPost]:
        raise NotImplementedError("X adapter requires a paid API plan; not wired in v1.")
        yield  # pragma: no cover  make the function a generator for type checkers
