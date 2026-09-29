import { useCallback, useEffect, useRef, useState } from 'react'
import { Activity, AlertTriangle, ChevronRight, CloudLightning, Crosshair, FastForward, Layers, Pause, Play, RotateCcw, Satellite, Zap } from 'lucide-react'

type Point = { lat: number; lon: number }
type Cell = Point & { id: string; peak_dbz: number; area_km2: number; radius_km: number; age_min: number; speed_kmh: number; heading_deg: number; trend_dbz_per_10min: number; severity: string; ci_score: number; ci_level: string; lightning_risk_pct: number; lightning_level: string; history: (Point & { frame: number; peak_dbz: number })[]; forecast: (Point & { minutes: number; peak_dbz: number; severity: string; radius_km: number })[]; outline: number[][]; lightning_hazard_polygon: number[][] }
type Locality = Point & { id: string; name: string; eta_min: number | null; risk_pct: number; risk_level: string; lightning_risk_pct: number; storm_severity: string; distance_to_path_km: number | null; source_cell_id: string | null }
type Alert = { id: string; event: string; severity: string; location: string; eta_min: number; lightning_risk_pct: number; recommended_action: string; channels: string[] }
type State = {
  scenario: { name: string; frame: number; max_frame: number; step_minutes: number; time: string; elapsed_minutes: number; complete: boolean }
  weather: { radar: { timestamp: string; radars: { id: string; status: string }[]; grid: { latitudes: number[]; longitudes: number[]; reflectivity_dbz: number[][] } }; satellite: { timestamp: string; cloud_top_temperature_c: number; cooling_rate_c_per_10min: number; cloud_polygon: number[][] }; lightning: { timestamp: string; recent_count: number; strikes: (Point & { id: string; intensity_ka: number })[] }; nwp: { timestamp: string; cape_j_kg: number; cin_j_kg: number; relative_humidity_pct: number; wind_u_ms: number; wind_v_ms: number } }
  cells: Cell[]; localities: Locality[]; alerts: Alert[]; explanations: string[]; forecast_horizons: number[]
}
type LayerKey = 'radar' | 'satellite' | 'lightning' | 'tracks' | 'risk'
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')
const BOUNDS = { west: 80.9, east: 82.2, south: 20.85, north: 21.615 }
const fmtTime = (value: string) => new Intl.DateTimeFormat('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Kolkata' }).format(new Date(value))
const riskClass = (v: string) => v.toLowerCase()
const x = (lon: number) => ((lon - BOUNDS.west) / (BOUNDS.east - BOUNDS.west)) * 1000
const y = (lat: number) => ((BOUNDS.north - lat) / (BOUNDS.north - BOUNDS.south)) * 650
const polygon = (points: number[][]) => points.map(([lat, lon]) => `${x(lon)},${y(lat)}`).join(' ')
const radarColor = (dbz: number) => dbz >= 55 ? '#ec434c' : dbz >= 45 ? '#f18a37' : dbz >= 35 ? '#e9c34a' : dbz >= 25 ? '#75bd76' : dbz >= 15 ? '#42a9a5' : '#306986'

async function getState(path = '/state', init?: RequestInit): Promise<State> {
  const res = await fetch(`${API_BASE_URL}/api${path}`, init)
  if (!res.ok) throw new Error(`Weather service returned ${res.status}`)
  return res.json()
}

function Metric({ label, value, unit, detail }: { label: string; value: string | number; unit?: string; detail?: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}<small>{unit}</small></strong>{detail && <em>{detail}</em>}</div>
}

