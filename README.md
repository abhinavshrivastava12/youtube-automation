# 🎬 YT Channel AI — Indian Shorts Automation

Hindi mein fully automated YouTube Shorts channel — topic do, video bane, upload ho jaye.

## Kya karta hai

- 🤣 **Memes & Humor** — Desi funny videos
- 🐣 **Kids Stories** — Hindi kahaniyaan  
- 😱 **Facts & News** — Shocking Indian facts
- 🎙️ **Hindi TTS** — Natural Hindi/Hinglish voice
- 📱 **Shorts Format** — 1080×1920 vertical
- ⏰ **Auto Schedule** — Din mein 3 baar automatic
- 📤 **YouTube Upload** — credentials.json se

## Setup (Windows)

### Step 1 — Backend

```powershell
cd ytchannel\backend
pip install flask flask-cors python-dotenv edge-tts Pillow groq
```

**.env file banao:**
```
GROQ_API_KEY=gsk_apni_key_yahan
```

**Chalaao:**
```powershell
python app.py
```

### Step 2 — Frontend

```powershell
cd ytchannel\frontend
npm install
npm run dev
```

Browser mein kholo: **http://localhost:3000**

---

## AI Fallback Chain

```
Groq (free) → Gemini (free) → OpenAI → Claude
```
Ek fail → automatically next try karta hai.

## Auto Scheduler

Frontend mein **⏰ Auto** tab mein:
1. Times set karo (default: 9am, 3pm, 8pm)
2. Niches chunno
3. Toggle ON karo
4. Backend chal raha ho — automatic videos banti rahengi

## YouTube Upload Setup

1. [Google Cloud Console](https://console.cloud.google.com) → New Project
2. "YouTube Data API v3" enable karo
3. Credentials → OAuth 2.0 → Desktop App → Download JSON
4. File ka naam `credentials.json` rakho → `backend/` mein daalo
5. Pehli baar browser mein login hoga → token save ho jayega

## File Structure

```
ytchannel/
├── backend/
│   ├── app.py            ← Main API
│   ├── requirements.txt
│   ├── .env              ← API keys
│   └── credentials.json  ← YouTube (optional)
└── frontend/
    ├── src/App.jsx       ← UI
    ├── index.html
    └── package.json
```