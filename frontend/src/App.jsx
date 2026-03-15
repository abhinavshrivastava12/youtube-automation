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

// Character options for custom content
const CHAR_OPTIONS = [
  { key:"cat",       label:"🐱 Billi (Cat)" },
  { key:"fish",      label:"🐟 Machli (Fish)" },
  { key:"elephant",  label:"🐘 Hathi (Elephant)" },
  { key:"moon",      label:"🌙 Chanda (Moon)" },
  { key:"star",      label:"⭐ Tara (Star)" },
  { key:"horse",     label:"🐴 Ghoda (Horse)" },
  { key:"peacock",   label:"🦚 Mor (Peacock)" },
  { key:"kid",       label:"👦 Bachcha (Kid)" },
]

const BG_OPTIONS = [
  { key:"billi",   label:"🌸 Pink Pastel", col:"#ff9a9e" },
  { key:"machli",  label:"🌊 Ocean Blue",  col:"#0096c7" },
  { key:"hathi",   label:"🌿 Forest Green",col:"#52b788" },
  { key:"chanda",  label:"🌙 Night Dark",  col:"#03045e" },
  { key:"tara",    label:"🌌 Space Purple",col:"#3c096c" },
  { key:"lakdi",   label:"🌅 Sunset Orange",col:"#ff6b35"},
  { key:"johny",   label:"🍭 Candy Pink",  col:"#ff99c8" },
  { key:"nani",    label:"🌿 Garden Green",col:"#2d6a4f" },
]

const inp = {
  background:"rgba(255,255,255,0.08)", border:"1px solid rgba(255,255,255,0.18)",
  borderRadius:10, padding:"10px 14px", color:"#fff", fontSize:14,
  outline:"none", width:"100%", boxSizing:"border-box",
}
const sel = { ...inp, cursor:"pointer" }
const btn = (active, col="#f72585") => ({
  padding:"10px 16px", borderRadius:10, border:"none", cursor:"pointer",
  background: active ? `linear-gradient(135deg,${col},${col}aa)` : "rgba(255,255,255,0.07)",
  color:"#fff", fontWeight:700, fontSize:13, transition:"all 0.2s",
})

