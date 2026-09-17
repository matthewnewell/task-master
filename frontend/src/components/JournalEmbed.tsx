import { useEffect, useState } from 'react'
import { usePersona } from '../lib/persona'

declare global {
  interface Window {
    JournalWidget?: {
      configure: (cfg: {
        depotUrl?: string
        personId?: string | null
        projects?: { id: string; name: string }[]
      }) => void
    }
  }
}

const DEPOT_URL = 'http://localhost:8090'
const SCRIPT_ID = 'depot-journal-widget-script'

/**
 * Loads Conway's Depot's embeddable Journal widget (backend/embed_assets/journal.js there) into
 * this page — the "common interface" piece: an operator can log a personal note ("plan my day")
 * or a project note without leaving Task Master. The script is loaded once and reconfigured
 * (window.JournalWidget.configure) whenever the active persona changes, since the widget has no
 * way to know that on its own — same reasoning usePersona() itself already follows the Depot's
 * own persona list rather than keeping a local copy (see lib/persona.tsx).
 *
 * No application-id is passed: Task Master doesn't publish federated journal entries of its
 * own, so the widget's "this app / whole project" filter wouldn't have anything to filter.
 */
export default function JournalEmbed() {
  const { persona } = usePersona()
  const [scriptReady, setScriptReady] = useState(false)

  // Loaded once per page load; onload (not just "script tag exists") is what actually gates
  // configure() below, since the tag can be in the DOM well before window.JournalWidget exists.
  useEffect(() => {
    const existing = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null
    if (existing) {
      if (window.JournalWidget) setScriptReady(true)
      else existing.addEventListener('load', () => setScriptReady(true))
      return
    }
    const script = document.createElement('script')
    script.id = SCRIPT_ID
    script.src = `${DEPOT_URL}/embed/journal.js`
    script.addEventListener('load', () => setScriptReady(true))
    document.body.appendChild(script)
  }, [])

  useEffect(() => {
    if (!scriptReady || !persona) return
    window.JournalWidget?.configure({
      depotUrl: DEPOT_URL,
      personId: persona.id,
      projects: persona.projects.map((p) => ({ id: p.id, name: p.name })),
    })
  }, [scriptReady, persona])

  return null
}
