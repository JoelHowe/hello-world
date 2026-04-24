# Nuzzle Clone

A web app that surfaces URLs shared by multiple accounts you follow in the
last 24 hours — inspired by [Nuzzle](https://en.wikipedia.org/wiki/Nuzzel)
(2014–2020).

Nuzzle was built during an era of free/open Twitter API access. That era is
over — X's API costs $200–$5,000/month. This clone targets **Bluesky** first
(free, open AT Protocol) and is architected so an X adapter can be plugged
in later if budget appears.

## Status

**v1 — local dev / personal use.**
- Signed-in user's own follow graph (Bluesky home timeline) only.
- SQLite on disk, app-password auth, on-demand refresh.
- No hosting, no email digests, no multi-user.

Planned for v2: arbitrary-user mode ("peek into someone else's corner"),
email digest, X adapter, OAuth.

## Quick start

Requirements: Python 3.11+, Node 20+.

```bash
make install     # sets up backend venv + frontend node_modules
make dev         # starts backend on :8000 and frontend on :5173
```

Open <http://localhost:5173>.

### First login

1. Go to <https://bsky.app/settings/app-passwords> and generate a new app
   password (name it "nuzzle-clone"). **Do not reuse your main password.**
2. In the web UI, enter your Bluesky handle (e.g. `alice.bsky.social`) and
   paste the app password.
3. Click **Refresh**. The backend paginates your last 24h of timeline,
   extracts URLs, expands known shorteners, clusters by canonical URL, and
   returns the ranked list.

### Refresh from the CLI

```bash
make ingest
```

Useful if you want to run the pass from cron.

## Repo layout

```
backend/    FastAPI + SQLite + atproto SDK
frontend/   Vite + React + TypeScript
Makefile    dev / test / ingest entrypoints
```

See [backend/README](./backend/) internals and
[the plan](./docs/) (if committed) for design rationale.

## Testing

```bash
make test
```

Covers URL canonicalization (tracking-param stripping, shortener expansion,
idempotency) and the ranking function.

## Security note

App passwords are stored in the local SQLite database unencrypted. This is
acceptable for a personal/local tool but **do not** deploy this as-is for
other users — sessions should move to a proper secrets store and the login
flow should use Bluesky OAuth (not yet widely rolled out at time of
writing).
