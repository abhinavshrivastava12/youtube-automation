import { useState, useEffect, useRef } from "react"

const API = "http://127.0.0.1:5000"

const BG_OPTIONS = [
  { key:"pastel",    label:"🌸 Pastel Pink" },
  { key:"ocean",     label:"🌊 Ocean Blue" },
  { key:"rainbow",   label:"🌈 Rainbow" },
  { key:"night_sky", label:"🌙 Night Sky" },
  { key:"dreamy",    label:"💫 Dreamy Purple" },
  { key:"festive",   label:"🪔 Festive Orange" },
  { key:"nature",    label:"🌿 Nature Green" },
]

const TYPE_OPTIONS = [
  { key:"rhyme",   label:"🎵 Kids Rhyme",    desc:"Machli, Lakdi Ki Kathi..." },
  { key:"lullaby", label:"🌙 Lullaby",       desc:"Sone ke gaane, lori..." },
  { key:"poem",    label:"📝 Hindi Poem",    desc:"Kavita, shloka..." },
  { key:"song",    label:"🎶 Slow Hindi Song",desc:"Slow emotional song..." },
]

const VOICE_OPTIONS = [
  { key:"swara",  label:"👩 Swara (Female) — Best for rhymes", default:true },
  { key:"madhur", label:"👨 Madhur (Male)" },
]

