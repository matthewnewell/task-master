import os
import sys

os.environ["DATA_DIR"] = os.path.join(os.path.dirname(__file__), "_tmp_data_summary")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import shutil

import pytest

from app import create_app
from db import db


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


def test_summary_counts_open_cards_for_project(client):
    for title, status in (("A", "backlog"), ("B", "doing"), ("C", "done")):
        t = client.post("/api/tasks", json={"person_id": "p1", "title": title, "project_id": "proj-x"}).get_json()
        client.put("/api/tasks/reorder", json={"person_id": "p1", "columns": {status: [t["id"]]}})
    d = client.get("/api/summary?project_id=proj-x").get_json()
    assert d["headline"] == "2"
    assert "1 in progress" in d["label"]
    assert d["status"] == "ok"


def test_summary_unknown_project_is_quiet(client):
    d = client.get("/api/summary?project_id=nope").get_json()
    assert d["headline"] is None and d["status"] is None
