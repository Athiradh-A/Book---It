import { ArrowDownRight, ArrowUpRight, Building2, CalendarDays, FlaskConical, Sparkles, Clock3, MapPin } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function Landing() {
  return <div className="landing">
    <header className="landing-nav"><div className="brand"><span>BOOK</span><i>•</i><span>IT</span></div><div><Link to="/login" className="text-link">Sign in</Link><Link to="/rooms" className="pill">Find a space <ArrowUpRight size={16}/></Link></div></header>
    <section className="hero nothin-hero">
      <div className="hero-rail hero-rail-left reveal"><span>Campus space</span><span>booking, simplified</span></div>
      <div className="hero-rail hero-rail-right reveal"><span>Scroll to explore</span><ArrowDownRight size={15}/></div>
      <div className="hero-center">
        <p className="hero-index reveal">000</p>
        <h1 aria-label="Book it"><span className="reveal delay-1">BOOK</span><span className="hero-mark reveal delay-2">•</span><span className="reveal delay-3">IT</span></h1>
        <p className="hero-manifesto reveal delay-3">Not just a room.<br/>A place for what happens next.</p>
        <Link to="/rooms" className="hero-cta reveal delay-3">find your space <ArrowUpRight/></Link>
      </div>
      <div className="float-object object-building" aria-hidden="true"><div className="building-face"><i/><i/><i/><i/><i/><i/></div><Building2/></div>
      <div className="float-object object-pin" aria-hidden="true"><MapPin/></div>
      <div className="float-object object-clock" aria-hidden="true"><Clock3/><b>08:50</b></div>
      <div className="float-object object-star" aria-hidden="true"><Sparkles/></div>
      <div className="float-object object-card" aria-hidden="true"><small>ROOM</small><strong>A 202</strong><span>AVAILABLE</span></div>
      <div className="chrome-loop" aria-hidden="true"/>
    </section>
    <section className="categories" aria-label="Booking categories">
      <Link to="/rooms" className="category-card cobalt"><span>01</span><Building2/><h2>Classrooms</h2><p>Timetable-aware booking with live holds.</p><ArrowUpRight/></Link>
      <Link to="/events" className="category-card ink"><span>02</span><CalendarDays/><h2>Halls & events</h2><p>Requests, decisions and approvals in one trail.</p><ArrowUpRight/></Link>
      <Link to="/amenities" className="category-card coral"><span>03</span><FlaskConical/><h2>Amenities</h2><p>Labs, equipment and facilities—reserved properly.</p><ArrowUpRight/></Link>
    </section>
    <section className="manifesto"><p>LESS SEARCHING.</p><p className="outline">MORE MAKING.</p><div>One reliable system for every campus resource.</div></section>
    <footer><div className="brand"><span>BOOK</span><i>•</i><span>IT</span></div><p>Built for campus life.</p></footer>
  </div>
}