export default function App() {
  const [tab, setTab]         = useState("builtin")
  const [builtins, setBlt]    = useState({})
  const [songs, setSongs]     = useState([])
  const [healthData, setHealth] = useState(null)

  // Form state
  const [form, setF] = useState({
    builtin_key:"", topic:"", custom_raw:"", type:"rhyme", voice:"swara",
  })

  // Custom song form
  const [customSong, setCS] = useState({
    title:"", lines_raw:"", char:"cat", bg_key:"billi", voice:"swara", type:"rhyme"
  })

  // Song upload
  const [uploadFile, setUploadFile]   = useState(null)
  const [uploadKey, setUploadKey]     = useState("")
  const [uploadTitle, setUploadTitle] = useState("")
  const [uploadMsg, setUploadMsg]     = useState("")
  const [uploading, setUploading]     = useState(false)
  const fileRef = useRef()

  // Job state
  const [jobId, setJobId]   = useState(null)
  const [job, setJob]       = useState(null)
  const [busy, setBusy]     = useState(false)
  const timer = useRef()

  const set  = (k,v) => setF(f=>({...f,[k]:v}))
  const setC = (k,v) => setCS(s=>({...s,[k]:v}))

  // Load builtins + songs + health
  useEffect(()=>{
    fetch(`${API}/api/builtins`).then(r=>r.json()).then(setBlt).catch(()=>{})
    refreshSongs()
    fetch(`${API}/api/health`).then(r=>r.json()).then(setHealth).catch(()=>{})
  },[])

  const refreshSongs = () => {
    fetch(`${API}/api/songs`).then(r=>r.json()).then(setSongs).catch(()=>[])
  }

  // Poll job status
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

  // Upload MP3
  const handleUpload = async () => {
    if (!uploadFile) return alert("Pehle MP3 file chuniye!")
    if (!uploadKey.trim()) return alert("Rhyme key daalna zaroori hai! (e.g. billi, machli, meri_kavita)")
    setUploading(true); setUploadMsg("⏳ Upload ho raha hai...")
    const fd = new FormData()
    fd.append("file", uploadFile)
    fd.append("rhyme_key", uploadKey.trim().toLowerCase().replace(/\s+/g,"_"))
    try {
      const data = await fetch(`${API}/api/upload-song`,{method:"POST",body:fd}).then(r=>r.json())
      if (data.ok) {
        setUploadMsg(`✅ Upload hua! Key: '${data.mapped_to}' (${Math.floor(data.duration_sec/60)}:${String(Math.round(data.duration_sec%60)).padStart(2,"0")})`)
        setUploadFile(null); setUploadKey(""); setUploadTitle("")
        if (fileRef.current) fileRef.current.value=""
        refreshSongs()
      } else {
        setUploadMsg(`❌ ${data.error}`)
      }
    } catch { setUploadMsg("❌ Upload fail — server chal raha hai?") }
    setUploading(false)
  }

  // Delete song
  const deleteSong = async (fname) => {
    if (!confirm(`'${fname}' delete karna hai?`)) return
    await fetch(`${API}/api/delete-song/${fname}`,{method:"DELETE"})
    refreshSongs()
  }

  // Generate video
  async function submit() {
    const body = { content_type:form.type, voice:form.voice }

    if (tab==="builtin") {
      if (!form.builtin_key) return alert("Ek rhyme chunao!")
      body.builtin_key = form.builtin_key
    } else if (tab==="ai") {
      if (!form.topic) return alert("Topic likho!")
      body.topic = form.topic; body.content_type = form.type
    } else if (tab==="custom") {
      // Custom lines with specific character/bg
      const lines = customSong.lines_raw.split("\n").map(l=>l.trim()).filter(Boolean)
      if (!lines.length) return alert("Kam se kam 1 line likho!")
      if (!customSong.title.trim()) return alert("Title daalo!")
      body.custom_lines = lines
      body.topic = customSong.title.trim()
      body.content_type = customSong.type
      body.voice = customSong.voice
      // Pass char+bg override via topic hint so story_config detects it
      body.builtin_key = customSong.bg_key  // bg_key is used for story config detection
      body.char_override = customSong.char
    } else if (tab==="songs") {
      return alert("Songs tab se video nahi banta — 'Custom' ya 'Builtin' tab use karo")
    }

    setJob(null)
    const d = await fetch(`${API}/api/generate`,{
      method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)
    }).then(r=>r.json())
    setJobId(d.job_id)
    setJob({status:"queued",progress:0,message:"Queue mein hai..."})
    setBusy(true)
    setTab("status") // auto switch to status tab
  }

  const fmtDur = s => s ? `${Math.floor(s/60)}:${String(Math.round(s%60)).padStart(2,"0")}` : "?"
  const statusIcon = s => s==="done"?"✅":s==="failed"?"❌":"⏳"

  return (
    <div style={{minHeight:"100vh",
                 background:"linear-gradient(160deg,#0d0221,#0a1a3a,#1a0030)",
                 color:"#fff", fontFamily:"system-ui,sans-serif", padding:"20px 16px"}}>
      <div style={{maxWidth:700, margin:"0 auto"}}>

        {/* Header */}
        <div style={{textAlign:"center", marginBottom:20}}>
          <div style={{fontSize:44}}>🎵</div>
          <h1 style={{margin:"4px 0 2px", fontSize:22, fontWeight:900,
                      background:"linear-gradient(90deg,#ff9de2,#a78bfa,#74c0fc)",
                      WebkitBackgroundClip:"text", WebkitTextFillColor:"transparent"}}>
            Kids Hindi Rhymes & Songs
          </h1>
          {healthData && (
            <div style={{fontSize:11,color:"#555",marginTop:4}}>
              🎶 Songs: {healthData.suno_songs?.length||0} uploaded
              &nbsp;•&nbsp;
              🤖 AI: {healthData.ai?.groq?"Groq✅":"No AI"}
            </div>
          )}
        </div>

        {/* Tab Navigation */}
        <div style={{display:"flex", gap:6, marginBottom:14, overflowX:"auto"}}>
          {[
            ["builtin","📚 Builtin"],
            ["ai","🤖 AI"],
            ["custom","✏️ Custom"],
            ["songs","🎵 Songs"],
            ["status","📊 Status"],
          ].map(([k,l])=>(
            <button key={k} onClick={()=>setTab(k)} style={btn(tab===k)}>
              {l}
              {k==="status" && busy && <span style={{marginLeft:6,fontSize:10}}>⏳</span>}
            </button>
          ))}
        </div>

        {/* ═══ BUILTIN TAB ═══ */}
        {tab==="builtin" && (
          <div style={{background:"rgba(255,255,255,0.05)", borderRadius:16, padding:16, marginBottom:14}}>
            <p style={{color:"#666",fontSize:12,margin:"0 0 12px"}}>
              Ready-made rhymes — ek click karo, video ban jayegi 🎉
            </p>
            <div style={{display:"grid", gridTemplateColumns:"repeat(2,1fr)", gap:8, marginBottom:14}}>
              {Object.entries(builtins).map(([k,v])=>(
                <button key={k} onClick={()=>set("builtin_key",k)}
                  style={{padding:"12px 10px", borderRadius:12, border:"2px solid",
                          borderColor:form.builtin_key===k?"#a78bfa":"transparent",
                          background:form.builtin_key===k?"rgba(167,139,250,0.2)":"rgba(255,255,255,0.04)",
                          color:"#fff", cursor:"pointer", textAlign:"left"}}>
                  <div style={{fontSize:13,fontWeight:700}}>{v.title}</div>
                  <div style={{fontSize:11,color:"#666"}}>{v.type}</div>
                </button>
              ))}
            </div>
            <VoiceTypeRow form={form} set={set} />
            <GenerateBtn busy={busy} onClick={submit} />
          </div>
        )}

        {/* ═══ AI TAB ═══ */}
        {tab==="ai" && (
          <div style={{background:"rgba(255,255,255,0.05)", borderRadius:16, padding:16, marginBottom:14}}>
            <p style={{color:"#666",fontSize:12,margin:"0 0 10px"}}>
              Koi bhi topic do → AI Hindi mein likhega ✍️<br/>
              <span style={{color:"#444"}}>Groq API key chahiye backend/.env mein</span>
            </p>
            <input value={form.topic} onChange={e=>set("topic",e.target.value)}
              style={{...inp, fontSize:16, padding:"14px", marginBottom:12}}
              placeholder="e.g. Hathi Raja, Titli, Diwali, Meri Nani..." />
            <VoiceTypeRow form={form} set={set} />
            <GenerateBtn busy={busy} onClick={submit} />
          </div>
        )}

        {/* ═══ CUSTOM TAB ═══ */}
        {tab==="custom" && (
          <div style={{background:"rgba(255,255,255,0.05)", borderRadius:16, padding:16, marginBottom:14}}>
            <p style={{color:"#666",fontSize:12,margin:"0 0 12px"}}>
              Apni khud ki lines likho + character/background chuniya + Suno song select karo
            </p>

            {/* Title */}
            <div style={{marginBottom:10}}>
              <Label>Video Title</Label>
              <input value={customSong.title} onChange={e=>setC("title",e.target.value)}
                style={inp} placeholder="e.g. Meri Pyari Titli, Sher Ka Beta..." />
            </div>

            {/* Lines */}
            <div style={{marginBottom:10}}>
              <Label>Lines (har line = ek karaoke card)</Label>
              <textarea value={customSong.lines_raw} onChange={e=>setC("lines_raw",e.target.value)}
                rows={6} style={{...inp, resize:"vertical", lineHeight:1.9}}
                placeholder={"टिमटिम करते तारे हैं\nजैसे हीरे प्यारे हैं\nऊँचे नीले आसमान में\nचमकते दिन और रात में"} />
              <div style={{fontSize:11,color:"#444",marginTop:3}}>
                {customSong.lines_raw.split("\n").filter(l=>l.trim()).length} lines
              </div>
            </div>

            {/* Character selection */}
            <div style={{marginBottom:10}}>
              <Label>Character (kaun sa character dance karega?)</Label>
              <div style={{display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:6}}>
                {CHAR_OPTIONS.map(c=>(
                  <button key={c.key} onClick={()=>setC("char",c.key)}
                    style={{...btn(customSong.char===c.key,"#06d6a0"),
                            padding:"8px 4px", fontSize:11, textAlign:"center"}}>
                    {c.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Background selection */}
            <div style={{marginBottom:10}}>
              <Label>Background Theme</Label>
              <div style={{display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:6}}>
                {BG_OPTIONS.map(b=>(
                  <button key={b.key} onClick={()=>setC("bg_key",b.key)}
                    style={{padding:"8px 4px", borderRadius:10, border:"2px solid",
                            borderColor:customSong.bg_key===b.key?"#fff":"transparent",
                            background:customSong.bg_key===b.key?b.col+"44":b.col+"22",
                            color:"#fff", cursor:"pointer", fontSize:11, textAlign:"center"}}>
                    {b.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Suno song for this custom video */}
            <div style={{marginBottom:12, background:"rgba(255,255,255,0.04)", borderRadius:12, padding:12}}>
              <Label>🎵 Suno Background Song (is video ke liye)</Label>
              {songs.length === 0 ? (
                <div style={{fontSize:12,color:"#555",padding:"8px 0"}}>
                  Koi song upload nahi hai → Songs tab mein jao aur upload karo
                </div>
              ) : (
                <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:6, marginTop:8}}>
                  <button onClick={()=>setC("bg_key","auto")}
                    style={{...btn(customSong.bg_key==="auto","#888"),padding:"8px",fontSize:12}}>
                    🤖 Auto detect
                  </button>
                  {songs.map(s=>(
                    <button key={s.filename} onClick={()=>{
                      // Use this song's mapped key as bg_key
                      const key = s.mapped_keys?.[0] || s.filename.replace(".mp3","")
                      setC("bg_key", key)
                    }}
                      style={{padding:"8px", borderRadius:10, border:"2px solid",
                              borderColor:(s.mapped_keys?.includes(customSong.bg_key))?"#06d6a0":"transparent",
                              background:(s.mapped_keys?.includes(customSong.bg_key))?"rgba(6,214,160,0.15)":"rgba(255,255,255,0.05)",
                              color:"#fff", cursor:"pointer", textAlign:"left", fontSize:11}}>
                      🎵 {s.name}<br/>
                      <span style={{color:"#555",fontSize:10}}>
                        {fmtDur(s.duration_sec)} • key: {s.mapped_keys?.[0]||"?"}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Voice + Type */}
            <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:10, marginBottom:12}}>
              <div>
                <Label>Content Type</Label>
                <select value={customSong.type} onChange={e=>setC("type",e.target.value)} style={sel}>
                  {TYPES.map(o=><option key={o.key} value={o.key}>{o.label}</option>)}
                </select>
              </div>
              <div>
                <Label>Voice</Label>
                <select value={customSong.voice} onChange={e=>setC("voice",e.target.value)} style={sel}>
                  {VOICES.map(o=><option key={o.key} value={o.key}>{o.label}</option>)}
                </select>
              </div>
            </div>

            <GenerateBtn busy={busy} onClick={submit} />
          </div>
        )}

        {/* ═══ SONGS TAB ═══ */}
        {tab==="songs" && (
          <div style={{marginBottom:14}}>

            {/* Upload new song */}
            <div style={{background:"rgba(255,255,255,0.05)", borderRadius:16, padding:16, marginBottom:12}}>
              <div style={{fontWeight:700, fontSize:15, marginBottom:12}}>
                ⬆️ Naya Suno Song Upload Karo
              </div>

              {/* How to get Suno MP3 */}
              <div style={{background:"rgba(167,139,250,0.08)", borderRadius:10, padding:12, marginBottom:12,
                           border:"1px solid rgba(167,139,250,0.2)"}}>
                <div style={{fontSize:12, fontWeight:700, color:"#a78bfa", marginBottom:6}}>
                  Suno se MP3 kaise download karein:
                </div>
                <div style={{fontSize:12, color:"#666", lineHeight:1.8}}>
                  1️⃣ <b style={{color:"#999"}}>suno.com</b> pe jao → apna song generate karo<br/>
                  2️⃣ Song ke neeche <b style={{color:"#999"}}>3 dots (⋯)</b> click karo<br/>
                  3️⃣ <b style={{color:"#999"}}>"Download"</b> → <b style={{color:"#999"}}>"Audio (.mp3)"</b> select karo<br/>
                  4️⃣ Download hua .mp3 yahan upload karo ⬇️
                </div>
              </div>

              {/* File picker */}
              <input ref={fileRef} type="file" accept=".mp3"
                onChange={e=>{ setUploadFile(e.target.files?.[0]||null); setUploadMsg("") }}
                style={{...inp, marginBottom:8, cursor:"pointer"}} />

              {/* Rhyme key */}
              <div style={{marginBottom:8}}>
                <Label>
                  Rhyme Key — ⚠️ ZAROORI hai!
                  <span style={{fontWeight:400, color:"#555"}}>
                    {" "}(yahi key song ko video se jorega)
                  </span>
                </Label>
                <input value={uploadKey} onChange={e=>setUploadKey(e.target.value)}
                  style={inp}
                  placeholder="e.g.  billi  /  machli  /  meri_kavita  /  koi_bhi_naam" />
                <div style={{fontSize:11, color:"#555", marginTop:4}}>
                  💡 Builtin keys: billi, machli, chanda, lakdi, johny, twinkle, hathi, nani, lori<br/>
                  💡 Custom videos ke liye kuch bhi likho: meri_song, happy_diwali, etc.
                </div>
              </div>

              <button onClick={handleUpload} disabled={uploading||!uploadFile}
                style={{width:"100%", padding:"12px", borderRadius:12, border:"none",
                        cursor:uploading||!uploadFile?"not-allowed":"pointer",
                        background:uploading||!uploadFile?"rgba(100,100,100,0.4)":"linear-gradient(135deg,#06d6a0,#118ab2)",
                        color:"#fff", fontWeight:700, fontSize:15}}>
                {uploading ? "⏳ Upload ho raha hai..." : "⬆️ Song Upload Karo"}
              </button>

              {uploadMsg && (
                <div style={{marginTop:8, fontSize:13,
                             color:uploadMsg.startsWith("✅")?"#06d6a0":uploadMsg.startsWith("❌")?"#ff8080":"#aaa"}}>
                  {uploadMsg}
                </div>
              )}
            </div>

            {/* Uploaded songs list */}
            <div style={{background:"rgba(255,255,255,0.05)", borderRadius:16, padding:16}}>
              <div style={{display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:12}}>
                <div style={{fontWeight:700, fontSize:15}}>📂 Upload Hue Songs ({songs.length})</div>
                <button onClick={refreshSongs}
                  style={{...btn(false), padding:"6px 12px", fontSize:12}}>
                  🔄 Refresh
                </button>
              </div>

              {songs.length === 0 ? (
                <div style={{color:"#555", fontSize:13, textAlign:"center", padding:"20px 0"}}>
                  Koi song nahi hai — upar se upload karo
                </div>
              ) : (
                songs.map(s=>(
                  <div key={s.filename} style={{
                    background:"rgba(255,255,255,0.04)", borderRadius:10,
                    padding:"10px 12px", marginBottom:8,
                    border:"1px solid rgba(255,255,255,0.08)",
                    display:"flex", justifyContent:"space-between", alignItems:"center"
                  }}>
                    <div>
                      <div style={{fontWeight:700, fontSize:13}}>🎵 {s.name}</div>
                      <div style={{fontSize:11, color:"#555", marginTop:2}}>
                        ⏱ {fmtDur(s.duration_sec)}
                        &nbsp;•&nbsp; 📁 {s.size_kb}KB
                        &nbsp;•&nbsp; 🔑 key: <b style={{color:"#a78bfa"}}>{s.mapped_keys?.join(", ")||"none"}</b>
                      </div>
                      <div style={{fontSize:10, color:"#333", marginTop:1}}>{s.filename}</div>
                    </div>
                    <button onClick={()=>deleteSong(s.filename)}
                      style={{background:"rgba(255,80,80,0.15)", border:"1px solid rgba(255,80,80,0.3)",
                              borderRadius:8, padding:"6px 10px", color:"#ff8080",
                              cursor:"pointer", fontSize:12}}>
                      🗑️
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* ═══ STATUS TAB ═══ */}
        {tab==="status" && (
          <div>
            {!job ? (
              <div style={{background:"rgba(255,255,255,0.05)", borderRadius:16, padding:30,
                           textAlign:"center", color:"#555"}}>
                Koi job nahi chal raha.<br/>Builtin / AI / Custom tab se video banao.
              </div>
            ) : (
              <div style={{background:"rgba(255,255,255,0.05)", borderRadius:16, padding:16}}>
                <div style={{display:"flex", justifyContent:"space-between",
                             alignItems:"center", marginBottom:10}}>
                  <span style={{fontWeight:700, fontSize:15}}>
                    {statusIcon(job.status)}{" "}
                    {job.status==="done"?"Video Taiyaar!":
                     job.status==="failed"?"Error Aaya":
                     "Ban Raha Hai..."}
                  </span>
                  <span style={{fontSize:13,color:"#555"}}>{job.progress||0}%</span>
                </div>

                {/* Step indicators */}
                <div style={{display:"flex", gap:4, marginBottom:10}}>
                  {["🎤 TTS","🔊 Mix","🎵 Music","🎨 Render","🎬 Encode"].map((step,i)=>{
                    const pct=job.progress||0
                    const stepPct=[0,20,30,35,90][i]
                    const done=pct>stepPct+10; const active=pct>=stepPct&&!done
                    return (
                      <div key={i} style={{flex:1, textAlign:"center", fontSize:9,
                                           padding:"4px 2px", borderRadius:6,
                                           background:done?"rgba(6,214,160,0.2)":active?"rgba(167,139,250,0.3)":"rgba(255,255,255,0.04)",
                                           color:done?"#06d6a0":active?"#c4b5fd":"#444",
                                           fontWeight:active?700:400,
                                           border:active?"1px solid rgba(167,139,250,0.4)":"1px solid transparent"}}>
                        {done?"✅":active?"⏳":"○"} {step}
                      </div>
                    )
                  })}
                </div>

                {/* Progress bar */}
                <div style={{height:8, background:"rgba(255,255,255,0.08)",
                             borderRadius:8, overflow:"hidden", marginBottom:10}}>
                  <div style={{height:"100%", borderRadius:8, width:`${job.progress||0}%`,
                               background:"linear-gradient(90deg,#f72585,#a78bfa,#74c0fc)",
                               transition:"width 0.5s"}} />
                </div>

                {/* Message */}
                <p style={{fontSize:12, margin:"0 0 10px",
                           color:(job.message||"").includes("✅")?"#06d6a0":
                                 (job.message||"").includes("⚠️")?"#fbbf24":"#999"}}>
                  {job.message}
                </p>

                {/* Content preview */}
                {job.content && (
                  <div style={{background:"rgba(0,0,0,0.2)", borderRadius:10, padding:12, marginBottom:10}}>
                    <div style={{fontWeight:700, color:"#f9c74f", marginBottom:6, fontSize:14}}>
                      {job.content.title}
                    </div>
                    {(job.content.lines||[]).map((l,i)=>(
                      <div key={i} style={{fontSize:12, color:"#ccc", padding:"3px 0",
                                           paddingLeft:10,
                                           borderLeft:"2px solid rgba(167,139,250,0.4)",
                                           marginBottom:2}}>
                        {l}
                      </div>
                    ))}
                  </div>
                )}

                {/* Download */}
                {job.status==="done" && (
                  <a href={`${API}/api/download/${jobId}`}
                    style={{display:"block", textAlign:"center", padding:"14px", borderRadius:12,
                            background:"linear-gradient(135deg,#06d6a0,#118ab2)",
                            color:"#fff", textDecoration:"none", fontWeight:900, fontSize:16}}>
                    ⬇️ Video Download Karo
                  </a>
                )}

                {/* Error detail */}
                {job.status==="failed" && (
                  <div style={{background:"rgba(255,50,50,0.1)", borderRadius:10,
                               padding:10, fontSize:11, color:"#ff8080",
                               fontFamily:"monospace", maxHeight:150, overflow:"auto"}}>
                    {job.error_detail || job.message}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <p style={{textAlign:"center", color:"#2a2a3a", fontSize:11, marginTop:20}}>
          🎵 Hindi TTS • 🎶 Suno AI Music • 🐱 Animated Characters • 📝 Karaoke
        </p>
      </div>
    </div>
  )
}

// ── Shared components ─────────────────────────────────────────────────────────

function Label({children}) {
  return <div style={{fontSize:11,color:"#666",marginBottom:5}}>{children}</div>
}

function VoiceTypeRow({form, set}) {
  return (
    <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:10, marginBottom:12}}>
      <div>
        <Label>Content Type</Label>
        <select value={form.type} onChange={e=>set("type",e.target.value)}
          style={{background:"rgba(255,255,255,0.08)",border:"1px solid rgba(255,255,255,0.18)",
                  borderRadius:10,padding:"10px 14px",color:"#fff",fontSize:14,
                  outline:"none",width:"100%",boxSizing:"border-box",cursor:"pointer"}}>
          {[{key:"rhyme",label:"🎵 Kids Rhyme"},{key:"lullaby",label:"🌙 Lullaby"},
            {key:"poem",label:"📝 Kavita"},{key:"song",label:"🎶 Slow Song"}]
            .map(o=><option key={o.key} value={o.key}>{o.label}</option>)}
        </select>
      </div>
      <div>
        <Label>Voice</Label>
        <select value={form.voice} onChange={e=>set("voice",e.target.value)}
          style={{background:"rgba(255,255,255,0.08)",border:"1px solid rgba(255,255,255,0.18)",
                  borderRadius:10,padding:"10px 14px",color:"#fff",fontSize:14,
                  outline:"none",width:"100%",boxSizing:"border-box",cursor:"pointer"}}>
          {[{key:"swara",label:"👩 Swara (Female)"},{key:"madhur",label:"👨 Madhur (Male)"}]
            .map(o=><option key={o.key} value={o.key}>{o.label}</option>)}
        </select>
      </div>
    </div>
  )
}

function GenerateBtn({busy, onClick}) {
  return (
    <button onClick={onClick} disabled={busy}
      style={{width:"100%", padding:"16px", borderRadius:14, border:"none",
              cursor:busy?"not-allowed":"pointer",
              background:busy?"rgba(100,100,100,0.4)":"linear-gradient(135deg,#f72585,#7209b7)",
              color:"#fff", fontSize:17, fontWeight:900,
              boxShadow:busy?"none":"0 4px 24px rgba(247,37,133,0.4)"}}>
      {busy ? "⏳ Video Ban Raha Hai..." : "🎬 Video Banao!"}
    </button>
  )
}