import { useState } from 'react'
import { NavLink, useLocation, useSearchParams } from 'react-router-dom'
import { useSuggestTasks } from '../api/hooks'
import { usePersona } from '../lib/persona'
import PersonaMenu from './PersonaMenu'
import './Nav.css'

/** Topbar: brand, the board switcher (My board | a project), and the AI backlog suggester. The
 * chosen board lives in the URL (`?board=<projectId>`) so Nav and BoardPage share it without a
 * context, and a project view is linkable. The switcher and Suggest only show on the board
 * itself, not the splash page. */
export default function Nav() {
  const { persona } = usePersona()
  const { pathname } = useLocation()
  const [params, setParams] = useSearchParams()
  const suggest = useSuggestTasks(persona?.id)
  const [note, setNote] = useState<string | null>(null)

  const onBoard = pathname === '/'
  const board = params.get('board') ?? ''
  const projects = persona?.projects ?? []
  const activeBoard = projects.some((p) => p.id === board) ? board : ''

  function selectBoard(id: string) {
    setNote(null)
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (id) next.set('board', id)
        else next.delete('board')
        return next
      },
      { replace: true },
    )
  }

  function runSuggest() {
    setNote(null)
    suggest.mutate(undefined, {
      onSuccess: (r) => {
        if (!Array.isArray(r)) setNote(r.error)
        else if (r.length === 0) setNote('Nothing new to suggest right now.')
      },
      onError: () => setNote('Could not get suggestions.'),
    })
  }

  return (
    <nav className="tm-nav">
      <NavLink to="/about" className="tm-nav__brand">
        Task Master
      </NavLink>
      {onBoard && persona && (
        <select
          className="tm-nav__board"
          value={activeBoard}
          onChange={(e) => selectBoard(e.target.value)}
          aria-label="Board"
        >
          <option value="">My board</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      )}
      <div className="tm-nav__right">
        {onBoard && !activeBoard && (
          <>
            {note && (
              <span className="tm-nav__note" title={note}>
                {note}
              </span>
            )}
            <button className="tm-btn tm-btn--primary" onClick={runSuggest} disabled={suggest.isPending}>
              {suggest.isPending ? 'Thinking…' : '✨ Suggest backlog items'}
            </button>
          </>
        )}
        <PersonaMenu />
      </div>
    </nav>
  )
}
