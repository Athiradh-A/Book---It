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

function Protected({ children }: { children: React.ReactNode }) {
    const location = useLocation()
    const loginTarget = `/login?next=${encodeURIComponent(location.pathname + location.search)}`
    return localStorage.getItem('token') ? children : <Navigate to={loginTarget} replace />
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
                    <Route path='/approvals' element={<Approvals />} />
                </Route>
                <Route path='*' element={<Navigate to='/' />} />
            </Routes>
        </Router>
    )
}
export default App


