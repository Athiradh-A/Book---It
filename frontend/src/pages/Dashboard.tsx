
import { useEffect, useState } from 'react'
import {
  ArrowRight,
  Bell,
  Building2,
  CalendarDays,
  CheckSquare,
  FlaskConical,
  Settings,
  Ticket,
  X
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { api, messageFrom } from '../lib/api'

type Session = {
  id?: number
  full_name?: string
  username: string
  roles: string[]
}

type Action = {
  title: string
  description: string
  href: string
  Icon: typeof Building2
}

type DetailItem = {
  id: string | number
  title: string
  subtitle: string
  status: string
  details: string[]
}

type Metric = {
  key: string
  label: string
  value: number
  items: DetailItem[]
}

const roleLabels: Record<string, string> = {
  STUDENT: 'Student',
  FACULTY: 'Faculty',
  WELFARE: 'Student Welfare',
  DIRECTOR: 'Campus Director',
  EVENTS: 'Events Office',
  ADMIN: 'System Administrator'
}

const workspaces: Record<string, {
  title: string
  description: string
  actions: Action[]
}> = {
  STUDENT: {
    title: 'Student workspace',
    description: 'Create event proposals, book campus facilities, and track your own requests.',
    actions: [
      { title: 'Submit an event proposal', description: 'Request a hall or organize an event.', href: '/events', Icon: CalendarDays },
      { title: 'Find a classroom', description: 'Search rooms and available slots.', href: '/rooms', Icon: Building2 },
      { title: 'My bookings', description: 'View your own reservations and requests.', href: '/bookings', Icon: Ticket }
    ]
  },
  FACULTY: {
    title: 'Faculty workspace',
    description: 'Review classroom and event requests assigned to the Faculty approval stage.',
    actions: [
      { title: 'Faculty approval queue', description: 'Review requests awaiting your stage.', href: '/approvals', Icon: CheckSquare },
      { title: 'Room availability', description: 'Search classrooms and available slots.', href: '/rooms', Icon: Building2 },
      { title: 'My bookings', description: 'View your own reservations.', href: '/bookings', Icon: Ticket }
    ]
  },
  WELFARE: {
    title: 'Student Welfare workspace',
    description: 'Review event proposals that have progressed to the Student Welfare stage.',
    actions: [
      { title: 'Welfare approval queue', description: 'Review proposals awaiting Welfare approval.', href: '/approvals', Icon: CheckSquare },
      { title: 'Hall and event requests', description: 'Access event proposal features.', href: '/events', Icon: CalendarDays },
      { title: 'My bookings', description: 'View your own reservations.', href: '/bookings', Icon: Ticket }
    ]
  },
  DIRECTOR: {
    title: 'Campus Director workspace',
    description: 'Review proposals awaiting Campus Director approval.',
    actions: [
      { title: 'Director approval queue', description: 'Review proposals assigned to this stage.', href: '/approvals', Icon: CheckSquare },
      { title: 'Room availability', description: 'Search classrooms and available slots.', href: '/rooms', Icon: Building2 },
      { title: 'My bookings', description: 'View your own reservations.', href: '/bookings', Icon: Ticket }
    ]
  },
  EVENTS: {
    title: 'Events Office workspace',
    description: 'Complete final-stage event reviews and access event operations.',
    actions: [
      { title: 'Final approval queue', description: 'Review proposals awaiting final approval.', href: '/approvals', Icon: CheckSquare },
      { title: 'Event registration', description: 'Open event registration.', href: '/event-registration', Icon: Ticket },
      { title: 'Hall and event requests', description: 'Access event proposal features.', href: '/events', Icon: CalendarDays }
    ]
  },
  ADMIN: {
    title: 'System administration',
    description: 'Access administrative tools. System administration does not automatically grant workflow approval authority.',
    actions: [
      { title: 'Timetable administration', description: 'Manage timetable import tools.', href: '/admin/timetable', Icon: Settings },
      { title: 'Room availability', description: 'Inspect classroom availability.', href: '/rooms', Icon: Building2 },
      { title: 'My bookings', description: 'View your own reservations.', href: '/bookings', Icon: Ticket }
    ]
  }
}

const reviewerRoles = ['FACULTY', 'WELFARE', 'DIRECTOR', 'EVENTS']

function displayStatus(value: unknown) {
  return String(value ?? 'UNKNOWN').replaceAll('_', ' ')
}

function formatDate(value: unknown) {
  if (!value) return 'Date unavailable'
  const date = new Date(String(value))
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString()
}

function toBookingDetail(item: any, prefix: string): DetailItem {
  return {
    id: `${prefix}-${item.id}`,
    title: item.room_code || item.event_name || item.purpose || `Request ${item.id}`,
    subtitle: item.academic_block
      ? `Block ${item.academic_block}`
      : item.booking_type || item.room_id ? `Room ${item.room_code || item.room_id || '—'}` : 'Request details',
    status: displayStatus(item.status),
    details: [
      `Start: ${formatDate(item.start_time)}`,
      `End: ${formatDate(item.end_time)}`,
      item.purpose ? `Purpose: ${item.purpose}` : '',
      item.description ? `Description: ${item.description}` : '',
      item.expected_attendees != null ? `Expected attendees: ${item.expected_attendees}` : '',
      item.decision_comment ? `Decision comment: ${item.decision_comment}` : ''
    ].filter(Boolean)
  }
}

function toEventDetail(item: any): DetailItem {
  return {
    id: `event-${item.id}`,
    title: item.event_name || `Event proposal ${item.id}`,
    subtitle: `Hall ${item.room_id ?? '—'} · Stage ${item.current_approval_level ?? '—'}/4`,
    status: displayStatus(item.status),
    details: [
      item.description ? `Description: ${item.description}` : '',
      item.expected_attendees != null ? `Expected attendees: ${item.expected_attendees}` : '',
      item.start_time ? `Start: ${formatDate(item.start_time)}` : '',
      item.end_time ? `End: ${formatDate(item.end_time)}` : ''
    ].filter(Boolean)
  }
}

export default function Dashboard() {
  const navigate = useNavigate()

  const [session, setSession] = useState<Session | null>(null)
  const [bookings, setBookings] = useState<any[]>([])
  const [events, setEvents] = useState<any[]>([])
  const [amenities, setAmenities] = useState<any[]>([])
  const [notifications, setNotifications] = useState<any[]>([])
  const [approvalEvents, setApprovalEvents] = useState<any[]>([])
  const [approvalClassrooms, setApprovalClassrooms] = useState<any[]>([])
  const [error, setError] = useState('')
  const [modal, setModal] = useState<{ title: string; items: DetailItem[] } | null>(null)

  useEffect(() => {
    let active = true

    async function loadDashboard() {
      const results = await Promise.allSettled([
        api.get('/auth/me'),
        api.get('/bookings/my'),
        api.get('/events/my'),
        api.get('/amenities/bookings/my'),
        api.get('/events/notifications')
      ])

      if (!active) return

      const [me, myBookings, myEvents, myAmenities, myNotifications] = results

      if (me.status === 'fulfilled') {
        setSession(me.value.data)
      } else {
        setError(messageFrom(me.reason))
        return
      }

      if (myBookings.status === 'fulfilled') {
        setBookings(Array.isArray(myBookings.value.data) ? myBookings.value.data : [])
      }

      if (myEvents.status === 'fulfilled') {
        setEvents(Array.isArray(myEvents.value.data) ? myEvents.value.data : [])
      }

      if (myAmenities.status === 'fulfilled') {
        setAmenities(Array.isArray(myAmenities.value.data) ? myAmenities.value.data : [])
      }

      if (myNotifications.status === 'fulfilled') {
        setNotifications(Array.isArray(myNotifications.value.data) ? myNotifications.value.data : [])
      }

      const roles: string[] = me.value.data.roles || []
      const canReview = reviewerRoles.some(role => roles.includes(role))

      if (canReview) {
        const [pendingEvents, pendingClassrooms] = await Promise.allSettled([
          api.get('/events/pending'),
          api.get('/bookings/pending')
        ])

        if (!active) return

        if (pendingEvents.status === 'fulfilled') {
          setApprovalEvents(Array.isArray(pendingEvents.value.data) ? pendingEvents.value.data : [])
        } else {
          setError(messageFrom(pendingEvents.reason))
        }

        if (pendingClassrooms.status === 'fulfilled') {
          setApprovalClassrooms(Array.isArray(pendingClassrooms.value.data) ? pendingClassrooms.value.data : [])
        } else {
          setError(messageFrom(pendingClassrooms.reason))
        }
      }
    }

    loadDashboard().catch(e => {
      if (active) setError(messageFrom(e))
    })

    return () => {
      active = false
    }
  }, [])

  const roles = session?.roles || []
  const roleOrder = ['ADMIN', 'EVENTS', 'DIRECTOR', 'WELFARE', 'FACULTY', 'STUDENT']
  const primaryRole = roleOrder.find(role => roles.includes(role)) || 'STUDENT'
  const workspace = workspaces[primaryRole]

  const upcomingBookings = bookings.filter(
    item => item.status === 'CONFIRMED' && item.start_time && new Date(item.start_time) > new Date()
  )

  const ownPending = [
    ...bookings.filter(item => String(item.status).startsWith('PENDING')).map(item => toBookingDetail(item, 'room')),
    ...events.filter(item => String(item.status).startsWith('PENDING')).map(toEventDetail),
    ...amenities.filter(item => String(item.status).startsWith('PENDING')).map(item => toBookingDetail(item, 'amenity'))
  ]

  const approvalItems = [
    ...approvalEvents.map(toEventDetail),
    ...approvalClassrooms.map(item => toBookingDetail(item, 'classroom'))
  ]

  const canReview = reviewerRoles.some(role => roles.includes(role))

  const metrics: Metric[] = [
    {
      key: 'upcoming',
      label: 'UPCOMING ROOMS',
      value: upcomingBookings.length,
      items: upcomingBookings.map(item => toBookingDetail(item, 'upcoming'))
    },
    {
      key: 'pending',
      label: canReview ? 'AWAITING YOUR APPROVAL' : 'MY PENDING REQUESTS',
      value: canReview ? approvalItems.length : ownPending.length,
      items: canReview ? approvalItems : ownPending
    },
    {
      key: 'notifications',
      label: 'NEW NOTIFICATIONS',
      value: notifications.filter(item => !item.is_read).length,
      items: notifications.filter(item => !item.is_read).map(item => ({
        id: `notification-${item.id}`,
        title: item.message || 'Notification',
        subtitle: formatDate(item.created_at),
        status: item.is_read ? 'READ' : 'UNREAD',
        details: [item.message || 'No additional details available.']
      }))
    }
  ]

  return (
    <div className="dashboard-page">
      <section className="dashboard-hero">
        <p className="kicker">BOOK-IT / {(roleLabels[primaryRole] || primaryRole).toUpperCase()}</p>
        <h1>
          Hello,
          <br />
          <em>{session?.full_name || session?.username || 'there'}.</em>
        </h1>
        <div className="role-line">
          {roles.map(role => <span key={role}>{roleLabels[role] || role}</span>)}
        </div>
      </section>

      <section className="dashboard-body">
        {error && <div className="booking-notice">{error}</div>}

        <article className="role-workflow-card">
          <p className="kicker">YOUR ROLE WORKSPACE</p>
          <h2>{workspace.title}</h2>
          <p>{workspace.description}</p>

          {canReview && (
            <button className="btn-primary" onClick={() => navigate('/approvals')}>
              Open approval queue <ArrowRight size={16} />
            </button>
          )}

          {primaryRole === 'ADMIN' && (
            <button className="btn-primary" onClick={() => navigate('/admin/timetable')}>
              Open administration <ArrowRight size={16} />
            </button>
          )}
        </article>

        <div className="metric-row">
          {metrics.map((metric, index) => (
            <button
              type="button"
              key={metric.key}
              className="dashboard-metric-card"
              onClick={() => setModal({ title: metric.label, items: metric.items })}
              aria-label={`View ${metric.label.toLowerCase()}`}
            >
              <span className="metric-index">0{index + 1}</span>
              <strong>{metric.value}</strong>
              <span className="metric-label">{metric.label}</span>
              <span className="metric-link">View details <ArrowRight size={16} /></span>
            </button>
          ))}
        </div>

        <div className="dashboard-grid">
          <div>
            <p className="kicker">YOUR ACTIONS</p>
            <div className="quick-grid">
              {workspace.actions.map(({ title, description, href, Icon }) => (
                <button type="button" key={title} onClick={() => navigate(href)}>
                  <Icon />
                  <span>
                    <b>{title}</b>
                    {description}
                  </span>
                  <ArrowRight />
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="kicker">LATEST UPDATES</p>
            <div className="notification-stack">
              {notifications.slice(0, 4).map(item => (
                <article key={item.id}>
                  <Bell />
                  <div>
                    <p>{item.message}</p>
                    <time>{formatDate(item.created_at)}</time>
                  </div>
                </article>
              ))}
              {!notifications.length && <div className="empty">No notifications yet.</div>}
            </div>
          </div>
        </div>
      </section>

      {modal && (
        <div className="modal-backdrop" onClick={() => setModal(null)}>
          <section
            className="booking-modal dashboard-details-modal"
            role="dialog"
            aria-modal="true"
            aria-label={modal.title}
            onClick={event => event.stopPropagation()}
          >
            <button
              type="button"
              className="modal-close"
              onClick={() => setModal(null)}
              aria-label="Close details"
            >
              <X />
            </button>

            <p className="kicker">DASHBOARD DETAILS</p>
            <h2>{modal.title}</h2>
            <p>{modal.items.length} item{modal.items.length === 1 ? '' : 's'}</p>

            <div className="dashboard-modal-list">
              {modal.items.map(item => (
                <article key={item.id} className="dashboard-detail-item">
                  <span className="status">{item.status}</span>
                  <h3>{item.title}</h3>
                  <p>{item.subtitle}</p>
                  {item.details.map((detail, index) => (
                    <p key={`${item.id}-detail-${index}`} className="dashboard-detail-line">
                      {detail}
                    </p>
                  ))}
                </article>
              ))}

              {!modal.items.length && (
                <div className="empty">There are no items to show here.</div>
              )}
            </div>

            {modal.title === 'AWAITING YOUR APPROVAL' && (
              <button
                type="button"
                className="btn-primary"
                onClick={() => {
                  setModal(null)
                  navigate('/approvals')
                }}
              >
                Open approval queue <ArrowRight size={16} />
              </button>
            )}

            {modal.title === 'MY PENDING REQUESTS' && (
              <button
                type="button"
                className="btn-primary"
                onClick={() => {
                  setModal(null)
                  navigate('/bookings')
                }}
              >
                Open my bookings <ArrowRight size={16} />
              </button>
            )}
          </section>
        </div>
      )}
    </div>
  )
}
