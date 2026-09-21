"""
Demo boards for the six personas in Conway's Depot's demo story (see that repo's demo_data.py —
the person and project ids below are its fixed ids). Each role gets cards that fit its job, and
two are pending delegation offers from Sam, so the accept/decline flow is on screen the moment
you switch to Alex or Priya.

`apply_demo_cards()` is idempotent (a card is added only if that person has none with the same
title), so it can seed a fresh database and also be re-run against a live one
(backend/refresh_demo.py).
"""

from datetime import datetime, timezone

from db import db
from models import Task

SAM = "e4801aaa-c33c-45e1-aec1-77e8600b5186"
ALEX = "b97db3f6-5cef-43a0-8db0-80d87ec01b2a"
PRIYA = "5b0e3f0a-6c1d-4a52-9d0e-7d2a1c8b4f11"
MARCUS = "8c2d7e14-3f5a-4b96-a1c7-92e5b6d0a3c2"
JESS = "c96051dc-b435-476f-8600-2283a6039df4"

BRACKET = ("ff5bfe0b-7b18-4337-a464-6517c6f6c13b", "Bracket Assembly Program")
NACELLE = ("35fe3413-20e9-4762-8828-029ecade70c2", "Nacelle Fairing Retrofit")
RADAR = ("2a9c5e71-84d3-4f0b-b6a2-c13e7d9f5a08", "Radar Housing Production")
AVIONICS = ("6f1b8d23-0a4e-47c5-8e93-5b7c2a1d9e64", "Avionics Bay Closeout")
RIVERSIDE = ("fee0a151-fc90-42d1-ac74-49525d7d9d8d", "Prospect: Riverside Facility Expansion")
COASTAL = ("d4e7a1b9-5c28-4360-9f1a-e83b0c6d72f5", "Prospect: Coastal Patrol Recompete")

# (person, status, title, note, project, offered_by_sam)
CARDS = [
    (SAM, "doing", "Capacity view for the Radar delivery-acceleration request", "Customer wants earlier deliveries — need machining capacity before we answer.", RADAR, False),
    (ALEX, "backlog", "Staffing plan for Radar Housing machining", "Two engineers for weeks 6–14 — see the Good Plan labor plan.", RADAR, False),
    (ALEX, "backlog", "Confirm CMM fixture design for the radar housing", "Sam's ask — needed before first-article inspection.", RADAR, True),
    (ALEX, "todo", "Stress review on ECO-114", None, BRACKET, False),
    (ALEX, "doing", "Close the two open Bracket ECOs", "Blocking the design bottleneck Value Stream flagged.", BRACKET, False),
    (ALEX, "done", "Bracket design review", None, BRACKET, False),
    (PRIYA, "backlog", "Corrective action draft for the Nacelle lay-up nonconformances", "Root cause is in The Fixer.", NACELLE, False),
    (PRIYA, "backlog", "Attend the Radar CMM program review", "Sam's ask — inspection needs a voice in the room.", RADAR, True),
    (PRIYA, "todo", "Approve the Radar first-article inspection plan", None, RADAR, False),
    (PRIYA, "doing", "KC-1 sampling plan for the Bracket hole pattern", "Acme QA signed off on the approach.", BRACKET, False),
    (PRIYA, "done", "Avionics closeout audit", "Clean — no open corrective actions.", AVIONICS, False),
    (MARCUS, "backlog", "Rebalance Q3 labor across Defense Systems", None, None, False),
    (MARCUS, "todo", "Prepare the Nacelle escalation brief", "Schedule risk for the quarter.", NACELLE, False),
    (MARCUS, "doing", "Portfolio review deck", None, None, False),
    (MARCUS, "done", "Avionics lessons-learned session", None, AVIONICS, False),
    (JESS, "backlog", "Draft the Coastal teaming matrix", "Two sensor vendors in talks.", COASTAL, False),
    (JESS, "todo", "Go/No-Go briefing for Riverside", "Scheduled for the 30th.", RIVERSIDE, False),
    (JESS, "doing", "Coastal RFP compliance matrix", None, COASTAL, False),
    (JESS, "done", "Riverside site walk", None, RIVERSIDE, False),
]


def apply_demo_cards() -> int:
    added = 0
    for person, status, title, note, project, offered in CARDS:
        if Task.query.filter_by(person_id=person, title=title).first() is not None:
            continue
        position = (
            db.session.query(db.func.max(Task.position)).filter_by(person_id=person, status=status).scalar()
        )
        task = Task(
            person_id=person,
            title=title,
            note=note,
            status=status,
            position=(position + 1) if position is not None else 0,
            source="manual",
            project_id=project[0] if project else None,
            project_name=project[1] if project else None,
        )
        if offered:
            task.created_by_id = SAM
            task.created_by_name = "Sam Ortiz"
            task.delegation_state = "offered"
            task.delegated_at = datetime.now(timezone.utc)
        db.session.add(task)
        added += 1
    db.session.commit()
    return added
