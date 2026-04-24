from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    handle: str
    app_password: str
    source: str = "bluesky"


class Viewer(BaseModel):
    viewer_id: str
    source: str
    handle: str
    display_name: str | None = None
    avatar_url: str | None = None


class RefreshResult(BaseModel):
    posts_seen: int
    urls_found: int
    links_ranked: int
    started_at: datetime
    finished_at: datetime


class Sharer(BaseModel):
    handle: str
    display_name: str | None = None
    avatar_url: str | None = None
    post_permalink: str
    posted_at: datetime


class TrendingLink(BaseModel):
    canonical_url: str
    domain: str
    title: str | None = None
    description: str | None = None
    image_url: str | None = None
    sharer_count: int
    sharers: list[Sharer]
    most_recent_share_at: datetime
    score: float
