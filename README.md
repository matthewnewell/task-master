# Task Master

A personal kanban — Backlog, To Do, Doing, Done — for someone supporting more than one
project at once. One board, not one board per project. An AI assistant can develop the
backlog for you, reading real signals from Conway's Depot instead of guessing.

## The idea

**One person's whole picture, not one project's.** A functional or portfolio manager on three
projects doesn't want three separate task boards to check — the same "same list, shown twice"
problem Conway's Depot's own Launchpad ran into and fixed by merging its Pinned Apps and Recent
Activity into one view. Task Master's board is per-*person*, spanning every project and pinned
app they have.

**Grounded suggestions, not guesses.** "✨ Suggest backlog items" gathers real context through
the Depot's own app-summary and journal contracts — a status tile gone critical on one project,
a wait-time bottleneck flagged by Value Stream, a recent WinMax gate decision — and asks the
configured AI to propose backlog cards with a stated reason, never an invented project or
event. A suggested card lands on the backlog clearly marked `✨ Suggested`; nothing moves
itself to Doing. Same "AI proposes, a person decides" posture every sibling app's AI feature
already takes.

**The one sibling app with a required live dependency on Conway's Depot.** Every other app in
this ecosystem is fully standalone, linked from the Depot only by a stored pointer. Task
Master's own persona switcher calls the Depot's `GET /api/people` directly — see
`backend/depot_client.py` and `backend/models.py`'s module docstring for why: its whole job is
staying aware of a person's Depot-wide context, so it depends on the Depot's own source of
truth for "who is this and what do they have" rather than keeping a second, unsynced copy.

## Run it

Backend:

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python app.py          # :8100
```

Frontend:

```bash
cd frontend
npm install
npm run dev                      # :5186, proxies /api to :8100
```

Needs Conway's Depot running on `:8090` (override with `DEPOT_API_URL`) for identity and for
backlog suggestions to have anything to read. The board itself (viewing, adding, editing,
dragging tasks) still works if the Depot is briefly down for anyone whose persona was already
loaded — only the switcher and "Suggest" need it live.

## AI (optional)

Off by default. Set in `backend/.env` or the environment:

```
AI_PROVIDER=claude   # or "gemini", "ollama"
AI_API_KEY=...        # Claude / Gemini
AI_MODEL=...           # optional override
```

Same `ai_client.py` every sibling app uses — Claude, Gemini (cloud), or Ollama (on-prem).

## Data model

`Task` — `person_id` (a Depot persona id, taken on faith, no shared database), `title`, `note`,
`status` (`backlog | todo | doing | done`), `position` (drag order within its column), `source`
(`manual | ai_suggested`), and an optional `project_id`/`project_name` + `application_id`/
`application_name` pointer pair — plain text, frozen at creation time, never a live link.

No journal here (yet) — every other sibling app's journal is scoped to one *project*; Task
Master's own activity is scoped to one *person*, a genuine mismatch with how the Depot's
project-level Journal aggregation works today. A per-person journal could follow the same
federated pattern later if it turns out to matter.

## Tests

```bash
cd backend && .venv/bin/python -m pytest -q
```
