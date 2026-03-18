import { useState, useEffect, useRef, Component } from "react"

const API = "http://127.0.0.1:5000"

// ── Error Boundary — blank screen se bachao ───────────────────────────────────
class ErrorBoundary extends Component {
  constructor(p){ super(p); this.state={err:null} }
  static getDerivedStateFromError(e){ return {err:e} }
  render(){
    if(this.state.err) return (
      <div style={{padding:24,color:"#f87171",fontFamily:"monospace",fontSize:13,
                   background:"#0d0d1a",minHeight:"100vh"}}>
        <b>⚠️ Kuch toot gaya — page refresh karo</b><br/><br/>
        <span style={{color:"#444"}}>{String(this.state.err)}</span><br/><br/>
        <button onClick={()=>this.setState({err:null})}
          style={{padding:"8px 16px",background:"#7c3aed",border:"none",
                  borderRadius:8,color:"#fff",cursor:"pointer"}}>
          🔄 Dobara Try Karo
        </button>
      </div>
    )
    return this.props.children
  }
}

// ── Style helpers ─────────────────────────────────────────────────────────────
const inp = {
  background:"rgba(255,255,255,0.07)", border:"1px solid rgba(255,255,255,0.15)",
  borderRadius:10, padding:"10px 14px", color:"#fff", fontSize:14,
  outline:"none", width:"100%", boxSizing:"border-box",
}
const sel = { ...inp, cursor:"pointer" }

const btnStyle = (active, col="#f72585") => ({
  padding:"9px 14px", borderRadius:10, border:"none", cursor:"pointer",
  background: active
    ? `linear-gradient(135deg,${col},${col}bb)`
    : "rgba(255,255,255,0.06)",
  color:"#fff", fontWeight:700, fontSize:13, transition:"all 0.15s",
})

// ── Theme options ─────────────────────────────────────────────────────────────
const ACCENT_OPTIONS = [
  { key:"lofi_blue",   label:"💙 Blue",   accent:"#4a9eff", bg:["#1a2a4a","#2d4a7a"] },
  { key:"lofi_purple", label:"💜 Purple", accent:"#c084fc", bg:["#2d1b4e","#4a2d7a"] },
  { key:"lofi_pink",   label:"🌸 Pink",   accent:"#f472b6", bg:["#3d1a2e","#6b2d5e"] },
  { key:"lofi_green",  label:"💚 Teal",   accent:"#34d399", bg:["#0d2b2b","#1a4a4a"] },
  { key:"lofi_warm",   label:"🟠 Warm",   accent:"#fb923c", bg:["#2b1a0d","#4a3520"] },
  { key:"chanda",      label:"🔵 Navy",   accent:"#4895ef", bg:["#03045e","#023e8a"] },
  { key:"tara",        label:"🟣 Space",  accent:"#9d4edd", bg:["#10002b","#3c096c"] },
  { key:"lori",        label:"🌙 Night",  accent:"#e2b714", bg:["#1a1a2e","#16213e"] },
]

const CHAR_OPTIONS = [
  {key:"cat",label:"🐱"},{key:"fish",label:"🐟"},{key:"elephant",label:"🐘"},
  {key:"moon",label:"🌙"},{key:"star",label:"⭐"},{key:"horse",label:"🐴"},
  {key:"peacock",label:"🦚"},{key:"kid",label:"👦"},
]

const BUILTIN_BG = [
  {key:"billi",label:"🌸 Pink",bg:["#ff9a9e","#fecfef"]},
  {key:"machli",label:"🌊 Ocean",bg:["#0096c7","#caf0f8"]},
  {key:"hathi",label:"🌿 Green",bg:["#52b788","#b7e4c7"]},
  {key:"lakdi",label:"🌅 Sunset",bg:["#ff6b35","#ffd166"]},
  {key:"johny",label:"🍭 Candy",bg:["#ff99c8","#fcf6bd"]},
]

