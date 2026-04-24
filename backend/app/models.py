from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint


class Account(SQLModel, table=True):
    """A post author we've seen. Keyed by `{source}:{handle}` so different
    networks can coexist without collision (e.g. `bluesky:alice.bsky.social`).
    """

    id: str = Field(primary_key=True)
    source: str = Field(index=True)
    handle: str
    display_name: str | None = None
    avatar_url: str | None = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Link(SQLModel, table=True):
    """A canonicalized URL. Metadata is backfilled lazily by metadata.py."""

    canonical_url: str = Field(primary_key=True)
    title: str | None = None
    description: str | None = None
    image_url: str | None = None
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)


class Share(SQLModel, table=True):
    """One (link, sharer) pair. Unique on `(canonical_url, account_id)` so
    repeated shares by the same account collapse to one row."""

    __table_args__ = (
        UniqueConstraint("canonical_url", "account_id", name="uq_share_link_account"),
    )

    id: int | None = Field(default=None, primary_key=True)
    canonical_url: str = Field(foreign_key="link.canonical_url", index=True)
    account_id: str = Field(foreign_key="account.id", index=True)
    post_uri: str
    post_permalink: str
    posted_at: datetime = Field(index=True)


class SessionRow(SQLModel, table=True):
    """Stored auth for a single local viewer. For v1 (personal/local), the
    app password and refresh JWT live here unencrypted. Do not deploy
    multi-user without moving these into a real secret store."""

    __tablename__ = "session"

    viewer_id: str = Field(primary_key=True)  # e.g. "bluesky:alice.bsky.social"
    source: str
    handle: str
    access_jwt: str
    refresh_jwt: str
    did: str | None = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RefreshLog(SQLModel, table=True):
    """Bookkeeping for the UI's 'last refreshed' indicator."""

    id: int | None = Field(default=None, primary_key=True)
    viewer_id: str = Field(index=True)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None
    posts_seen: int = 0
    urls_found: int = 0
    links_ranked: int = 0
    error: str | None = None
