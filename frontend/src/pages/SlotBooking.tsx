import { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, ArrowRight, Check, Clock3, ShieldCheck } from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api, messageFrom } from '../lib/api'

type Slot = { slot:number; start:string; end:string; status:string }

export default function SlotBooking() {
  const [query] = useSearchParams(), navigate = useNavigate()
  const roomId = Number(query.get('roomId')), date = query.get('date') || ''
  const attendees = Number(query.get('capacity') || 1)
  const [slots,setSlots]=useState<Slot[]>([]), [selected,setSelected]=useState<number[]>([])
  const [hold,setHold]=useState<{id:number;expiresAt:number}|null>(null), [seconds,setSeconds]=useState(0)
  const [purpose,setPurpose]=useState('Study / meeting'), [notice,setNotice]=useState(''), [loading,setLoading]=useState(true)

  const load=async()=>{setLoading(true);try{const {data}=await api.get(`/bookings/slots/${roomId}`,{params:{date}});setSlots(data.slots)}catch(e){setNotice(messageFrom(e))}finally{setLoading(false)}}
  useEffect(()=>{if(roomId&&date)load()},[roomId,date])
  useEffect(()=>{if(!hold)return;const tick=()=>{const left=Math.max(0,Math.ceil((hold.expiresAt-Date.now())/1000));setSeconds(left);if(!left){setHold(null);setSelected([]);setNotice('Your hold expired. The slots are available to others again.');load()}};tick();const id=window.setInterval(tick,1000);return()=>window.clearInterval(id)},[hold])

  const selectedSlots=useMemo(()=>slots.filter(s=>selected.includes(s.slot)).sort((a,b)=>a.slot-b.slot),[slots,selected])
  const toggle=(slot:Slot)=>{
    if(hold||slot.status!=='AVAILABLE')return
    if(selected.includes(slot.slot)){setSelected(selected.filter(n=>n!==slot.slot));return}
    const next=[...selected,slot.slot].sort((a,b)=>a-b)
    if(next.some((n,i)=>i>0&&n!==next[i-1]+1)){setNotice('Choose consecutive slots only.');return}
    setNotice('');setSelected(next)
  }
  const createHold=async()=>{
    if(!selectedSlots.length)return
    try{const {data}=await api.post('/bookings/classroom/hold',{room_id:roomId,start_time:`${date}T${selectedSlots[0].start}:00`,end_time:`${date}T${selectedSlots.at(-1)!.end}:00`,expected_attendees:attendees});setHold({id:data.hold_id,expiresAt:new Date(data.expires_at).getTime()});setNotice('Space secured. Confirm before the timer reaches zero.')}catch(e){setNotice(messageFrom(e));load()}
  }
  const confirm=async()=>{if(!hold)return;try{await api.post('/bookings/classroom/confirm',{hold_id:hold.id,purpose,expected_attendees:attendees});setNotice('Booking confirmed — the room is yours.');setHold(null);setSelected([]);load()}catch(e){setNotice(messageFrom(e))}}
  const clock=`${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}`
  if(!roomId||!date)return <div className="content-wrap"><div className="empty">Room or date is missing.</div></div>

  return <div className="booking-experience">
    <section className="booking-title"><button className="back-link" onClick={()=>navigate(-1)}><ArrowLeft/> Back to spaces</button><p className="kicker">STEP 02 — SELECT TIME</p><h1>Make time<br/><em>for the idea.</em></h1><div className="booking-context"><span>ROOM {roomId}</span><span>{new Date(date+'T12:00').toLocaleDateString(undefined,{weekday:'long',month:'long',day:'numeric'})}</span><span>{attendees} PEOPLE</span></div></section>
    <section className="slot-panel">
      <div className="slot-panel-head"><div><p className="kicker">ELEVEN ACADEMIC SLOTS</p><h2>Choose one or more<br/>consecutive periods.</h2></div><div className="legend"><span><i className="available"/>Available</span><span><i className="occupied"/>Occupied</span><span><i className="chosen"/>Selected</span></div></div>
      {notice&&<div className="booking-notice" role="status">{notice}</div>}
      {loading?<div className="empty">Checking the timetable…</div>:<div className="slot-grid">{slots.map(s=><button key={s.slot} onClick={()=>toggle(s)} disabled={s.status!=='AVAILABLE'||!!hold} className={`slot-tile ${selected.includes(s.slot)?'selected':''} ${s.status!=='AVAILABLE'?'unavailable':''}`}><span>0{s.slot}</span><strong>{s.start}</strong><small>TO {s.end}</small><b>{selected.includes(s.slot)?'SELECTED':s.status.replaceAll('_',' ')}</b></button>)}</div>}
      <div className="selection-bar"><div><span>YOUR SELECTION</span><strong>{selectedSlots.length?`${selectedSlots[0].start} — ${selectedSlots.at(-1)!.end}`:'Choose a starting slot'}</strong></div><button className="booking-action" disabled={!selected.length||!!hold} onClick={createHold}>Hold selected slots <ArrowRight/></button></div>
    </section>
    {hold&&<aside className="hold-drawer"><div className="timer-ring"><Clock3/><strong>{clock}</strong><span>REMAINING</span></div><div><p className="kicker">TEMPORARY HOLD ACTIVE</p><h2>Your space is waiting.</h2><p>No one else can claim these slots while the timer is active.</p><label>Purpose<input value={purpose} onChange={e=>setPurpose(e.target.value)} minLength={3}/></label><button className="confirm-action" onClick={confirm} disabled={seconds===0||purpose.trim().length<3}><ShieldCheck/> Confirm booking</button></div></aside>}
    {!hold&&notice.startsWith('Booking confirmed')&&<div className="success-stamp"><Check/><span>CONFIRMED</span></div>}
  </div>
}
