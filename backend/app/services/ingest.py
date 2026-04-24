"""Orchestrates a single refresh pass: pull timeline → extract URLs →
canonicalize → upsert Accounts/Links/Shares → backfill metadata for new
links. Source-agnostic; takes a `SourceAdapter` injected by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

import httpx
from sqlmodel import Session, select

from ..config import settings
from ..models import Account, Link, RefreshLog, Share
from ..sources import SharedPost, SourceAdapter, SourceCredentials
from .metadata import fetch_metadata
from .url_canonicalize import (
    canonicalize,
    domain_of,
    expand_and_canonicalize,
    new_expand_cache,
)


@dataclass
class IngestStats:
    posts_seen: int = 0
    urls_found: int = 0
    links_upserted: int = 0
    shares_upserted: int = 0


def _account_id(source: str, handle: str) -> str:
    return f"{source}:{handle}"


def _upsert_account(session: Session, post: SharedPost) -> Account:
    aid = _account_id(post.source, post.author_handle)
    row = session.get(Account, aid)
    if row is None:
        row = Account(
            id=aid,
            source=post.source,
            handle=post.author_handle,
            display_name=post.author_display_name,
            avatar_url=post.author_avatar_url,
            updated_at=datetime.utcnow(),
        )
        session.add(row)
    else:
        row.display_name = post.author_display_name or row.display_name
        row.avatar_url = post.author_avatar_url or row.avatar_url
        row.updated_at = datetime.utcnow()
    return row


def _upsert_link(session: Session, canonical_url: str) -> tuple[Link, bool]:
    row = session.get(Link, canonical_url)
    if row is None:
        row = Link(canonical_url=canonical_url, first_seen_at=datetime.utcnow())
        session.add(row)
        return row, True
    return row, False


def _upsert_share(
    session: Session,
    canonical_url: str,
    account_id: str,
    post_uri: str,
    post_permalink: str,
    posted_at: datetime,
) -> bool:
    existing = session.exec(
        select(Share).where(
            Share.canonical_url == canonical_url,
            Share.account_id == account_id,
        )
    ).first()
    if existing is not None:
        # Keep the earliest post_uri/permalink for stability.
        return False
    session.add(
        Share(
            canonical_url=canonical_url,
            account_id=account_id,
            post_uri=post_uri,
            post_permalink=post_permalink,
            posted_at=posted_at,
        )
    )
    return True


def _backfill_metadata(session: Session, urls: Iterable[str], client: httpx.Client) -> None:
    for url in urls:
        link = session.get(Link, url)
        if link is None or link.title:
            continue
        meta = fetch_metadata(url, client)
        link.title = meta.title
        link.description = meta.description
        link.image_url = meta.image_url


def run_ingest(
    *,
    session: Session,
    adapter: SourceAdapter,
    creds: SourceCredentials,
    viewer_id: str,
    now: datetime | None = None,
) -> IngestStats:
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(hours=settings.window_hours)

    log = RefreshLog(viewer_id=viewer_id, started_at=datetime.utcnow())
    session.add(log)
    session.commit()

    stats = IngestStats()
    new_canonical_urls: set[str] = set()
    expand_cache = new_expand_cache()

    try:
        with httpx.Client(http2=False, timeout=10.0) as http:
            posts = adapter.recent_self_timeline(
                creds, since=since, max_posts=settings.max_posts_per_refresh
            )
            for post in posts:
                stats.posts_seen += 1
                _upsert_account(session, post)

                for raw_url in post.urls:
                    stats.urls_found += 1
                    # Cheap pass first; only hit the network for known shorteners.
                    fast = canonicalize(raw_url)
                    if domain_of(fast) in _SHORTENER_HINT_HOSTS:
                        final_url = expand_and_canonicalize(raw_url, http, expand_cache)
                    else:
                        final_url = fast

                    _, is_new = _upsert_link(session, final_url)
                    if is_new:
                        stats.links_upserted += 1
                        new_canonical_urls.add(final_url)

                    if _upsert_share(
                        session,
                        canonical_url=final_url,
                        account_id=_account_id(post.source, post.author_handle),
                        post_uri=post.post_uri,
                        post_permalink=post.permalink,
                        posted_at=post.posted_at,
                    ):
                        stats.shares_upserted += 1

                # Commit in chunks so a crash mid-run doesn't lose everything.
                if stats.posts_seen % 100 == 0:
                    session.commit()

            session.commit()
            _backfill_metadata(session, new_canonical_urls, http)
            session.commit()

        log.finished_at = datetime.utcnow()
        log.posts_seen = stats.posts_seen
        log.urls_found = stats.urls_found
        log.links_ranked = stats.links_upserted
        session.add(log)
        session.commit()
    except Exception as e:
        log.finished_at = datetime.utcnow()
        log.error = f"{type(e).__name__}: {e}"
        session.add(log)
        session.commit()
        raise

    return stats


# Local import to avoid cycle and keep config close to canonicalize.
from .url_canonicalize import _KNOWN_SHORTENERS as _SHORTENER_HINT_HOSTS  # noqa: E402