function MapView({ data, layers, horizon, selectedCell, selectedLocation, onCell, onLocation }: { data: State; layers: Record<LayerKey, boolean>; horizon: number; selectedCell: string | null; selectedLocation: string | null; onCell: (id: string) => void; onLocation: (id: string) => void }) {
  const radar = data.weather.radar.grid
  const primary = data.cells.find(c => c.id === selectedCell) || data.cells[0]
  return <div className="map-wrap">
    <div className="map-caption"><Crosshair size={14}/><span>RAIPUR FORECAST DOMAIN</span><span className="map-caption-right">21.25°N · 81.63°E / EPSG:4326</span></div>
    <svg className="weather-map" viewBox="0 0 1000 650" role="img" aria-label="Offline weather map showing radar, storm cells, lightning, trajectories, risk zones and localities">
      <defs>
        <pattern id="grid" width="100" height="100" patternUnits="userSpaceOnUse"><path d="M 100 0 L 0 0 0 100" fill="none" stroke="#274456" strokeWidth=".7" opacity=".7"/></pattern>
        <pattern id="terrain" width="12" height="12" patternUnits="userSpaceOnUse"><path d="M0 12L12 0" stroke="#1a3441" strokeWidth=".5" opacity=".4"/></pattern>
        <filter id="soft"><feGaussianBlur stdDeviation="9"/></filter>
      </defs>
      <rect width="1000" height="650" fill="#0b1c2a"/>
      <path d="M0,75 C180,46 260,110 402,54 S676,19 1000,100 L1000,650 L0,650Z" fill="#122b35"/>
      <path d="M0,332 C151,290 221,381 361,345 S598,266 762,335 S942,290 1000,309 L1000,650 L0,650Z" fill="#17323a" opacity=".72"/>
      <rect width="1000" height="650" fill="url(#terrain)"/>
      <path d="M73 0 C115 95 156 163 228 225 S332 323 345 422 S352 562 432 650" className="map-river"/>
      <path d="M0 264 C199 294 315 345 453 360 S676 349 1000 378 M335 0 C395 189 460 283 580 370 S757 509 856 650 M0 488 C186 470 312 482 470 458 S797 480 1000 513" className="map-road"/>
      <path d="M163 0L200 99 334 145 399 247 541 270 613 370 710 397 801 478 1000 462 M52 650L145 562 284 557 415 491 566 515 695 459 1000 522" className="map-boundary"/>
      <rect width="1000" height="650" fill="url(#grid)"/>
      {[21.0,21.2,21.4,21.6].map(lat=><text key={lat} x="9" y={y(lat)-5} className="grid-label">{lat.toFixed(1)}°N</text>)}
      {[81.0,81.3,81.6,81.9,82.2].map(lon=><text key={lon} x={x(lon)+4} y="643" className="grid-label">{lon.toFixed(1)}°E</text>)}
      {layers.satellite && <polygon points={polygon(data.weather.satellite.cloud_polygon)} fill="#7c9aa8" opacity=".12" stroke="#a8cad1" strokeWidth="2" strokeDasharray="10 8"/>}
      {layers.radar && radar.reflectivity_dbz.flatMap((row, i)=>row.map((v,j)=>v>=9 ? <rect key={`${i}-${j}`} x={x(radar.longitudes[j]) - 7.7} y={y(radar.latitudes[i]) - 7.2} width="15.5" height="14.6" fill={radarColor(v)} opacity={v>=25?.66:.31} />:null))}
      {layers.risk && data.cells.map(c=><polygon key={`hazard-${c.id}`} points={polygon(c.lightning_hazard_polygon)} fill="#ef6442" fillOpacity={c.lightning_risk_pct/100*.16} stroke="#f29a58" strokeOpacity={c.lightning_risk_pct/100*.85} strokeWidth="2" strokeDasharray="7 5"/>)}
      {layers.tracks && data.cells.map(c=><g key={`track-${c.id}`}>
        <polyline points={c.history.map(p=>`${x(p.lon)},${y(p.lat)}`).join(' ')} fill="none" stroke="#8bd7df" strokeWidth="2.5" opacity=".8"/>
        {c.forecast.filter(p=>p.minutes<=horizon).map((p,i)=><g key={p.minutes}><line x1={x(i ? c.forecast[i-1].lon : c.lon)} y1={y(i ? c.forecast[i-1].lat : c.lat)} x2={x(p.lon)} y2={y(p.lat)} stroke="#fff0a7" strokeWidth="2" strokeDasharray="7 6" opacity=".8"/><circle cx={x(p.lon)} cy={y(p.lat)} r={i===0?8:6} fill="#e8b953" stroke="#fff0ba" strokeWidth="1.5"/><text x={x(p.lon)+11} y={y(p.lat)-8} className="forecast-label">+{p.minutes}m</text></g>)}
      </g>)}
      {layers.lightning && data.weather.lightning.strikes.map(s=><g key={s.id} transform={`translate(${x(s.lon)},${y(s.lat)})`}><circle r="7" fill="#ffbb50" opacity=".16"/><path d="M1 -6L-3 1H0L-1 6L4 -2H1Z" fill="#ffd17e"/></g>)}
      {data.cells.map(c=><g key={c.id} className="map-hit" onClick={()=>onCell(c.id)} tabIndex={0} role="button" aria-label={`Select storm ${c.id}`} onKeyDown={e=>e.key==='Enter'&&onCell(c.id)}>
        <polygon points={polygon(c.outline)} fill="none" stroke={c.id===primary?.id?'#f9dc81':'#8bd7df'} strokeWidth={c.id===primary?.id?2.7:1.5} opacity=".9"/>
        <circle cx={x(c.lon)} cy={y(c.lat)} r="14" fill="#081a28" stroke="#f0ca6b" strokeWidth="2.5"/>
        <circle cx={x(c.lon)} cy={y(c.lat)} r="5" fill="#f2bd4d"/>
        <rect x={x(c.lon)+18} y={y(c.lat)-27} width="88" height="24" rx="3" fill="#071723" stroke="#49616b"/>
        <text x={x(c.lon)+28} y={y(c.lat)-10} className="cell-label">{c.id} · {Math.round(c.peak_dbz)} dBZ</text>
      </g>)}
      {data.localities.map(loc=><g key={loc.id} className="map-hit" onClick={()=>onLocation(loc.id)} tabIndex={0} role="button" aria-label={`Select ${loc.name}`} onKeyDown={e=>e.key==='Enter'&&onLocation(loc.id)}>
        <circle cx={x(loc.lon)} cy={y(loc.lat)} r={loc.id===selectedLocation?11:8} fill={loc.risk_pct>=55?'#e66b52':'#79d5d5'} opacity=".2"/>
        <circle cx={x(loc.lon)} cy={y(loc.lat)} r="3.5" fill={loc.risk_pct>=55?'#ff9a65':'#e0f2ed'} stroke="#071b25" strokeWidth="1"/>
        <text x={x(loc.lon)+9} y={y(loc.lat)+5} className="location-label">{loc.name}</text>
      </g>)}
    </svg>
    <div className="map-scale">↔ 20 km <span>LOCAL OFFLINE BASEMAP</span></div>
    <div className="map-legend"><span><i className="radar-gradient"/>Radar reflectivity</span><span>10</span><span>25</span><span>40</span><span>55+ dBZ</span></div>
  </div>
}

