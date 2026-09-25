"""
The Launchpad's app-summary contract for Task Master (see Conway's Depot's routes/applications.py
for the proxy; it renders `headline`/`label`/`status` opaquely). `project_id` is the Depot's own
project id — Task Master cards carry it directly.

Headline is the project's open cards (everything not Done); the label says how many are being
worked and how many delegated offers are still waiting on an answer, which is the one thing worth
turning the tile yellow for. `person_id` (optional, a Depot person id) narrows it to that
person's own board: the Launchpad's pinned tile sends it, so it matches what they see when they
open Task Master. With neither, it's the same numbers across every card.
"""

import os

from flask import Blueprint, jsonify, request

from models import Task

bp = Blueprint("summary", __name__, url_prefix="/api")

FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost:5186")


@bp.get("/summary")
def summary():
    project_id = request.args.get("project_id")
    person_id = request.args.get("person_id")
    query = Task.query.filter(Task.status != "done")
    if project_id:
        query = query.filter_by(project_id=project_id)
    if person_id:
        query = query.filter_by(person_id=person_id)
    tasks = query.all()

    if project_id and not tasks:
        has_any = Task.query.filter_by(project_id=project_id).first() is not None
        return jsonify({
            "headline": None,
            "label": "Nothing open" if has_any else "No cards tagged to this project yet",
            "status": None,
            "href": f"{FRONTEND_BASE_URL}/?board={project_id}",
        })

    doing = sum(1 for t in tasks if t.status == "doing")
    offered = sum(1 for t in tasks if t.delegation_state == "offered")
    label = f"open · {doing} in progress"
    if offered:
        label += f" · {offered} awaiting response"

    return jsonify({
        "headline": str(len(tasks)),
        "label": label,
        "status": "warn" if offered else "ok",
        "href": (
            f"{FRONTEND_BASE_URL}/?board={project_id}" if project_id
            else f"{FRONTEND_BASE_URL}/?person_id={person_id}" if person_id
            else f"{FRONTEND_BASE_URL}/"
        ),
    })
