import { useEffect, useMemo, useState } from 'react'
import { Box, Calendar, MapPin, Search, X } from 'lucide-react'
import { api, messageFrom } from '../lib/api'

type Amenity = {id:number; name:string; category:string; description?:string; resource_kind:string; quantity:number; capacity?:number; location?:string; requires_approval:boolean; status:string}
export default function Amenities() {
  const [items,setItems]=useState<Amenity[]>([]), [search,setSearch]=useState(''), [selected,setSelected]=useState<Amenity|null>(null)
  const [notice,setNotice]=useState(''), [loading,setLoading]=useState(true)
  const [form,setForm]=useState({start_time:'',end_time:'',quantity:1,purpose:''})
  useEffect(()=>{api.get('/amenities').then(r=>setItems(r.data)).catch(e=>setNotice(messageFrom(e))).finally(()=>setLoading(false))},[])
  const filtered=useMemo(()=>items.filter(x=>(x.name+x.category).toLowerCase().includes(search.toLowerCase())),[items,search])
  const submit=async(e:React.FormEvent)=>{e.preventDefault(); if(!selected)return; try{await api.post('/amenities/bookings',{...form,amenity_id:selected.id});setNotice('Request submitted. You can follow it in My bookings.');setSelected(null)}catch(err){setNotice(messageFrom(err))}}
  return <div className="content-wrap">
    <div className="page-heading"><div><p className="kicker">BOOKABLE CAMPUS RESOURCES</p><h1>Amenities,<br/><em>without the runaround.</em></h1></div><p>Reserve shared equipment, specialist labs and campus facilities with real availability and accountable approvals.</p></div>
    <label className="search-box"><Search/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search projectors, labs, audio…"/></label>
    {notice&&<div className="notice" role="status">{notice}</div>}
    {loading?<div className="empty">Loading amenities…</div>:filtered.length===0?<div className="empty">No amenities found. Administrators can add resources through the API.</div>:
    <div className="resource-grid">{filtered.map((item,i)=><button className="resource-card" key={item.id} onClick={()=>setSelected(item)} style={{'--i':i} as React.CSSProperties}>
      <div className="resource-icon"><Box/></div><span className={`status ${item.status.toLowerCase()}`}>{item.status}</span><p>{item.category} · {item.resource_kind}</p><h2>{item.name}</h2><div className="meta"><span><MapPin/> {item.location||'Campus'}</span><span>{item.quantity} available</span></div>
    </button>)}</div>}
    {selected&&<div className="modal-backdrop" onMouseDown={()=>setSelected(null)}><div className="booking-modal" onMouseDown={e=>e.stopPropagation()}><button className="modal-close" onClick={()=>setSelected(null)}><X/></button><p className="kicker">REQUEST AMENITY</p><h2>{selected.name}</h2><p>{selected.description||'Select a period and tell the coordinator what you need it for.'}</p><form onSubmit={submit} className="form-grid"><label>Starts<input type="datetime-local" required value={form.start_time} onChange={e=>setForm({...form,start_time:e.target.value})}/></label><label>Ends<input type="datetime-local" required value={form.end_time} onChange={e=>setForm({...form,end_time:e.target.value})}/></label><label>Quantity<input type="number" min="1" max={selected.quantity} value={form.quantity} onChange={e=>setForm({...form,quantity:+e.target.value})}/></label><label className="wide">Purpose<textarea required minLength={3} value={form.purpose} onChange={e=>setForm({...form,purpose:e.target.value})}/></label><button className="primary wide" type="submit"><Calendar/> Submit request</button></form></div></div>}
  </div>
}