// ══════════════════════════════════════════════════════════════════════════════
function AppInner() {
  const [tab, setTab]         = useState("song")   // "song" | "kids" | "songs" | "status"
  const [builtins, setBlt]    = useState({})
  const [songs, setSongs]     = useState([])
  const [bgAssets, setBgAssets] = useState([])    // all bg images/frames
  const [health, setHealth]   = useState(null)

  // ── Song tab state ──────────────────────────────────────────────────────────
  const [song, setSong] = useState({
    title:"",
    lines_raw:"",
    song_key:"",
    accent_key:"lofi_blue",
    selected_assets: [],  // filenames selected for Ken Burns
  })

  // ── Kids tab state ──────────────────────────────────────────────────────────
  const [kids, setKids] = useState({
    builtin_key:"",
    topic:"",
    custom_lines:"",
    custom_title:"",
    char:"kid",
    bg_key:"billi",
    type:"rhyme",
    voice:"swara",
    mode:"builtin",  // "builtin" | "ai" | "custom"
    song_key:"",     // "" = auto-match, otherwise specific uploaded MP3 key
  })

  // ── Upload state ────────────────────────────────────────────────────────────
  const [assetFile, setAssetFile]   = useState(null)
  const [assetMsg, setAssetMsg]     = useState("")
  const [assetBusy, setAssetBusy]   = useState(false)
  const [songFile, setSongFile]     = useState(null)
  const [songKey, setSongKey2]       = useState("")
  const [songMsg, setSongMsg]       = useState("")
  const [songBusy, setSongBusy]     = useState(false)
  const assetRef = useRef()
  const songRef  = useRef()

  // ── Job state ───────────────────────────────────────────────────────────────
  const [jobId, setJobId] = useState(null)
  const [job, setJob]     = useState(null)
  const [busy, setBusy]   = useState(false)
  const timer = useRef()

  const setSf = (k, v) => setSong(s => ({
    ...s,
    [k]: typeof v === "function" ? v(s[k]) : v
  }))
  const setKf = (k, v) => setKids(s => ({
    ...s,
    [k]: typeof v === "function" ? v(s[k]) : v
  }))

  const [whisperAvail, setWhisperAvail] = useState(null)  // null=checking, true/false
  const [syncStatus, setSyncStatus]     = useState("")     // "" | "syncing" | "done" | "fallback"
  const [timestamps, setTimestamps]     = useState(null)   // synced timestamps or null

  // ── Init ────────────────────────────────────────────────────────────────────
  useEffect(()=>{
    fetch(`${API}/api/builtins`).then(r=>r.json()).then(setBlt).catch(()=>{})
    refreshSongs()
    refreshAssets()
    fetch(`${API}/api/health`).then(r=>r.json()).then(setHealth).catch(()=>{})
    // Check whisper availability
    fetch(`${API}/api/whisper-status`).then(r=>r.json())
      .then(d=>setWhisperAvail(d.available)).catch(()=>setWhisperAvail(false))
  },[])

  const refreshSongs  = ()=> fetch(`${API}/api/songs`).then(r=>r.json()).then(d=>{ if(Array.isArray(d)) setSongs(d) }).catch(()=>{})
  const refreshAssets = ()=> fetch(`${API}/api/bg-images`).then(r=>r.json()).then(d=>{ if(Array.isArray(d)) setBgAssets(d) }).catch(()=>{})

  // ── Job polling ─────────────────────────────────────────────────────────────
  useEffect(()=>{
    if(!jobId||!busy) return
    timer.current = setInterval(async()=>{
      try{
        const d = await fetch(`${API}/api/status/${jobId}`).then(r=>r.json())
        setJob(d)
        if(d.status==="done"||d.status==="failed"){setBusy(false);clearInterval(timer.current)}
      }catch{}
    },1500)
    return ()=>clearInterval(timer.current)
  },[jobId,busy])

  // ── Asset upload (image OR video) ───────────────────────────────────────────
  const uploadAsset = async()=>{
    if(!assetFile){ setAssetMsg("❌ Pehle file chuniye!"); return }
    setAssetBusy(true); setAssetMsg("⏳ Upload ho raha hai...")
    const fd = new FormData(); fd.append("file", assetFile)
    try {
      const res = await fetch(`${API}/api/upload-bg-image`, {method:"POST", body:fd})
      const d   = await res.json()
      if(d.ok){
        const isVid = d.type === "video"
        setAssetMsg(isVid
          ? `✅ Video se ${d.frame_count} frames extract hue (${d.duration_sec}s)`
          : `✅ ${d.filename} upload hua (${d.size_kb}KB)`)
        setAssetFile(null)
        if(assetRef.current) assetRef.current.value = ""
        // First update assets list, THEN auto-select
        await new Promise(res2 => {
          fetch(`${API}/api/bg-images`).then(r=>r.json()).then(list=>{
            if(Array.isArray(list)) setBgAssets(list)
            res2()
          }).catch(res2)
        })
        if(isVid && d.frames){
          setSf("selected_assets", s => [...new Set([...s, ...d.frames])])
        } else if(d.filename){
          setSf("selected_assets", s => [...new Set([...s, d.filename])])
        }
      } else {
        setAssetMsg(`❌ ${d.error || "Upload fail hua"}`)
      }
    } catch(e) {
      setAssetMsg("❌ Server se connect nahi hua — backend chal raha hai?")
    }
    setAssetBusy(false)
  }

  const deleteAsset = async(fname)=>{
    // Optimistic update first — remove from UI immediately
    setBgAssets(prev => prev.filter(a => a.filename !== fname))
    setSf("selected_assets", s => s.filter(x => x !== fname))
    try {
      await fetch(`${API}/api/delete-bg-image/${encodeURIComponent(fname)}`, {method:"DELETE"})
      // Refresh to confirm
      fetch(`${API}/api/bg-images`).then(r=>r.json()).then(d=>{ if(Array.isArray(d)) setBgAssets(d) }).catch(()=>{})
    } catch(e) {
      setAssetMsg("❌ Delete fail — dobara try karo")
    }
  }

  const toggleAsset = (fname)=>{
    setSf("selected_assets",s=>
      s.includes(fname)?s.filter(x=>x!==fname):[...s,fname])
  }

  // ── Song upload ─────────────────────────────────────────────────────────────
  const uploadSong = async()=>{
    if(!songFile) return alert("MP3 chuniye!")
    if(!songKey.trim()) return alert("Rhyme key daalo!")
    setSongBusy(true); setSongMsg("⏳...")
    const fd=new FormData(); fd.append("file",songFile)
    fd.append("rhyme_key",songKey.trim().toLowerCase().replace(/\s+/g,"_"))
    try{
      const d = await fetch(`${API}/api/upload-song`,{method:"POST",body:fd}).then(r=>r.json())
      if(d.ok){
        const dur=d.duration_sec; const mm=Math.floor(dur/60); const ss=String(Math.round(dur%60)).padStart(2,"0")
        setSongMsg(`✅ ${d.mapped_to} — ${mm}:${ss}`)
        setSongFile(null); if(songRef.current) songRef.current.value=""
        refreshSongs()
      } else setSongMsg(`❌ ${d.error}`)
    }catch{ setSongMsg("❌ Server se connect nahi hua") }
    setSongBusy(false)
  }

  // ── Whisper sync ─────────────────────────────────────────────────────────────
  const doWhisperSync = async(lines, song_key) => {
    setSyncStatus("syncing")
    setTimestamps(null)
    try {
      const d = await fetch(`${API}/api/whisper-sync`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ song_key, lines, model:"tiny" })
      }).then(r=>r.json())
      if(d.ok && d.timestamps) {
        setTimestamps(d.timestamps)
        setSyncStatus(d.method==="whisper" ? "done" : "fallback")
        return { timestamps: d.timestamps, method: d.method }
      }
    } catch {}
    setSyncStatus("fallback")
    return null
  }

  // ── Generate ─────────────────────────────────────────────────────────────────
  const generate = async()=>{
    let body = {}

    if(tab==="song"){
      const lines = song.lines_raw.split("\n").map(l=>l.trim()).filter(Boolean)
      if(!lines.length) return alert("Lyrics likho!")
      if(!song.title.trim()) return alert("Song title daalo!")
      if(!song.song_key) return alert("Song select karo (Songs tab se upload karo pehle)!")
      if(song.selected_assets.length===0) return alert("Kam se kam 1 image ya video select karo!")

      // Auto whisper sync if available
      let syncResult = null
      if(whisperAvail) {
        syncResult = await doWhisperSync(lines, song.song_key)
      }

      body = {
        custom_lines: lines,
        topic: song.title.trim(),
        content_type: "song",
        voice: "swara",
        builtin_key: song.song_key,
        bg_key: song.accent_key,
        bg_image_keys: song.selected_assets,
        ...(syncResult ? { timestamps: syncResult.timestamps, sync_method: syncResult.method } : {})
      }
    } else if(tab==="kids"){
      // song_key: if user picked one explicitly, use it; else fallback to builtin_key/topic
      const kSongKey = kids.song_key || kids.builtin_key || kids.topic

      if(kids.mode==="builtin"){
        if(!kids.builtin_key) return alert("Rhyme chunao!")
        body = {
          builtin_key: kids.builtin_key,
          content_type: "rhyme",
          voice: kids.voice,
          ...(kids.song_key ? { song_key_override: kids.song_key } : {})
        }
      } else if(kids.mode==="ai"){
        if(!kids.topic) return alert("Topic likho!")
        body = {
          topic: kids.topic,
          content_type: kids.type,
          voice: kids.voice,
          builtin_key: kids.song_key || kids.topic,
        }
      } else {
        const lines = kids.custom_lines.split("\n").map(l=>l.trim()).filter(Boolean)
        if(!lines.length) return alert("Lyrics likho!")
        if(!kids.custom_title.trim()) return alert("Title daalo!")
        if(!kids.song_key && songs.length > 0) return alert("Song select karo — ya Auto option chunao!")
        body = {
          custom_lines: lines,
          topic: kids.custom_title,
          content_type: kids.type,
          voice: kids.voice,
          char_override: kids.char,
          bg_key: kids.bg_key,
          builtin_key: kSongKey,
        }
      }
    }

    setSyncStatus("")
    setJob(null)
    const d = await fetch(`${API}/api/generate`,{
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify(body)
    }).then(r=>r.json())
    setJobId(d.job_id)
    setJob({status:"queued",progress:0,message:"Queue mein hai..."})
    setBusy(true)
    setTab("status")
  }

  const fmtDur = s => s?`${Math.floor(s/60)}:${String(Math.round(s%60)).padStart(2,"0")}`:"?"

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div style={{minHeight:"100vh",
                 background:"linear-gradient(160deg,#080810,#0d1228,#100820)",
                 color:"#fff",fontFamily:"system-ui,sans-serif",padding:"16px"}}>
      <div style={{maxWidth:700,margin:"0 auto"}}>

        {/* Header */}
        <div style={{textAlign:"center",marginBottom:18}}>
          <h1 style={{margin:"4px 0 2px",fontSize:20,fontWeight:900,letterSpacing:"-0.5px",
                      background:"linear-gradient(90deg,#a78bfa,#60a5fa,#f472b6)",
                      WebkitBackgroundClip:"text",WebkitTextFillColor:"transparent"}}>
            🎵 YT Channel AI
          </h1>
          {health && (
            <div style={{fontSize:11,color:"#444"}}>
              🎶 {health.suno_songs?.length||0} songs &nbsp;•&nbsp;
              🖼️ {health.bg_images?.length||0} images
              {health.ai?.groq && " &nbsp;•&nbsp; 🤖 AI ON"}
            </div>
          )}
        </div>

        {/* Tabs */}
        <div style={{display:"flex",gap:5,marginBottom:14,overflowX:"auto",paddingBottom:2}}>
          {[
            ["song","🎶 Song Video"],
            ["kids","🐱 Kids Rhyme"],
            ["songs","🎵 Songs"],
            ["status","📊 Status"],
          ].map(([k,l])=>(
            <button key={k} onClick={()=>setTab(k)} style={btnStyle(tab===k,"#7c3aed")}>
              {l}{k==="status"&&busy&&" ⏳"}
            </button>
          ))}
        </div>

        {/* ════ SONG VIDEO TAB ════ */}
        {tab==="song" && (
          <div style={{display:"flex",flexDirection:"column",gap:12}}>

            {/* Song title + lyrics */}
            <Card>
              <SectionTitle>✍️ Lyrics</SectionTitle>
              <input value={song.title} onChange={e=>setSf("title",e.target.value)}
                style={{...inp,marginBottom:8}} placeholder="Song title (e.g. Toot Gaya, Tere Bina...)" />
              <textarea value={song.lines_raw} onChange={e=>setSf("lines_raw",e.target.value)}
                rows={6} style={{...inp,resize:"vertical",lineHeight:2.0}}
                placeholder={"toot gayaa hoon main tukado mein\nteree yaadon mein khoyaa hoon\njode na jude ye dil ke tukade\ntere bina adhuraa hoon main"} />
              <div style={{fontSize:11,color:"#444",marginTop:4}}>
                {song.lines_raw.split("\n").filter(l=>l.trim()).length} lines
                &nbsp;•&nbsp; Hindi ya Hinglish dono chalega
              </div>
            </Card>

            {/* Whisper Sync Status Banner */}
            <div style={{
              borderRadius:10, padding:"10px 14px",
              fontSize:12, lineHeight:1.7,
              background: whisperAvail
                ? "rgba(52,211,153,0.07)"
                : "rgba(251,146,60,0.07)",
              border: `1px solid ${whisperAvail ? "rgba(52,211,153,0.2)" : "rgba(251,146,60,0.2)"}`,
              color: whisperAvail ? "#34d399" : "#fb923c",
            }}>
              {whisperAvail === null && "⏳ Whisper check ho raha hai..."}
              {whisperAvail === true && (
                syncStatus === "syncing" ? "⏳ Whisper lyrics sync kar raha hai..." :
                syncStatus === "done"    ? "✅ Whisper sync complete — exact timestamps milenge!" :
                syncStatus === "fallback"? "⚠️ Whisper sync fail — equal division use hogi" :
                "✅ Whisper available — lyrics auto-sync hongi song ke saath!"
              )}
              {whisperAvail === false && (
                <span>
                  ⚠️ Whisper nahi hai — <b>equal division</b> use hogi.<br/>
                  Exact sync ke liye: <code style={{background:"rgba(0,0,0,0.3)",
                    padding:"1px 5px",borderRadius:4}}>pip install openai-whisper torch</code>
                </span>
              )}
            </div>

            {/* Manual Timestamp Editor — shown when whisper not available */}
            {whisperAvail === false && song.song_key && song.lines_raw.trim() && (
              <ManualSyncEditor
                lines={song.lines_raw.split("\n").map(l=>l.trim()).filter(Boolean)}
                songKey={song.song_key}
                songs={songs}
                timestamps={timestamps}
                onDone={(ts)=>{ setTimestamps(ts); setSyncStatus("done") }}
                onClear={()=>{ setTimestamps(null); setSyncStatus("") }}
              />
            )}

            <Card>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8}}>
                <SectionTitle style={{margin:0}}>🖼️ Background Media</SectionTitle>
                <span style={{fontSize:11,color:"#555"}}>
                  {song.selected_assets.length} selected
                </span>
              </div>

              {/* Upload row */}
              <div style={{background:"rgba(124,58,237,0.08)",borderRadius:10,
                           padding:10,marginBottom:10,
                           border:"1px solid rgba(124,58,237,0.2)",
                           fontSize:12,color:"#888",lineHeight:1.8}}>
                📷 <b style={{color:"#a78bfa"}}>Images</b>: JPG, PNG, WebP (1080×1920 best)<br/>
                🎬 <b style={{color:"#a78bfa"}}>Short clips</b>: MP4, MOV, WebM (2-5 sec) — frames auto-extract hote hain<br/>
                ✨ 2-3 images/clips dalo → Ken Burns effect + smooth crossfade
              </div>

              <div style={{display:"flex",gap:8,marginBottom:assetMsg?6:0,flexWrap:"wrap"}}>
                <input ref={assetRef} type="file"
                  accept=".jpg,.jpeg,.png,.webp,.mp4,.mov,.webm"
                  onChange={e=>{setAssetFile(e.target.files?.[0]||null);setAssetMsg("")}}
                  style={{...inp,flex:1,minWidth:0,padding:"8px 10px",fontSize:12,cursor:"pointer"}} />
                <button onClick={uploadAsset} disabled={assetBusy||!assetFile}
                  style={{...btnStyle(!assetBusy&&!!assetFile,"#7c3aed"),
                          padding:"9px 16px",whiteSpace:"nowrap"}}>
                  {assetBusy?"⏳":"⬆️ Upload"}
                </button>
              </div>
              {assetMsg&&<div style={{fontSize:12,marginBottom:8,
                color:assetMsg.startsWith("✅")?"#34d399":assetMsg.startsWith("❌")?"#f87171":"#aaa"}}>
                {assetMsg}</div>}

              {/* Asset grid */}
              {bgAssets.length===0 ? (
                <div style={{textAlign:"center",color:"#333",fontSize:13,padding:"20px 0"}}>
                  Koi image/video nahi — upar se upload karo
                </div>
              ) : (
                <>
                  <div style={{fontSize:11,color:"#444",marginBottom:6}}>
                    👇 Tap to select/deselect — selected items video mein use honge
                  </div>
                  <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:8}}>
                    {bgAssets.map(asset=>{
                      const sel2 = song.selected_assets.includes(asset.filename)
                      return (
                        <div key={asset.filename}
                          style={{position:"relative",borderRadius:10,overflow:"hidden",
                                  border:`2px solid ${sel2?"#a78bfa":"rgba(255,255,255,0.08)"}`,
                                  cursor:"pointer",aspectRatio:"9/16",background:"#0a0814"}}
                          onClick={()=>toggleAsset(asset.filename)}>
                          <img
                            src={`${API}/api/bg-image/${asset.filename}`}
                            alt=""
                            style={{width:"100%",height:"100%",objectFit:"cover",
                                    display:"block",
                                    filter:sel2?"brightness(1)":"brightness(0.4)",
                                    transition:"filter 0.2s"}} />
                          {sel2&&(
                            <div style={{position:"absolute",top:6,right:6,
                                         background:"#a78bfa",borderRadius:"50%",
                                         width:22,height:22,display:"flex",
                                         alignItems:"center",justifyContent:"center",
                                         fontSize:12,fontWeight:900,color:"#fff"}}>✓</div>
                          )}
                          {/* Order badge when selected */}
                          {sel2&&(
                            <div style={{position:"absolute",top:6,left:6,
                                         background:"rgba(0,0,0,0.7)",borderRadius:6,
                                         padding:"2px 6px",fontSize:10,color:"#a78bfa",fontWeight:700}}>
                              #{song.selected_assets.indexOf(asset.filename)+1}
                            </div>
                          )}
                          {asset.from_video&&(
                            <div style={{position:"absolute",bottom:24,left:0,right:0,
                                         textAlign:"center",fontSize:9,color:"#60a5fa",
                                         background:"rgba(0,0,0,0.5)",padding:"2px"}}>
                              🎬 clip frame
                            </div>
                          )}
                          <div style={{position:"absolute",bottom:0,left:0,right:0,
                                       background:"rgba(0,0,0,0.6)",padding:"3px 5px",
                                       fontSize:9,color:"#888",overflow:"hidden",
                                       textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                            {asset.filename.replace(/_f\d{2}\.jpg$/,"")}
                          </div>
                          <button onClick={e=>{e.stopPropagation();deleteAsset(asset.filename)}}
                            style={{position:"absolute",top:sel2?34:6,left:6,
                                    background:"rgba(220,40,40,0.8)",border:"none",
                                    borderRadius:6,padding:"2px 7px",color:"#fff",
                                    fontSize:10,cursor:"pointer"}}>🗑</button>
                        </div>
                      )
                    })}
                  </div>
                </>
              )}
            </Card>

            {/* Song + Accent color */}
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>

              {/* Song selection */}
              <Card>
                <SectionTitle>🎵 MP3 Song</SectionTitle>
                {songs.length===0 ? (
                  <div style={{fontSize:12,color:"#444",padding:"6px 0"}}>
                    Songs tab se upload karo
                  </div>
                ) : (
                  <div style={{display:"flex",flexDirection:"column",gap:5}}>
                    {songs.map(s=>{
                      const skey = s.mapped_keys?.[0]||s.filename.replace(".mp3","")
                      const active = song.song_key===skey
                      return (
                        <button key={s.filename} onClick={()=>setSf("song_key",skey)}
                          style={{padding:"8px 10px",borderRadius:9,border:"1px solid",
                                  borderColor:active?"#60a5fa":"rgba(255,255,255,0.08)",
                                  background:active?"rgba(96,165,250,0.12)":"rgba(255,255,255,0.03)",
                                  color:"#fff",cursor:"pointer",textAlign:"left",fontSize:12}}>
                          🎵 {s.name}
                          <span style={{fontSize:10,color:"#555",marginLeft:6}}>
                            {fmtDur(s.duration_sec)}
                          </span>
                        </button>
                      )
                    })}
                  </div>
                )}
              </Card>

              {/* Accent color */}
              <Card>
                <SectionTitle>🎨 Accent Color</SectionTitle>
                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:5}}>
                  {ACCENT_OPTIONS.map(a=>{
                    const active=song.accent_key===a.key
                    return(
                      <button key={a.key} onClick={()=>setSf("accent_key",a.key)}
                        style={{padding:"7px 6px",borderRadius:8,border:"1px solid",
                                borderColor:active?a.accent:"rgba(255,255,255,0.08)",
                                background:active?a.accent+"22":"rgba(255,255,255,0.03)",
                                color:"#fff",cursor:"pointer",fontSize:11,
                                display:"flex",alignItems:"center",gap:4}}>
                        <span style={{width:10,height:10,borderRadius:"50%",
                                      background:a.accent,flexShrink:0,display:"inline-block"}}/>
                        {a.label}
                      </button>
                    )
                  })}
                </div>
              </Card>
            </div>

            <GenBtn busy={busy} onClick={generate} label="🎬 Song Video Banao!" />
          </div>
        )}

        {/* ════ KIDS RHYME TAB ════ */}
        {tab==="kids" && (
          <div style={{display:"flex",flexDirection:"column",gap:10}}>

            {/* Mode selector */}
            <Card>
              <div style={{display:"flex",gap:6,marginBottom:12}}>
                {[["builtin","📚 Builtin"],["ai","🤖 AI"],["custom","✏️ Custom"]]
                  .map(([k,l])=>(
                    <button key={k} onClick={()=>setKf("mode",k)}
                      style={btnStyle(kids.mode===k,"#f72585")}>
                      {l}
                    </button>
                  ))}
              </div>

              {/* Builtin */}
              {kids.mode==="builtin"&&(
                <div style={{display:"grid",gridTemplateColumns:"repeat(2,1fr)",gap:7}}>
                  {Object.entries(builtins).map(([k,v])=>(
                    <button key={k} onClick={()=>setKf("builtin_key",k)}
                      style={{padding:"10px",borderRadius:10,border:"1px solid",
                              borderColor:kids.builtin_key===k?"#f472b6":"rgba(255,255,255,0.08)",
                              background:kids.builtin_key===k?"rgba(244,114,182,0.12)":"rgba(255,255,255,0.03)",
                              color:"#fff",cursor:"pointer",textAlign:"left"}}>
                      <div style={{fontSize:13,fontWeight:700}}>{v.title}</div>
                    </button>
                  ))}
                </div>
              )}

              {/* AI */}
              {kids.mode==="ai"&&(
                <input value={kids.topic} onChange={e=>setKf("topic",e.target.value)}
                  style={inp} placeholder="Topic: Hathi Raja, Diwali, Titli..." />
              )}

              {/* Custom */}
              {kids.mode==="custom"&&(
                <>
                  <input value={kids.custom_title} onChange={e=>setKf("custom_title",e.target.value)}
                    style={{...inp,marginBottom:8}} placeholder="Title..." />
                  <textarea value={kids.custom_lines} onChange={e=>setKf("custom_lines",e.target.value)}
                    rows={5} style={{...inp,resize:"vertical",lineHeight:1.9,marginBottom:8}}
                    placeholder={"बिल्ली मौसी बिल्ली मौसी\nक्या खाओगी खाना..."} />
                </>
              )}
            </Card>

            {/* Song selector — for ALL modes */}
            <Card>
              <SectionTitle>🎵 MP3 Song Select Karo</SectionTitle>
              {songs.length === 0 ? (
                <div style={{fontSize:12,color:"#555",padding:"6px 0",lineHeight:1.7}}>
                  Koi MP3 nahi mila — <b style={{color:"#f472b6"}}>Songs tab</b> se upload karo pehle
                </div>
              ) : (
                <div style={{display:"flex",flexDirection:"column",gap:5}}>
                  {/* "Auto" option — use builtin song or topic-matched */}
                  <button
                    onClick={()=>setKf("song_key","")}
                    style={{padding:"8px 10px",borderRadius:9,border:"1px solid",
                            borderColor:!kids.song_key?"#f472b6":"rgba(255,255,255,0.08)",
                            background:!kids.song_key?"rgba(244,114,182,0.12)":"rgba(255,255,255,0.03)",
                            color:"#fff",cursor:"pointer",textAlign:"left",fontSize:12}}>
                    🔀 Auto — builtin/topic se match karo
                  </button>
                  {songs.map(s=>{
                    const skey = s.mapped_keys?.[0] || s.filename.replace(".mp3","")
                    const active = kids.song_key === skey
                    return (
                      <button key={s.filename} onClick={()=>setKf("song_key", skey)}
                        style={{padding:"8px 10px",borderRadius:9,border:"1px solid",
                                borderColor:active?"#f472b6":"rgba(255,255,255,0.08)",
                                background:active?"rgba(244,114,182,0.12)":"rgba(255,255,255,0.03)",
                                color:"#fff",cursor:"pointer",textAlign:"left",fontSize:12}}>
                        🎵 {s.name}
                        <span style={{fontSize:10,color:"#555",marginLeft:6}}>
                          {fmtDur(s.duration_sec)}
                        </span>
                      </button>
                    )
                  })}
                </div>
              )}
            </Card>

            {/* Character + BG */}
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
              <Card>
                <SectionTitle>🐱 Character</SectionTitle>
                <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:5}}>
                  {CHAR_OPTIONS.map(c=>(
                    <button key={c.key} onClick={()=>setKf("char",c.key)}
                      style={{...btnStyle(kids.char===c.key,"#06d6a0"),
                              padding:"8px 4px",fontSize:18,textAlign:"center"}}>
                      {c.label}
                    </button>
                  ))}
                </div>
              </Card>
              <Card>
                <SectionTitle>🎨 Background</SectionTitle>
                <div style={{display:"flex",flexDirection:"column",gap:5}}>
                  {BUILTIN_BG.map(b=>(
                    <button key={b.key} onClick={()=>setKf("bg_key",b.key)}
                      style={{padding:"7px 10px",borderRadius:8,border:"1px solid",
                              borderColor:kids.bg_key===b.key?"#fff":"rgba(255,255,255,0.08)",
                              background:kids.bg_key===b.key
                                ?`linear-gradient(135deg,${b.bg[0]}66,${b.bg[1]}66)`
                                :"rgba(255,255,255,0.03)",
                              color:"#fff",cursor:"pointer",fontSize:12,textAlign:"left"}}>
                      {b.label}
                    </button>
                  ))}
                </div>
              </Card>
            </div>

            {/* Type + Voice */}
            <Card>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
                <div>
                  <Label>Content Type</Label>
                  <select value={kids.type} onChange={e=>setKf("type",e.target.value)} style={sel}>
                    {[["rhyme","🎵 Kids Rhyme"],["lullaby","🌙 Lullaby"],
                      ["poem","📝 Kavita"],["song","🎶 Slow Song"],["lofi","☁️ Lofi"]].map(([k,l])=>
                      <option key={k} value={k}>{l}</option>)}
                  </select>
                </div>
                <div>
                  <Label>Voice</Label>
                  <select value={kids.voice} onChange={e=>setKf("voice",e.target.value)} style={sel}>
                    <option value="swara">👩 Swara</option>
                    <option value="madhur">👨 Madhur</option>
                  </select>
                </div>
              </div>
            </Card>

            <GenBtn busy={busy} onClick={generate} label="🎬 Kids Video Banao!" col="#f72585" />
          </div>
        )}

        {/* ════ SONGS TAB ════ */}
        {tab==="songs" && (
          <div style={{display:"flex",flexDirection:"column",gap:10}}>

            {/* Upload song */}
            <Card>
              <SectionTitle>⬆️ Naya Suno MP3 Upload</SectionTitle>
              <div style={{background:"rgba(96,165,250,0.07)",borderRadius:9,
                           padding:10,marginBottom:10,fontSize:12,color:"#666",lineHeight:1.8,
                           border:"1px solid rgba(96,165,250,0.15)"}}>
                1️⃣ suno.com → song generate karo<br/>
                2️⃣ 3 dots → Download → Audio (.mp3)<br/>
                3️⃣ Yahan upload karo, key daalo
              </div>
              <input ref={songRef} type="file" accept=".mp3"
                onChange={e=>{setSongFile(e.target.files?.[0]||null);setSongMsg("")}}
                style={{...inp,marginBottom:8,cursor:"pointer"}} />
              <input value={songKey} onChange={e=>setSongKey2(e.target.value)}
                style={{...inp,marginBottom:8}}
                placeholder="Rhyme key (e.g. toot_gaya, tere_bina, school_chalo)" />
              <button onClick={uploadSong} disabled={songBusy||!songFile}
                style={{...btnStyle(!songBusy&&!!songFile,"#06d6a0"),width:"100%",
                        padding:"12px",fontSize:15}}>
                {songBusy?"⏳ Upload...":"⬆️ Upload Karo"}
              </button>
              {songMsg&&<div style={{marginTop:8,fontSize:13,
                color:songMsg.startsWith("✅")?"#34d399":songMsg.startsWith("❌")?"#f87171":"#aaa"}}>
                {songMsg}</div>}
            </Card>

            {/* Song list */}
            <Card>
              <div style={{display:"flex",justifyContent:"space-between",
                           alignItems:"center",marginBottom:10}}>
                <SectionTitle style={{margin:0}}>📂 Uploaded Songs ({songs.length})</SectionTitle>
                <button onClick={refreshSongs}
                  style={{...btnStyle(false),padding:"5px 10px",fontSize:12}}>🔄</button>
              </div>
              {songs.length===0
                ? <div style={{color:"#333",textAlign:"center",padding:"16px 0",fontSize:13}}>
                    Koi song nahi
                  </div>
                : songs.map(s=>(
                  <div key={s.filename} style={{
                    display:"flex",justifyContent:"space-between",alignItems:"center",
                    padding:"10px 12px",borderRadius:10,marginBottom:6,
                    background:"rgba(255,255,255,0.03)",
                    border:"1px solid rgba(255,255,255,0.06)"}}>
                    <div>
                      <div style={{fontWeight:700,fontSize:13}}>🎵 {s.name}</div>
                      <div style={{fontSize:11,color:"#444",marginTop:2}}>
                        {fmtDur(s.duration_sec)} • {s.size_kb}KB
                        {s.mapped_keys?.length>0 &&
                          <span style={{color:"#a78bfa",marginLeft:6}}>
                            key: {s.mapped_keys.join(", ")}
                          </span>}
                      </div>
                    </div>
                    <button
                      onClick={async()=>{
                        // Optimistic remove
                        setSongs(prev => prev.filter(x => x.filename !== s.filename))
                        await fetch(`${API}/api/delete-song/${encodeURIComponent(s.filename)}`,{method:"DELETE"})
                        refreshSongs()
                      }}
                      style={{background:"rgba(220,40,40,0.15)",border:"none",
                              borderRadius:7,padding:"5px 9px",color:"#f87171",
                              cursor:"pointer",fontSize:12}}>🗑️</button>
                  </div>
                ))}
            </Card>
          </div>
        )}

        {/* ════ STATUS TAB ════ */}
        {tab==="status" && (
          <Card>
            {!job ? (
              <div style={{textAlign:"center",color:"#333",padding:"30px 0"}}>
                Koi job nahi — Song Video ya Kids Rhyme tab se banao
              </div>
            ) : (
              <>
                <div style={{display:"flex",justifyContent:"space-between",
                             alignItems:"center",marginBottom:10}}>
                  <span style={{fontWeight:700,fontSize:15}}>
                    {job.status==="done"?"✅ Video Taiyaar!":
                     job.status==="failed"?"❌ Error":
                     "⏳ Ban Raha Hai..."}
                  </span>
                  <span style={{fontSize:13,color:"#555"}}>{job.progress||0}%</span>
                </div>

                {/* Progress bar */}
                <div style={{height:6,background:"rgba(255,255,255,0.06)",
                             borderRadius:6,overflow:"hidden",marginBottom:10}}>
                  <div style={{height:"100%",borderRadius:6,
                               width:`${job.progress||0}%`,
                               background:"linear-gradient(90deg,#7c3aed,#a78bfa,#60a5fa)",
                               transition:"width 0.5s"}} />
                </div>

                <p style={{fontSize:12,color:"#666",margin:"0 0 10px"}}>{job.message}</p>

                {/* Lines preview */}
                {job.content && (
                  <div style={{background:"rgba(0,0,0,0.25)",borderRadius:10,
                               padding:10,marginBottom:10}}>
                    <div style={{fontWeight:700,color:"#a78bfa",marginBottom:6,fontSize:14}}>
                      {job.content.title}
                    </div>
                    {(job.content.lines||[]).map((l,i)=>(
                      <div key={i} style={{fontSize:12,color:"#888",padding:"2px 0",
                                           paddingLeft:10,
                                           borderLeft:"2px solid rgba(124,58,237,0.3)",
                                           marginBottom:2}}>
                        {l}
                      </div>
                    ))}
                  </div>
                )}

                {job.status==="done" && (
                  <a href={`${API}/api/download/${jobId}`}
                    style={{display:"block",textAlign:"center",padding:"14px",
                            borderRadius:12,
                            background:"linear-gradient(135deg,#7c3aed,#60a5fa)",
                            color:"#fff",textDecoration:"none",fontWeight:900,fontSize:16}}>
                    ⬇️ Video Download Karo
                  </a>
                )}

                {job.status==="failed" && (
                  <div style={{background:"rgba(220,40,40,0.08)",borderRadius:10,
                               padding:10,fontSize:11,color:"#f87171",
                               fontFamily:"monospace",maxHeight:150,overflow:"auto"}}>
                    {job.error_detail||job.message}
                  </div>
                )}
              </>
            )}
          </Card>
        )}

        <p style={{textAlign:"center",color:"#1a1a2e",fontSize:11,marginTop:20}}>
          🎬 Suno Music • 🖼️ Ken Burns • 📝 Synced Captions
        </p>
      </div>
    </div>
  )
}

