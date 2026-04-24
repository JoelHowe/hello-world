"""CLI entrypoint for running ingestion outside the HTTP server.

Usage:
    python -m app.cli ingest
"""

from __future__ import annotations

import sys

from sqlmodel import select

from .db import get_session, init_db
from .models import SessionRow
from .services.ingest import run_ingest
from .sources import SourceCredentials, get_adapter


def _cmd_ingest() -> int:
    init_db()
    with get_session() as session:
        row = session.exec(select(SessionRow).order_by(SessionRow.updated_at.desc())).first()
        if row is None:
            print("No active session. Log in from the web UI first.", file=sys.stderr)
            return 2

        adapter = get_adapter(row.source)
        creds = SourceCredentials(
            access_token=row.access_jwt,
            refresh_token=row.refresh_jwt or None,
            extra={"did": row.did or "", "handle": row.handle},
        )
        stats = run_ingest(
            session=session, adapter=adapter, creds=creds, viewer_id=row.viewer_id
        )
        print(
            f"Done. posts={stats.posts_seen} urls={stats.urls_found} "
            f"new_links={stats.links_upserted} shares={stats.shares_upserted}"
        )
    return 0


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] == "--help":
        print(__doc__)
        return 0
    cmd = sys.argv[1]
    if cmd == "ingest":
        return _cmd_ingest()
    print(f"Unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
