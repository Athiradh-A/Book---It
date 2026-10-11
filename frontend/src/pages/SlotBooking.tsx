import React, { useState, useEffect } from "react"
import { useSearchParams, useNavigate } from "react-router-dom"
import { api } from "../lib/api"

function SlotBooking() {
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()
    const roomId = searchParams.get("roomId")
    const date = searchParams.get("date") || new Date().toISOString().split("T")[0]

    const [slots, setSlots] = useState([])
    const [holdId, setHoldId] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchSlots()
    }, [roomId, date])

    const fetchSlots = async () => {
        setLoading(true)
        try {
            const res = await api.get(`/bookings/slots/${roomId}?date=${date}`)
            setSlots(res.data.slots)
        } catch (err) {
            alert("Error fetching slots")
        } finally {
            setLoading(false)
        }
    }

    const handleSlotClick = async (slot) => {
        if (slot.status !== "AVAILABLE") {
            alert(`This slot is ${slot.status.replace("_", " ").toLowerCase()}`)
            return
        }

        try {
            const start = `${date}T${slot.start}:00`
            const end = `${date}T${slot.end}:00`
            const res = await api.post("/bookings/classroom/hold", {
                room_id: parseInt(roomId),
                start_time: start,
                end_time: end
            })
            setHoldId(res.data.hold_id)
            alert("Slot held for 5 minutes!")
        } catch (err) {
            alert(err.response?.data?.detail || "Hold failed")
        }
    }

    const handleConfirm = async () => {
        try {
            await api.post("/bookings/classroom/confirm", {
                hold_id: holdId,
                purpose: "Meeting/Study",
                expected_attendees: 10
            })
            alert("Booking Confirmed!")
            setHoldId(null)
            fetchSlots()
        } catch (err) {
            alert(err.response?.data?.detail || "Confirmation failed")
        }
    }

    if (!roomId) return <div className="p-6">Room ID missing in URL.</div>
    if (loading) return <div className="p-6">Loading slots...</div>

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <button onClick={() => navigate(-1)} className="mb-4 text-[#D51F36] hover:underline">? Back to Search</button>
            <h1 className="text-2xl font-bold mb-2">Select a Time Slot</h1>
            <p className="mb-6 text-gray-600">Room ID: {roomId} | Date: {date}</p>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                <div className="flex items-center gap-2"><div className="w-4 h-4 bg-white border border-gray-300"></div><span>Available</span></div>
                <div className="flex items-center gap-2"><div className="w-4 h-4 bg-gray-300"></div><span>Timetable Occupied</span></div>
                <div className="flex items-center gap-2"><div className="w-4 h-4 bg-red-400"></div><span>User Booked</span></div>
                <div className="flex items-center gap-2"><div className="w-4 h-4 bg-yellow-300"></div><span>Held by You</span></div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {slots.map(slot => (
                    <button 
                        key={slot.slot} 
                        onClick={() => handleSlotClick(slot)}
                        className={`p-4 rounded-lg border transition-all ${
                            slot.status === "AVAILABLE" ? "bg-white hover:bg-[#F3DADD] border-gray-200" : 
                            slot.status === "TIMETABLE_OCCUPIED" ? "bg-gray-200 text-gray-500 cursor-not-allowed" : 
                            slot.status === "HELD" ? "bg-yellow-200 border-yellow-400 font-bold" :
                            "bg-red-100 text-red-600 cursor-not-allowed"
                        }`}
                    >
                        <div className="font-bold">Slot {slot.slot}</div>
                        <div className="text-sm">{slot.start} - {slot.end}</div>
                        <div className="text-xs mt-2 uppercase">{slot.status.replace("_", " ")}</div>
                    </button>
                ))}
            </div>

            {holdId && (
                <div className="fixed bottom-8 right-8 p-6 bg-yellow-100 border border-yellow-400 rounded-xl shadow-xl flex flex-col gap-3">
                    <span className="font-bold text-yellow-800">Slot held! Confirm now to book.</span>
                    <button onClick={handleConfirm} className="bg-green-600 text-white px-6 py-2 rounded-lg font-bold hover:bg-green-700">Confirm Booking</button>
                </div>
            )}
        </div>
    )
}
export default SlotBooking
