import React, { useState } from "react"
import { api } from "../lib/api"
import { useNavigate } from "react-router-dom"

function RoomSearch() {
    const navigate = useNavigate()
    
    // Helper function to get local date in YYYY-MM-DD format
    const getLocalDate = () => {
        const now = new Date();
        const offset = now.getTimezoneOffset();
        const localDate = new Date(now.getTime() - (offset * 60 * 1000));
        return localDate.toISOString().split('T')[0];
    };

    const [params, setParams] = useState({ 
        date: getLocalDate(), 
        start: "09:00", 
        end: "10:00", 
        capacity: 10, 
        roomType: "", 
        academicBlock: "" 
    })
    const [rooms, setRooms] = useState([])
    const [holdId, setHoldId] = useState(null)

    const searchRooms = async () => {
        try {
            const res = await api.get("/bookings/availability", { 
                params: { 
                    date_str: params.date, 
                    start_str: params.start, 
                    end_str: params.end, 
                    capacity: params.capacity,
                    room_type: params.roomType || undefined,
                    academic_block: params.academicBlock || undefined
                } 
            })
            setRooms(res.data)
        } catch (err) { alert("Error searching rooms") }
    }

    const handleHold = (roomId) => {
        navigate(`/rooms/slots?roomId=${roomId}&date=${params.date}`)
    }

    const handleConfirm = async () => {
        try {
            await api.post("/bookings/classroom/confirm", {
                hold_id: holdId,
                purpose: "Study Session",
                expected_attendees: parseInt(params.capacity)
            })
            alert("Booking Confirmed!")
            setHoldId(null)
            searchRooms()
        } catch (err) { alert(err.response?.data?.detail || "Confirmation failed") }
    }

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <h1 className="text-2xl font-bold mb-6">Find Available Rooms</h1>
            <div className="bg-white p-4 rounded shadow-sm grid grid-cols-1 md:grid-cols-6 gap-4 mb-8">
                <input 
                    type="date" 
                    className="p-2 border rounded" 
                    value={params.date} 
                    onChange={e => setParams({...params, date: e.target.value})} 
                />
                <input 
                    type="time" 
                    className="p-2 border rounded" 
                    value={params.start} 
                    onChange={e => {
                        setParams({...params, start: e.target.value});
                        e.target.blur(); // Closes the native time picker menu immediately
                    }} 
                />
                <input 
                    type="time" 
                    className="p-2 border rounded" 
                    value={params.end} 
                    onChange={e => {
                        setParams({...params, end: e.target.value});
                        e.target.blur(); // Closes the native time picker menu immediately
                    }} 
                />
                <input 
                    type="number" 
                    className="p-2 border rounded" 
                    placeholder="Capacity" 
                    value={params.capacity} 
                    onChange={e => setParams({...params, capacity: e.target.value})} 
                />
                <select 
                    className="p-2 border rounded" 
                    value={params.academicBlock} 
                    onChange={e => setParams({...params, academicBlock: e.target.value})}
                >
                    <option value="">All Blocks</option>
                    <option value="AB-1">AB-1</option>
                    <option value="AB-2">AB-2</option>
                    <option value="AB-3">AB-3</option>
                    <option value="AB-4">AB-4</option>
                </select>
                <button onClick={searchRooms} className="bg-[#D51F36] text-white px-4 py-2 rounded hover:bg-[#A91224]">Search</button>
            </div>
            {holdId && (
                <div className="mb-6 p-4 bg-yellow-100 border border-yellow-400 rounded flex justify-between items-center">
                    <span>Room is currently held. Confirm your booking now!</span>
                    <button onClick={handleConfirm} className="bg-green-600 text-white px-4 py-2 rounded">Confirm Now</button>
                </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {rooms.filter(room => room.is_available).map(room => (
                    <div key={room.room_id} className="p-4 rounded border shadow-sm bg-green-50 border-green-200">
                        <div className="flex justify-between items-center mb-2">
                            <span className="font-bold">Room {room.code}</span>
                            <span className="text-xs px-2 py-1 rounded bg-green-200 text-green-800">
                                Available
                            </span>
                        </div>
                        <button onClick={() => handleHold(room.room_id)} className="mt-3 w-full bg-[#D51F36] text-white py-1 rounded text-sm">Hold Room</button>
                    </div>
                ))}
            </div>
        </div>
    )
}
export default RoomSearch