export default function App() {
  const [tab, setTab]           = useState("builtin") // builtin | ai | custom
  const [builtins, setBuiltins] = useState({rhymes:{},songs:{}})
  const [form, setForm]         = useState({
    builtin_key:"", topic:"", custom_lines_raw:"",
    content_type:"rhyme", bg:"pastel", voice:"swara", channel_name:"@KidsHindiRhymes"
  })
  const [jobId, setJobId]       = useState(null)
  const [job, setJob]           = useState(null)
  const [polling, setPolling]   = useState(false)
  const pollRef = useRef(null)

  useEffect(() => {
    fetch(`${API}/api/builtins`).then(r=>r.json()).then(setBuiltins).catch(()=>{})
  }, [])

  useEffect(() => {
    if (!jobId || !polling) return
    pollRef.current = setInterval(async () => {
      try {
        const r = await fetch(`${API}/api/status/${jobId}`)
        const d = await r.json()
        setJob(d)
        if (d.status === "done" || d.status === "failed") {
          setPolling(false)
          clearInterval(pollRef.current)
        }
      } catch {}
    }, 1500)
    return () => clearInterval(pollRef.current)
  }, [jobId, polling])

  async function submit() {
    const body = {
      content_type: form.content_type,
      bg:           form.bg,
      voice:        form.voice,
      channel_name: form.channel_name,
    }
    if (tab === "builtin" && form.builtin_key) {
      body.builtin_key = form.builtin_key
    } else if (tab === "ai" && form.topic) {
      body.topic = form.topic
    } else if (tab === "custom") {
      const lines = form.custom_lines_raw.split("\n").map(l=>l.trim()).filter(Boolean)
      if (!lines.length) return alert("Lines daalo!")
      body.custom_lines = lines
      body.topic = form.topic || "Meri Kavita"
    } else {
      return alert("Kuch select/fill karo!")
    }

    setJob(null)
    const r = await fetch(`${API}/api/generate`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify(body)
    })
    const d = await r.json()
    setJobId(d.job_id)
    setJob({ status:"queued", progress:0, message:"Queue mein hai..." })
    setPolling(true)
  }

  const allBuiltins = {...builtins.rhymes, ...builtins.songs}

  return (
    <div style={{minHeight:"100vh",background:"linear-gradient(135deg,#1a0030,#0a1a3a)",color:"#fff",fontFamily:"system-ui,sans-serif",padding:"24px 16px"}}>
      <div style={{maxWidth:720,margin:"0 auto"}}>

        {/* Header */}
        <div style={{textAlign:"center",marginBottom:32}}>
          <div style={{fontSize:64}}>🐰</div>
          <h1 style={{margin:"8px 0 4px",fontSize:28,fontWeight:800,background:"linear-gradient(90deg,#ff9de2,#a78bfa)",WebkitBackgroundClip:"text",WebkitTextFillColor:"transparent"}}>
            Kids Hindi Rhymes & Songs
          </h1>
          <p style={{color:"#aaa",fontSize:14}}>Karaoke-style • Best Hindi Voice • YouTube Shorts</p>
        </div>

        {/* Common settings */}
        <div style={{background:"rgba(255,255,255,0.06)",borderRadius:16,padding:20,marginBottom:20}}>
          <h3 style={{margin:"0 0 14px",fontSize:16,color:"#c8b6ff"}}>⚙️ Settings</h3>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
            <div>
              <label style={{fontSize:12,color:"#aaa",display:"block",marginBottom:4}}>Content Type</label>
              <select value={form.content_type}
                onChange={e=>setForm(f=>({...f,content_type:e.target.value}))}
                style={selectStyle}>
                {TYPE_OPTIONS.map(o=><option key={o.key} value={o.key}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{fontSize:12,color:"#aaa",display:"block",marginBottom:4}}>Background Theme</label>
              <select value={form.bg}
                onChange={e=>setForm(f=>({...f,bg:e.target.value}))}
                style={selectStyle}>
                {BG_OPTIONS.map(o=><option key={o.key} value={o.key}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{fontSize:12,color:"#aaa",display:"block",marginBottom:4}}>Voice</label>
              <select value={form.voice}
                onChange={e=>setForm(f=>({...f,voice:e.target.value}))}
                style={selectStyle}>
                {VOICE_OPTIONS.map(o=><option key={o.key} value={o.key}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{fontSize:12,color:"#aaa",display:"block",marginBottom:4}}>Channel Name</label>
              <input value={form.channel_name}
                onChange={e=>setForm(f=>({...f,channel_name:e.target.value}))}
                style={inputStyle} placeholder="@YourChannel" />
            </div>
          </div>
        </div>

        {/* Tab selector */}
        <div style={{display:"flex",gap:8,marginBottom:16}}>
          {[["builtin","📚 Builtin Rhymes"],["ai","🤖 AI se Banao"],["custom","✏️ Apni Lines"]].map(([k,l])=>(
            <button key={k} onClick={()=>setTab(k)}
              style={{flex:1,padding:"10px 0",borderRadius:12,border:"none",cursor:"pointer",
                      background: tab===k ? "linear-gradient(135deg,#ff9de2,#a78bfa)" : "rgba(255,255,255,0.08)",
                      color: tab===k ? "#1a0030" : "#ddd",fontWeight:700,fontSize:13}}>
              {l}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div style={{background:"rgba(255,255,255,0.06)",borderRadius:16,padding:20,marginBottom:20}}>

          {tab === "builtin" && (
            <div>
              <p style={{color:"#aaa",fontSize:13,margin:"0 0 12px"}}>
                Ready-made popular rhymes — ek click mein video!
              </p>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
                {Object.entries(allBuiltins).map(([k,v])=>(
                  <button key={k} onClick={()=>setForm(f=>({...f,builtin_key:k}))}
                    style={{padding:"12px",borderRadius:12,border:"2px solid",cursor:"pointer",textAlign:"left",
                            borderColor: form.builtin_key===k ? "#a78bfa" : "transparent",
                            background: form.builtin_key===k ? "rgba(167,139,250,0.2)" : "rgba(255,255,255,0.05)",
                            color:"#fff"}}>
                    <div style={{fontSize:22}}>{v.emoji}</div>
                    <div style={{fontSize:12,fontWeight:700,marginTop:4}}>{v.title}</div>
                    <div style={{fontSize:11,color:"#aaa",marginTop:2,textTransform:"capitalize"}}>{v.type}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {tab === "ai" && (
            <div>
              <p style={{color:"#aaa",fontSize:13,margin:"0 0 12px"}}>
                Topic do, AI Hindi mein original rhyme likhega!
              </p>
              <label style={{fontSize:12,color:"#aaa",display:"block",marginBottom:4}}>Topic / Idea</label>
              <input value={form.topic}
                onChange={e=>setForm(f=>({...f,topic:e.target.value}))}
                style={{...inputStyle, width:"100%",boxSizing:"border-box",fontSize:16,padding:"14px"}}
                placeholder="e.g. Hathi Raja, Titli, Baarish..." />
              <p style={{color:"#666",fontSize:11,marginTop:6}}>
                💡 Examples: "Hathi Raja", "Chhota Baccha", "Baarish Ki Boond", "Chanda Mama"
              </p>
            </div>
          )}

          {tab === "custom" && (
            <div>
              <p style={{color:"#aaa",fontSize:13,margin:"0 0 12px"}}>
                Apni poem/rhyme ki lines likho — ek line = ek karaoke card
              </p>
              <label style={{fontSize:12,color:"#aaa",display:"block",marginBottom:4}}>Title (optional)</label>
              <input value={form.topic}
                onChange={e=>setForm(f=>({...f,topic:e.target.value}))}
                style={{...inputStyle,width:"100%",boxSizing:"border-box",marginBottom:10}}
                placeholder="Video ka title..." />
              <label style={{fontSize:12,color:"#aaa",display:"block",marginBottom:4}}>
                Lines (har line alag — Enter dabao)
              </label>
              <textarea value={form.custom_lines_raw}
                onChange={e=>setForm(f=>({...f,custom_lines_raw:e.target.value}))}
                rows={8}
                style={{...inputStyle,width:"100%",boxSizing:"border-box",resize:"vertical",lineHeight:1.8}}
                placeholder={"मछली जल की रानी है\nजीवन उसका पानी है\nहाथ लगाओ डर जाएगी\nबाहर निकालो मर जाएगी"} />
              <p style={{color:"#666",fontSize:11,marginTop:4}}>
                {form.custom_lines_raw.split("\n").filter(l=>l.trim()).length} lines
              </p>
            </div>
          )}
        </div>

        {/* Generate button */}
        <button onClick={submit}
          disabled={polling}
          style={{width:"100%",padding:"18px",borderRadius:16,border:"none",cursor:polling?"not-allowed":"pointer",
                  background: polling ? "#444" : "linear-gradient(135deg,#f72585,#7209b7)",
                  color:"#fff",fontSize:18,fontWeight:800,letterSpacing:1,
                  boxShadow: polling ? "none" : "0 4px 24px rgba(247,37,133,0.4)"}}>
          {polling ? "⏳ Video Ban Raha Hai..." : "🎬 Video Banao!"}
        </button>

        {/* Job status */}
        {job && (
          <div style={{marginTop:20,background:"rgba(255,255,255,0.06)",borderRadius:16,padding:20}}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:12}}>
              <span style={{fontWeight:700,fontSize:15}}>
                {job.status === "done"   ? "✅ Ready!" :
                 job.status === "failed" ? "❌ Error" :
                 "⏳ Progress"}
              </span>
              <span style={{fontSize:13,color:"#aaa"}}>{job.progress || 0}%</span>
            </div>

            {/* Progress bar */}
            <div style={{height:10,background:"rgba(255,255,255,0.1)",borderRadius:8,overflow:"hidden",marginBottom:12}}>
              <div style={{height:"100%",borderRadius:8,transition:"width 0.5s",
                           width:`${job.progress||0}%`,
                           background:"linear-gradient(90deg,#f72585,#a78bfa)"}} />
            </div>

            <p style={{color:"#ccc",fontSize:13,margin:"0 0 12px"}}>{job.message}</p>

            {/* Content preview */}
            {job.content && (
              <div style={{background:"rgba(0,0,0,0.3)",borderRadius:12,padding:14,marginBottom:12}}>
                <div style={{fontWeight:700,fontSize:14,marginBottom:8,color:"#f9c74f"}}>
                  {job.content.emoji} {job.content.title}
                </div>
                {(job.content.lines||[]).map((l,i)=>(
                  <div key={i} style={{fontSize:13,color:"#ddd",padding:"3px 0",
                                       borderLeft:"2px solid rgba(167,139,250,0.4)",paddingLeft:8,marginBottom:3}}>
                    {l}
                  </div>
                ))}
              </div>
            )}

            {job.status === "done" && (
              <a href={`${API}/api/download/${jobId}`}
                style={{display:"block",textAlign:"center",padding:"14px",borderRadius:12,
                        background:"linear-gradient(135deg,#06d6a0,#118ab2)",color:"#fff",
                        textDecoration:"none",fontWeight:800,fontSize:16}}>
                ⬇️ Video Download Karo
              </a>
            )}

            {job.status === "failed" && (
              <div style={{background:"rgba(255,50,50,0.15)",borderRadius:8,padding:10,fontSize:12,color:"#ff8080"}}>
                {job.message}
              </div>
            )}
          </div>
        )}

        <p style={{textAlign:"center",color:"#555",fontSize:12,marginTop:24}}>
          🎵 Voice: Microsoft hi-IN-SwaraNeural • Free & Best Hindi TTS
        </p>
      </div>
    </div>
  )
}

const inputStyle = {
  background:"rgba(255,255,255,0.08)",border:"1px solid rgba(255,255,255,0.15)",
  borderRadius:10,padding:"10px 14px",color:"#fff",fontSize:14,outline:"none",
}
const selectStyle = {
  ...inputStyle, width:"100%", cursor:"pointer",
}