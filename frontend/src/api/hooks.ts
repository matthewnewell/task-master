import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { PeopleResponse, Task, TaskStatus } from './types'

export function usePeople() {
  return useQuery({
    queryKey: ['people'],
    queryFn: () => api.get<PeopleResponse>('/people'),
    staleTime: 60_000,
  })
}

function useInvalidateTasks(personId: string | undefined) {
  const qc = useQueryClient()
  return () => qc.invalidateQueries({ queryKey: ['tasks', personId] })
}

export function useTasks(personId: string | undefined) {
  return useQuery({
    queryKey: ['tasks', personId],
    queryFn: () => api.get<Task[]>(`/tasks?person_id=${encodeURIComponent(personId!)}`),
    enabled: !!personId,
  })
}

/** Everyone's cards for one project — the read-only project view. */
export function useProjectTasks(projectId: string | undefined) {
  return useQuery({
    queryKey: ['tasks', 'project', projectId],
    queryFn: () => api.get<Task[]>(`/tasks?project_id=${encodeURIComponent(projectId!)}`),
    enabled: !!projectId,
  })
}

export function useDelegateTask(personId: string | undefined) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, toPersonId }: { id: string; toPersonId: string }) =>
      api.post<Task>(`/tasks/${id}/delegate`, { by_person_id: personId, to_person_id: toPersonId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'] }),
  })
}

export function useRespondTask(personId: string | undefined) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, accept, reason }: { id: string; accept: boolean; reason?: string }) =>
      api.post<Task>(`/tasks/${id}/respond`, { person_id: personId, accept, reason }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'] }),
  })
}

export function useCreateTask(personId: string | undefined) {
  const invalidate = useInvalidateTasks(personId)
  return useMutation({
    mutationFn: (data: { title: string; note?: string; project_id?: string | null; project_name?: string | null }) =>
      api.post<Task>('/tasks', { person_id: personId, ...data }),
    onSuccess: invalidate,
  })
}

export function useUpdateTask(personId: string | undefined) {
  const invalidate = useInvalidateTasks(personId)
  return useMutation({
    mutationFn: ({
      id,
      ...data
    }: {
      id: string
      title?: string
      note?: string
      project_id?: string | null
      project_name?: string | null
    }) =>
      api.put<Task>(`/tasks/${id}`, data),
    onSuccess: invalidate,
  })
}

export function useDeleteTask(personId: string | undefined) {
  const invalidate = useInvalidateTasks(personId)
  return useMutation({
    mutationFn: (id: string) => api.del<void>(`/tasks/${id}`),
    onSuccess: invalidate,
  })
}

/** One drag, one call — the whole board's column membership + order goes up together. See
 * backend routes/tasks.py's reorder_tasks for why. */
export function useReorderTasks(personId: string | undefined) {
  const invalidate = useInvalidateTasks(personId)
  return useMutation({
    mutationFn: (columns: Partial<Record<TaskStatus, string[]>>) =>
      api.put<Task[]>('/tasks/reorder', { person_id: personId, columns }),
    onSuccess: invalidate,
  })
}

/** Gathers cross-app signals via the Depot and proposes new backlog cards — see backend
 * routes/suggest.py. Returns {error} in the success (200) body when AI isn't configured or the
 * Depot is unreachable, same "normal state, not an exception" shape every AI feature in this
 * ecosystem uses; only a genuinely unexpected failure rejects the promise. */
export function useSuggestTasks(personId: string | undefined) {
  const invalidate = useInvalidateTasks(personId)
  return useMutation({
    mutationFn: () => api.post<Task[] | { error: string }>('/tasks/suggest', { person_id: personId }),
    onSuccess: (result) => {
      if (Array.isArray(result)) invalidate()
    },
  })
}
