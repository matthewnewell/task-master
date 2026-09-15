import { NavLink } from 'react-router-dom'
import PersonaMenu from './PersonaMenu'
import './Nav.css'

export default function Nav() {
  return (
    <nav className="tm-nav">
      <NavLink to="/about" className="tm-nav__brand">
        Task Master
      </NavLink>
      <div className="tm-nav__right">
        <PersonaMenu />
      </div>
    </nav>
  )
}
