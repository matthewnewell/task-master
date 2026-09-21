import os
import sys

os.environ["DATA_DIR"] = os.path.join(os.path.dirname(__file__), "_tmp_data_deleg")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import shutil

import pytest

import depot_client
from app import create_app
from db import db

PROJ = "proj-1"
ALEX, SAM, OUTSIDER = "alex", "sam", "outsider"
PEOPLE = [
    {"id": ALEX, "name": "Alex", "project_ids": [PROJ]},
    {"id": SAM, "name": "Sam", "project_ids": [PROJ]},
    {"id": OUTSIDER, "name": "Out", "project_ids": []},
]


@pytest.fixture()
def client(monkeypatch):
    shutil.rmtree(os.environ["DATA_DIR"], ignore_errors=True)
    notes = []
    monkeypatch.setattr(depot_client, "fetch_people", lambda: PEOPLE)
    monkeypatch.setattr(
        depot_client, "post_project_note", lambda pid, who, body: notes.append((pid, who, body)) or True
    )
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        c.notes = notes
        yield c
    with app.app_context():
        db.session.remove()
    shutil.rmtree(os.environ["DATA_DIR"], ignore_errors=True)


def _task(client, person=ALEX, project=PROJ, title="Order fixtures"):
    body = {"person_id": person, "title": title}
    if project:
        body.update(project_id=project, project_name="Bracket")
    return client.post("/api/tasks", json=body).get_json()


def _delegate(client, t, to=SAM, by=ALEX):
    return client.post(f"/api/tasks/{t['id']}/delegate", json={"by_person_id": by, "to_person_id": to})


def test_delegate_moves_card_as_offer_and_journals(client):
    t = _task(client)
    res = _delegate(client, t)
    assert res.status_code == 200
    d = res.get_json()
    assert d["person_id"] == SAM and d["status"] == "backlog"
    assert d["delegation_state"] == "offered"
    assert d["created_by_id"] == ALEX and d["created_by_name"] == "Alex"
    assert len(client.notes) == 1 and "delegated" in client.notes[0][2] and "Sam" in client.notes[0][2]
    assert client.get(f"/api/tasks?person_id={ALEX}").get_json() == []


def test_delegate_rules(client):
    personal = _task(client, project=None)
    assert _delegate(client, personal).status_code == 400  # no project
    t = _task(client)
    assert _delegate(client, t, to=OUTSIDER).status_code == 400  # not a member
    assert _delegate(client, t, to=ALEX).status_code == 400  # self
    assert _delegate(client, t, by=SAM).status_code == 403  # not the assignee


def test_accept_clears_offer_without_journal(client):
    t = _task(client)
    _delegate(client, t)
    client.notes.clear()
    res = client.post(f"/api/tasks/{t['id']}/respond", json={"person_id": SAM, "accept": True})
    assert res.get_json()["delegation_state"] == "accepted"
    assert client.notes == []


def test_decline_returns_to_creator_and_journals_reason(client):
    t = _task(client)
    _delegate(client, t)
    client.notes.clear()
    res = client.post(
        f"/api/tasks/{t['id']}/respond", json={"person_id": SAM, "accept": False, "reason": "no capacity"}
    )
    d = res.get_json()
    assert d["person_id"] == ALEX and d["delegation_state"] == "declined"
    assert "no capacity" in d["note"]
    assert len(client.notes) == 1 and "declined" in client.notes[0][2] and "no capacity" in client.notes[0][2]


def test_only_assignee_responds_and_only_when_offered(client):
    t = _task(client)
    _delegate(client, t)
    assert client.post(f"/api/tasks/{t['id']}/respond", json={"person_id": ALEX, "accept": True}).status_code == 403
    client.post(f"/api/tasks/{t['id']}/respond", json={"person_id": SAM, "accept": True})
    assert client.post(f"/api/tasks/{t['id']}/respond", json={"person_id": SAM, "accept": True}).status_code == 400


def test_offered_card_cannot_leave_backlog(client):
    t = _task(client)
    _delegate(client, t)
    res = client.put("/api/tasks/reorder", json={"person_id": SAM, "columns": {"doing": [t["id"]]}})
    assert res.status_code == 400


def test_project_view_lists_everyones_cards(client):
    a = _task(client)
    _task(client, person=SAM, title="Other")
    _task(client, project=None, title="Private")
    ids = {x["id"] for x in client.get(f"/api/tasks?project_id={PROJ}").get_json()}
    assert len(ids) == 2 and a["id"] in ids
