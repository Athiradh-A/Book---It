import React, { useState, useEffect } from "react"
import axios from "axios"

const api = axios.create({ baseURL: "http://localhost:8000/api" })

function EventRequest() {
    const [form, setForm] = useState({
        event_name: "",
        description: "",
        date: "",
        start_time: "",
        end_time: "",
        expected_attendees: 50,
        room_id: "",
        academic_block: ""
    })
    const [status, setStatus] = useState("")

    const handleSubmit = async (e) => {
        e.preventDefault()
        try {
            await api.post("/events/request", {
                ...form,
                date: new Date(form.date),
                start_time: new Date(form.date + "T" + form.start_time),
                end_time: new Date(form.date + "T" + form.end_time),
                room_id: parseInt(form.room_id),
                academic_block: form.academic_block
            })
            setStatus("Success! Your request has been submitted for approval.")
        } catch (err) {
            setStatus("Error submitting request. Please check your details.")
        }
    }

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <h1 className="text-2xl font-bold mb-6">Request a Hall/Auditorium</h1>
            <div className="max-w-2xl mx-auto bg-white p-8 rounded-lg shadow">
                <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Event Name</label>
                        <input type="text" className="w-full p-2 border rounded mt-1" value={form.event_name} onChange={e => setForm({...form, event_name: e.target.value})} required />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Description</label>
                        <textarea className="w-full p-2 border rounded mt-1" rows="3" value={form.description} onChange={e => setForm({...form, description: e.target.value})} required></textarea>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Date</label>
                            <input type="date" className="w-full p-2 border rounded mt-1" value={form.date} onChange={e => setForm({...form, date: e.target.value})} required />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Academic Block</label>
                            <select className="w-full p-2 border rounded mt-1" value={form.academic_block} onChange={e => setForm({...form, academic_block: e.target.value})} required>
                                <option value="">Select Block</option>
                                <option value="AB-1">AB-1</option>
                                <option value="AB-2">AB-2</option>
                                <option value="AB-3">AB-3</option>
                                <option value="AB-4">AB-4</option>
                            </select>
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Room ID (Hall/Auditorium)</label>
                            <input type="number" className="w-full p-2 border rounded mt-1" value={form.room_id} onChange={e => setForm({...form, room_id: e.target.value})} required />
                        </div>
                        <div className="hidden"></div> {/* spacer */}
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Start Time</label>
                            <input type="time" className="w-full p-2 border rounded mt-1" value={form.start_time} onChange={e => setForm({...form, start_time: e.target.value})} required />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">End Time</label>
                            <input type="time" className="w-full p-2 border rounded mt-1" value={form.end_time} onChange={e => setForm({...form, end_time: e.target.value})} required />
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Expected Attendees</label>
                        <input type="number" className="w-full p-2 border rounded mt-1" value={form.expected_attendees} onChange={e => setForm({...form, expected_attendees: e.target.value})} required />
                    </div>
                    <button type="submit" className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 font-bold">Submit Request</button>
                    {status && <p className="mt-4 text-center font-semibold" style={{color: status.startsWith("Success") ? "green" : "red"}}>{status}</p>}
                </form>
            </div>
        </div>
    )
}
export default EventRequest