export default function App() {
  return <ErrorBoundary><AppInner /></ErrorBoundary>
}

// ── Manual Timestamp Editor ──────────────────────────────────────────────────
function ManualSyncEditor({ lines, songKey, songs, timestamps, onDone, onClear }) {
  const [open, setOpen]       = useState(false)
  const [marks, setMarks]     = useState([])     // array of {start, end} per line
  const [curLine, setCurLine] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [currentT, setCurrentT] = useState(0)
  const audioRef = useRef(null)
  const rafRef   = useRef(null)

  // Find the actual MP3 filename
  const songObj = songs.find(s => s.mapped_keys?.includes(songKey) || s.filename.replace(".mp3","")===songKey)
  const audioSrc = songObj ? `${API}/api/stream-song/${songObj.filename}` : null

  const reset = () => {
    setMarks([]); setCurLine(0); setPlaying(false); setCurrentT(0)
    if(audioRef.current){ audioRef.current.pause(); audioRef.current.currentTime=0 }
  }

  const tick = () => {
    if(audioRef.current && !audioRef.current.paused){
      setCurrentT(audioRef.current.currentTime)
      rafRef.current = requestAnimationFrame(tick)
    }
  }

  const togglePlay = () => {
    if(!audioRef.current) return
    if(audioRef.current.paused){
      audioRef.current.play()
      setPlaying(true)
      rafRef.current = requestAnimationFrame(tick)
    } else {
      audioRef.current.pause(); setPlaying(false)
      cancelAnimationFrame(rafRef.current)
    }
  }

  const markLine = () => {
    if(!audioRef.current) return
    const t = audioRef.current.currentTime
    setMarks(prev => {
      const next = [...prev]
      // Set end of previous line
      if(curLine > 0 && next[curLine-1]){
        next[curLine-1] = { ...next[curLine-1], end: t - 0.05 }
      }
      // Start of current line
      next[curLine] = { start: t, end: t + 3 }
      return next
    })
    if(curLine < lines.length - 1){
      setCurLine(c => c+1)
    } else {
      // Last line — mark end at song duration
      const dur = audioRef.current.duration || currentT + 2
      setMarks(prev => {
        const next = [...prev]
        if(next[curLine]) next[curLine].end = dur - 0.1
        return next
      })
      setPlaying(false)
      audioRef.current.pause()
    }
  }

  const finish = () => {
    const ts = lines.map((text, i) => ({
      text,
      start: marks[i]?.start ?? (i * 3),
      end:   marks[i]?.end   ?? (i * 3 + 2.8),
    }))
    onDone(ts)
    setOpen(false)
  }

  // Keyboard: spacebar = mark
  useEffect(()=>{
    if(!open) return
    const handler = (e) => {
      if(e.code === "Space"){ e.preventDefault(); markLine() }
    }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [open, curLine, currentT])

  useEffect(()=>{ return ()=>cancelAnimationFrame(rafRef.current) },[])

  const fmtT = s => `${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,"0")}.${String(Math.floor((s%1)*10))}`

  if(!open) return (
    <div style={{display:"flex",gap:8,alignItems:"center"}}>
      <button onClick={()=>{setOpen(true);reset()}}
        style={{...btnStyle(false,"#f59e0b"),padding:"9px 14px",fontSize:12,flex:1}}>
        ✋ Manual Sync Editor — Khud timestamps mark karo
      </button>
      {timestamps && (
        <button onClick={onClear}
          style={{...btnStyle(false,"#ef4444"),padding:"9px 12px",fontSize:12}}>
          🗑 Clear
        </button>
      )}
    </div>
  )

  return (
    <Card style={{border:"1px solid rgba(245,158,11,0.3)",background:"rgba(245,158,11,0.05)"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
        <SectionTitle style={{margin:0,color:"#f59e0b"}}>✋ Manual Sync Editor</SectionTitle>
        <button onClick={()=>setOpen(false)}
          style={{...btnStyle(false),padding:"4px 10px",fontSize:11}}>✕ Close</button>
      </div>

      <div style={{fontSize:12,color:"#777",marginBottom:10,lineHeight:1.7}}>
        1️⃣ Play karo &nbsp;→&nbsp; 2️⃣ Jab bhi next line shuru ho, <b style={{color:"#f59e0b"}}>SPACEBAR</b> dabaao<br/>
        Ya <b style={{color:"#f59e0b"}}>Mark karo</b> button dabao &nbsp;→&nbsp; Sab lines mark hone ke baad <b>Save karo</b>
      </div>

      {/* Audio player */}
      {audioSrc && <audio ref={audioRef} src={audioSrc} onEnded={()=>setPlaying(false)} />}
      {!audioSrc && <div style={{color:"#f87171",fontSize:12,marginBottom:8}}>⚠️ Audio stream nahi — Songs tab mein check karo</div>}

      {/* Controls */}
      <div style={{display:"flex",gap:8,marginBottom:12}}>
        <button onClick={togglePlay} disabled={!audioSrc}
          style={{...btnStyle(playing,"#f59e0b"),padding:"10px 18px",fontSize:14,flex:1}}>
          {playing ? "⏸ Pause" : "▶️ Play"}
        </button>
        <button onClick={markLine} disabled={!audioSrc||!playing}
          style={{...btnStyle(playing&&!!audioSrc,"#10b981"),
                  padding:"10px 18px",fontSize:14,flex:1,
                  opacity: playing ? 1 : 0.4}}>
          🎯 Mark Line {curLine+1}/{lines.length}
        </button>
        <button onClick={reset}
          style={{...btnStyle(false),padding:"10px 14px",fontSize:12}}>
          🔄
        </button>
      </div>

      {/* Current time */}
      <div style={{textAlign:"center",fontSize:11,color:"#555",marginBottom:10,fontFamily:"monospace"}}>
        ⏱ {fmtT(currentT)}
        {playing && curLine < lines.length &&
          <span style={{color:"#f59e0b",marginLeft:8}}>
            → SPACE = Mark "{lines[curLine]?.slice(0,20)}..."
          </span>
        }
      </div>

      {/* Lines with marks */}
      <div style={{display:"flex",flexDirection:"column",gap:5,marginBottom:12,
                   maxHeight:200,overflowY:"auto"}}>
        {lines.map((line,i)=>{
          const marked = !!marks[i]
          const isCur  = i === curLine
          return (
            <div key={i} style={{
              display:"flex",alignItems:"center",gap:8,
              padding:"7px 10px",borderRadius:8,
              background: isCur ? "rgba(245,158,11,0.12)"
                         : marked ? "rgba(16,185,129,0.08)"
                         : "rgba(255,255,255,0.03)",
              border:`1px solid ${isCur?"rgba(245,158,11,0.4)":marked?"rgba(16,185,129,0.25)":"rgba(255,255,255,0.05)"}`,
            }}>
              <span style={{fontSize:16,flexShrink:0}}>
                {isCur ? "👉" : marked ? "✅" : "⬜"}
              </span>
              <span style={{fontSize:12,flex:1,color:isCur?"#f59e0b":marked?"#34d399":"#555"}}>
                {line}
              </span>
              {marked && marks[i] && (
                <span style={{fontSize:10,fontFamily:"monospace",color:"#444",flexShrink:0}}>
                  {fmtT(marks[i].start)} → {fmtT(marks[i].end)}
                </span>
              )}
            </div>
          )
        })}
      </div>

      {/* Save button */}
      {marks.length === lines.length && (
        <button onClick={finish}
          style={{...btnStyle(true,"#10b981"),width:"100%",padding:"12px",fontSize:14}}>
          💾 Timestamps Save Karo — Video Banao!
        </button>
      )}
    </Card>
  )
}



function Card({children,style={}}) {
  return (
    <div style={{
      background:"rgba(255,255,255,0.035)",
      borderRadius:14,padding:14,
      border:"1px solid rgba(255,255,255,0.07)",
      ...style}}>
      {children}
    </div>
  )
}

function SectionTitle({children,style={}}) {
  return (
    <div style={{fontSize:12,fontWeight:700,color:"#666",
                 marginBottom:8,textTransform:"uppercase",
                 letterSpacing:"0.5px",...style}}>
      {children}
    </div>
  )
}

function Label({children}) {
  return <div style={{fontSize:11,color:"#555",marginBottom:5}}>{children}</div>
}

function GenBtn({busy,onClick,label,col="#7c3aed"}) {
  return (
    <button onClick={onClick} disabled={busy}
      style={{width:"100%",padding:"16px",borderRadius:13,border:"none",
              cursor:busy?"not-allowed":"pointer",
              background:busy
                ?"rgba(80,80,80,0.3)"
                :`linear-gradient(135deg,${col},${col}cc)`,
              color:"#fff",fontSize:16,fontWeight:900,
              boxShadow:busy?"none":`0 4px 24px ${col}55`,
              letterSpacing:"0.3px"}}>
      {busy?"⏳ Video Ban Raha Hai...":label}
    </button>
  )
}