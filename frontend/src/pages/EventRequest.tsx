import { useEffect, useState } from 'react'
import { ArrowRight, CalendarDays, Clock3, FileText } from 'lucide-react'
import { api, messageFrom } from '../lib/api'

type Room={id:number;code:string;room_type:string;capacity:number;academic_block?:string}
type Proposal={id:number;event_name:string;status:string;current_approval_level:number;date:string;room_id:number;expected_attendees:number}
const initialForm={event_name:'',event_category:'GENERAL',description:'',date:'',start_time:'',end_time:'',expected_attendees:50,room_id:'',department:'',responsible_faculty:'',discipline_faculty:'',infrastructure_needs:'',catering_needs:'',vehicle_needs:'',accommodation_needs:'',funding_source:'',funding_amount:'',risk_assessment:''}

export default function EventRequest(){
  const [rooms,setRooms]=useState<Room[]>([]),[proposals,setProposals]=useState<Proposal[]>([]),[roles,setRoles]=useState<string[]>([]),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false)
  const [form,setForm]=useState(initialForm),[documents,setDocuments]=useState<File[]>([]),[history,setHistory]=useState<any|null>(null)
  const load=()=>Promise.all([api.get('/auth/me'),api.get('/resources/rooms'),api.get('/events/my')]).then(([m,r,e])=>{setRoles(m.data.roles||[]);setRooms(r.data.filter((x:Room)=>['HALL','AUDITORIUM'].includes(x.room_type)));setProposals(e.data)}).catch(e=>setNotice(messageFrom(e)))
  useEffect(()=>{load()},[])
  const submit=async(e:React.FormEvent)=>{e.preventDefault();if(form.end_time<=form.start_time){setNotice('End time must be after start time.');return}setBusy(true);setNotice('');try{
    const payload={...form,room_id:Number(form.room_id),date:`${form.date}T00:00:00`,start_time:`${form.date}T${form.start_time}:00`,end_time:`${form.date}T${form.end_time}:00`,expected_attendees:Number(form.expected_attendees),funding_amount:form.funding_amount?Number(form.funding_amount):null}
    const {data}=await api.post('/events/request',payload)
    if(documents.length){const body=new FormData();documents.forEach(file=>body.append('files',file));await api.post(`/events/${data.id}/documents`,body)}
    setNotice(`Proposal #${data.id} submitted. It will move through Faculty → Student Welfare → Campus Director → Events Office.`)
    setForm(initialForm);setDocuments([]);await load()
  }catch(err){setNotice(messageFrom(err))}finally{setBusy(false)}}
  const viewHistory=async(id:number)=>{try{const {data}=await api.get(`/events/${id}/history`);setHistory(data)}catch(e){setNotice(messageFrom(e))}}
  const downloadDocument=async(eventId:number,file:any)=>{try{const {data}=await api.get(`/events/${eventId}/documents/${file.id}`,{responseType:'blob'});const url=URL.createObjectURL(data);const a=window.document.createElement('a');a.href=url;a.download=file.original_name;a.click();URL.revokeObjectURL(url)}catch(e){setNotice(messageFrom(e))}}
  const requestMeeting=async(id:number)=>{const reason=window.prompt('Briefly explain why a meeting is needed (at least 5 characters):');if(!reason?.trim())return;try{await api.post(`/events/${id}/meeting-requests`,{reason:reason.trim()});setNotice('Meeting request recorded.');await viewHistory(id)}catch(e){setNotice(messageFrom(e))}}
  const update=(key:string,value:any)=>setForm(x=>({...x,[key]:value}))
  return <div className="event-page">
    <section className="event-hero"><p className="kicker">HALLS & EVENTS</p><h1>Big ideas<br/><em>need a room.</em></h1><div className="event-disc"><CalendarDays/><span>FOUR-STAGE<br/>APPROVAL</span></div></section>
    {roles.includes('STUDENT')&&<section className="event-workspace"><div className="event-intro"><p className="kicker">DETAILED EVENT PROPOSAL</p><h2>One proposal.<br/>A visible approval trail.</h2><p>Submit the event plan, supporting documents, funding and logistics. A temporary hall hold is created after Student Welfare approval and is rechecked before final confirmation.</p></div>
    <form className="event-form" onSubmit={submit}>
      {notice&&<div className="booking-notice wide" role="status">{notice}</div>}
      <label className="wide">Event name<input required minLength={3} value={form.event_name} onChange={e=>update('event_name',e.target.value)}/></label>
      <label>Category<select value={form.event_category} onChange={e=>update('event_category',e.target.value)}><option value="GENERAL">General</option><option value="ACADEMIC">Academic</option><option value="CULTURAL">Cultural</option><option value="MAJOR">Major event</option></select></label>
      <label>Preferred hall<select required value={form.room_id} onChange={e=>update('room_id',e.target.value)}><option value="">Select a hall</option>{rooms.map(r=><option key={r.id} value={r.id}>{r.code} · {r.capacity} people</option>)}</select></label>
      <label>Date<input type="date" required min={new Date().toISOString().slice(0,10)} value={form.date} onChange={e=>update('date',e.target.value)}/></label>
      <label>Expected attendance<input type="number" min="1" required value={form.expected_attendees} onChange={e=>update('expected_attendees',Number(e.target.value))}/></label>
      <label>Starts<input type="time" required value={form.start_time} onChange={e=>update('start_time',e.target.value)}/></label>
      <label>Ends<input type="time" required value={form.end_time} onChange={e=>update('end_time',e.target.value)}/></label>
      <label>Department<input value={form.department} onChange={e=>update('department',e.target.value)} placeholder="Department / club"/></label>
      <label>Responsible faculty<input value={form.responsible_faculty} onChange={e=>update('responsible_faculty',e.target.value)}/></label>
      <label>Discipline faculty<input value={form.discipline_faculty} onChange={e=>update('discipline_faculty',e.target.value)}/></label>
      <label>Funding source<input value={form.funding_source} onChange={e=>update('funding_source',e.target.value)} placeholder="Department / sponsor / none"/></label>
      <label>Estimated funding amount<input type="number" min="0" value={form.funding_amount} onChange={e=>update('funding_amount',e.target.value)}/></label>
      <label className="wide">Event description<textarea required minLength={10} value={form.description} onChange={e=>update('description',e.target.value)}/></label>
      <label>Infrastructure / AV needs<textarea value={form.infrastructure_needs} onChange={e=>update('infrastructure_needs',e.target.value)}/></label>
      <label>Catering needs<textarea value={form.catering_needs} onChange={e=>update('catering_needs',e.target.value)}/></label>
      <label>Vehicles / transport<textarea value={form.vehicle_needs} onChange={e=>update('vehicle_needs',e.target.value)}/></label>
      <label>Accommodation needs<textarea value={form.accommodation_needs} onChange={e=>update('accommodation_needs',e.target.value)}/></label>
      <label className="wide">Risk assessment / safety plan<textarea value={form.risk_assessment} onChange={e=>update('risk_assessment',e.target.value)}/></label>
      <label className="wide">Supporting documents (PDF, DOC/DOCX, images, XLSX, PPTX; max 10 MB each)<input type="file" multiple accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.xlsx,.pptx" onChange={e=>setDocuments(Array.from(e.target.files||[]))}/><small>{documents.length?documents.map(x=>x.name).join(', '):'Attach proposals, approvals, quotations or safety documents.'}</small></label>
      <button className="event-submit wide" disabled={busy}>{busy?'Submitting proposal…':'Submit full proposal'} <ArrowRight/></button>
    </form></section>}
    {!roles.includes('STUDENT')&&<div className="booking-notice">Event proposals are submitted by student accounts. Use the approvals workspace for your assigned role.</div>}
    <section className="approval-body"><div className="ticket-heading"><div><p className="kicker">YOUR SUBMISSIONS</p><h2>Proposal tracking</h2></div><span>{proposals.length} REQUEST{proposals.length===1?'':'S'}</span></div>
      <div className="approval-list">{proposals.map(p=><article key={p.id}><div className="approval-index">#{p.id}</div><div><p className="kicker">{String(p.status).replaceAll('_',' ')}</p><h2>{p.event_name}</h2><p>Hall ID {p.room_id} · {p.expected_attendees} attendees · Stage {p.current_approval_level}/4</p></div><div className="decision-box"><button onClick={()=>viewHistory(p.id)}><FileText/> Approval history</button><button onClick={()=>requestMeeting(p.id)}><Clock3/> Request meeting</button></div></article>)}{!proposals.length&&<div className="empty">Your event proposals will appear here after submission.</div>}</div>
    </section>
    {history&&<div className="modal-backdrop"><div className="booking-modal"><button className="modal-close" onClick={()=>setHistory(null)}>×</button><p className="kicker">PROPOSAL #{history.event_id}</p><h2>{history.event_name}</h2><p>Status: {String(history.status).replaceAll('_',' ')} · Stage {history.current_approval_level}/4</p><h3>Approval history</h3><div className="applicant-table">{history.approval_history.map((x:any)=><div key={x.id}><span>Stage {x.level}</span><b>{x.decision}</b><small>{x.comment}</small><em>{x.decided_at?new Date(x.decided_at).toLocaleString():'Pending timestamp'}</em></div>)}{!history.approval_history.length&&<p>No decisions recorded yet.</p>}</div><h3>Meetings</h3><div className="applicant-table">{history.meetings.map((x:any)=><div key={x.id}><b>{x.status}</b><small>{x.reason}</small><em>{x.preferred_at?new Date(x.preferred_at).toLocaleString():'No preferred time'}</em></div>)}{!history.meetings.length&&<p>No meeting requests.</p>}</div><h3>Documents</h3>{history.documents.map((x:any)=><p key={x.id}><button onClick={()=>downloadDocument(history.event_id,x)}>{x.original_name} · {Math.ceil(x.file_size/1024)} KB</button></p>)}</div></div>}
  </div>
}
