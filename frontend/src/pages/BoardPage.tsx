import { useEffect, useMemo, useState } from 'react'
import {
  useCreateTask,
  useDeleteTask,
  useReorderTasks,
  useSuggestTasks,
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
  const suggestTasks = useSuggestTasks(persona?.id)

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

  const suggestResult = suggestTasks.data
  const suggestError =
    suggestResult && !Array.isArray(suggestResult) ? suggestResult.error : null

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

  return (
    <div className="board-page">
      <div className="board-page__toolbar">
        <h1 className="board-page__title">{persona.name}'s board</h1>
        <button
          className="tm-btn tm-btn--primary"
          onClick={() => suggestTasks.mutate()}
          disabled={suggestTasks.isPending}
        >
          {suggestTasks.isPending ? 'Thinking…' : '✨ Suggest backlog items'}
        </button>
      </div>

      {suggestError && (
        <p className="board-page__suggest-error">{suggestError}</p>
      )}
      {Array.isArray(suggestResult) && suggestResult.length === 0 && (
        <p className="board-page__suggest-note">
          Nothing in your current projects and apps warranted a new item right now.
        </p>
      )}

      {tasksLoading ? (
        <div className="board-page__loading">Loading board…</div>
      ) : (
        <div className="board-columns">
          {STATUSES.map((status) => (
            <div
              key={status}
              className="board-column"
              onDragOver={(e) => e.preventDefault()}
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
                      onSave={(data) => updateTask.mutate({ id, ...data })}
                      onDelete={() => deleteTask.mutate(id)}
                    />
                  )
                })}
              </div>

              {status === 'backlog' &&
                (addingTo === 'backlog' ? (
                  <AddTaskForm
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

function AddTaskForm({
  onSave,
  onCancel,
}: {
  onSave: (data: { title: string; note?: string }) => void
  onCancel: () => void
}) {
  const [title, setTitle] = useState('')
  const [note, setNote] = useState('')

  function save() {
    const t = title.trim()
    if (!t) return
    onSave({ title: t, note: note.trim() || undefined })
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
  onSave,
  onDelete,
}: {
  task: Task
  dragging: boolean
  onDragStart: () => void
  onDragEnd: () => void
  onDropOn: () => void
  onSave: (data: { title: string; note?: string }) => void
  onDelete: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(task.title)
  const [note, setNote] = useState(task.note ?? '')

  function startEdit() {
    setTitle(task.title)
    setNote(task.note ?? '')
    setEditing(true)
  }

  function save() {
    const t = title.trim()
    if (!t) return
    onSave({ title: t, note: note.trim() || undefined })
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
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onDragOver={(e) => {
        e.preventDefault()
        e.stopPropagation()
      }}
      onDrop={(e) => {
        e.preventDefault()
        e.stopPropagation()
        onDropOn()
      }}
      title="Drag to reorder or move"
    >
      {task.source === 'ai_suggested' && <span className="task-card__badge">✨ Suggested</span>}
      <p className="task-card__title">{task.title}</p>
      {task.note && <p className="task-card__note">{task.note}</p>}
      {task.project_name && <span className="task-card__tag">{task.project_name}</span>}
      <div className="task-card__actions">
        <button className="task-card__action" onClick={startEdit}>
          Edit
        </button>
        <button className="task-card__action task-card__action--delete" onClick={onDelete}>
          Delete
        </button>
      </div>
    </div>
  )
}
