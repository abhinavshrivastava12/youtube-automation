import { useState, useEffect, useRef } from "react"

const API = "http://127.0.0.1:5000"

const TYPES = [
  { key:"rhyme",   label:"🎵 Kids Rhyme" },
  { key:"lullaby", label:"🌙 Lullaby" },
  { key:"poem",    label:"📝 Kavita" },
  { key:"song",    label:"🎶 Slow Song" },
]
const VOICES = [
  { key:"swara",  label:"👩 Swara (Sweet Female)" },
  { key:"madhur", label:"👨 Madhur (Male)" },
]

const inp = {
  background:"rgba(255,255,255,0.08)", border:"1px solid rgba(255,255,255,0.18)",
  borderRadius:10, padding:"10px 14px", color:"#fff", fontSize:14,
  outline:"none", width:"100%", boxSizing:"border-box",
}
const sel = { ...inp, cursor:"pointer" }

export default function App() {
  const [tab, setTab]       = useState("builtin")
  const [builtins, setBlt]  = useState({})
  const [form, setF]        = useState({
    builtin_key:"", topic:"", custom_raw:"", type:"rhyme", voice:"swara",
  })
  const [jobId, setJobId]   = useState(null)
  const [job, setJob]       = useState(null)
  const [busy, setBusy]     = useState(false)

  // Music state
  const [musicFile, setMusicFile]       = useState(null)   // File object
  const [musicUploaded, setMusicUploaded] = useState(null) // {filename, duration}
  const [uploading, setUploading]       = useState(false)
  const [uploadMsg, setUploadMsg]       = useState("")
  const musicRef = useRef()
  const timer    = useRef()

  const set = (k,v) => setF(f=>({...f,[k]:v}))

  useEffect(()=>{
    fetch(`${API}/api/builtins`).then(r=>r.json()).then(setBlt).catch(()=>{})
  },[])

  useEffect(()=>{
    if (!jobId || !busy) return
    timer.current = setInterval(async()=>{
      try {
        const d = await fetch(`${API}/api/status/${jobId}`).then(r=>r.json())
        setJob(d)
        if (d.status==="done"||d.status==="failed"){
          setBusy(false); clearInterval(timer.current)
        }
      } catch {}
    }, 1500)
    return ()=>clearInterval(timer.current)
  },[jobId,busy])

  // Upload Suno MP3
  const handleMusicPick = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.name.endsWith(".mp3")) {
      setUploadMsg("❌ Sirf .mp3 file allowed hai")
      return
    }
    setMusicFile(file)
    setUploading(true)
    setUploadMsg("⏳ Upload ho raha hai...")

    const fd = new FormData()
    fd.append("file", file)
    // Map to current rhyme key automatically
    const key = form.builtin_key || form.topic.toLowerCase().split(" ")[0] || "custom"
    fd.append("rhyme_key", key)

    try {
      const data = await fetch(`${API}/api/upload-song`,{method:"POST",body:fd}).then(r=>r.json())
      if (data.ok) {
        setMusicUploaded({ filename: data.filename, duration: data.duration_sec, key })
        setUploadMsg(`✅ Music ready! (${Math.floor(data.duration_sec/60)}:${String(Math.round(data.duration_sec%60)).padStart(2,"0")})`)
      } else {
        setUploadMsg(`❌ ${data.error}`)
      }
    } catch {
      setUploadMsg("❌ Upload fail — server connected hai?")
    }
    setUploading(false)
    if (musicRef.current) musicRef.current.value = ""
  }

  const removeMusicFile = () => {
    setMusicFile(null); setMusicUploaded(null); setUploadMsg("")
  }

  async function submit() {
    const body = { content_type:form.type, voice:form.voice }
    if (tab==="builtin") {
      if (!form.builtin_key) return alert("Ek rhyme chunao!")
      body.builtin_key = form.builtin_key
    } else if (tab==="ai") {
      if (!form.topic) return alert("Topic likho!")
      body.topic = form.topic
    } else {
      const lines = form.custom_raw.split("\n").map(l=>l.trim()).filter(Boolean)
      if (!lines.length) return alert("Lines likho!")
      body.custom_lines = lines
      body.topic = form.topic || "Meri Kavita"
    }
    setJob(null)
    const d = await fetch(`${API}/api/generate`,{
      method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)
    }).then(r=>r.json())
    setJobId(d.job_id)
    setJob({status:"queued",progress:0,message:"Queue mein hai..."})
    setBusy(true)
  }

  const statusIcon = s => s==="done"?"✅":s==="failed"?"❌":"⏳"
  const fmtDur = s => s ? `${Math.floor(s/60)}:${String(Math.round(s%60)).padStart(2,"0")}` : ""

  return (
    <div style={{minHeight:"100vh",
                 background:"linear-gradient(160deg,#0d0221,#0a1a3a,#1a0030)",
                 color:"#fff", fontFamily:"system-ui,sans-serif", padding:"20px 16px"}}>
      <div style={{maxWidth:680, margin:"0 auto"}}>

        {/* Header */}
        <div style={{textAlign:"center", marginBottom:22}}>
          <div style={{fontSize:48}}>👦🎵</div>
          <h1 style={{margin:"4px 0", fontSize:22, fontWeight:900,
                      background:"linear-gradient(90deg,#ff9de2,#a78bfa,#74c0fc)",
                      WebkitBackgroundClip:"text", WebkitTextFillColor:"transparent"}}>
            Kids Hindi Rhymes & Songs
          </h1>
          <p style={{color:"#555", fontSize:12, margin:0}}>
            Suno AI Music • Karaoke • Story Characters • YouTube Shorts
          </p>
        </div>

        {/* Settings row */}
        <div style={{background:"rgba(255,255,255,0.05)", borderRadius:16, padding:16, marginBottom:14}}>
          <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:10}}>
            <div>
              <div style={{fontSize:11,color:"#888",marginBottom:4}}>Content Type</div>
              <select value={form.type} onChange={e=>set("type",e.target.value)} style={sel}>
                {TYPES.map(o=><option key={o.key} value={o.key}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <div style={{fontSize:11,color:"#888",marginBottom:4}}>Voice</div>
              <select value={form.voice} onChange={e=>set("voice",e.target.value)} style={sel}>
                {VOICES.map(o=><option key={o.key} value={o.key}>{o.label}</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* Content tabs */}
        <div style={{display:"flex", gap:8, marginBottom:12}}>
          {[["builtin","📚 Builtin"],["ai","🤖 AI se"],["custom","✏️ Custom"]].map(([k,l])=>(
            <button key={k} onClick={()=>setTab(k)}
              style={{flex:1, padding:"10px 0", borderRadius:12, border:"none", cursor:"pointer",
                      background: tab===k ? "linear-gradient(135deg,#f72585,#7209b7)" : "rgba(255,255,255,0.07)",
                      color:"#fff", fontWeight:700, fontSize:13}}>
              {l}
            </button>
          ))}
        </div>

        <div style={{background:"rgba(255,255,255,0.05)", borderRadius:16, padding:16, marginBottom:14}}>
          {tab==="builtin" && (
            <>
              <p style={{color:"#777",fontSize:12,margin:"0 0 10px"}}>Ready-made rhymes — ek click karo 🎉</p>
              <div style={{display:"grid", gridTemplateColumns:"repeat(2,1fr)", gap:8}}>
                {Object.entries(builtins).map(([k,v])=>(
                  <button key={k} onClick={()=>set("builtin_key",k)}
                    style={{padding:"12px 10px", borderRadius:12, border:"2px solid",
                            borderColor: form.builtin_key===k ? "#a78bfa":"transparent",
                            background: form.builtin_key===k ? "rgba(167,139,250,0.2)":"rgba(255,255,255,0.04)",
                            color:"#fff", cursor:"pointer", textAlign:"left"}}>
                    <div style={{fontSize:13,fontWeight:700,marginBottom:2}}>{v.title}</div>
                    <div style={{fontSize:11,color:"#888"}}>{v.type}</div>
                  </button>
                ))}
              </div>
            </>
          )}
          {tab==="ai" && (
            <>
              <p style={{color:"#777",fontSize:12,margin:"0 0 8px"}}>Topic do → AI Hindi rhyme likhega ✍️</p>
              <input value={form.topic} onChange={e=>set("topic",e.target.value)}
                style={{...inp, fontSize:16, padding:"14px"}}
                placeholder="e.g. Hathi Raja, Titli, Diwali..." />
            </>
          )}
          {tab==="custom" && (
            <>
              <p style={{color:"#777",fontSize:12,margin:"0 0 8px"}}>Apni lines likho — har line = ek karaoke card</p>
              <input value={form.topic} onChange={e=>set("topic",e.target.value)}
                style={{...inp, marginBottom:8}}
                placeholder="Title (optional)..." />
              <textarea value={form.custom_raw} onChange={e=>set("custom_raw",e.target.value)}
                rows={6} style={{...inp, resize:"vertical", lineHeight:1.9}}
                placeholder={"मछली जल की रानी है\nजीवन उसका पानी है\nहाथ लगाओ डर जाएगी"} />
              <div style={{fontSize:11,color:"#555",marginTop:4}}>
                {form.custom_raw.split("\n").filter(l=>l.trim()).length} lines
              </div>
            </>
          )}
        </div>

        {/* ── MUSIC UPLOAD — inline, right here ── */}
        <div style={{background:"rgba(255,255,255,0.05)", borderRadius:16,
                     padding:16, marginBottom:16,
                     border: musicUploaded ? "1px solid rgba(6,214,160,0.4)" : "1px solid rgba(255,255,255,0.06)"}}>

          <div style={{display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:10}}>
            <div style={{fontWeight:700, fontSize:14}}>🎵 Suno Background Music</div>
            <div style={{fontSize:11, color:"#555"}}>Optional — video banegi music ke saath</div>
          </div>

          {!musicUploaded ? (
            /* Upload button */
            <div
              onClick={()=>!uploading && musicRef.current?.click()}
              style={{border:"2px dashed rgba(167,139,250,0.4)", borderRadius:12,
                      padding:"18px 16px", textAlign:"center",
                      cursor: uploading?"not-allowed":"pointer",
                      background:"rgba(167,139,250,0.05)",
                      transition:"background 0.2s"}}
              onMouseEnter={e=>e.currentTarget.style.background="rgba(167,139,250,0.12)"}
              onMouseLeave={e=>e.currentTarget.style.background="rgba(167,139,250,0.05)"}
            >
              <input ref={musicRef} type="file" accept=".mp3"
                onChange={handleMusicPick} style={{display:"none"}} />
              <div style={{fontSize:30, marginBottom:6}}>{uploading?"⏳":"🎶"}</div>
              <div style={{fontWeight:700, color:"#a78bfa", fontSize:14}}>
                {uploading ? "Upload ho raha hai..." : "Suno MP3 Upload Karo"}
              </div>
              <div style={{color:"#555", fontSize:11, marginTop:4}}>
                Suno.com → Generate → Download → Yahan click karo
              </div>
            </div>
          ) : (
            /* Uploaded state */
            <div style={{background:"rgba(6,214,160,0.08)", borderRadius:12,
                         padding:"12px 14px", display:"flex",
                         justifyContent:"space-between", alignItems:"center"}}>
              <div>
                <div style={{fontWeight:700, color:"#06d6a0", fontSize:14}}>
                  ✅ {musicUploaded.filename}
                </div>
                <div style={{fontSize:12, color:"#888", marginTop:2}}>
                  ⏱ {fmtDur(musicUploaded.duration)} &nbsp;•&nbsp; 🔑 linked: {musicUploaded.key}
                </div>
              </div>
              <button onClick={removeMusicFile}
                style={{background:"rgba(255,80,80,0.15)", border:"1px solid rgba(255,80,80,0.3)",
                        borderRadius:8, padding:"6px 12px", color:"#ff8080",
                        cursor:"pointer", fontSize:12}}>
                ✕ Hatao
              </button>
            </div>
          )}

          {uploadMsg && !musicUploaded && (
            <div style={{marginTop:8, fontSize:12,
                         color: uploadMsg.startsWith("✅") ? "#06d6a0"
                              : uploadMsg.startsWith("❌") ? "#ff8080" : "#aaa"}}>
              {uploadMsg}
            </div>
          )}

          {/* How to get Suno music */}
          {!musicUploaded && !uploading && (
            <div style={{marginTop:10, display:"flex", gap:10, flexWrap:"wrap"}}>
              {[
                ["1️⃣","suno.com → Create"],
                ["2️⃣","Custom → lyrics likho"],
                ["3️⃣","Generate → Download MP3"],
                ["4️⃣","Yahan upload karo ⬆️"],
              ].map(([n,t])=>(
                <div key={n} style={{fontSize:11, color:"#555", display:"flex", gap:4}}>
                  <span>{n}</span><span>{t}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Generate button */}
        <button onClick={submit} disabled={busy}
          style={{width:"100%", padding:"18px", borderRadius:16, border:"none",
                  cursor: busy?"not-allowed":"pointer",
                  background: busy ? "rgba(100,100,100,0.4)"
                                   : "linear-gradient(135deg,#f72585,#7209b7)",
                  color:"#fff", fontSize:18, fontWeight:900,
                  boxShadow: busy?"none":"0 4px 28px rgba(247,37,133,0.45)"}}>
          {busy ? "⏳ Video Ban Raha Hai..." : "🎬 Video Banao!"}
        </button>

        {/* Status */}
        {job && (
          <div style={{marginTop:16, background:"rgba(255,255,255,0.05)",
                       borderRadius:16, padding:16}}>
            <div style={{display:"flex", justifyContent:"space-between",
                         alignItems:"center", marginBottom:8}}>
              <span style={{fontWeight:700, fontSize:15}}>
                {statusIcon(job.status)}{" "}
                {job.status==="done"?"Video Ready!":job.status==="failed"?"Error":"Chal raha hai..."}
              </span>
              <span style={{fontSize:13, color:"#888"}}>{job.progress||0}%</span>
            </div>

            {/* Step indicators */}
            <div style={{display:"flex", gap:4, marginBottom:10}}>
              {["🎤 TTS","🔊 Mix","🎵 Music","🎨 Render","🎬 Encode"].map((step,i)=>{
                const pct = job.progress||0
                const stepPct = [0,25,30,35,90][i]
                const done   = pct > stepPct+8
                const active = pct >= stepPct && !done
                return (
                  <div key={i} style={{flex:1, textAlign:"center", fontSize:9,
                                       padding:"4px 2px", borderRadius:6,
                                       background: done   ? "rgba(6,214,160,0.2)"
                                                 : active ? "rgba(167,139,250,0.3)"
                                                 : "rgba(255,255,255,0.04)",
                                       color: done?"#06d6a0":active?"#c4b5fd":"#444",
                                       fontWeight: active?700:400,
                                       border: active?"1px solid rgba(167,139,250,0.4)":"1px solid transparent"}}>
                    {done?"✅":active?"⏳":"○"} {step}
                  </div>
                )
              })}
            </div>

            <div style={{height:8, background:"rgba(255,255,255,0.08)",
                         borderRadius:8, overflow:"hidden", marginBottom:10}}>
              <div style={{height:"100%", borderRadius:8, width:`${job.progress||0}%`,
                           background:"linear-gradient(90deg,#f72585,#a78bfa,#74c0fc)",
                           transition:"width 0.5s"}} />
            </div>

            <p style={{fontSize:12, margin:"0 0 10px",
                       color: (job.message||"").includes("Suno music mila") ? "#06d6a0"
                            : (job.message||"").includes("nahi mila") ? "#fbbf24" : "#999"}}>
              {job.message}
            </p>

            {job.content && (
              <div style={{background:"rgba(0,0,0,0.2)", borderRadius:10, padding:12, marginBottom:10}}>
                <div style={{fontWeight:700, color:"#f9c74f", marginBottom:6, fontSize:14}}>
                  {job.content.title}
                </div>
                {(job.content.lines||[]).map((l,i)=>(
                  <div key={i} style={{fontSize:12, color:"#ccc", padding:"3px 0",
                                       paddingLeft:10, borderLeft:"2px solid rgba(167,139,250,0.4)",
                                       marginBottom:2}}>
                    {l}
                  </div>
                ))}
              </div>
            )}

            {job.status==="done" && (
              <a href={`${API}/api/download/${jobId}`}
                style={{display:"block", textAlign:"center", padding:"14px", borderRadius:12,
                        background:"linear-gradient(135deg,#06d6a0,#118ab2)",
                        color:"#fff", textDecoration:"none", fontWeight:900, fontSize:16}}>
                ⬇️ Video Download Karo
              </a>
            )}
            {job.status==="failed" && (
              <div style={{background:"rgba(255,50,50,0.1)", borderRadius:10,
                           padding:10, fontSize:12, color:"#ff8080"}}>
                {job.message}
              </div>
            )}
          </div>
        )}

        <p style={{textAlign:"center", color:"#2a2a3a", fontSize:11, marginTop:20}}>
          🎵 SwaraNeural TTS • 🎶 Suno AI Music • 🐱 Story Characters • 📝 Karaoke
        </p>
      </div>
    </div>
  )
}