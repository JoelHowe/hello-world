"""Bluesky / AT Protocol source adapter.

Uses the official `atproto` Python SDK. The key call is
`app.bsky.feed.getTimeline`, which returns the signed-in viewer's home feed
directly — so v1 doesn't have to enumerate follows and fan out, unlike the
X equivalent.

Session persistence: the SDK exposes `client.export_session_string()` and
`client.login(session_string=...)` as a clean serialize/restore pair. We
stash the exported string in `SourceCredentials.access_token` and treat it
as an opaque blob.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

from atproto import Client

from . import SharedPost, SourceCredentials, register

_PAGE_SIZE = 100


def _parse_at_datetime(raw: str) -> datetime:
    """AT Protocol timestamps are ISO-8601, sometimes with 'Z'."""
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw).astimezone(timezone.utc)


def _permalink(handle: str, post_uri: str) -> str:
    # at://did:plc:xxx/app.bsky.feed.post/<rkey>  ->  https://bsky.app/profile/<handle>/post/<rkey>
    rkey = post_uri.rsplit("/", 1)[-1]
    return f"https://bsky.app/profile/{handle}/post/{rkey}"


def _urls_from_post(record) -> list[str]:
    """Extract URLs from facets (authoritative per AT protocol) plus any
    external link embed."""
    urls: list[str] = []
    facets = getattr(record, "facets", None) or []
    for facet in facets:
        for feat in getattr(facet, "features", []) or []:
            uri = getattr(feat, "uri", None)
            if uri:
                urls.append(uri)
    embed = getattr(record, "embed", None)
    if embed is not None:
        ext = getattr(embed, "external", None)
        if ext is not None:
            uri = getattr(ext, "uri", None)
            if uri:
                urls.append(uri)
    return urls


class BlueskyAdapter:
    name = "bluesky"

    def login(self, handle: str, secret: str) -> tuple[SourceCredentials, dict]:
        client = Client()
        profile = client.login(handle, secret)
        session_string = client.export_session_string()
        creds = SourceCredentials(access_token=session_string)
        meta = {
            "did": profile.did,
            "handle": profile.handle,
            "display_name": getattr(profile, "display_name", None),
            "avatar_url": getattr(profile, "avatar", None),
        }
        return creds, meta

    def _client_from_creds(self, creds: SourceCredentials) -> Client:
        client = Client()
        client.login(session_string=creds.access_token)
        return client

    def recent_self_timeline(
        self,
        creds: SourceCredentials,
        since: datetime,
        max_posts: int,
    ) -> Iterator[SharedPost]:
        client = self._client_from_creds(creds)
        cursor: str | None = None
        seen_uris: set[str] = set()
        yielded = 0

        while yielded < max_posts:
            resp = client.app.bsky.feed.get_timeline(
                {"cursor": cursor, "limit": _PAGE_SIZE}
            )
            feed = resp.feed or []
            if not feed:
                break

            page_had_in_window = False
            for feed_view in feed:
                post = feed_view.post
                record = post.record
                uri = post.uri
                if uri in seen_uris:
                    continue
                seen_uris.add(uri)

                try:
                    created_at = _parse_at_datetime(record.created_at)
                except Exception:
                    continue

                if created_at < since:
                    continue
                page_had_in_window = True

                urls = _urls_from_post(record)
                if not urls:
                    continue

                author = post.author
                yield SharedPost(
                    source=self.name,
                    author_handle=author.handle,
                    author_display_name=getattr(author, "display_name", None),
                    author_avatar_url=getattr(author, "avatar", None),
                    posted_at=created_at,
                    permalink=_permalink(author.handle, uri),
                    post_uri=uri,
                    urls=urls,
                )
                yielded += 1
                if yielded >= max_posts:
                    break

            cursor = resp.cursor
            if not cursor:
                break
            if not page_had_in_window:
                # every post on this page was older than `since` — done
                break


register(BlueskyAdapter())
