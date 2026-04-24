"""Ranking tests — pure logic, no I/O."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.rank import ShareInput, rank_shares


def _t(minutes_ago: int) -> datetime:
    return datetime(2026, 4, 24, 12, 0, 0, tzinfo=timezone.utc) - timedelta(minutes=minutes_ago)


NOW = datetime(2026, 4, 24, 12, 0, 0, tzinfo=timezone.utc)


def test_filters_links_below_min_sharers():
    shares = [
        ShareInput("https://a.com/1", "bluesky:alice", _t(5)),
        ShareInput("https://b.com/1", "bluesky:alice", _t(5)),
        ShareInput("https://b.com/1", "bluesky:bob", _t(10)),
    ]
    ranked = rank_shares(shares, min_sharers=2, now=NOW)
    urls = [r.canonical_url for r in ranked]
    assert urls == ["https://b.com/1"]


def test_orders_by_distinct_sharer_count():
    shares = [
        ShareInput("https://a.com/1", "bluesky:alice", _t(5)),
        ShareInput("https://a.com/1", "bluesky:bob", _t(7)),
        ShareInput("https://b.com/1", "bluesky:carol", _t(3)),
        ShareInput("https://b.com/1", "bluesky:dave", _t(3)),
        ShareInput("https://b.com/1", "bluesky:eve", _t(3)),
    ]
    ranked = rank_shares(shares, min_sharers=2, now=NOW)
    assert [r.canonical_url for r in ranked] == [
        "https://b.com/1",  # 3 sharers
        "https://a.com/1",  # 2 sharers
    ]
    assert ranked[0].sharer_count == 3
    assert ranked[1].sharer_count == 2


def test_recency_breaks_ties_in_sharer_count():
    shares = [
        # 2 sharers, most recent 5 min ago
        ShareInput("https://recent.com/1", "bluesky:alice", _t(5)),
        ShareInput("https://recent.com/1", "bluesky:bob", _t(30)),
        # 2 sharers, most recent 60 min ago
        ShareInput("https://stale.com/1", "bluesky:carol", _t(60)),
        ShareInput("https://stale.com/1", "bluesky:dave", _t(90)),
    ]
    ranked = rank_shares(shares, min_sharers=2, now=NOW)
    assert ranked[0].canonical_url == "https://recent.com/1"
    assert ranked[1].canonical_url == "https://stale.com/1"


def test_same_sharer_twice_counts_once():
    shares = [
        ShareInput("https://a.com/1", "bluesky:alice", _t(5)),
        ShareInput("https://a.com/1", "bluesky:alice", _t(10)),  # dup
        ShareInput("https://a.com/1", "bluesky:bob", _t(15)),
    ]
    ranked = rank_shares(shares, min_sharers=2, now=NOW)
    assert len(ranked) == 1
    assert ranked[0].sharer_count == 2
    assert set(ranked[0].account_ids) == {"bluesky:alice", "bluesky:bob"}


def test_empty_input():
    assert rank_shares([], min_sharers=2, now=NOW) == []


def test_handles_naive_datetimes():
    naive_now = datetime(2026, 4, 24, 12, 0, 0)
    shares = [
        ShareInput("https://a.com/1", "bluesky:alice", naive_now - timedelta(minutes=5)),
        ShareInput("https://a.com/1", "bluesky:bob", naive_now - timedelta(minutes=10)),
    ]
    ranked = rank_shares(shares, min_sharers=2, now=NOW)
    assert len(ranked) == 1
