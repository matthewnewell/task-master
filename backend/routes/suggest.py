"""
"Suggest backlog items" — the reason Task Master depends on the Depot at all. Gathers real
signals from every app on every project a person has (or is pinned to), via the Depot's own
summary/journal proxies — the same contract Conway's Depot itself calls to render the
Launchpad — and asks the configured AI to turn that into proposed backlog cards with a stated
reason. Nothing here is autonomous: a suggestion lands on the board tagged `ai_suggested`,
same evidence-not-just-a-number-flip posture every other app's AI feature already takes, and a
person decides what happens to it from there (edit, delete, drag it into Todo — or ignore it).
"""

from flask import Blueprint, jsonify, request

import ai_client
import depot_client
from db import db
from models import Task

bp = Blueprint("suggest", __name__, url_prefix="/api/tasks")

# How many projects' worth of app calls to gather context from in one go — a demo persona has
# a handful of projects and a handful of apps each, but this caps the fan-out regardless so a
# person on many projects doesn't turn one click into fifty outbound requests.
_MAX_PROJECTS = 6
_MAX_APPS_PER_PROJECT = 6

_SYSTEM_PROMPT = """You help a program/functional manager keep a personal task backlog current.

You'll be given:
- Their existing backlog (so you don't propose duplicates)
- Their current projects, phases, and role on each
- Live status tiles and recent journal entries from the apps connected to those projects —
  things like a wait-time bottleneck, a slipping gate, a status flip, a bid decision

Propose 0-5 new backlog items grounded ONLY in what's actually in that context — a real
bottleneck, a real status change, a real gap (a project connected to no relevant app, a project
with no recent activity at all). Never invent a project, app, or event that wasn't given to you.
If nothing in the context actually warrants a new task, propose fewer items, or none.

Respond with ONLY this JSON shape:
{"suggestions": [
  {"title": "short, specific, actionable", "note": "one sentence: what you saw and why it matters",
   "project_id": "<id from context, or null>", "project_name": "<name, or null>",
   "application_id": "<id from context, or null>", "application_name": "<name, or null>"}
]}
"""


def _build_context(person: dict, existing_tasks: list[Task]) -> str:
    lines = [f'Person: {person["name"]} ({person.get("title") or "no title on file"})']

    if existing_tasks:
        lines.append("\nExisting backlog (do not duplicate these):")
        for t in existing_tasks:
            lines.append(f"- [{t.status}] {t.title}")
    else:
        lines.append("\nExisting backlog: empty.")

    projects = (person.get("projects") or [])[:_MAX_PROJECTS]
    if not projects:
        lines.append("\nNo projects on file for this person.")
        return "\n".join(lines)

    lines.append("\nProjects and connected-app signals:")
    for proj in projects:
        role = proj.get("role_label") or "Admin"
        lines.append(f'\n"{proj["name"]}" (id {proj["id"]}, phase {proj["phase"]}, role: {role}):')
        app_ids = (proj.get("application_ids") or [])[:_MAX_APPS_PER_PROJECT]
        if not app_ids:
            lines.append("  - no connected apps")
            continue
        for app_id in app_ids:
            summary = depot_client.fetch_app_summary(app_id, proj["id"])
            if summary and summary.get("headline"):
                lines.append(
                    f'  - app {app_id}: {summary["headline"]} — {summary.get("label")} '
                    f'(status: {summary.get("status")})'
                )
            journal = depot_client.fetch_app_journal(app_id, proj["id"]) or []
            for entry in journal[:2]:
                lines.append(f'    recent: {entry.get("summary")}')

    return "\n".join(lines)


@bp.post("/suggest")
def suggest_tasks():
    if not ai_client.is_configured():
        return jsonify({"error": ai_client.NOT_CONFIGURED_MESSAGE}), 200

    body = request.get_json(force=True) or {}
    person_id = body.get("person_id")
    if not person_id:
        return jsonify({"error": "person_id is required"}), 400

    people = depot_client.fetch_people()
    if people is None:
        return jsonify({"error": "Conway's Depot is unreachable — can't gather context without it."}), 200
    person = next((p for p in people if p["id"] == person_id), None)
    if person is None:
        return jsonify({"error": "person_id not found on the Depot"}), 400

    existing = Task.query.filter_by(person_id=person_id).order_by(Task.status, Task.position).all()
    context = _build_context(person, existing)

    result = ai_client.chat_json(
        messages=[{"role": "user", "content": context}],
        system=_SYSTEM_PROMPT,
        max_tokens=1024,
    )
    if "error" in result:
        return jsonify({"error": result["error"]}), 200

    suggestions = result.get("suggestions")
    if not isinstance(suggestions, list):
        return jsonify({"error": "AI reply didn't include a suggestions list."}), 200

    max_pos = (
        db.session.query(db.func.max(Task.position))
        .filter_by(person_id=person_id, status="backlog")
        .scalar()
    )
    next_pos = (max_pos + 1) if max_pos is not None else 0

    created = []
    for i, s in enumerate(suggestions[:5]):
        title = (s.get("title") or "").strip()
        if not title:
            continue
        task = Task(
            person_id=person_id,
            title=title,
            note=(s.get("note") or "").strip() or None,
            status="backlog",
            position=next_pos + i,
            source="ai_suggested",
            project_id=s.get("project_id"),
            project_name=s.get("project_name"),
            application_id=s.get("application_id"),
            application_name=s.get("application_name"),
        )
        db.session.add(task)
        created.append(task)

    db.session.commit()
    return jsonify([t.to_dict() for t in created]), 201
