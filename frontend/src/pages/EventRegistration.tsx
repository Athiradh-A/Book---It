import { useEffect, useState } from "react";
import { ArrowRight, Clock3, Ticket, Users, X } from "lucide-react";
import { api, messageFrom } from "../lib/api";

type EventItem = {
  id: number;
  name: string;
  description?: string;
  starts_at: string;
  registration_deadline?: string;
  capacity: number;
  applicant_count: number;
  confirmed_count: number;
  room_code?: string;
};

export default function EventRegistration() {
  const [role, setRole] = useState(""),
    [events, setEvents] = useState<EventItem[]>([]),
    [rooms, setRooms] = useState<any[]>([]),
    [notice, setNotice] = useState("");
  const [selected, setSelected] = useState<EventItem | null>(null),
    [applicants, setApplicants] = useState<any[] | null>(null);
  const [hold, setHold] = useState<{
      eventId: number;
      bookingId: string;
      expires: number;
    } | null>(null),
    [seconds, setSeconds] = useState(0);
  const [ticketForm, setTicketForm] = useState({
    participant_name: "",
    roll_number: "",
    department: "",
  });
  const [eventForm, setEventForm] = useState({
    name: "",
    description: "",
    starts_at: "",
    registration_deadline: "",
    capacity: 50,
    room_id: "",
  });
  const load = () =>
    Promise.all([
      api.get("/auth/me"),
      api.get("/event-registration"),
      api.get("/resources/rooms"),
    ])
      .then(([m, e, r]) => {
        setRole(
          m.data.roles?.some((r: string) =>
            ["FACULTY", "WELFARE", "DIRECTOR", "EVENTS", "ADMIN"].includes(r),
          )
            ? "FACULTY"
            : "STUDENT",
        );
        setTicketForm((x) => ({
          ...x,
          participant_name: m.data.full_name || m.data.username,
        }));
        setEvents(e.data);
        setRooms(
          r.data.filter((x: any) =>
            ["HALL", "AUDITORIUM"].includes(x.room_type),
          ),
        );
      })
      .catch((e) => setNotice(messageFrom(e)));
  useEffect(() => {
    load();
  }, []);
  useEffect(() => {
    if (!hold) return;
    const tick = () => {
      const n = Math.max(0, Math.ceil((hold.expires - Date.now()) / 1000));
      setSeconds(n);
      if (!n) {
        setNotice("Your ticket hold expired.");
        setHold(null);
      }
    };
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [hold]);
  const createEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/event-registration", {
        ...eventForm,
        capacity: Number(eventForm.capacity),
        room_id: eventForm.room_id ? Number(eventForm.room_id) : null,
        registration_deadline: eventForm.registration_deadline || null,
      });
      setNotice("Registration event published.");
      load();
    } catch (x) {
      setNotice(messageFrom(x));
    }
  };
  const reserve = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected) return;
    try {
      const { data } = await api.post(
        `/event-registration/${selected.id}/hold`,
        ticketForm,
      );
      setHold({
        eventId: selected.id,
        bookingId: data.booking_id,
        expires: new Date(data.expires_at).getTime(),
      });
      setNotice(data.message);
    } catch (x) {
      setNotice(messageFrom(x));
    }
  };
  const confirm = async () => {
    if (!hold) return;
    try {
      await api.post(`/event-registration/${hold.eventId}/confirm`, {
        booking_id: hold.bookingId,
      });
      setNotice("Your event ticket is confirmed.");
      setHold(null);
      setSelected(null);
      load();
    } catch (x) {
      setNotice(messageFrom(x));
    }
  };
  const viewApplicants = async (id: number) => {
    try {
      const { data } = await api.get(`/event-registration/${id}/applicants`);
      setApplicants(data.applicants);
      setSelected(events.find((e) => e.id === id) || null);
    } catch (x) {
      setNotice(messageFrom(x));
    }
  };
  const time = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
  return (
    <div className="ticket-page">
      <section className="ticket-hero">
        <p className="kicker">
          {role === "FACULTY" ? "FACULTY EVENT DESK" : "STUDENT DISCOVERY"}
        </p>
        <h1>
          {role === "FACULTY" ? (
            <>
              Publish.
              <br />
              <em>Fill the room.</em>
            </>
          ) : (
            <>
              Find it.
              <br />
              <em>Claim your seat.</em>
            </>
          )}
        </h1>
        <Ticket />
      </section>
      <section className="ticket-body">
        {notice && <div className="booking-notice">{notice}</div>}
        {role === "FACULTY" && (
          <form className="publish-form" onSubmit={createEvent}>
            <div>
              <p className="kicker">CREATE REGISTRATION EVENT</p>
              <h2>Open the doors.</h2>
            </div>
            <label>
              Event name
              <input
                required
                value={eventForm.name}
                onChange={(e) =>
                  setEventForm({ ...eventForm, name: e.target.value })
                }
              />
            </label>
            <label>
              Starts
              <input
                type="datetime-local"
                required
                value={eventForm.starts_at}
                onChange={(e) =>
                  setEventForm({ ...eventForm, starts_at: e.target.value })
                }
              />
            </label>
            <label>
              Deadline
              <input
                type="datetime-local"
                value={eventForm.registration_deadline}
                onChange={(e) =>
                  setEventForm({
                    ...eventForm,
                    registration_deadline: e.target.value,
                  })
                }
              />
            </label>
            <label>
              Capacity
              <input
                type="number"
                min="1"
                required
                value={eventForm.capacity}
                onChange={(e) =>
                  setEventForm({ ...eventForm, capacity: +e.target.value })
                }
              />
            </label>
            <label>
              Venue
              <select
                value={eventForm.room_id}
                onChange={(e) =>
                  setEventForm({ ...eventForm, room_id: e.target.value })
                }
              >
                <option value="">No specific hall</option>
                {rooms.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.code}
                  </option>
                ))}
              </select>
            </label>
            <label className="wide">
              Description
              <textarea
                value={eventForm.description}
                onChange={(e) =>
                  setEventForm({ ...eventForm, description: e.target.value })
                }
              />
            </label>
            <button className="event-submit wide">
              Publish event <ArrowRight />
            </button>
          </form>
        )}
        <div className="ticket-heading">
          <div>
            <p className="kicker">
              {role === "FACULTY" ? "YOUR EVENTS" : "OPEN REGISTRATIONS"}
            </p>
            <h2>
              {role === "FACULTY"
                ? "Applicant overview"
                : "What's happening next?"}
            </h2>
          </div>
          <span>
            {events.length} EVENT{events.length === 1 ? "" : "S"}
          </span>
        </div>
        <div className="ticket-grid">
          {events.map((event, i) => (
            <article key={event.id} style={{ "--i": i } as React.CSSProperties}>
              <div className="ticket-count">
                <strong>{event.confirmed_count}</strong>
                <span>/ {event.capacity} CONFIRMED</span>
              </div>
              <p className="kicker">{event.room_code || "CAMPUS EVENT"}</p>
              <h3>{event.name}</h3>
              <p>{new Date(event.starts_at).toLocaleString()}</p>
              <div className="seat-meter">
                <i
                  style={{
                    width: `${Math.min(100, (event.applicant_count / event.capacity) * 100)}%`,
                  }}
                />
              </div>
              <button
                onClick={() =>
                  role === "FACULTY"
                    ? viewApplicants(event.id)
                    : setSelected(event)
                }
              >
                {role === "FACULTY" ? (
                  <>
                    <Users /> View applicants
                  </>
                ) : (
                  <>
                    Reserve a seat <ArrowRight />
                  </>
                )}
              </button>
            </article>
          ))}
        </div>
      </section>
      {selected && role === "STUDENT" && !hold && (
        <div className="modal-backdrop">
          <form className="booking-modal" onSubmit={reserve}>
            <button
              type="button"
              className="modal-close"
              onClick={() => setSelected(null)}
            >
              <X />
            </button>
            <p className="kicker">TEN-MINUTE SEAT HOLD</p>
            <h2>{selected.name}</h2>
            <div className="form-grid">
              <label>
                Name
                <input
                  required
                  value={ticketForm.participant_name}
                  onChange={(e) =>
                    setTicketForm({
                      ...ticketForm,
                      participant_name: e.target.value,
                    })
                  }
                />
              </label>
              <label>
                Roll number
                <input
                  required
                  value={ticketForm.roll_number}
                  onChange={(e) =>
                    setTicketForm({
                      ...ticketForm,
                      roll_number: e.target.value,
                    })
                  }
                />
              </label>
              <label className="wide">
                Department
                <input
                  required
                  value={ticketForm.department}
                  onChange={(e) =>
                    setTicketForm({ ...ticketForm, department: e.target.value })
                  }
                />
              </label>
              <button className="event-submit wide">
                Hold my seat <ArrowRight />
              </button>
            </div>
          </form>
        </div>
      )}
      {hold && (
        <div className="ticket-hold">
          <Clock3 />
          <strong>{time}</strong>
          <div>
            <p className="kicker">SEAT HELD</p>
            <span>Confirm before the timer ends.</span>
          </div>
          <button onClick={confirm}>Confirm ticket</button>
        </div>
      )}
      {applicants && (
        <div className="modal-backdrop">
          <div className="booking-modal">
            <button
              className="modal-close"
              onClick={() => {
                setApplicants(null);
                setSelected(null);
              }}
            >
              <X />
            </button>
            <p className="kicker">ACTIVE APPLICANTS</p>
            <h2>{selected?.name}</h2>
            <div className="applicant-table">
              {applicants.map((a, i) => (
                <div key={a.roll_number}>
                  <span>0{i + 1}</span>
                  <b>{a.participant_name}</b>
                  <small>
                    {a.roll_number} · {a.department}
                  </small>
                  <em>{a.status}</em>
                </div>
              ))}
              {!applicants.length && (
                <div className="empty">No applicants yet.</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
