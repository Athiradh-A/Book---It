import React from 'react'
import { useNavigate } from 'react-router-dom'

function Dashboard() {
    const navigate = useNavigate()
    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <div className="flex justify-between items-center mb-8">
                <h1 className="text-2xl font-bold">User Dashboard</h1>
                <button onClick={() => { localStorage.removeItem('token'); navigate('/login') }} 
                        className="text-red-500 hover:underline">Logout</button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div onClick={() => navigate('/rooms')} className="p-6 bg-white rounded-lg shadow cursor-pointer hover:shadow-md transition border-l-4 border-blue-500">
                    <h3 className="text-xl font-semibold mb-2">Book a Classroom</h3>
                    <p className="text-gray-600">Instant booking for classrooms with 5-minute holds.</p>
                </div>
                <div onClick={() => navigate('/events')} className="p-6 bg-white rounded-lg shadow cursor-pointer hover:shadow-md transition border-l-4 border-purple-500">
                    <h3 className="text-xl font-semibold mb-2">Request a Hall</h3>
                    <p className="text-gray-600">Submit event requests for auditoriums and halls.</p>
                </div>
            </div>
        </div>
    )
}
export default Dashboard


