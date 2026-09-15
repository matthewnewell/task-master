from flask import Blueprint, jsonify, request

from db import db
from models import STATUSES, Task

bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")


@bp.get("")
def list_tasks():
    person_id = request.args.get("person_id")
    if not person_id:
        return jsonify({"error": "person_id is required"}), 400
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

    for status, ids in columns.items():
        for i, tid in enumerate(ids):
            tasks_by_id[tid].status = status
            tasks_by_id[tid].position = i

    db.session.commit()
    return jsonify([t.to_dict() for t in tasks_by_id.values()])
