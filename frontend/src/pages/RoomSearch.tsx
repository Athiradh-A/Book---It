import { useEffect, useState } from 'react'
import { ArrowRight, Building2, CalendarDays, Search, Users } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { api, messageFrom } from '../lib/api'

type Room={room_id:number;code:string;is_available:boolean}
type Building={id:number;name:string;code:string}
const localDate=()=>{const d=new Date();d.setMinutes(d.getMinutes()-d.getTimezoneOffset());return d.toISOString().slice(0,10)}

export default function RoomSearch(){
  const navigate=useNavigate(),[rooms,setRooms]=useState<Room[]>([]),[buildings,setBuildings]=useState<Building[]>([])
  const [params,setParams]=useState({date:localDate(),start:'09:00',end:'10:00',capacity:10,roomType:'CLASSROOM',academicBlock:'',buildingId:''})
  const [loading,setLoading]=useState(false),[notice,setNotice]=useState('Start with what you need. We’ll check the timetable, holds and maintenance.')
  useEffect(()=>{api.get('/resources/buildings').then(r=>setBuildings(r.data)).catch(()=>{})},[])
  const search=async(e?:React.FormEvent)=>{e?.preventDefault();if(params.end<=params.start){setNotice('End time must be after start time.');return}setLoading(true);try{const {data}=await api.get('/bookings/availability',{params:{date_str:params.date,start_str:params.start,end_str:params.end,capacity:params.capacity,room_type:params.roomType||undefined,academic_block:params.academicBlock||undefined,building_id:params.buildingId||undefined}});setRooms(data);setNotice(data.length?`${data.length} spaces match this moment.`:'No rooms match. Try another time, block or capacity.')}catch(err){setNotice(messageFrom(err))}finally{setLoading(false)}}
  const choose=(id:number)=>navigate(`/rooms/slots?roomId=${id}&date=${params.date}&capacity=${params.capacity}`)
  return <div className="room-finder">
    <section className="finder-hero"><div><p className="kicker">01 — FIND YOUR SPACE</p><h1>Room for<br/><em>what’s next.</em></h1></div><p>Tell us when, where and how many. Book-It checks every academic class, confirmed booking, live hold and maintenance window before showing a room.</p><div className="finder-orbit"><Building2/><span>LIVE<br/>CAMPUS</span></div></section>
    <section className="finder-workspace">
      <form className="finder-form" onSubmit={search}>
        <div className="field-number">01</div><label>Date<div><CalendarDays/><input type="date" min={localDate()} value={params.date} onChange={e=>setParams({...params,date:e.target.value})}/></div></label>
        <div className="field-number">02</div><label>Time window<div className="time-pair"><input type="time" value={params.start} onChange={e=>setParams({...params,start:e.target.value})}/><span>—</span><input type="time" value={params.end} onChange={e=>setParams({...params,end:e.target.value})}/></div></label>
        <div className="field-number">03</div><label>People<div><Users/><input type="number" min="1" value={params.capacity} onChange={e=>setParams({...params,capacity:Number(e.target.value)})}/></div></label>
        <div className="field-number">04</div><label>Building<select value={params.buildingId} onChange={e=>setParams({...params,buildingId:e.target.value})}><option value="">Every building</option>{buildings.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label>
        <div className="field-number">05</div><label>Academic block<select value={params.academicBlock} onChange={e=>setParams({...params,academicBlock:e.target.value})}><option value="">Every block</option>{['AB1','AB2','AB3','AB4'].map(x=><option key={x}>{x}</option>)}</select></label>
        <button className="finder-submit" type="submit" disabled={loading}><Search/>{loading?'Checking campus…':'Find available rooms'}</button>
      </form>
      <div className="results-head"><p className="kicker">LIVE RESULTS</p><span>{notice}</span></div>
      <div className="room-results">{rooms.map((room,i)=><button className="cinema-room-card" key={room.room_id} onClick={()=>choose(room.room_id)} style={{'--i':i} as React.CSSProperties}><span className="room-no">0{i+1}</span><div className="room-symbol"><Building2/></div><div><p>CLASSROOM · AVAILABLE</p><h2>{room.code}</h2></div><span className="room-arrow"><ArrowRight/></span></button>)}</div>
      {!loading&&!rooms.length&&<div className="finder-empty"><span>SPACE</span><p>Set your requirements and search. Only genuinely available rooms will appear here.</p></div>}
    </section>
  </div>
}
