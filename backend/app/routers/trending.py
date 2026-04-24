"""Trending endpoints.

`POST /refresh` runs an ingest pass for the current viewer synchronously.
`GET  /trending` groups shares in the window and returns the ranked list,
hydrated with link metadata and sharer profile info.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from ..config import settings
from ..db import get_session
from ..models import Account, Link, RefreshLog, SessionRow, Share
from ..schemas import RefreshResult, Sharer, TrendingLink
from ..services.ingest import run_ingest
from ..services.rank import ShareInput, rank_shares
from ..sources import SourceCredentials, get_adapter

router = APIRouter(tags=["trending"])


def _session_dep():
    s = get_session()
    try:
        yield s
    finally:
        s.close()


def _require_session(session: Session) -> SessionRow:
    row = session.exec(select(SessionRow).order_by(SessionRow.updated_at.desc())).first()
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in.")
    return row


def _domain(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")


@router.post("/refresh", response_model=RefreshResult)
def refresh(session: Session = Depends(_session_dep)) -> RefreshResult:
    sess = _require_session(session)
    adapter = get_adapter(sess.source)
    creds = SourceCredentials(
        access_token=sess.access_jwt,
        refresh_token=sess.refresh_jwt or None,
        extra={"did": sess.did or "", "handle": sess.handle},
    )

    started_at = datetime.utcnow()
    try:
        stats = run_ingest(
            session=session, adapter=adapter, creds=creds, viewer_id=sess.viewer_id
        )
    except Exception as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Ingest failed: {e}") from e
    finished_at = datetime.utcnow()

    return RefreshResult(
        posts_seen=stats.posts_seen,
        urls_found=stats.urls_found,
        links_ranked=stats.links_upserted,
        started_at=started_at,
        finished_at=finished_at,
    )


@router.get("/trending", response_model=list[TrendingLink])
def trending(
    session: Session = Depends(_session_dep),
    hours: int = Query(default=settings.window_hours, ge=1, le=24 * 14),
    limit: int = Query(default=settings.default_trending_limit, ge=1, le=500),
) -> list[TrendingLink]:
    _require_session(session)  # v1: shares are global across viewers (there's only one)

    now = datetime.now(timezone.utc)
    since_naive = (now - timedelta(hours=hours)).replace(tzinfo=None)

    shares = session.exec(
        select(Share).where(Share.posted_at >= since_naive)
    ).all()

    ranked = rank_shares(
        [
            ShareInput(
                canonical_url=s.canonical_url,
                account_id=s.account_id,
                posted_at=s.posted_at if s.posted_at.tzinfo else s.posted_at.replace(tzinfo=timezone.utc),
            )
            for s in shares
        ],
        min_sharers=settings.min_sharers,
        now=now,
    )[:limit]

    # Bulk-load the detail rows we need for the response.
    urls = [r.canonical_url for r in ranked]
    account_ids = {aid for r in ranked for aid in r.account_ids}

    link_rows = (
        {l.canonical_url: l for l in session.exec(select(Link).where(Link.canonical_url.in_(urls))).all()}
        if urls
        else {}
    )
    account_rows = (
        {a.id: a for a in session.exec(select(Account).where(Account.id.in_(account_ids))).all()}
        if account_ids
        else {}
    )

    # Need the actual Share rows (per-link) for permalinks + posted_at per sharer.
    share_rows_by_url: dict[str, list[Share]] = {}
    for s in shares:
        share_rows_by_url.setdefault(s.canonical_url, []).append(s)

    out: list[TrendingLink] = []
    for r in ranked:
        link = link_rows.get(r.canonical_url)
        sharers: list[Sharer] = []
        # Keep the per-account most recent share
        seen: set[str] = set()
        for s in sorted(
            share_rows_by_url.get(r.canonical_url, []),
            key=lambda x: x.posted_at,
            reverse=True,
        ):
            if s.account_id in seen:
                continue
            seen.add(s.account_id)
            acct = account_rows.get(s.account_id)
            sharers.append(
                Sharer(
                    handle=acct.handle if acct else s.account_id.split(":", 1)[-1],
                    display_name=acct.display_name if acct else None,
                    avatar_url=acct.avatar_url if acct else None,
                    post_permalink=s.post_permalink,
                    posted_at=s.posted_at if s.posted_at.tzinfo else s.posted_at.replace(tzinfo=timezone.utc),
                )
            )

        assert r.most_recent_share_at is not None
        out.append(
            TrendingLink(
                canonical_url=r.canonical_url,
                domain=_domain(r.canonical_url),
                title=link.title if link else None,
                description=link.description if link else None,
                image_url=link.image_url if link else None,
                sharer_count=r.sharer_count,
                sharers=sharers,
                most_recent_share_at=r.most_recent_share_at,
                score=r.score,
            )
        )
    return out


@router.get("/last-refresh")
def last_refresh(session: Session = Depends(_session_dep)) -> dict:
    row = session.exec(select(RefreshLog).order_by(RefreshLog.started_at.desc())).first()
    if row is None:
        return {"last_refreshed_at": None}
    return {
        "last_refreshed_at": (row.finished_at or row.started_at).isoformat() + "Z",
        "posts_seen": row.posts_seen,
        "urls_found": row.urls_found,
        "links_ranked": row.links_ranked,
        "error": row.error,
    }
