"""
Task Master: a simple per-person kanban — Backlog / To Do / Doing / Done — with AI-assisted
backlog development. See db.py for the shared migration conventions.

Deliberately NOT its own identity system: `person_id` here is Conway's Depot's own Person id,
taken on faith the same way every id crossing an app boundary in this ecosystem is — a plain
string, no foreign key, no shared database. This is the one sibling app with a *required* live
dependency on the Depot (see lib/depot_client.py): its own persona switcher calls the Depot's
GET /api/people directly rather than keeping a local, unsynced copy of who exists. Every other
app in this ecosystem stays fully standalone; Task Master's whole job is staying aware of a
person's Depot-wide context, so depending on Depot's own source of truth for "who is this and
what do they have" beats inventing a second one that could drift.

Deliberately NOT scoped to one project — that's the point (see the Launchpad's own "Recent
Activity" section, the same federated-fetch idea one level up: an engineering manager on three
projects doesn't want three separate boards). A task MAY carry a project tag (`project_id` +
a frozen `project_name`, same "denormalize the display name so a deleted/renamed project's
history still reads sensibly" pattern Value Stream's MapEvent and WinMax's PursuitEvent both
already use) when it's about one specific project, or carry neither when it's a general task.
"""

from datetime import datetime, timezone

from db import _uuid, db


def _now():
    return datetime.now(timezone.utc)


# The four kanban columns. "Backlog" is explicitly drag-reorderable by priority (the whole
# point of it — a plain unordered pile isn't a backlog); the other three are drag-reorderable
# too, same `position` field, for the ordinary kanban reason (what you're doing right now vs.
# what's next in that column).
STATUSES = ("backlog", "todo", "doing", "done")
STATUS_LABEL = {"backlog": "Backlog", "todo": "To Do", "doing": "Doing", "done": "Done"}

# A card a person typed themselves vs. one the AI proposed from cross-app signals (see
# routes/suggest.py) — surfaced in the UI so a suggested card reads differently until someone
# accepts it onto their own backlog for real, same "AI proposes, a person decides" posture
# every other app's AI feature already takes (WinMax's score notes, Value Stream's chat).
SOURCES = ("manual", "ai_suggested")

# Delegation lifecycle for a project-tagged card handed to someone else. NULL = never delegated.
# An "offered" card sits in the assignee's Backlog until they accept or decline — a delegation is
# an offer, not a command, so it never silently lands in someone's Doing column.
DELEGATION_STATES = ("offered", "accepted", "declined")


class Task(db.Model):
    __tablename__ = "task"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    person_id = db.Column(db.String(36), nullable=False, index=True)
    title = db.Column(db.String(300), nullable=False)
    # Free text — a person's own note, or (for an AI-suggested card) the rationale it proposed
    # this for. One field, not two: a suggested card's "why" IS its note until edited, same as
    # anything else here — there's no separate immutable-rationale column to keep in sync.
    note = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="backlog")
    position = db.Column(db.Integer, nullable=False, default=0)
    source = db.Column(db.String(20), nullable=False, default="manual")

    # Optional tags back to Conway's Depot — plain pointers, never a live link once stored (the
    # same "a link is a pointer, never a live integration" rule the whole ecosystem runs on).
    project_id = db.Column(db.String(36), nullable=True, index=True)
    project_name = db.Column(db.String(200), nullable=True)
    application_id = db.Column(db.String(36), nullable=True)
    application_name = db.Column(db.String(200), nullable=True)

    # Delegation. `person_id` above stays the *assignee* (whose board the card is on); these record
    # who originally created it and where it stands. `created_by_id` NULL = self-created and never
    # delegated. A decline hands the card back to created_by_id; a re-delegation by the assignee
    # changes person_id but keeps created_by_id, so provenance survives a chain of hand-offs.
    created_by_id = db.Column(db.String(36), nullable=True)
    created_by_name = db.Column(db.String(200), nullable=True)
    delegation_state = db.Column(db.String(20), nullable=True)
    delegated_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "person_id": self.person_id,
            "title": self.title,
            "note": self.note,
            "status": self.status,
            "position": self.position,
            "source": self.source,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "application_id": self.application_id,
            "application_name": self.application_name,
            "created_by_id": self.created_by_id,
            "created_by_name": self.created_by_name,
            "delegation_state": self.delegation_state,
            "delegated_at": self.delegated_at.isoformat() if self.delegated_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
