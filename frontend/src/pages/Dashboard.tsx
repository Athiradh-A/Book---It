import { useEffect, useState } from 'react'
import { ArrowRight, Bell, Building2, CalendarDays, FlaskConical } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { api, messageFrom } from '../lib/api'

type Session={full_name?:string;username:string;roles:string[]}
export default function Dashboard(){
  const navigate=useNavigate(),[session,setSession]=useState<Session|null>(null),[bookings,setBookings]=useState<any[]>([]),[events,setEvents]=useState<any[]>([]),[amenities,setAmenities]=useState<any[]>([]),[notifications,setNotifications]=useState<any[]>([]),[error,setError]=useState('')
  useEffect(()=>{Promise.all([api.get('/auth/me'),api.get('/bookings/my'),api.get('/events/my'),api.get('/amenities/bookings/my'),api.get('/events/notifications')]).then(([me,b,e,a,n])=>{setSession(me.data);setBookings(b.data);setEvents(e.data);setAmenities(a.data);setNotifications(n.data)}).catch(x=>setError(messageFrom(x)))},[])
  const upcoming=bookings.filter(x=>x.status==='CONFIRMED'&&new Date(x.start_time)>new Date()).length
  const pending=events.filter(x=>String(x.status).startsWith('PENDING')).length+amenities.filter(x=>String(x.status).startsWith('PENDING')).length
  return <div className="dashboard-page"><section className="dashboard-hero"><p className="kicker">YOUR CAMPUS, IN ONE VIEW</p><h1>Hello,<br/><em>{session?.full_name||session?.username||'there'}.</em></h1><div className="role-line">{session?.roles?.map(r=><span key={r}>{r}</span>)}</div></section>
    <section className="dashboard-body">{error&&<div className="booking-notice">{error}</div>}<div className="metric-row"><article><span>01</span><strong>{upcoming}</strong><p>UPCOMING ROOMS</p></article><article><span>02</span><strong>{pending}</strong><p>PENDING REQUESTS</p></article><article><span>03</span><strong>{notifications.filter(n=>!n.is_read).length}</strong><p>NEW NOTIFICATIONS</p></article></div>
      <div className="dashboard-grid"><div><p className="kicker">BOOK SOMETHING</p><div className="quick-grid"><button onClick={()=>navigate('/rooms')}><Building2/><span><b>Classroom</b>Instant hold</span><ArrowRight/></button><button onClick={()=>navigate('/events')}><CalendarDays/><span><b>Hall & event</b>Approval workflow</span><ArrowRight/></button><button onClick={()=>navigate('/amenities')}><FlaskConical/><span><b>Amenity</b>Equipment & labs</span><ArrowRight/></button></div></div><div><p className="kicker">LATEST UPDATES</p><div className="notification-stack">{notifications.slice(0,4).map(n=><article key={n.id}><Bell/><div><p>{n.message}</p><time>{new Date(n.created_at).toLocaleString()}</time></div></article>)}{!notifications.length&&<div className="empty">No notifications yet.</div>}</div></div></div>
    </section></div>
}
