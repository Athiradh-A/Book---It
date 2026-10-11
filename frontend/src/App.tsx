import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import RoomSearch from './pages/RoomSearch'
import EventRequest from './pages/EventRequest'
import SlotBooking from './pages/SlotBooking'

function App() {
    const isAuthenticated = true // BYPASS LOGIN: Always authenticated

    return (
        <Router>
            <Routes>
                <Route path='/login' element={<Login />} />
                <Route path='/dashboard' element={isAuthenticated ? <Dashboard /> : <Navigate to='/login' />} />
                <Route path='/rooms' element={isAuthenticated ? <RoomSearch /> : <Navigate to='/login' />} />
                <Route path='/rooms/slots' element={isAuthenticated ? <SlotBooking /> : <Navigate to='/login' />} />
                <Route path='/events' element={isAuthenticated ? <EventRequest /> : <Navigate to='/login' />} />
                <Route path='/' element={<Navigate to='/dashboard' />} />
            </Routes>
        </Router>
    )
}
export default App


