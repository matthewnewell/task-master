import { Route, Routes } from 'react-router-dom'
import Nav from './components/Nav'
import { PersonaProvider } from './lib/persona'
import BoardPage from './pages/BoardPage'
import SplashPage from './pages/SplashPage'
import './App.css'

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-layout">
      <Nav />
      <div className="app-layout__body">{children}</div>
    </div>
  )
}

export default function App() {
  return (
    <PersonaProvider>
      <Routes>
        <Route path="/about" element={<SplashPage />} />
        <Route path="/" element={<Layout><BoardPage /></Layout>} />
      </Routes>
    </PersonaProvider>
  )
}
