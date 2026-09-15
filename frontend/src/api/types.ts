export type TaskStatus = 'backlog' | 'todo' | 'doing' | 'done'
export const STATUSES: TaskStatus[] = ['backlog', 'todo', 'doing', 'done']
export const STATUS_LABEL: Record<TaskStatus, string> = {
  backlog: 'Backlog',
  todo: 'To Do',
  doing: 'Doing',
  done: 'Done',
}

export type TaskSource = 'manual' | 'ai_suggested'

export interface Task {
  id: string
  person_id: string
  title: string
  note: string | null
  status: TaskStatus
  position: number
  source: TaskSource
  project_id: string | null
  project_name: string | null
  application_id: string | null
  application_name: string | null
  created_at: string
  updated_at: string
}

/** Mirrors Conway's Depot's own /api/people shape exactly — this app never stores its own copy,
 * see backend models.py's module docstring for why. Only the fields Task Master actually reads. */
export interface DepotProject {
  id: string
  name: string
  phase: 'pursuit' | 'award' | 'execution' | 'closeout'
  application_ids: string[]
  role_label: string | null
}

export interface DepotPerson {
  id: string
  name: string
  title: string | null
  is_admin: boolean
  projects: DepotProject[]
  project_ids: string[]
  application_ids: string[]
  pinned_application_ids: string[]
}

export interface PeopleResponse {
  people: DepotPerson[]
  depot_reachable: boolean
}
