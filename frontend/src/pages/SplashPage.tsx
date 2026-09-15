import { Link } from 'react-router-dom'
import Nav from '../components/Nav'
import './SplashPage.css'

const FEATURES = [
  {
    title: 'One board, every project',
    body: "Backlog, To Do, Doing, Done — for everything you're on, not one board per project you have to keep checking separately. The same reason Conway's Depot's own Launchpad merged its Pinned Apps and Recent Activity into one view instead of several.",
  },
  {
    title: 'Grounded suggestions, not guesses',
    body: "\"Suggest backlog items\" reads real signals through Conway's Depot — a status tile gone critical, a wait-time bottleneck, a recent journal entry — and proposes cards with a stated reason. Never invents a project or event that isn't actually there.",
  },
  {
    title: 'A proposal, not a decision',
    body: "An AI-suggested card lands on your backlog clearly marked as one — same as WinMax's scored judgment calls or Value Stream's journal entries. Nothing moves itself to Doing; you decide what's worth doing.",
  },
]

export default function SplashPage() {
  return (
    <div className="splash-page">
      <Nav />
      <div className="splash-page__scroll">
        <div className="splash-page__content">
          <header className="splash-hero">
            <h1 className="splash-hero__title">Task Master</h1>
            <p className="splash-hero__sub">
              A personal kanban that already knows what's going on across your projects.
            </p>
            <div className="splash-hero__actions">
              <Link className="tm-btn tm-btn--primary" to="/">
                Open your board →
              </Link>
            </div>
          </header>

          <section className="splash-features">
            {FEATURES.map((f) => (
              <article className="splash-feature" key={f.title}>
                <h3 className="splash-feature__title">{f.title}</h3>
                <p className="splash-feature__body">{f.body}</p>
              </article>
            ))}
          </section>

          <section className="splash-note">
            <p>
              Task Master is the one sibling app that depends on Conway's Depot directly — its
              persona switcher reads the Depot's own persona list live, rather than keeping a
              separate copy that could drift. Every other app in this ecosystem stays fully
              standalone; this one's whole job is staying aware of a person's Depot-wide
              context, so it leans on the Depot's own source of truth for who that person is.
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}
