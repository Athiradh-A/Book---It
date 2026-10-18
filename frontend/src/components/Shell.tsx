import { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { Building2, CalendarDays, CheckSquare, Grid2X2, Home, LogOut, Menu, Sparkles, Ticket, X, Upload } from 'lucide-react'
import { api } from '../lib/api'

type LinkItem = { label: string; href: string; Icon: typeof Home; roles?: string[] }
const links: LinkItem[] = [
  { label: 'Dashboard', href: '/dashboard', Icon: Home },
  { label: 'Classrooms', href: '/rooms', Icon: Building2 },
  { label: 'Halls & event requests', href: '/events', Icon: CalendarDays },
  { label: 'Event tickets', href: '/event-registration', Icon: Ticket, roles: ['STUDENT', 'FACULTY', 'WELFARE', 'DIRECTOR', 'EVENTS'] },
  { label: 'Amenities', href: '/amenities', Icon: Sparkles },
  { label: 'My bookings', href: '/bookings', Icon: Grid2X2 },
  { label: 'Approvals', href: '/approvals', Icon: CheckSquare, roles: ['FACULTY', 'WELFARE', 'DIRECTOR', 'EVENTS', 'ADMIN'] },
  { label: 'Timetable import', href: '/admin/timetable', Icon: Upload, roles: ['ADMIN'] },
]
const hierarchy: Record<string, number> = { STUDENT: 1, FACULTY: 2, WELFARE: 3, DIRECTOR: 4, EVENTS: 5 }
function hasFeatureRole(roles: string[], allowed: string[]) {
  if (allowed.includes('ADMIN') && roles.includes('ADMIN')) return true
  const level = Math.max(0, ...roles.map(role => hierarchy[role] || 0))
  return allowed.some(role => (hierarchy[role] || 0) <= level && level > 0)
}
export default function Shell() {
  const [open, setOpen] = useState(false)
  const [roles, setRoles] = useState<string[]>([])
  const navigate = useNavigate()
  useEffect(() => { api.get('/auth/me').then(r => setRoles(r.data.roles || [])).catch(() => { localStorage.removeItem('token'); localStorage.removeItem('refresh_token'); navigate('/login', { replace: true }) }) }, [navigate])
  const visibleLinks = links.filter(link => !link.roles || hasFeatureRole(roles, link.roles))
  return <div className="app-shell">
    <header className="topbar">
      <NavLink to="/" className="brand" aria-label="Book-It home"><span>BOOK</span><i>•</i><span>IT</span></NavLink>
      <button className="menu-button" onClick={() => setOpen(!open)} aria-label="Toggle menu">{open ? <X/> : <Menu/>}</button>
      <nav className={open ? 'nav open' : 'nav'}>
        {visibleLinks.map(({ label, href, Icon }) => <NavLink key={href} to={href} onClick={() => setOpen(false)}><Icon size={16}/>{label}</NavLink>)}
      </nav>
      <button className="icon-button logout" onClick={() => { localStorage.removeItem('token'); localStorage.removeItem('refresh_token'); navigate('/login', { replace: true }) }} aria-label="Log out"><LogOut size={18}/></button>
    </header>
    <main className="page"><Outlet/></main>
  </div>
}
