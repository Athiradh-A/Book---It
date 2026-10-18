import { HashRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import RoomSearch from './pages/RoomSearch'
import EventRequest from './pages/EventRequest'
import SlotBooking from './pages/SlotBooking'
import Landing from './pages/Landing'
import Amenities from './pages/Amenities'
import MyBookings from './pages/MyBookings'
import Shell from './components/Shell'
import Approvals from './pages/Approvals'
import EventRegistration from './pages/EventRegistration'
import TimetableAdmin from './pages/TimetableAdmin'
import { useEffect, useState } from 'react'
import { api } from './lib/api'

function Protected({ children, roles: allowed }: { children: React.ReactNode; roles?: string[] }) {
    const location = useLocation()
    const [roles, setRoles] = useState<string[] | null>(null)
    const token = localStorage.getItem('token')
    useEffect(() => {
        if (!token) { setRoles([]); return }
        api.get('/auth/me').then(r => setRoles(r.data.roles || [])).catch(() => { localStorage.removeItem('token'); localStorage.removeItem('refresh_token'); setRoles([]) })
    }, [token])
    const loginTarget = `/login?next=${encodeURIComponent(location.pathname + location.search)}`
    if (!token) return <Navigate to={loginTarget} replace />
    if (roles === null) return <div className="page-loading">Loading your permissions…</div>
    if (!roles.length) return <Navigate to={loginTarget} replace />
    if (allowed && !allowed.some(role => roles.includes(role))) return <Navigate to="/dashboard" replace />
    return children
}

function App() {
    return (
        <Router>
            <Routes>
                <Route path='/login' element={<Login />} />
                <Route path='/' element={<Landing />} />
                <Route element={<Protected><Shell /></Protected>}>
                    <Route path='/dashboard' element={<Dashboard />} />
                    <Route path='/rooms' element={<RoomSearch />} />
                    <Route path='/rooms/slots' element={<SlotBooking />} />
                    <Route path='/events' element={<EventRequest />} />
                    <Route path='/event-registration' element={<EventRegistration />} />
                    <Route path='/amenities' element={<Amenities />} />
                    <Route path='/bookings' element={<MyBookings />} />
                    <Route path='/approvals' element={<Protected roles={['FACULTY', 'WELFARE', 'DIRECTOR', 'EVENTS']}><Approvals /></Protected>} />
                    <Route path='/admin/timetable' element={<Protected roles={['ADMIN']}><TimetableAdmin /></Protected>} />
                </Route>
                <Route path='*' element={<Navigate to='/' />} />
            </Routes>
        </Router>
    )
}
export default App


