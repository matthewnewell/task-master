import os
import sys

os.environ["DATA_DIR"] = os.path.join(os.path.dirname(__file__), "_tmp_data")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import shutil

import pytest

from app import create_app
from db import db
from seed import SAM_ORTIZ_PERSON_ID


@pytest.fixture()
def client():
    shutil.rmtree(os.environ["DATA_DIR"], ignore_errors=True)
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
    with app.app_context():
        db.session.remove()
    shutil.rmtree(os.environ["DATA_DIR"], ignore_errors=True)


def test_seeded_board(client):
    res = client.get(f"/api/tasks?person_id={SAM_ORTIZ_PERSON_ID}")
    assert res.status_code == 200
    tasks = res.get_json()
    assert len(tasks) == 5
    statuses = {t["status"] for t in tasks}
    assert statuses == {"backlog", "todo", "doing", "done"}


def test_missing_person_id_rejected(client):
    res = client.get("/api/tasks")
    assert res.status_code == 400


def test_create_task_lands_at_end_of_backlog(client):
    res = client.post("/api/tasks", json={"person_id": "someone", "title": "New thing"})
    assert res.status_code == 201
    task = res.get_json()
    assert task["status"] == "backlog"
    assert task["source"] == "manual"


def test_create_task_requires_title(client):
    res = client.post("/api/tasks", json={"person_id": "someone", "title": "  "})
    assert res.status_code == 400


def test_update_task(client):
    created = client.post("/api/tasks", json={"person_id": "someone", "title": "Original"}).get_json()
    res = client.put(f"/api/tasks/{created['id']}", json={"title": "Edited", "note": "why"})
    assert res.status_code == 200
    updated = res.get_json()
    assert updated["title"] == "Edited"
    assert updated["note"] == "why"


def test_delete_task(client):
    created = client.post("/api/tasks", json={"person_id": "someone", "title": "Gone soon"}).get_json()
    res = client.delete(f"/api/tasks/{created['id']}")
    assert res.status_code == 204
    listing = client.get("/api/tasks?person_id=someone").get_json()
    assert all(t["id"] != created["id"] for t in listing)


def test_reorder_moves_between_columns(client):
    a = client.post("/api/tasks", json={"person_id": "p1", "title": "A"}).get_json()
    b = client.post("/api/tasks", json={"person_id": "p1", "title": "B"}).get_json()

    res = client.put(
        "/api/tasks/reorder",
        json={"person_id": "p1", "columns": {"backlog": [b["id"]], "doing": [a["id"]]}},
    )
    assert res.status_code == 200

    listing = {t["id"]: t for t in client.get("/api/tasks?person_id=p1").get_json()}
    assert listing[a["id"]]["status"] == "doing"
    assert listing[b["id"]]["status"] == "backlog"
    assert listing[b["id"]]["position"] == 0


def test_reorder_rejects_tasks_not_owned_by_person(client):
    a = client.post("/api/tasks", json={"person_id": "p1", "title": "A"}).get_json()
    res = client.put(
        "/api/tasks/reorder",
        json={"person_id": "someone-else", "columns": {"backlog": [a["id"]]}},
    )
    assert res.status_code == 400


def test_suggest_reports_ai_not_configured(client):
    # AI_PROVIDER defaults to "none" in this test environment — suggest should say so
    # gracefully (200 with an error field), not 500.
    res = client.post("/api/tasks/suggest", json={"person_id": SAM_ORTIZ_PERSON_ID})
    assert res.status_code == 200
    assert "error" in res.get_json()
