"""
Demo seed — a starter board for Sam Ortiz (Program Manager on two of Conway's Depot's own
demo projects, id fixed to match the Depot's own seeded persona so this actually demonstrates
something real if you switch to her there too — see conways-depot/backend/seed.py's
_DEMO_PEOPLE). A fresh person with no seeded tasks just gets an empty board, which is a normal
state here, not a bug — see AI_ASSIST doc comments in routes/suggest.py for how it fills in.
"""

from db import db
from models import Task

# Matches Conway's Depot's own seeded "Sam Ortiz" persona id exactly (not derived — a plain
# copied constant, the same kind of drift-risk every cross-app pointer in this ecosystem
# accepts; see conways-depot's own VALUE_STREAM_DEMO_MAP_ID comment for the precedent).
SAM_ORTIZ_PERSON_ID = "e4801aaa-c33c-45e1-aec1-77e8600b5186"
BRACKET_PROJECT_ID = "ff5bfe0b-7b18-4337-a464-6517c6f6c13b"


def seed_if_empty():
    if Task.query.count() > 0:
        return

    tasks = [
        Task(
            person_id=SAM_ORTIZ_PERSON_ID,
            title="Review long-lead casting supplier schedule",
            note="Value Stream flagged this as the critical-path bottleneck on Bracket Assembly.",
            status="backlog",
            position=0,
            source="manual",
            project_id=BRACKET_PROJECT_ID,
            project_name="Bracket Assembly Project",
        ),
        Task(
            person_id=SAM_ORTIZ_PERSON_ID,
            title="Confirm Nacelle Fairing staffing for next sprint",
            status="backlog",
            position=1,
            source="manual",
        ),
        Task(
            person_id=SAM_ORTIZ_PERSON_ID,
            title="Draft kickoff agenda for Riverside pursuit",
            status="todo",
            position=0,
            source="manual",
        ),
        Task(
            person_id=SAM_ORTIZ_PERSON_ID,
            title="Weekly program status rollup",
            status="doing",
            position=0,
            source="manual",
        ),
        Task(
            person_id=SAM_ORTIZ_PERSON_ID,
            title="Bracket Assembly kickoff",
            status="done",
            position=0,
            source="manual",
            project_id=BRACKET_PROJECT_ID,
            project_name="Bracket Assembly Project",
        ),
    ]
    db.session.add_all(tasks)
    db.session.commit()

    from demo_cards import apply_demo_cards

    apply_demo_cards()
