import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import RoomSearch from './pages/RoomSearch'
import EventRequest from './pages/EventRequest'
import SlotBooking from './pages/SlotBooking'
import Landing from './pages/Landing'
import Amenities from './pages/Amenities'
import MyBookings from './pages/MyBookings'
import Shell from './components/Shell'

function Protected({ children }: { children: React.ReactNode }) {
    return localStorage.getItem('token') ? children : <Navigate to="/login" replace />
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
                    <Route path='/amenities' element={<Amenities />} />
                    <Route path='/bookings' element={<MyBookings />} />
                    <Route path='/approvals' element={<div className="content-wrap"><div className="page-heading compact"><div><p className="kicker">AUTHORIZED QUEUES</p><h1>Approvals.</h1></div></div><div className="empty">Approval requests for your assigned role appear here.</div></div>} />
                </Route>
                <Route path='*' element={<Navigate to='/' />} />
            </Routes>
        </Router>
    )
}
export default App


