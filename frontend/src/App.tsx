import { DrawerLayout, DepotBackBar } from '@conways/drawer'
import { Route, Routes } from 'react-router-dom'
import Nav from './components/Nav'
import { PersonaProvider, usePersona } from './lib/persona'
import BoardPage from './pages/BoardPage'
import SplashPage from './pages/SplashPage'
import './App.css'

const DEPOT_URL = 'http://localhost:8090'

/** The board is person-scoped (one person across every project), so the shared drawer runs in
 * its person-scoped mode: Journal opens on the active persona's personal "My day" feed with a
 * picker for any of their projects, and Agent is Conway's Depot's own portfolio assistant
 * (called directly — it already knows who's asking via person_id, and can trigger this app's
 * own backlog suggestions). */
function Layout({ children }: { children: React.ReactNode }) {
  const { persona } = usePersona()
  return (
    <div className="app-layout">
      <Nav />
      <DrawerLayout
        storageKey="task-master:drawer"
        scrollMain={false}
        agent={{
          chatUrl: `${DEPOT_URL}/api/chat`,
          chatExtra: { person_id: persona?.id },
          aiConfigured: true,
          intro: 'Ask about your projects and where things stand — or ask me to suggest backlog items.',
        }}
        journal={{
          depotUrl: DEPOT_URL,
          personId: persona?.id,
          projects: (persona?.projects ?? []).map((p) => ({ id: p.id, name: p.name })),
        }}
      >
        <div className="app-layout__body">{children}</div>
      </DrawerLayout>
    </div>
  )
}

export default function App() {
  return (
    <PersonaProvider>
      <DepotBackBar />
      <Routes>
        <Route path="/about" element={<SplashPage />} />
        <Route path="/" element={<Layout><BoardPage /></Layout>} />
      </Routes>
    </PersonaProvider>
  )
}
