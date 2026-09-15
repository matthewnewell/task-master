import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { usePeople } from '../api/hooks'
import type { DepotPerson } from '../api/types'

/**
 * The "viewing as" persona — mirrors Conway's Depot's own persona switcher exactly, because
 * it IS the Depot's own list (see api/hooks.ts's usePeople, backend depot_client.py). Every
 * other sibling app in this ecosystem keeps its own illustrative persona/demo-data; this one
 * doesn't, on purpose — see backend models.py's module docstring. Same localStorage-survives-
 * reload pattern as the Depot's own lib/persona.tsx.
 */

const STORAGE_KEY = 'task-master:person-id'

interface PersonaContextValue {
  persona: DepotPerson | null
  people: DepotPerson[]
  isLoading: boolean
  depotReachable: boolean
  setPersonId: (id: string) => void
}

const PersonaContext = createContext<PersonaContextValue | undefined>(undefined)

function readStoredId(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

/** The Depot's own "Test drive" link rides the active persona along as `?person_id=` (see
 * Conway's Depot's ApplicationDetailPage.tsx) — read once, on mount, not on every render, so
 * it doesn't fight a later in-app persona switch. */
function readUrlPersonId(): string | null {
  try {
    return new URLSearchParams(window.location.search).get('person_id')
  } catch {
    return null
  }
}

export function PersonaProvider({ children }: { children: ReactNode }) {
  const { data, isLoading } = usePeople()
  const [urlPersonId] = useState<string | null>(readUrlPersonId)
  const [personId, setPersonIdState] = useState<string | null>(readStoredId)

  function setPersonId(id: string) {
    setPersonIdState(id)
    try {
      window.localStorage.setItem(STORAGE_KEY, id)
    } catch {
      /* private mode / storage disabled — the choice just won't persist */
    }
  }

  const people = data?.people ?? []

  useEffect(() => {
    if (people.length === 0) return
    // Arriving from the Depot with a person_id always wins on first load, even over whatever
    // was last used locally — that's the whole point of following a link that names you.
    if (urlPersonId && people.some((p) => p.id === urlPersonId)) {
      if (personId !== urlPersonId) setPersonId(urlPersonId)
      return
    }
    const stored = people.find((p) => p.id === personId)
    if (stored) return
    const fallback = people.find((p) => p.is_admin) ?? people[0]
    setPersonId(fallback.id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])

  const value = useMemo<PersonaContextValue>(
    () => ({
      persona: people.find((p) => p.id === personId) ?? null,
      people,
      isLoading,
      depotReachable: data?.depot_reachable ?? true,
      setPersonId,
    }),
    [people, personId, isLoading, data],
  )

  return <PersonaContext.Provider value={value}>{children}</PersonaContext.Provider>
}

export function usePersona(): PersonaContextValue {
  const ctx = useContext(PersonaContext)
  if (!ctx) throw new Error('usePersona must be used within a PersonaProvider')
  return ctx
}
