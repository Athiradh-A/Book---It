import { useEffect, useState } from 'react'
import { FileUp, Download, CheckCircle2, AlertTriangle } from 'lucide-react'
import { api, messageFrom } from '../lib/api'

export default function TimetableAdmin(){
  const [inventoryFile,setInventoryFile]=useState<File|null>(null),[timetableFile,setTimetableFile]=useState<File|null>(null)
  const [inventoryResult,setInventoryResult]=useState<any|null>(null),[timetableResult,setTimetableResult]=useState<any|null>(null)
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[authorized,setAuthorized]=useState<boolean|null>(null)
  useEffect(()=>{api.get('/auth/me').then(r=>setAuthorized((r.data.roles||[]).includes('ADMIN'))).catch(()=>setAuthorized(false))},[])
  const inventoryTemplate=['classroom_id,building,capacity,room_type,active','C-101,AB1,40,CLASSROOM,true','W-101,AB1,40,CLASSROOM,true','E-101,AB1,40,CLASSROOM,true','C-101,AB2,40,CLASSROOM,true','W-101,AB2,40,CLASSROOM,true','E-101,AB2,40,CLASSROOM,true','C-101,AB3,40,CLASSROOM,true','W-101,AB3,40,CLASSROOM,true','E-101,AB3,40,CLASSROOM,true','C-101,AB4,40,CLASSROOM,true','W-101,AB4,40,CLASSROOM,true','E-101,AB4,40,CLASSROOM,true'].join('\\n')
  const timetableTemplate=['classroom_id,building,day_of_week,start_time,end_time,semester,course_code,course_name,faculty_email,effective_from,effective_to','C-101,AB1,MON,08:00,08:50,2026-ODD,CS101,Introduction to Computing,,2026-07-01,2026-12-31'].join('\n')
  const download=(name:string,content:string)=>{const url=URL.createObjectURL(new Blob([content],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();URL.revokeObjectURL(url)}
  const upload=async(kind:'inventory'|'timetable')=>{const file=kind==='inventory'?inventoryFile:timetableFile;if(!file)return;setBusy(true);setError('');try{const body=new FormData();body.append('file',file);const {data}=await api.post(kind==='inventory'?'/resources/rooms/import-inventory':'/resources/timetables/import-dataset',body);if(kind==='inventory')setInventoryResult(data);else setTimetableResult(data)}catch(e){setError(messageFrom(e))}finally{setBusy(false)}}
  const resultBox=(result:any)=>result&&<div className="booking-notice"><CheckCircle2/> {(result.created!==undefined?'Created '+result.created+', updated '+result.updated+'.':'Imported '+result.imported+' timetable rows.')} {result.errors?.length||0} row errors.</div>
  const errorsBox=(result:any)=>result?.errors?.length>0&&<div className="approval-list">{result.errors.map((x:any)=><article key={x.row}><AlertTriangle/><div><h3>Row {x.row} · {x.classroom_id||'Unknown classroom'}</h3><p>{x.error}</p></div></article>)}</div>
  if(authorized===null)return <div className="content-wrap"><div className="empty">Checking administrator permissions…</div></div>
  if(!authorized)return <div className="content-wrap"><div className="booking-notice">Administrator access is required to import room and timetable data.</div></div>
  return <div className="content-wrap"><div className="page-heading compact"><div><p className="kicker">ADMINISTRATION · ACADEMIC DATA</p><h1>Classroom data.</h1><p>Import the room inventory first, then import occupied timetable periods. Book-It derives free periods from the schedule and active reservations.</p></div></div>
    <section className="finder-workspace">
      <div className="ticket-heading"><div><p className="kicker">STEP 01</p><h2>Room inventory</h2></div><button className="booking-action" type="button" onClick={()=>download('classroom_inventory_template.csv',inventoryTemplate)}><Download/> Inventory template</button></div>
      <p>Each row identifies a room by its building and code. The hundreds digit in codes such as C-101 indicates the floor; the last two digits identify the room on that floor. Replace the illustrative rows with every real classroom and its actual capacity.</p>
      <form className="event-form" onSubmit={e=>{e.preventDefault();upload('inventory')}}><label className="wide">Inventory CSV<input type="file" accept=".csv,text/csv" required onChange={e=>setInventoryFile(e.target.files?.[0]||null)}/></label><button className="event-submit wide" disabled={!inventoryFile||busy}><FileUp/>{busy?'Importing…':'Import room inventory'}</button></form>
      {resultBox(inventoryResult)}{errorsBox(inventoryResult)}
      <div className="divider-line"/>
      <div className="ticket-heading"><div><p className="kicker">STEP 02</p><h2>Occupied timetable</h2></div><button className="booking-action" type="button" onClick={()=>download('classroom_timetable_template.csv',timetableTemplate)}><Download/> Timetable template</button></div>
      <p>Use one row per occupied class period. Weekdays can be MON–SUN or 0–6 (Monday is 0). Dates use YYYY-MM-DD. Leave faculty_email blank if the faculty record is not mapped yet.</p>
      <form className="event-form" onSubmit={e=>{e.preventDefault();upload('timetable')}}><label className="wide">Timetable CSV<input type="file" accept=".csv,text/csv" required onChange={e=>setTimetableFile(e.target.files?.[0]||null)}/></label><button className="event-submit wide" disabled={!timetableFile||busy}><FileUp/>{busy?'Importing…':'Import timetable'}</button></form>
      {resultBox(timetableResult)}{errorsBox(timetableResult)}{error&&<div className="booking-notice">{error}</div>}
      <p className="kicker">BUILDINGS: AB1 · AB2 · AB3 · AB4</p><p>The repository templates contain illustrative sample rows, not an official Amrita timetable. Upload the official inventory and timetable before using availability results for real bookings.</p>
    </section></div>
}
