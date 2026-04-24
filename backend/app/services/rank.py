"""Rank clustered shares into the Nuzzle-style trending list.

Pure function over a list of share-tuples so it's trivially unit-testable.
Constants are tunable; defaults chosen to prioritise breadth of sharers
over raw recency (that was Nuzzle's whole thing — "X people you follow
shared this" > "someone shared this 3 minutes ago").
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ShareInput:
    canonical_url: str
    account_id: str  # "{source}:{handle}"
    posted_at: datetime


@dataclass
class RankedLink:
    canonical_url: str
    sharer_count: int
    account_ids: list[str] = field(default_factory=list)
    most_recent_share_at: datetime | None = None
    score: float = 0.0


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def rank_shares(
    shares: list[ShareInput],
    *,
    min_sharers: int = 2,
    now: datetime | None = None,
    recency_weight: float = 0.3,
) -> list[RankedLink]:
    """Group by canonical URL, keep distinct sharers, score, and sort.

    score = distinct_sharers + recency_weight * 1 / (1 + hours_since_last)
    Filter: distinct_sharers >= min_sharers.
    Order: score desc, then most_recent_share_at desc as tiebreaker.
    """
    now = now or _now_utc()

    by_url: dict[str, RankedLink] = {}
    for s in shares:
        rec = by_url.setdefault(
            s.canonical_url, RankedLink(canonical_url=s.canonical_url, sharer_count=0)
        )
        if s.account_id in rec.account_ids:
            # Same sharer again (e.g. they reposted themselves) — doesn't count.
            # Still track the most recent timestamp.
            pass
        else:
            rec.account_ids.append(s.account_id)
            rec.sharer_count += 1

        posted = s.posted_at if s.posted_at.tzinfo else s.posted_at.replace(tzinfo=timezone.utc)
        if rec.most_recent_share_at is None or posted > rec.most_recent_share_at:
            rec.most_recent_share_at = posted

    ranked: list[RankedLink] = []
    for rec in by_url.values():
        if rec.sharer_count < min_sharers:
            continue
        assert rec.most_recent_share_at is not None
        hours = max(0.0, (now - rec.most_recent_share_at).total_seconds() / 3600.0)
        rec.score = rec.sharer_count + recency_weight * (1.0 / (1.0 + hours))
        ranked.append(rec)

    ranked.sort(
        key=lambda r: (r.score, r.most_recent_share_at or datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True,
    )
    return ranked
