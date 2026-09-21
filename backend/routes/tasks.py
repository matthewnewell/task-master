from flask import Blueprint, jsonify, request

import depot_client
from db import db
from models import STATUSES, Task, _now

bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")


@bp.get("")
def list_tasks():
    project_id = request.args.get("project_id")
    if project_id:
        # The project view: everyone's cards for one project. Ordering is per assignee (each
        # person's own column positions) — there is deliberately no project-wide priority rank.
        tasks = (
            Task.query.filter_by(project_id=project_id)
            .order_by(Task.person_id, Task.status, Task.position)
            .all()
        )
        return jsonify([t.to_dict() for t in tasks])
    person_id = request.args.get("person_id")
    if not person_id:
        return jsonify({"error": "person_id or project_id is required"}), 400
    tasks = (
        Task.query.filter_by(person_id=person_id)
        .order_by(Task.status, Task.position)
        .all()
    )
    return jsonify([t.to_dict() for t in tasks])


@bp.post("")
def create_task():
    """Manual card creation — always lands at the end of Backlog regardless of what the
    caller asks for elsewhere; source is always "manual" here (routes/suggest.py is the only
    path that ever writes "ai_suggested")."""
    body = request.get_json(force=True) or {}
    person_id = body.get("person_id")
    title = (body.get("title") or "").strip()
    if not person_id or not title:
        return jsonify({"error": "person_id and title are required"}), 400

    max_pos = (
        db.session.query(db.func.max(Task.position))
        .filter_by(person_id=person_id, status="backlog")
        .scalar()
    )
    task = Task(
        person_id=person_id,
        title=title,
        note=(body.get("note") or "").strip() or None,
        status="backlog",
        position=(max_pos + 1) if max_pos is not None else 0,
        source="manual",
        project_id=body.get("project_id"),
        project_name=body.get("project_name"),
        application_id=body.get("application_id"),
        application_name=body.get("application_name"),
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@bp.put("/<task_id>")
def update_task(task_id):
    """Edits a card in place — title/note/tags. Not where status or position change (see
    /reorder below, which handles both at once since a drag always implies both)."""
    task = Task.query.get_or_404(task_id)
    body = request.get_json(force=True) or {}
    if "title" in body:
        title = (body["title"] or "").strip()
        if not title:
            return jsonify({"error": "title cannot be empty"}), 400
        task.title = title
    if "note" in body:
        task.note = (body["note"] or "").strip() or None
    if "project_id" in body:
        task.project_id = body["project_id"]
    if "project_name" in body:
        task.project_name = body["project_name"]
    if "application_id" in body:
        task.application_id = body["application_id"]
    if "application_name" in body:
        task.application_name = body["application_name"]
    db.session.commit()
    return jsonify(task.to_dict())


@bp.delete("/<task_id>")
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return "", 204


@bp.put("/reorder")
def reorder_tasks():
    """One drag, one call: the frontend always sends the *whole* board back — every column's
    task ids in their new order — after any drop, whether that drop reordered within a column
    (priority) or moved a card to a different one (status change). Simplest correct model, same
    "replace the whole thing, not a per-item patch" shape Conway's Depot's own PinOrder reorder
    uses. Body: {person_id, columns: {backlog: [id, ...], todo: [...], doing: [...], done: [...]}}.
    Any status missing from the body is left untouched; a task id that doesn't belong to
    person_id is rejected outright rather than silently reassigning someone else's card."""
    body = request.get_json(force=True) or {}
    person_id = body.get("person_id")
    columns = body.get("columns")
    if not person_id or not isinstance(columns, dict):
        return jsonify({"error": "person_id and columns are required"}), 400

    bad_status = [s for s in columns if s not in STATUSES]
    if bad_status:
        return jsonify({"error": f"unknown status in columns: {bad_status}"}), 400

    all_ids = [tid for ids in columns.values() for tid in ids]
    tasks_by_id = {t.id: t for t in Task.query.filter(Task.id.in_(all_ids)).all()}
    not_owned = [tid for tid in all_ids if tasks_by_id.get(tid) is None or tasks_by_id[tid].person_id != person_id]
    if not_owned:
        return jsonify({"error": f"task ids not owned by person_id: {not_owned}"}), 400

    stuck = [
        tid
        for status, ids in columns.items()
        for tid in ids
        if status != "backlog" and tasks_by_id[tid].delegation_state == "offered"
    ]
    if stuck:
        return jsonify({"error": f"accept or decline a delegated task before moving it: {stuck}"}), 400

    for status, ids in columns.items():
        for i, tid in enumerate(ids):
            tasks_by_id[tid].status = status
            tasks_by_id[tid].position = i

    db.session.commit()
    return jsonify([t.to_dict() for t in tasks_by_id.values()])


def _person_lookup():
    """{person_id: person} from the Depot, or None if it's unreachable."""
    people = depot_client.fetch_people()
    if people is None:
        return None
    return {p["id"]: p for p in people}


def _end_of_backlog(person_id):
    max_pos = (
        db.session.query(db.func.max(Task.position))
        .filter_by(person_id=person_id, status="backlog")
        .scalar()
    )
    return (max_pos + 1) if max_pos is not None else 0


@bp.post("/<task_id>/delegate")
def delegate_task(task_id):
    """Hand a project-tagged card to another member of that project. Body: {by_person_id,
    to_person_id}. Only the card's current assignee can delegate it (by_person_id must equal
    person_id). The card moves to the end of the new assignee's Backlog as an *offer* they
    accept or decline (see respond_task). Personal (project-less) cards can't be delegated, so
    there is no way to push private to-dos onto someone. Membership comes from the Depot.
    A Journal entry is posted to the project, best-effort."""
    task = Task.query.get_or_404(task_id)
    body = request.get_json(force=True) or {}
    by_id = body.get("by_person_id")
    to_id = body.get("to_person_id")
    if not by_id or not to_id:
        return jsonify({"error": "by_person_id and to_person_id are required"}), 400
    if by_id != task.person_id:
        return jsonify({"error": "only the current assignee can delegate this task"}), 403
    if to_id == by_id:
        return jsonify({"error": "cannot delegate a task to yourself"}), 400
    if not task.project_id:
        return jsonify({"error": "only tasks tagged with a project can be delegated"}), 400

    people = _person_lookup()
    if people is None:
        return jsonify({"error": "Conway's Depot is unreachable, so project membership can't be checked"}), 503
    assignee = people.get(to_id)
    if not assignee or task.project_id not in (assignee.get("project_ids") or []):
        return jsonify({"error": "that person is not a member of this project"}), 400
    actor = people.get(by_id) or {}

    if not task.created_by_id:
        task.created_by_id = by_id
        task.created_by_name = actor.get("name")
    task.person_id = to_id
    task.status = "backlog"
    task.delegation_state = "offered"
    task.delegated_at = _now()
    task.position = _end_of_backlog(to_id)
    db.session.commit()

    posted = depot_client.post_project_note(
        task.project_id,
        by_id,
        f"{actor.get('name', 'Someone')} delegated \u201c{task.title}\u201d to {assignee['name']}.",
    )
    return jsonify({**task.to_dict(), "journal_posted": posted})


@bp.post("/<task_id>/respond")
def respond_task(task_id):
    """The assignee's answer to an offered card. Body: {person_id, accept, reason?}. Accepting
    just clears the offer (no Journal entry — it's the expected outcome and would only add
    noise). Declining hands the card back to whoever created it and posts a Journal entry
    carrying the reason, since a decline is the signal the project actually needs to see."""
    task = Task.query.get_or_404(task_id)
    body = request.get_json(force=True) or {}
    person_id = body.get("person_id")
    if person_id != task.person_id:
        return jsonify({"error": "only the current assignee can respond to this task"}), 403
    if task.delegation_state != "offered":
        return jsonify({"error": "this task has no pending offer"}), 400

    if body.get("accept"):
        task.delegation_state = "accepted"
        db.session.commit()
        return jsonify({**task.to_dict(), "journal_posted": False})

    creator_id = task.created_by_id
    if not creator_id:
        return jsonify({"error": "this task has no creator to hand it back to"}), 400
    reason = (body.get("reason") or "").strip()
    decliner_name = ((_person_lookup() or {}).get(person_id) or {}).get("name", "Someone")

    task.person_id = creator_id
    task.status = "backlog"
    task.delegation_state = "declined"
    task.position = _end_of_backlog(creator_id)
    if reason:
        task.note = f"Declined by {decliner_name}: {reason}" + (f"\n\n{task.note}" if task.note else "")
    db.session.commit()

    text = f"{decliner_name} declined \u201c{task.title}\u201d"
    if task.created_by_name:
        text += f" (delegated by {task.created_by_name})"
    text += f": {reason}" if reason else "."
    posted = depot_client.post_project_note(task.project_id, person_id, text)
    return jsonify({**task.to_dict(), "journal_posted": posted})