export default function App() {
  const [data, setData] = useState<State | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [playing, setPlaying] = useState(false)
  const [selectedCell, setSelectedCell] = useState<string | null>(null)
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null)
  const [horizon, setHorizon] = useState(60)
  const [layers, setLayers] = useState<Record<LayerKey, boolean>>({radar:true,satellite:true,lightning:true,tracks:true,risk:true})
  const lock = useRef(false)
  const load = useCallback(async (path = '/state', init?: RequestInit) => {
    if (lock.current) return
    lock.current = true; setBusy(true)
    try { const result = await getState(path, init); setData(result); setError(''); if(result.scenario.complete) setPlaying(false) }
    catch (e) { setError(e instanceof Error ? e.message : 'Weather service unavailable'); setPlaying(false) }
    finally { lock.current = false; setBusy(false) }
  }, [])
  useEffect(()=>{ void load() },[load])
  useEffect(()=>{ if(!playing) return; const timer = window.setInterval(()=>{void load('/scenario/advance',{method:'POST'})},1800); return ()=>window.clearInterval(timer) },[playing,load])
  const mutate = (path: string, body?: object) => { setPlaying(false); void load(path,{method:'POST',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined}) }
  const selected = data?.cells.find(c=>c.id===selectedCell) || data?.cells[0]
  const location = data?.localities.find(l=>l.id===selectedLocation)
  const displayTime = data ? fmtTime(data.scenario.time) : '--:--'
  return <div className="app-shell">
    <header className="topbar"><div className="brand"><div className="brand-mark"><CloudLightning size={24}/></div><div><strong>MeghDrishti</strong><span>THUNDERSTORM & LIGHTNING NOWCASTING</span></div></div><div className="top-status"><span className="live-dot"/> SCENARIO ACTIVE <span className="top-divider"/> RAIPUR · CHHATTISGARH <span className="top-divider"/><strong>{displayTime} IST</strong></div></header>
    {error && <div className="error-banner"><AlertTriangle size={18}/>{import.meta.env.DEV ? `${error}. Start the backend on port 8000, then ` : 'Weather service is unavailable or failed to respond. '}<button onClick={()=>void load()}>Retry</button>.</div>}
    {!data ? <div className="loading">Connecting to MeghDrishti weather service…</div> : <>
      <div className="headline"><div><div className="eyebrow">SIH26072 / OPERATIONAL DEMONSTRATION</div><h1>Thunderstorm command overview</h1><p>Multi-source observations → local impact and lightning warnings</p></div><div className="headline-right"><div><span>OBSERVATION TIME</span><strong>{displayTime} IST</strong></div><div><span>SCENARIO ELAPSED</span><strong>T + {String(data.scenario.elapsed_minutes).padStart(3,'0')} MIN</strong></div></div></div>
      <main className="dashboard">
        <aside className="sidebar left">
          <section className="panel"><div className="section-title"><span>DATA INGESTION</span><Activity size={15}/></div>
            {(['radar','satellite','lightning','nwp'] as const).map((key,i)=><div className="source-row" key={key}><div className={`source-icon source-${key}`}>{i===0?<Crosshair size={17}/>:i===1?<Satellite size={17}/>:i===2?<Zap size={17}/>:<Layers size={17}/>}</div><div><strong>{key==='nwp'?'NWP / Environment':key[0].toUpperCase()+key.slice(1)}</strong><span>{key==='radar'?'2 Doppler coverages':key==='satellite'?'Cloud-top IR signal':key==='lightning'?`${data.weather.lightning.recent_count} recent strikes`:'Instability fields'}</span></div><em><i/>ONLINE</em></div>)}
            <div className="source-footer">All sources synchronized · {displayTime} IST</div></section>
          <section className="panel"><div className="section-title"><span>ATMOSPHERIC STATE</span><span className="micro">FUSED GRID</span></div><div className="metric-grid"><Metric label="CAPE" value={data.weather.nwp.cape_j_kg} unit="J/kg"/><Metric label="HUMIDITY" value={data.weather.nwp.relative_humidity_pct} unit="%"/><Metric label="CLOUD TOP" value={data.weather.satellite.cloud_top_temperature_c} unit="°C"/><Metric label="COOLING" value={data.weather.satellite.cooling_rate_c_per_10min} unit="°C/10m"/></div></section>
          <section className="panel layers-panel"><div className="section-title"><span>MAP LAYERS</span><Layers size={15}/></div>{([['radar','Radar reflectivity'],['satellite','Satellite cloud shield'],['lightning','Lightning observations'],['tracks','Cell tracks & forecast'],['risk','Lightning hazard zones']] as [LayerKey,string][]).map(([key,label])=><label key={key} className="layer-row"><span>{label}</span><input type="checkbox" checked={layers[key]} onChange={()=>setLayers(v=>({...v,[key]:!v[key]}))}/><i/></label>)}</section>
          <section className="panel why-panel"><div className="section-title"><span>WHY RISK IS CHANGING</span><ChevronRight size={15}/></div>{data.explanations.map((reason,i)=><div className="reason" key={i}><span>+</span>{reason}</div>)}<small>Transparent deterministic scoring · Demo model</small></section>
        </aside>
        <div className="center-column">
          <div className="map-head"><div><span className="status-pill"><i/> LIVE OBSERVATIONS</span><span>CONVECTIVE DOMAIN / RAIPUR</span></div><div><span>{data.cells.length} TRACKED CELL{data.cells.length!==1?'S':''}</span><span className="map-head-time">{displayTime} IST</span></div></div>
          <MapView data={data} layers={layers} horizon={horizon} selectedCell={selectedCell} selectedLocation={selectedLocation} onCell={setSelectedCell} onLocation={setSelectedLocation}/>
          <div className="control-panel"><div className="control-top"><div><div className="section-title">SCENARIO REPLAY <span className="micro">10-MIN OBSERVATION STEPS</span></div><div className="control-buttons"><button className="button-primary" onClick={()=>setPlaying(v=>!v)} disabled={busy||data.scenario.complete}>{playing?<><Pause size={15}/> Pause</>:<><Play size={15}/> {data.scenario.frame===0?'Start scenario':'Play'}</>}</button><button onClick={()=>mutate('/scenario/advance')} disabled={busy||data.scenario.complete}><FastForward size={15}/> Next step</button><button onClick={()=>mutate('/scenario/reset')} disabled={busy}><RotateCcw size={15}/> Reset demo</button></div></div><div className="forecast-picker"><label htmlFor="horizon">FORECAST VIEW</label><select id="horizon" value={horizon} onChange={e=>setHorizon(Number(e.target.value))}>{data.forecast_horizons.map(h=><option key={h} value={h}>+{h} min</option>)}</select></div></div>
            <div className="timeline"><span>T+0</span><input aria-label="Scenario timeline" type="range" min="0" max={data.scenario.max_frame} value={data.scenario.frame} onChange={e=>mutate('/scenario/seek',{frame:Number(e.target.value)})}/><span>T+120</span><strong>T + {data.scenario.elapsed_minutes} MIN</strong></div>
            <div className="timeline-markers"><span>INITIATION</span><span>INTENSIFICATION</span><span>TRACKING</span><span>LOCAL WARNING</span></div>
          </div>
          <section className={`alert-panel ${data.alerts.length?'has-alert':''}`}><div className="alert-heading"><AlertTriangle size={18}/><strong>{data.alerts.length ? `${data.alerts.length} ACTIVE LOCAL WARNING${data.alerts.length>1?'S':''}` : 'NO ACTIVE LOCAL WARNINGS'}</strong><span>THRESHOLD ENGINE</span></div>{data.alerts.length ? <div className="alert-list">{data.alerts.map(a=><div key={a.id} className="alert-item"><div><b>{a.severity} · {a.event.toUpperCase()}</b><span>{a.location} · Arrival in {a.eta_min} min · Lightning risk {a.lightning_risk_pct}%</span></div><p>{a.recommended_action}</p><small>DISSEMINATION READY: {a.channels.join(' · ')}</small></div>)}</div> : <p className="alert-empty">Monitoring storm trajectory and lightning density. Warnings appear when locality thresholds are crossed.</p>}</section>
        </div>
        <aside className="sidebar right">
          <section className="panel current-storm"><div className="section-title"><span>ACTIVE STORM CELL</span><span className="micro">{selected?.id || '—'}</span></div>{selected ? <><div className="storm-hero"><div><span>RADAR CORE</span><strong>{selected.peak_dbz}<small> dBZ</small></strong></div><span className={`risk-pill ${riskClass(selected.severity)}`}>{selected.severity}</span></div><div className="storm-stats"><Metric label="MOTION" value={selected.speed_kmh} unit="km/h"/><Metric label="HEADING" value={selected.heading_deg} unit="°"/><Metric label="AGE" value={selected.age_min} unit="min"/><Metric label="TREND" value={`${selected.trend_dbz_per_10min>0?'+':''}${selected.trend_dbz_per_10min}`} unit="dBZ/10m"/></div><div className="score-block"><div><span>CONVECTIVE INITIATION</span><strong>{selected.ci_score}%</strong></div><div className="bar"><i style={{width:`${selected.ci_score}%`}}/></div><small>{selected.ci_level} · satellite + radar + instability</small></div><div className="score-block lightning-score"><div><span>LIGHTNING RISK</span><strong>{selected.lightning_risk_pct}%</strong></div><div className="bar"><i style={{width:`${selected.lightning_risk_pct}%`}}/></div><small>{selected.lightning_level} · strikes + growth + CAPE</small></div></> : <p>No detected cell at this step.</p>}</section>
          <section className="panel"><div className="section-title"><span>SHORT-TERM NOWCAST</span><span className="micro">SELECTED CELL</span></div>{selected?.forecast.filter(f=>[15,30,60,90,120].includes(f.minutes)).map(f=><div className={`forecast-row ${f.minutes===horizon?'active':''}`} key={f.minutes} onClick={()=>setHorizon(f.minutes)}><span>+{f.minutes}m</span><div><b>{Math.round(f.peak_dbz)} dBZ</b><small>{f.severity} · {f.lat.toFixed(2)}°N, {f.lon.toFixed(2)}°E</small></div><ChevronRight size={15}/></div>)}</section>
          <section className="panel localities"><div className="section-title"><span>AFFECTED LOCALITIES</span><span className="micro">PATH IMPACT</span></div>{[...data.localities].sort((a,b)=>(b.risk_pct-a.risk_pct)).map(loc=><button className={`locality-row ${selectedLocation===loc.id?'selected':''}`} key={loc.id} onClick={()=>setSelectedLocation(loc.id)}><div><strong>{loc.name}</strong><span>{loc.eta_min===null?'Outside forecast corridor':`Arrival in ${loc.eta_min} min`}</span></div><div><b className={riskClass(loc.risk_level)}>{loc.risk_pct}%</b><small>{loc.risk_level}</small></div></button>)}{location && <div className="location-detail"><strong>{location.name}</strong><p>{location.distance_to_path_km} km from projected path · Lightning risk {location.lightning_risk_pct}%</p></div>}</section>
        </aside>
      </main>
      <footer><span>MeghDrishti / SIH26072</span><span>DETERMINISTIC SCENARIO · OFFLINE MAP · LOCAL API</span><span>FORECAST IS A DEMONSTRATION, NOT AN OFFICIAL WARNING</span></footer>
    </>}
  </div>
}
