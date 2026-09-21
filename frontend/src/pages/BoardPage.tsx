import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  useCreateTask,
  useDelegateTask,
  useDeleteTask,
  useProjectTasks,
  useReorderTasks,
  useRespondTask,
  useTasks,
  useUpdateTask,
} from '../api/hooks'
import { STATUS_LABEL, STATUSES, type Task, type TaskStatus } from '../api/types'
import { usePersona } from '../lib/persona'
import './BoardPage.css'

type Columns = Record<TaskStatus, string[]>

function emptyColumns(): Columns {
  return { backlog: [], todo: [], doing: [], done: [] }
}

/** The board — four columns, drag-reorderable within and between them (same native HTML5 DnD
 * pattern the Launchpad's own Pinned Apps grid uses, no library). One drag always sends the
 * *whole* board back in one call (see useReorderTasks) — simplest correct model for "this also
 * changed which column it's in," which a plain within-column reorder never has to handle but a
 * kanban always does. */
export default function BoardPage() {
  const { persona, isLoading: personaLoading, depotReachable } = usePersona()
  const { data: tasks, isLoading: tasksLoading } = useTasks(persona?.id)
  const createTask = useCreateTask(persona?.id)
  const updateTask = useUpdateTask(persona?.id)
  const deleteTask = useDeleteTask(persona?.id)
  const reorderTasks = useReorderTasks(persona?.id)
  const delegateTask = useDelegateTask(persona?.id)
  const respondTask = useRespondTask(persona?.id)
  const [params] = useSearchParams()
  const boardProject = (persona?.projects ?? []).find((p) => p.id === params.get('board'))

  const tasksById = useMemo(() => new Map((tasks ?? []).map((t) => [t.id, t])), [tasks])

  const serverColumns = useMemo(() => {
    const cols = emptyColumns()
    for (const t of tasks ?? []) cols[t.status].push(t.id)
    return cols
  }, [tasks])

  // A local override that survives exactly as long as a reorder's server round-trip takes —
  // same reasoning as the Launchpad's Pinned Apps grid. Reset whenever the underlying *set* of
  // task ids changes (a create, delete, or AI suggestion) so it can never go stale; a pure drag
  // (this component's own doing) never changes that set, only which column an id sits in.
  const [localColumns, setLocalColumns] = useState<Columns | null>(null)
  const serverIdSet = (tasks ?? [])
    .map((t) => t.id)
    .sort()
    .join(',')
  useEffect(() => {
    setLocalColumns(null)
  }, [serverIdSet])

  const columns = localColumns ?? serverColumns

  const [dragId, setDragId] = useState<string | null>(null)
  const [addingTo, setAddingTo] = useState<TaskStatus | null>(null)

  function handleDrop(targetStatus: TaskStatus, targetId: string | null) {
    const id = dragId
    setDragId(null)
    if (!id) return

    const next: Columns = {
      backlog: [...columns.backlog],
      todo: [...columns.todo],
      doing: [...columns.doing],
      done: [...columns.done],
    }
    for (const s of STATUSES) {
      const idx = next[s].indexOf(id)
      if (idx !== -1) next[s].splice(idx, 1)
    }
    const list = next[targetStatus]
    const insertAt = targetId ? list.indexOf(targetId) : -1
    list.splice(insertAt === -1 ? list.length : insertAt, 0, id)

    setLocalColumns(next)
    reorderTasks.mutate(next)
  }

  if (personaLoading) {
    return <div className="board-page__loading">Loading…</div>
  }

  if (!depotReachable) {
    return (
      <div className="board-page__loading">
        Conway's Depot is unreachable — Task Master needs it to know who you are. Start the
        Depot and reload.
      </div>
    )
  }

  if (!persona) {
    return <div className="board-page__loading">No persona to view as yet.</div>
  }

  if (boardProject) {
    return <ProjectBoard projectId={boardProject.id} projectName={boardProject.name} />
  }

  const projects = persona.projects.map((p) => ({ id: p.id, name: p.name }))

  return (
    <div className="board-page">
      {delegateTask.error && <p className="board-page__suggest-error">{delegateTask.error.message}</p>}
      {respondTask.error && <p className="board-page__suggest-error">{respondTask.error.message}</p>}
      {tasksLoading ? (
        <div className="board-page__loading">Loading board…</div>
      ) : (
        <div className="board-columns">
          {STATUSES.map((status) => (
            <div
              key={status}
              className="board-column"
              onDragOver={(e) => {
                e.preventDefault()
                e.dataTransfer.dropEffect = 'move'
              }}
              onDrop={(e) => {
                e.preventDefault()
                handleDrop(status, null)
              }}
            >
              <div className="board-column__head">
                <span className="board-column__title">{STATUS_LABEL[status]}</span>
                <span className="board-column__count">{columns[status].length}</span>
              </div>

              <div className="board-column__cards">
                {columns[status].map((id) => {
                  const task = tasksById.get(id)
                  if (!task) return null
                  return (
                    <TaskCard
                      key={id}
                      task={task}
                      dragging={dragId === id}
                      onDragStart={() => setDragId(id)}
                      onDragEnd={() => setDragId(null)}
                      onDropOn={() => handleDrop(status, id)}
                      projects={projects}
                      onSave={(data) => updateTask.mutate({ id, ...data })}
                      onDelete={() => deleteTask.mutate(id)}
                      onDelegate={(toPersonId) => delegateTask.mutate({ id, toPersonId })}
                      onRespond={(accept, reason) => respondTask.mutate({ id, accept, reason })}
                    />
                  )
                })}
              </div>

              {status === 'backlog' &&
                (addingTo === 'backlog' ? (
                  <AddTaskForm
                    projects={projects}
                    onCancel={() => setAddingTo(null)}
                    onSave={(data) => {
                      createTask.mutate(data)
                      setAddingTo(null)
                    }}
                  />
                ) : (
                  <button className="board-column__add" onClick={() => setAddingTo('backlog')}>
                    + Add task
                  </button>
                ))}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

type ProjectOption = { id: string; name: string }
type SaveData = { title: string; note?: string; project_id?: string | null; project_name?: string | null }

function ProjectSelect({
  projects,
  value,
  onChange,
}: {
  projects: ProjectOption[]
  value: string
  onChange: (id: string) => void
}) {
  return (
    <select className="task-form__project" value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">Personal (no project)</option>
      {projects.map((p) => (
        <option key={p.id} value={p.id}>
          {p.name}
        </option>
      ))}
    </select>
  )
}

function AddTaskForm({
  projects,
  onSave,
  onCancel,
}: {
  projects: ProjectOption[]
  onSave: (data: SaveData) => void
  onCancel: () => void
}) {
  const [title, setTitle] = useState('')
  const [note, setNote] = useState('')
  const [projectId, setProjectId] = useState('')

  function save() {
    const t = title.trim()
    if (!t) return
    onSave({
      title: t,
      note: note.trim() || undefined,
      project_id: projectId || null,
      project_name: projects.find((p) => p.id === projectId)?.name ?? null,
    })
  }

  return (
    <div className="task-form">
      <input
        className="task-form__title"
        placeholder="Task title"
        value={title}
        autoFocus
        onChange={(e) => setTitle(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            save()
          }
          if (e.key === 'Escape') onCancel()
        }}
      />
      <textarea
        className="task-form__note"
        placeholder="Note (optional)"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        rows={2}
      />
      <ProjectSelect projects={projects} value={projectId} onChange={setProjectId} />
      <div className="task-form__actions">
        <button className="tm-btn tm-btn--primary" disabled={!title.trim()} onClick={save}>
          Add
        </button>
        <button className="tm-btn tm-btn--ghost" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  )
}

function TaskCard({
  task,
  dragging,
  onDragStart,
  onDragEnd,
  onDropOn,
  projects,
  onSave,
  onDelete,
  onDelegate,
  onRespond,
}: {
  task: Task
  dragging: boolean
  onDragStart: () => void
  onDragEnd: () => void
  onDropOn: () => void
  projects: ProjectOption[]
  onSave: (data: SaveData) => void
  onDelete: () => void
  onDelegate: (toPersonId: string) => void
  onRespond: (accept: boolean, reason?: string) => void
}) {
  const { persona, people } = usePersona()
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(task.title)
  const [note, setNote] = useState(task.note ?? '')
  const [projectId, setProjectId] = useState(task.project_id ?? '')
  const [delegating, setDelegating] = useState(false)
  const [toPerson, setToPerson] = useState('')
  const [declining, setDeclining] = useState(false)
  const [reason, setReason] = useState('')

  const offered = task.delegation_state === 'offered'
  const members = people.filter(
    (p) => p.id !== persona?.id && !p.is_admin && !!task.project_id && p.project_ids.includes(task.project_id),
  )
  const delegatedBy =
    task.created_by_id && task.created_by_id !== persona?.id ? task.created_by_name : null

  function startEdit() {
    setTitle(task.title)
    setNote(task.note ?? '')
    setProjectId(task.project_id ?? '')
    setEditing(true)
  }

  function save() {
    const t = title.trim()
    if (!t) return
    onSave({
      title: t,
      note: note.trim() || undefined,
      project_id: projectId || null,
      project_name: projects.find((p) => p.id === projectId)?.name ?? null,
    })
    setEditing(false)
  }

  if (editing) {
    return (
      <div className="task-form">
        <input
          className="task-form__title"
          value={title}
          autoFocus
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          className="task-form__note"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={2}
        />
        <ProjectSelect projects={projects} value={projectId} onChange={setProjectId} />
        <div className="task-form__actions">
          <button className="tm-btn tm-btn--primary" disabled={!title.trim()} onClick={save}>
            Save
          </button>
          <button className="tm-btn tm-btn--ghost" onClick={() => setEditing(false)}>
            Cancel
          </button>
        </div>
      </div>
    )
  }

  return (
    <div
      className={`task-card ${dragging ? 'task-card--dragging' : ''} ${task.source === 'ai_suggested' ? 'task-card--suggested' : ''}`}
      draggable={!offered}
      onDragStart={(e) => {
        // Firefox won't start a drag without data on the transfer; Chromium doesn't care.
        e.dataTransfer.effectAllowed = 'move'
        e.dataTransfer.setData('text/plain', task.id)
        onDragStart()
      }}
      onDragEnd={onDragEnd}
      onDragOver={(e) => {
        e.preventDefault()
        e.stopPropagation()
        e.dataTransfer.dropEffect = 'move'
      }}
      onDrop={(e) => {
        e.preventDefault()
        e.stopPropagation()
        onDropOn()
      }}
      title={offered ? 'Accept or decline to move this card' : 'Drag to reorder or move'}
    >
      {offered && (
        <span className="task-card__badge task-card__badge--offer">
          Offered{delegatedBy ? ` by ${delegatedBy}` : ''}
        </span>
      )}
      {!offered && delegatedBy && task.delegation_state === 'accepted' && (
        <span className="task-card__badge task-card__badge--from">From {delegatedBy}</span>
      )}
      {task.delegation_state === 'declined' && (
        <span className="task-card__badge task-card__badge--declined">Declined</span>
      )}
      {task.source === 'ai_suggested' && <span className="task-card__badge">✨ Suggested</span>}
      <p className="task-card__title">{task.title}</p>
      {task.note && <p className="task-card__note">{task.note}</p>}
      {task.project_name && <span className="task-card__tag">{task.project_name}</span>}
      {offered && !declining && (
        <div className="task-card__actions">
          <button className="tm-btn tm-btn--primary task-card__respond" onClick={() => onRespond(true)}>
            Accept
          </button>
          <button className="tm-btn tm-btn--ghost task-card__respond" onClick={() => setDeclining(true)}>
            Decline
          </button>
        </div>
      )}
      {offered && declining && (
        <div className="task-card__inline">
          <input
            className="task-form__title"
            placeholder="Reason (optional)"
            value={reason}
            autoFocus
            onChange={(e) => setReason(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && onRespond(false, reason)}
          />
          <div className="task-form__actions">
            <button className="tm-btn tm-btn--primary" onClick={() => onRespond(false, reason)}>
              Decline
            </button>
            <button className="tm-btn tm-btn--ghost" onClick={() => setDeclining(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}
      {delegating && (
        <div className="task-card__inline">
          <select className="task-form__project" value={toPerson} onChange={(e) => setToPerson(e.target.value)}>
            <option value="">Delegate to…</option>
            {members.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
          <div className="task-form__actions">
            <button
              className="tm-btn tm-btn--primary"
              disabled={!toPerson}
              onClick={() => {
                onDelegate(toPerson)
                setDelegating(false)
                setToPerson('')
              }}
            >
              Send
            </button>
            <button className="tm-btn tm-btn--ghost" onClick={() => setDelegating(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}
      {!offered && !delegating && (
        <div className="task-card__actions">
          <button className="task-card__action" onClick={startEdit}>
            Edit
          </button>
          {task.project_id && members.length > 0 && (
            <button className="task-card__action" onClick={() => setDelegating(true)}>
              Delegate
            </button>
          )}
          <button className="task-card__action task-card__action--delete" onClick={onDelete}>
            Delete
          </button>
        </div>
      )}
    </div>
  )
}

/** Read-only view of one project: the same four columns as the personal board, holding everyone's
 * cards with the assignee named on each tile. Within a column, cards group by person and keep that
 * person's own order — there is deliberately no project-wide ranking, and you can't drag anyone
 * else's cards. Delegating happens from a card on your own board. */
function ProjectBoard({ projectId, projectName }: { projectId: string; projectName: string }) {
  const { people } = usePersona()
  const { data: tasks, isLoading } = useProjectTasks(projectId)
  const names = new Map(people.map((p) => [p.id, p.name]))

  const columns = useMemo(() => {
    const cols: Record<TaskStatus, Task[]> = { backlog: [], todo: [], doing: [], done: [] }
    for (const t of tasks ?? []) cols[t.status].push(t)
    const nameOf = (id: string) => names.get(id) ?? ''
    for (const list of Object.values(cols))
      list.sort((a, b) => nameOf(a.person_id).localeCompare(nameOf(b.person_id)) || a.position - b.position)
    return cols
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tasks, people])

  if (isLoading) return <div className="board-page__loading">Loading {projectName}…</div>

  return (
    <div className="board-page">
      <div className="board-columns">
        {STATUSES.map((status) => (
          <div key={status} className="board-column">
            <div className="board-column__head">
              <span className="board-column__title">{STATUS_LABEL[status]}</span>
              <span className="board-column__count">{columns[status].length}</span>
            </div>
            <div className="board-column__cards">
              {columns[status].map((t) => (
                <div key={t.id} className="task-card task-card--readonly">
                  {t.delegation_state === 'offered' && (
                    <span className="task-card__badge task-card__badge--offer">Offered</span>
                  )}
                  <p className="task-card__title">{t.title}</p>
                  <div className="task-card__row">
                    <span className="task-card__assignee">{names.get(t.person_id) ?? 'Unknown'}</span>
                    {t.created_by_name && t.created_by_id !== t.person_id && (
                      <span className="task-card__tag">from {t.created_by_name}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      {(tasks ?? []).length === 0 && (
        <p className="board-page__suggest-note">
          No cards are tagged to {projectName} yet. Tag one from your own board (or delegate it) and it appears here.
        </p>
      )}
    </div>
  )
}
