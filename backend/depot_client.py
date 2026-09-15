"""
A thin, read-only client for Conway's Depot's own API — see models.py's module docstring for
why Task Master depends on it directly instead of keeping a local copy of personas/projects.
Every call here is server-to-server (same reason the Depot's own summary/journal proxies never
hit a sibling app from the browser) and tolerant of the Depot being unreachable: every function
returns `None` on any failure rather than raising, so a caller always has one thing to check.
"""

import os

import httpx

DEPOT_API_URL = os.environ.get("DEPOT_API_URL", "http://localhost:8090").rstrip("/")


def fetch_people() -> list[dict] | None:
    """Every Depot persona, each with its `projects` (id, name, phase, application_ids) — the
    Launchpad's own persona-switcher payload. Task Master's persona switcher renders this
    directly; nothing here is ever cached or copied into Task Master's own database."""
    try:
        r = httpx.get(f"{DEPOT_API_URL}/api/people", timeout=3.0)
        if r.status_code != 200:
            return None
        return r.json()
    except httpx.HTTPError:
        return None


def fetch_app_summary(application_id: str, project_id: str) -> dict | None:
    """One connected app's Launchpad tile for one project — {headline, label, status, href}.
    Same contract the Depot itself renders opaquely; Task Master reads `status` (ok/warn/
    critical) as a raw signal for backlog suggestions and otherwise doesn't interpret it either."""
    try:
        r = httpx.get(
            f"{DEPOT_API_URL}/api/applications/{application_id}/summary",
            params={"project_id": project_id},
            timeout=3.0,
        )
        if r.status_code != 200:
            return None
        return r.json()
    except httpx.HTTPError:
        return None


def fetch_app_journal(application_id: str, project_id: str) -> list[dict] | None:
    """One connected app's recent journal entries for one project — the same feed the
    Launchpad's Recent Activity section merges. Returns the entry list directly (already
    unwrapped from {"entries": [...]})."""
    try:
        r = httpx.get(
            f"{DEPOT_API_URL}/api/applications/{application_id}/journal",
            params={"project_id": project_id},
            timeout=3.0,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        entries = data.get("entries") if isinstance(data, dict) else None
        return entries if isinstance(entries, list) else None
    except httpx.HTTPError:
        return None
