"""Authentication.

Single-viewer local tool for v1. The UI posts handle + app password; we
hand it to the source adapter's `login`, get back durable credentials,
and store a SessionRow keyed by `{source}:{handle}`.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..db import get_session
from ..models import Account, SessionRow
from ..schemas import LoginRequest, Viewer
from ..sources import get_adapter

router = APIRouter(prefix="/auth", tags=["auth"])


def _viewer_id(source: str, handle: str) -> str:
    return f"{source}:{handle}"


def _session_dep():
    s = get_session()
    try:
        yield s
    finally:
        s.close()


def _current_session_row(session: Session) -> SessionRow | None:
    return session.exec(select(SessionRow).order_by(SessionRow.updated_at.desc())).first()


@router.post("/login", response_model=Viewer)
def login(body: LoginRequest, session: Session = Depends(_session_dep)) -> Viewer:
    try:
        adapter = get_adapter(body.source)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    try:
        creds, meta = adapter.login(body.handle, body.app_password)
    except NotImplementedError as e:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(e))
    except Exception as e:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, f"{type(e).__name__}: {e}"
        )

    vid = _viewer_id(body.source, meta.get("handle", body.handle))
    row = session.get(SessionRow, vid)
    if row is None:
        row = SessionRow(
            viewer_id=vid,
            source=body.source,
            handle=meta.get("handle", body.handle),
            access_jwt=creds.access_token,
            refresh_jwt=creds.refresh_token or "",
            did=meta.get("did"),
        )
    else:
        row.access_jwt = creds.access_token
        row.refresh_jwt = creds.refresh_token or ""
        row.did = meta.get("did") or row.did
    row.updated_at = datetime.utcnow()
    session.add(row)

    # Also persist/update an Account row for the viewer so their avatar
    # shows up in the header.
    acct = session.get(Account, vid)
    if acct is None:
        acct = Account(
            id=vid,
            source=body.source,
            handle=meta.get("handle", body.handle),
            display_name=meta.get("display_name"),
            avatar_url=meta.get("avatar_url"),
            updated_at=datetime.utcnow(),
        )
    else:
        acct.display_name = meta.get("display_name") or acct.display_name
        acct.avatar_url = meta.get("avatar_url") or acct.avatar_url
        acct.updated_at = datetime.utcnow()
    session.add(acct)
    session.commit()

    return Viewer(
        viewer_id=vid,
        source=body.source,
        handle=acct.handle,
        display_name=acct.display_name,
        avatar_url=acct.avatar_url,
    )


@router.post("/logout")
def logout(session: Session = Depends(_session_dep)) -> dict:
    row = _current_session_row(session)
    if row is not None:
        session.delete(row)
        session.commit()
    return {"ok": True}


@router.get("/me", response_model=Viewer | None)
def me(session: Session = Depends(_session_dep)) -> Viewer | None:
    row = _current_session_row(session)
    if row is None:
        return None
    acct = session.get(Account, row.viewer_id)
    return Viewer(
        viewer_id=row.viewer_id,
        source=row.source,
        handle=row.handle,
        display_name=acct.display_name if acct else None,
        avatar_url=acct.avatar_url if acct else None,
    )
