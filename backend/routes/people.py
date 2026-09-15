"""
Proxies Conway's Depot's own persona list — see models.py's module docstring for why this app
depends on the Depot directly instead of keeping a local copy. Server-to-server only, same
reason every cross-app call in this ecosystem is (no CORS setup needed across separate repos);
the frontend only ever talks to this app's own backend.
"""

from flask import Blueprint, jsonify

import depot_client

bp = Blueprint("people", __name__, url_prefix="/api")


@bp.get("/people")
def list_people():
    """Mirrors the Depot's own GET /api/people exactly — same shape, straight passthrough. An
    unreachable Depot returns an empty list with a flag the frontend uses to explain why the
    persona switcher is empty, not a 500 — this app is *dependent* on the Depot for identity,
    but it should still say so plainly rather than breaking outright."""
    people = depot_client.fetch_people()
    if people is None:
        return jsonify({"people": [], "depot_reachable": False})
    return jsonify({"people": people, "depot_reachable": True})
