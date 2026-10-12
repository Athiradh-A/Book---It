import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { Building2, CalendarDays, CheckSquare, Grid2X2, Home, LogOut, Menu, Sparkles, X } from 'lucide-react'

const links = [
  ['Dashboard', '/dashboard', Home], ['Classrooms', '/rooms', Building2], ['Halls', '/events', CalendarDays],
  ['Amenities', '/amenities', Sparkles], ['My bookings', '/bookings', Grid2X2], ['Approvals', '/approvals', CheckSquare],
] as const

export default function Shell() {
  const [open, setOpen] = useState(false); const navigate = useNavigate()
  return <div className="app-shell">
    <header className="topbar">
      <NavLink to="/" className="brand" aria-label="Book-It home"><span>BOOK</span><i>•</i><span>IT</span></NavLink>
      <button className="menu-button" onClick={() => setOpen(!open)} aria-label="Toggle menu">{open ? <X/> : <Menu/>}</button>
      <nav className={open ? 'nav open' : 'nav'}>
        {links.map(([label, href, Icon]) => <NavLink key={href} to={href} onClick={() => setOpen(false)}><Icon size={16}/>{label}</NavLink>)}
      </nav>
      <button className="icon-button logout" onClick={() => {localStorage.removeItem('token'); navigate('/')}} aria-label="Log out"><LogOut size={18}/></button>
    </header>
    <main className="page"><Outlet/></main>
  </div>
}
