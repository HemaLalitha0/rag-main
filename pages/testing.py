from __future__ import annotations
import re
import io
import sys
import json
import time
import math
import pickle
import base64
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from io import BytesIO
import streamlit as st
import html as _html
import subprocess
import shutil
import requests
from urllib.parse import urlparse, parse_qs

# Optional/soft imports for extended features; set to None when unavailable.
try:
    import openai
except Exception:
    openai = None
try:
    import importlib
    genai = importlib.import_module("genai")
except Exception:
    genai = None
try:
    from groq import Groq
except Exception:
    Groq = None
try:
    import fitz
except Exception:
    fitz = None
try:
    from PIL import Image, ImageDraw
except Exception:
    Image = None
    ImageDraw = None
try:
    import pytesseract
except Exception:
    pytesseract = None
try:
    import tiktoken
except Exception:
    tiktoken = None
if "torchvision" not in sys.modules:
    sys.modules["torchvision"] = None
SentenceTransformer = None
CrossEncoder = None
try:
    import faiss
except Exception:
    faiss = None
import numpy as np
try:
    from rank_bm25 import BM25Okapi
except Exception:
    BM25Okapi = None

# Local paths and caches
PDF_DIR = Path.cwd() / "pdfs"
PDF_DIR.mkdir(parents=True, exist_ok=True)
KB_DIR = Path.cwd() / "kb_cache"
KB_DIR.mkdir(parents=True, exist_ok=True)
CHUNKS_PATH = KB_DIR / "chunks.json"
METAS_PATH = KB_DIR / "metas.json"
EMBED_CACHE_PATH = KB_DIR / "embed_cache.json"
FAISS_INDEX_PATH = KB_DIR / "faiss.index"
BM25_CACHE_PATH = KB_DIR / "bm25_cache.json"

# Small defaults to avoid NameErrors
BOOST_TERMS = []
_lemm = None

# ----------------------------
# Enhanced YouTube Transcript Fetcher (from test.py)
# ----------------------------
import os
import io
import pickle

# Optional: Google OAuth (only if client_secret.json exists)
GOOGLE_AUTH_AVAILABLE = False
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    import google.auth.exceptions
    GOOGLE_AUTH_AVAILABLE = True
except Exception:
    pass

# Optional: community transcript lib
try:
    from youtube_transcript_api import YouTubeTranscriptApi
except Exception:
    YouTubeTranscriptApi = None

# Config
TMP = Path(tempfile.gettempdir()) / "yt_transcript_cleaner"
TMP.mkdir(exist_ok=True)
TOKEN_PICKLE = TMP / "yt_token.pickle"
CLIENT_SECRET = Path("client_secret.json")
PDF_DIR = Path.cwd() / "pdfs"  # Reuse your existing PDF_DIR

def extract_vid(url: str) -> Optional[str]:
    if not url:
        return None
    m = re.search(r"(?:v=|/)([A-Za-z0-9_-]{11})(?:[&?]|$)", url)
    return m.group(1) if m else None

def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def clean_vtt_text(vtt: str) -> str:
    if not vtt:
        return ""
    vtt = re.sub(r"^\s*WEBVTT.*?\n", "", vtt, flags=re.S | re.I)
    vtt = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}[^\n]*\n", "", vtt)
    vtt = re.sub(r"</?c[^>]*>", "", vtt)
    vtt = re.sub(r"<[^>]+>", "", vtt)
    lines = [line.strip() for line in vtt.splitlines() if line.strip()]
    cleaned_lines = []
    prev = None
    for ln in lines:
        ln = normalize_whitespace(ln)
        if ln == prev:
            continue
        cleaned_lines.append(ln)
        prev = ln
    return normalize_whitespace(" ".join(cleaned_lines))

def extract_text_from_ttml(ttml: str) -> str:
    parts = re.findall(r"<text[^>]*>(.*?)</text>", ttml, flags=re.S)
    parts = [_html.unescape(re.sub(r"\s+", " ", p.replace("\n", " ")).strip()) for p in parts if p.strip()]
    result = []
    prev = None
    for p in parts:
        if p == prev:
            continue
        result.append(p)
        prev = p
    return " ".join(result).strip()

def remove_timestamped_fragments_and_dedup(text: str) -> str:
    text = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3}", "", text)
    text = re.sub(r"-->", "", text)
    text = re.sub(r"\[music\]|\(music\)", "", text, flags=re.I)
    return normalize_whitespace(text)

def get_youtube_service():
    creds = None
    if TOKEN_PICKLE.exists():
        try:
            with open(TOKEN_PICKLE, "rb") as f:
                creds = pickle.load(f)
        except Exception:
            creds = None
    if not creds or not getattr(creds, "valid", False):
        if creds and getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds:
            if not CLIENT_SECRET.exists():
                return None
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), ["https://www.googleapis.com/auth/youtube.force-ssl"])
            creds = flow.run_local_server(port=0, prompt="consent")
        try:
            with open(TOKEN_PICKLE, "wb") as f:
                pickle.dump(creds, f)
        except Exception:
            pass
    try:
        return build("youtube", "v3", credentials=creds)
    except Exception:
        return None

def fetch_via_api(video_id: str):
    try:
        service = get_youtube_service()
        if not service:
            return None
        req = service.captions().list(part="snippet", videoId=video_id)
        resp = req.execute()
        items = resp.get("items", [])
        if not items:
            return None
        chosen = next((c for c in items if c.get("snippet", {}).get("language", "").startswith("en")), items[0])
        cap_id = chosen["id"]
        from googleapiclient.http import MediaIoBaseDownload
        download_request = service.captions().download(id=cap_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, download_request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)
        raw = fh.read().decode("utf-8", errors="ignore")
        text = extract_text_from_ttml(raw) if raw.strip().startswith("<") else raw
        return remove_timestamped_fragments_and_dedup(text) or None
    except Exception:
        return None

def fetch_via_youtube_transcript_api(video_id: str):
    if not YouTubeTranscriptApi:
        return None
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
        text = " ".join(t["text"] for t in transcript if t.get("text"))
        return normalize_whitespace(text) or None
    except Exception:
        return None

def fetch_via_timedtext(video_id: str):
    for lang in ("en", "en-US", "a.en"):
        try:
            r = requests.get(f"https://www.youtube.com/api/timedtext?lang={lang}&v={video_id}", timeout=10)
            if r.status_code == 200 and r.text.strip():
                text = extract_text_from_ttml(r.text)
                if text:
                    return text
        except Exception:
            continue
    return None

def fetch_via_scrape(video_id: str):
    try:
        r = requests.get(f"https://www.youtube.com/watch?v={video_id}", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        m = re.search(r'"captionTracks":(\[.*?\])', r.text)
        if not m:
            return None
        tracks = json.loads(m.group(1))
        track = next((t for t in tracks if str(t.get("languageCode", "")).startswith("en")), tracks[0])
        base_url = track.get("baseUrl")
        if not base_url:
            return None
        for suffix in ("&fmt=vtt", "&fmt=srv3", ""):
            try:
                res = requests.get(base_url + suffix, timeout=10)
                if res.status_code == 200 and res.text.strip():
                    if suffix.endswith("srv3") or res.text.strip().startswith("<"):
                        return extract_text_from_ttml(res.text)
                    else:
                        return clean_vtt_text(res.text)
            except Exception:
                continue
    except Exception:
        pass
    return None

def fetch_via_ytdlp_captions(video_url: str, video_id: str):
    tmp = TMP / f"ytdlp_{video_id}"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        cmd = ["yt-dlp", "--write-auto-sub", "--sub-lang", "en", "--skip-download", "-o", "%(id)s.%(ext)s", video_url]
        subprocess.run(cmd, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        vtt = next((f for f in tmp.glob("*.vtt")), None)
        if not vtt:
            candidates = list(tmp.glob("*.en.vtt")) + list(tmp.glob("*.en.*"))
            vtt = candidates[0] if candidates else None
        if vtt and vtt.exists():
            raw = vtt.read_text(encoding="utf-8", errors="ignore")
            return clean_vtt_text(raw) or None
    except Exception:
        pass
    return None

def fetch_via_whisper(video_url: str, video_id: str):
    tmp = TMP / f"whisper_{video_id}"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        cmd = ["yt-dlp", "-x", "--audio-format", "mp3", "-o", "%(id)s.%(ext)s", video_url]
        subprocess.run(cmd, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        audio = next((f for f in tmp.glob("*.mp3")), None)
        if not audio:
            return None
        try:
            import importlib
            fw = importlib.import_module("faster_whisper")
            model = fw.WhisperModel("base", device="cpu")
            segments, _ = model.transcribe(str(audio))
            text = " ".join(s.text for s in segments)
            return normalize_whitespace(text) or None
        except Exception:
            pass
        try:
            import importlib
            whisper = importlib.import_module("whisper")
            model = whisper.load_model("base")
            result = model.transcribe(str(audio))
            return normalize_whitespace(result.get("text", "")) or None
        except Exception:
            return None
    except Exception:
        return None

def fetch_youtube_transcript_safe(url: str) -> Optional[str]:
    """Returns clean transcript text or None. Tries 6 methods in order."""
    vid = extract_vid(url)
    if not vid:
        return None

    # 1. OAuth API
    txt = fetch_via_api(vid)
    if txt and len(txt.split()) > 8:
        return txt

    # 2. Community API
    txt = fetch_via_youtube_transcript_api(vid)
    if txt and len(txt.split()) > 8:
        return txt

    # 3. Timedtext
    txt = fetch_via_timedtext(vid)
    if txt and len(txt.split()) > 8:
        return txt

    # 4. Scrape
    txt = fetch_via_scrape(vid)
    if txt and len(txt.split()) > 8:
        return txt

    # 5. yt-dlp captions
    txt = fetch_via_ytdlp_captions(url, vid)
    if txt and len(txt.split()) > 8:
        return txt

    # 6. Whisper fallback
    txt = fetch_via_whisper(url, vid)
    if txt and len(txt.split()) > 8:
        return txt

    return None

def get_youtube_thumbnail_url(video_id: str) -> str:
    if not video_id:
        return ""
    qualities = ["maxresdefault", "sddefault", "hqdefault", "mqdefault", "default"]
    base_url = f"https://img.youtube.com/vi/{video_id}/"
    for quality in qualities:
        url = f"{base_url}{quality}.jpg"
        try:
            response = requests.head(url, timeout=2)
            if response.status_code == 200:
                return url
        except Exception:
            continue
    return f"{base_url}default.jpg"

# ---------- End Enhanced YouTube Transcript Methods ----------

def get_secret(name: str) -> Optional[str]:
    if hasattr(st, "secrets") and name in st.secrets:
        return st.secrets[name]
    return os.getenv(name)

GEMINI_KEY = get_secret("GOOGLE_API_KEY") or get_secret("GEMINI_KEY")
GROQ_KEY = get_secret("GROQ_API_KEY") or get_secret("GROQ_KEY")
OPENAI_KEY = get_secret("OPENAI_API_KEY") or get_secret("OPENAI_KEY")
SERPAPI_KEY = get_secret("SERPAPI_KEY")

if genai is not None and GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
    except Exception:
        pass

groq_client = None
if Groq is not None and GROQ_KEY:
    try:
        groq_client = Groq(api_key=GROQ_KEY)
    except Exception:
        groq_client = None

if openai is not None and OPENAI_KEY:
    try:
        openai.api_key = OPENAI_KEY
    except Exception:
        pass

# ---------------------------
# Streamlit page config & CSS
# ---------------------------
st.set_page_config(page_title="RAG Assistant", page_icon="📚", layout="wide")
CSS_STYLES = """
<style>
:root { color-scheme: dark; }
html, body, .stApp { background: #000000; color: #e6eef3; }
.block-container { padding-top: 0.4rem; }
.big-title { font-size: 4rem; font-weight: 700; color:#FF69B4; text-align:center; margin:6px 0; }
.container-card { background: rgba(12,12,12,0.6); border-radius:10px; padding:12px; margin-bottom:12px; }
.user-box { background: linear-gradient(90deg,#ffd7a8,#ffb4c6); color:#0b0b0b; padding:12px; border-radius:12px; max-width:80%; margin-left:auto; white-space:pre-wrap; }
.ai-box { background: linear-gradient(90deg,#0f1724,#071426); color:#e6eef3; padding:12px; border-radius:12px; max-width:85%; white-space:pre-wrap; }
.ref-card { background:#071426; padding:8px; border-radius:8px; margin-top:6px; color:#cfe8ff; }
.modal-overlay { position: fixed; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.6); display:flex; align-items:center; justify-content:flex-start; z-index:9999; }
.modal-card { background: #071426; padding:16px; border-radius:10px; width:70%; height:85%; overflow:auto; margin-left:6%; }
.modal-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; color:#fff; }
.copy-btn { background:#0b1220; border-radius:6px; color:#fff; padding:6px 10px; border:none; margin-top:6px; cursor: pointer; }
.small-muted { color:#9aa6b2; font-size:0.9em; }
.score-badge { font-size:0.8em; color:#64d8ff; background:#0b1e33; padding:3px 6px; border-radius:6px; }
.answer-section { margin-bottom: 15px; }
.answer-header { font-weight: bold; margin-bottom: 5px; color: #4f7bfd; }
.hover-container {
  position: relative;
  display: inline-block;
}
.hover-preview {
  display: none;
  position: absolute;
  bottom: 120%;
  left: 0;
  z-index: 10000;
  background: #071426;
  padding: 10px;
  border-radius: 8px;
  width: 300px;
  max-height: 420px;
  overflow: auto;
  box-shadow: 0 4px 20px rgba(0,0,0,0.7);
  border: 1px solid #4f7bfd;
}
.hover-preview img {
  width: 100%;
  height: auto;
  object-fit: contain;
}
.hover-container:hover .hover-preview {
  display: block;
}
.scrollable-summary {
  max-height: 300px;
  overflow-y: auto;
  padding: 10px;
  background: rgba(15,23,36,0.6);
  border-radius: 10px;
  border: 1px solid #1e293b;
  font-size: 0.95em;
  line-height: 1.6;
}
.feedback-area {
  margin-top: 10px;
  padding: 10px;
  background: #0a101a;
  border-radius: 8px;
  border: 1px solid #334155;
}
.feedback-btn {
    font-size: 1.1em !important;
    padding: 0 8px !important;
    border-radius: 12px !important;
    margin: 0 2px !important;
    min-width: 28px;
    min-height: 28px;
}
.like-btn { background-color: #4ade80 !important; color: white !important; }
.dislike-btn { background-color: #f87171 !important; color: white !important; }
.retrieval-explain {
  background: rgba(8,10,14,0.55);
  border: 1px solid #2b394b;
  padding: 10px;
  border-radius: 8px;
  font-size: 0.95em;
}
.api-key-info {
  background: rgba(45, 80, 120, 0.3);
  border-left: 4px solid #3498db;
  padding: 12px;
  border-radius: 0 8px 8px 0;
  margin: 10px 0;
}
.test-video-btn {
  background: linear-gradient(90deg, #8e44ad, #3498db);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 0.3s ease;
}
.test-video-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}
</style>
"""
st.markdown(CSS_STYLES, unsafe_allow_html=True)
JS_SCRIPTS = """
<script>
function copyToClipboard(id) {
  const el = document.getElementById(id);
  if (!el) { alert('Copy failed'); return; }
  const text = el.innerText || el.textContent || "";
  navigator.clipboard.writeText(text).then(() => {
    alert(' Copied to clipboard!');
  }).catch(err => {
    prompt('Copy failed. Press Ctrl+C to copy:', text);
  });
}
</script>
"""
st.markdown(JS_SCRIPTS, unsafe_allow_html=True)

# ---------------------------
# Simple nav
# ---------------------------
is_logged_in = st.session_state.get('logged_in', False)
username = st.session_state.get('username', 'Guest')
st.markdown(f"""
<style>
.nav-container {{
    display: flex;
    justify-content: space-between;
    padding: 12px 20px;
    background: #0a0a0a;
    border-bottom: 1px solid #333;
    position: sticky;
    top: 0;
    z-index: 100;
    font-family: 'Exo 2', sans-serif;
}}
.nav-links {{
    display: flex;
    gap: 0.8rem;
}}
.nav-link {{
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
    min-width: 80px;
    text-align: center;
    background: rgba(255,255,255,0.08);
    color: #b3b3b3;
    border: 1px solid #333;
    transition: all 0.2s ease;
}}
.nav-link:hover {{
    background: rgba(255,255,255,0.15);
    transform: translateY(-2px);
}}
.user-info {{
    display: flex;
    align-items: center;
    gap: 12px;
    color: white;
}}
</style>
<div class="nav-container">
  <div class="nav-links">
    <div class="nav-link" onclick="window.top.location.href='/login'">Login</div>
    <div class="nav-link" onclick="window.top.location.href='/admin'">Admin</div>
    <div class="nav-link" onclick="window.top.location.href='/RAG_Assistant'">Colab</div>
    <div class="nav-link active">Pro</div>
    <div class="nav-link" onclick="window.top.location.href='/mock_interview'" style="border-color:#3B82F6;color:#60A5FA;">🎯 Mock Interview</div>
  </div>
  <div class="user-info">
    <span>👤 {username}</span>
  </div>
</div>
""", unsafe_allow_html=True)

nav_c1, nav_c2, nav_c3, nav_c4, nav_c5 = st.columns(5)
with nav_c1:
    if st.button("🔐 Login", key="top_nav_login_pro", use_container_width=True):
        st.switch_page("pages/login.py")
with nav_c2:
    if st.button("👑 Admin", key="top_nav_admin_pro", use_container_width=True):
        st.switch_page("pages/admin.py")
with nav_c3:
    if st.button("📚 Colab", key="top_nav_colab_pro", use_container_width=True):
        st.switch_page("pages/RAG_Assistant.py")
with nav_c4:
    st.button("⚡ Pro (Active)", key="top_nav_pro_pro", disabled=True, use_container_width=True)
with nav_c5:
    if st.button("🎯 Mock Interview", key="top_nav_mock_pro", type="primary", use_container_width=True):
        st.switch_page("pages/mock_interview.py")

# ---------------------------
# Logout handling
# ---------------------------
if is_logged_in:
    if st.button("🚪 Logout", key="logout_btn", use_container_width=True):
        for k in ["logged_in", "username", "is_premium", "is_admin", "user_id"]:
            if k in st.session_state:
                del st.session_state[k]
        st.success("You have been logged out. Redirecting to login...")
        try:
            st.switch_page("pages/login.py")
        except Exception:
            st.markdown("""<script>window.location.href = 'pages/login.py';</script>""", unsafe_allow_html=True)
        time.sleep(0.6)
        st.stop()

# ---------------------------
# Utilities: file save, PDF extract
# ---------------------------
def save_uploaded_file(uploaded, dest_dir: Path = PDF_DIR) -> str:
    dest = dest_dir / uploaded.name
    with open(dest, "wb") as wf:
        wf.write(uploaded.getbuffer())
    return str(dest)

def extract_blocks_from_pdf(path: str) -> List[Tuple[str, int, Optional[Tuple[float, float, float, float]]]]:
    out = []
    if fitz is None:
        return out
    try:
        doc = fitz.open(path)
        for pidx in range(len(doc)):
            page = doc.load_page(pidx)
            blocks = page.get_text("dict").get("blocks", [])
            for b in blocks:
                if b.get("type") != 0:
                    continue
                spans = []
                for line in b.get("lines", []):
                    for span in line.get("spans", []):
                        t = span.get("text", "").strip()
                        if t:
                            spans.append(t)
                txt = " ".join(spans).strip()
                if len(txt) > 10:
                    bbox = tuple(b.get("bbox")) if b.get("bbox") else None
                    out.append((txt, pidx, bbox))
        doc.close()
    except Exception as e:
        st.error(f"Failed to extract text from PDF: {e}")
    return out

def extract_text_fallback(path: str) -> str:
    try:
        with open(path, "rb") as f:
            raw = f.read().decode("utf-8", errors="ignore")
            lines = [line.strip() for line in raw.splitlines() if len(line.strip()) > 20 and any(c.isalpha() for c in line)]
            return " ".join(lines[:50])
    except Exception:
        return ""

def extract_texts_from_file(path: str) -> List[Dict[str, Any]]:
    suffix = Path(path).suffix.lower()
    out = []
    if suffix == ".pdf":
        blocks = extract_blocks_from_pdf(path)
        if blocks:
            for txt, pidx, bbox in blocks:
                out.append({"text": txt, "meta": {"file": Path(path).name, "page": pidx + 1, "bbox": bbox}})
            return out
        raw = extract_text_fallback(path)
        if raw:
            out.append({"text": raw, "meta": {"file": Path(path).name, "page": 1, "bbox": None}})
            return out
    elif suffix == ".txt":
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read().strip()
            if raw and len(raw) > 10:
                out.append({"text": raw, "meta": {"file": Path(path).name, "page": 1, "bbox": None}})
            return out
        except Exception as e:
            st.warning(f"Failed to read text file: {e}")
            return []
    else:
        try:
            if Image is not None and pytesseract is not None:
                img = Image.open(path)
                text = pytesseract.image_to_string(img).strip()
                if text and len(text) > 20:
                    out.append({"text": text, "meta": {"file": Path(path).name, "page": 1, "bbox": None}})
                    return out
        except Exception as e:
            st.warning(f"OCR failed: {e}")
        out.append({"text": f"[Image: {Path(path).name}] (OCR failed)", "meta": {"file": Path(path).name, "page": 1, "bbox": None}})
    return out

# ---------------------------
# Chunking functions
# ---------------------------
def chunk_paragraph(text: str, size_words: int, overlap_words: int) -> List[str]:
    parts = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
    out = []
    for p in parts:
        words = p.split()
        if len(words) > size_words:
            step = max(50, size_words - overlap_words)
            for i in range(0, len(words), step):
                out.append(" ".join(words[i:i+size_words]))
        else:
            out.append(p)
    return out

def chunk_sentence(text: str) -> List[str]:
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

def chunk_fixed(text: str, size: int) -> List[str]:
    toks = text.split()
    return [" ".join(toks[i:i+size]) for i in range(0, len(toks), size)]

def chunk_sliding(text: str, size: int, overlap: int) -> List[str]:
    toks = text.split()
    step = max(1, size - overlap)
    return [" ".join(toks[i:i+size]) for i in range(0, len(toks), step)]

def chunk_recursive(text: str, max_words: int, overlap_words: int) -> List[str]:
    if len(text.split()) <= max_words:
        return [text]
    sents = chunk_sentence(text)
    parts = []
    cur = []
    cur_words = 0
    for s in sents:
        sw = len(s.split())
        if cur_words + sw <= max_words:
            cur.append(s)
            cur_words += sw
        else:
            parts.append(" ".join(cur))
            if overlap_words > 0:
                ov = []
                wcount = 0
                for sent in reversed(cur):
                    sw2 = len(sent.split())
                    if wcount + sw2 > overlap_words:
                        break
                    ov.insert(0, sent)
                    wcount += sw2
                cur = ov.copy()
                cur_words = wcount
            else:
                cur = []
                cur_words = 0
            cur.append(s)
            cur_words += sw
    if cur:
        parts.append(" ".join(cur))
    return parts

def chunk_token_aware(text: str, max_tokens: int, overlap_tokens: int, model_name: str = "gpt-3.5-turbo") -> List[str]:
    if tiktoken is not None:
        try:
            enc = tiktoken.encoding_for_model(model_name)
        except Exception:
            enc = None
    else:
        enc = None
    if enc:
        toks = enc.encode(text)
        chunks = []
        i = 0
        while i < len(toks):
            chunk_toks = toks[i:i+max_tokens]
            chunks.append(enc.decode(chunk_toks))
            i += max_tokens - overlap_tokens
        return chunks
    else:
        approx_words = max(50, int(max_tokens / 1.3))
        overlap_words = int(overlap_tokens / 1.3)
        return chunk_sliding(text, approx_words, overlap_words)

def chunk_semantic(text: str, chunk_size_words: int = 300, overlap_words: int = 50):
    paras = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
    chunks = []
    cur = []
    cur_count = 0
    for p in paras:
        pw = len(p.split())
        if cur_count + pw <= chunk_size_words:
            cur.append(p)
            cur_count += pw
        else:
            chunks.append(" ".join(cur))
            cur = [p]
            cur_count = pw
    if cur:
        chunks.append(" ".join(cur))
    return chunks

def chunk_text_master(text: str, method: str, size: int = 600, overlap: int = 100, token_aware: bool = False, token_model: str = "gpt-3.5-turbo") -> List[str]:
    if method == "paragraph":
        return chunk_paragraph(text, size, overlap)
    if method == "sentence":
        return chunk_sentence(text)
    if method == "fixed":
        return chunk_fixed(text, size)
    if method == "sliding":
        return chunk_sliding(text, size, overlap)
    if method == "recursive":
        return chunk_recursive(text, size, overlap)
    if method == "semantic":
        return chunk_semantic(text, chunk_size_words=size, overlap_words=overlap)
    if method == "token_aware" or token_aware:
        return chunk_token_aware(text, max_tokens=size, overlap_tokens=overlap, model_name=token_model)
    return [text]

# ---------------------------
# Embedding & index helpers
# ---------------------------
_embedder_singleton = None
_reranker_singleton = None

def load_embedder():
    global _embedder_singleton, SentenceTransformer
    if _embedder_singleton is not None:
        return _embedder_singleton
    try:
        if SentenceTransformer is None:
            from sentence_transformers import SentenceTransformer as _ST
            SentenceTransformer = _ST
        _embedder_singleton = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception as e:
        st.error(f"Failed to load embedder: {e}")
        _embedder_singleton = None
    return _embedder_singleton

def load_reranker():
    global _reranker_singleton, CrossEncoder
    if _reranker_singleton is not None:
        return _reranker_singleton
    try:
        if CrossEncoder is None:
            from sentence_transformers import CrossEncoder as _CE
            CrossEncoder = _CE
        _reranker_singleton = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    except Exception as e:
        st.error(f"Failed to load reranker: {e}")
        _reranker_singleton = None
    return _reranker_singleton

def _load_embed_cache() -> Dict[str, Any]:
    try:
        if EMBED_CACHE_PATH.exists():
            with open(EMBED_CACHE_PATH, "rb") as f:
                return pickle.load(f)
    except Exception:
        pass
    return {}

def _save_embed_cache(cache: Dict[str, Any]):
    try:
        with open(EMBED_CACHE_PATH, "wb") as f:
            pickle.dump(cache, f)
    except Exception:
        pass

def build_faiss_index(vecs):
    if faiss is None or np is None or not vecs:
        return None
    try:
        arr = np.array(vecs, dtype="float32")
        idx = faiss.IndexFlatL2(arr.shape[1])
        idx.add(arr)
        faiss.write_index(idx, str(FAISS_INDEX_PATH))
        return idx
    except Exception as e:
        st.error(f"FAISS index build failed: {e}")
        return None

# ---------------------------
# Build/load KB
# ---------------------------
def build_kb_from_paths(paths: List[str], chunk_mode: str = "sliding", chunk_size: int = 600, chunk_overlap: int = 100, token_aware: bool = False, token_model: str = "gpt-3.5-turbo"):
    chunks = []
    metas = []
    for path in paths:
        items = extract_texts_from_file(path)
        for it in items:
            text = it.get("text", "")
            blocks = chunk_text_master(text, method=chunk_mode, size=chunk_size, overlap=chunk_overlap, token_aware=token_aware, token_model=token_model)
            for b in blocks:
                if len(b.strip()) > 30:
                    chunks.append(b)
                    metas.append({"file": it["meta"]["file"], "page": it["meta"]["page"], "bbox": it["meta"].get("bbox")})
    embedder = load_embedder()
    cache = _load_embed_cache()
    vecs = []
    for ch in chunks:
        key = str(hash(ch))
        if key in cache:
            v = cache[key]
        else:
            if embedder is not None:
                try:
                    v = embedder.encode([ch])[0].astype("float32")
                except Exception:
                    v = np.zeros(384, dtype="float32") if np is not None else [0.0] * 384
            else:
                v = np.zeros(384, dtype="float32") if np is not None else [0.0] * 384
            cache[key] = v
        vecs.append(v)
    _save_embed_cache(cache)
    faiss_index = build_faiss_index(vecs)
    bm25_obj = None
    if BM25Okapi is not None and chunks:
        try:
            corpus = [re.sub(r"\s+", " ", c).split() for c in chunks]
            bm25_obj = BM25Okapi(corpus)
            with open(BM25_CACHE_PATH, "wb") as f:
                pickle.dump({"corpus": corpus}, f)
        except Exception:
            bm25_obj = None
    try:
        with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False)
        with open(METAS_PATH, "w", encoding="utf-8") as f:
            json.dump(metas, f, ensure_ascii=False)
    except Exception:
        pass
    return {"chunks": chunks, "metas": metas, "vecs": vecs, "faiss": faiss_index, "bm25": bm25_obj}

def load_persisted_kb() -> Dict[str, Any]:
    kb = {"chunks": [], "metas": [], "vecs": [], "faiss": None, "bm25": None}
    try:
        if CHUNKS_PATH.exists():
            kb["chunks"] = json.load(open(CHUNKS_PATH, "r", encoding="utf-8"))
        if METAS_PATH.exists():
            kb["metas"] = json.load(open(METAS_PATH, "r", encoding="utf-8"))
        if FAISS_INDEX_PATH.exists() and faiss is not None:
            kb["faiss"] = faiss.read_index(str(FAISS_INDEX_PATH))
        if BM25_CACHE_PATH.exists() and BM25Okapi is not None:
            data = pickle.load(open(BM25_CACHE_PATH, "rb"))
            kb["bm25"] = BM25Okapi(data["corpus"])
    except Exception as e:
        st.error(f"Failed to load KB: {e}")
    return kb

# ---------------------------
# Query expansion & retrieval
# ---------------------------
def expand_query_terms(query: str) -> List[str]:
    if not query:
        return []
    if _lemm is None:
        return list({t.lower() for t in re.findall(r"\w+", query)})
    words = re.findall(r"\w+", query.lower())
    expanded = set()
    for w in words:
        lemma = _lemm.lemmatize(w)
        expanded.add(lemma)
        try:
            for syn in __import__("nltk").corpus.wordnet.synsets(lemma):
                for l in syn.lemmas():
                    term = l.name().replace("_", " ").lower()
                    if len(term) > 2:
                        expanded.add(term)
            if lemma.endswith("e"):
                expanded.add(lemma[:-1] + "ing")
            expanded.add(lemma + "s")
        except Exception:
            expanded.add(w)
    return list(expanded)

def _bm25_scores(terms: List[str], kb: Dict[str, Any]) -> Dict[int, float]:
    scores = {}
    bm25 = kb.get("bm25")
    if bm25 is None or not terms:
        return scores
    try:
        raw_scores = bm25.get_scores(terms)
        if raw_scores is None or len(raw_scores) == 0:
            return scores
        arr = np.array(raw_scores, dtype=np.float32)
        min_val, max_val = np.min(arr), np.max(arr)
        range_val = max_val - min_val
        normalized = (arr - min_val) / range_val if range_val != 0 else np.ones_like(arr)
        for i, s in enumerate(normalized):
            score_val = max(0.0, min(1.0, float(s)))
            if score_val > 0:
                scores[i] = score_val
    except Exception as e:
        st.warning(f"BM25 scoring failed: {e}")
    return scores

def _faiss_scores(query: str, kb: Dict[str, Any], topk: int = 8) -> Dict[int, float]:
    scores = {}
    idx = kb.get("faiss")
    if idx is None or np is None:
        return scores
    emb = load_embedder()
    if emb is None:
        return scores
    try:
        qv = emb.encode([query])[0].astype("float32")
        D, I = idx.search(np.array([qv]), topk)
        dists = D[0]
        sims = [1.0 / (1.0 + d) for d in dists]
        min_sim, max_sim = min(sims), max(sims)
        normalized = [(s - min_sim) / (max_sim - min_sim + 1e-8) for s in sims] if max_sim != min_sim else [1.0]*len(sims)
        for pos, i in enumerate(I[0]):
            if 0 <= i < len(kb.get("chunks", [])):
                score_val = normalized[pos]
                scores[i] = max(0.0, min(1.0, float(score_val)))
    except Exception as e:
        st.warning(f"FAISS scoring failed: {e}")
    return scores

def _apply_boosts(scores: Dict[int, float], chunks: List[str], boosts: List[str]):
    if not boosts:
        return
    for i in list(scores.keys()):
        txt = chunks[i].lower()
        bcount = sum(1 for b in boosts if b.lower() in txt)
        if bcount > 0:
            scores[i] = scores[i] * (1.0 + 0.10 * bcount) + 0.25

def hybrid_retrieve(query: str, kb: Dict[str, Any], topk: int = 6, rerank_topk: int = 6, boost_terms: List[str] = None, reranker_model: str = None) -> List[Dict[str, Any]]:
    chunks = kb.get("chunks", [])
    metas = kb.get("metas", [])
    if not chunks:
        return []
    terms = expand_query_terms(query)
    merged_scores: Dict[int, float] = {}
    merged_scores.update(_bm25_scores(terms, kb))
    merged_scores.update({k: merged_scores.get(k, 0) + v for k, v in _faiss_scores(query, kb, topk=max(topk, 12)).items()})
    if not merged_scores:
        for i, ch in enumerate(chunks):
            cnt = sum(1 for t in terms if t in ch.lower())
            if cnt > 0:
                merged_scores[i] = float(cnt)
    _apply_boosts(merged_scores, chunks, boost_terms or BOOST_TERMS)
    prelim = sorted(merged_scores.items(), key=lambda x: -x[1])[:max(topk, rerank_topk)]
    candidates = [{"source": chunks[i], "meta": metas[i], "score": max(0.0, min(1.0, float(s)))} for i, s in prelim]
    if reranker_model and CrossEncoder is not None:
        reranker = load_reranker()
        if reranker:
            pairs = [(query, c["source"]) for c in candidates[:rerank_topk]]
            try:
                scores = reranker.predict(pairs)
                min_score = min(scores) if len(scores) > 0 else 0
                max_score = max(scores) if len(scores) > 0 else 1
                score_range = max_score - min_score
                for j, s in enumerate(scores):
                    normalized_score = (s - min_score) / (score_range + 1e-8) if score_range > 0 else 0.5
                    normalized_score = max(0.0, min(1.0, normalized_score))
                    candidates[j]["rerank_score"] = normalized_score
                candidates = sorted(candidates, key=lambda x: x.get("rerank_score", 0), reverse=True)
            except Exception as e:
                st.warning(f"Reranking failed: {e}")
    return candidates[:topk]

# ---------------------------
# Helper: keep top-k refs
# ---------------------------
def _top_k_refs(refs: List[Dict[str, Any]], k: int = 5) -> List[Dict[str, Any]]:
    if not refs:
        return []
    ranked = []
    web_refs = []
    for r in refs:
        try:
            if r.get("web"):
                web_refs.append(r)
            else:
                s = r.get("rerank_score", r.get("score", 0.0))
                ranked.append((float(s or 0.0), r))
        except Exception:
            web_refs.append(r)
    ranked.sort(key=lambda x: -x[0])
    final = [r for _, r in ranked[:k]]
    for w in web_refs:
        if len(final) >= k:
            break
        final.append(w)
    return final

# ---------------------------
# SerpAPI wrapper
# ---------------------------
def serpapi_search(query: str, num_results: int = 5, api_key: Optional[str] = None) -> List[Dict[str, str]]:
    if requests is None:
        return []
    key = api_key or SERPAPI_KEY or get_secret("SERPAPI_KEY")
    if not key:
        return []
    try:
        params = {"engine": "google", "q": query, "num": num_results, "api_key": key}
        resp = requests.get("https://serpapi.com/search", params=params, timeout=12)
        data = resp.json()
        out = []
        for r in data.get("organic_results", []):
            out.append({"title": r.get("title", ""), "snippet": r.get("snippet", ""), "link": r.get("link", "")})
        return out
    except Exception as e:
        st.warning(f"SerpAPI error: {e}")
        return []

# ---------------------------
# LLM client wrapper
# ---------------------------
class LLMClient:
    def __init__(self, google_key: Optional[str] = None, groq_key: Optional[str] = None, openai_key: Optional[str] = None):
        self.google_key = google_key or GEMINI_KEY
        self.groq_key = groq_key or GROQ_KEY
        self.openai_key = openai_key or OPENAI_KEY
        self.gem_available = False
        self.groq = None
        if self.google_key and genai is not None:
            try:
                genai.configure(api_key=self.google_key)
                self.gem_available = True
            except Exception:
                self.gem_available = False
        if self.groq_key and Groq is not None:
            try:
                self.groq = Groq(api_key=self.groq_key)
            except Exception:
                self.groq = None
        if self.openai_key and openai is not None:
            try:
                openai.api_key = self.openai_key
            except Exception:
                pass

    def generate(self, prompt: str, model_name: str = "gemini-2.5-flash", max_tokens: int = 700, temperature: float = 0.1) -> str:
        short = prompt if len(prompt) < 6000 else prompt[-6000:]
        if model_name.lower().startswith("gemini") and self.gem_available and genai is not None:
            try:
                m = genai.GenerativeModel(model_name)
                res = m.generate_content(short)
                return (res.text or "").strip()
            except Exception as e:
                st.error(f"Gemini generation failed: {e}")
                return ""
        if model_name.lower().startswith("llama") and self.groq:
            try:
                comp = self.groq.chat.completions.create(messages=[{"role": "user", "content": short}], model=model_name, max_tokens=max_tokens, temperature=temperature)
                return comp.choices[0].message.content.strip()
            except Exception as e:
                st.error(f"Groq generation failed: {e}")
                return ""
        if openai is not None and self.openai_key:
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4" if "gpt-4" in model_name else "gpt-3.5-turbo",
                    messages=[{"role": "user", "content": short}],
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                txt = response["choices"][0]["message"]["content"]
                return txt.strip()
            except Exception as e:
                st.error(f"OpenAI generation failed: {e}")
                return ""
        return ""

# ---------------------------
# Grammar & summarization helpers
# ---------------------------
def local_grammar_fix(q: str) -> str:
    t = (q or "").strip()
    if not t:
        return t
    t = re.sub(r'\s+', ' ', t)
    if t and t[0].islower():
        t = t[0].upper() + t[1:]
    return t

def grammar_fix(llm: Optional[LLMClient], question: str, use_llm: bool = True) -> str:
    if not question:
        return question
    if not use_llm or llm is None:
        return local_grammar_fix(question)
    prompt = f"Correct grammar and clarity of the following question. Return only the corrected question (no commentary):\n{question}"
    out = llm.generate(prompt, max_tokens=120)
    return out or local_grammar_fix(question)

def format_bulleted(text: str, llm: Optional[LLMClient], max_bullets: int = 6, model_choice: str = "gemini-2.5-flash") -> str:
    if llm is None:
        sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        bullets = sents[:max_bullets]
        return "\n".join([f"- {b}" for b in bullets])
    prompt = f"Produce up to {max_bullets} concise bullet points summarizing the text below. Keep bullets short:\n{text[:3000]}"
    out = llm.generate(prompt, model_name=model_choice, max_tokens=200)
    return out or ""

def summarize_with_type(text: str, llm: Optional[LLMClient], style: str = "Small", model_choice: str = "gemini-2.5-flash") -> str:
    if not text:
        return ""
    if llm is None:
        s = re.sub(r'\s+', ' ', text).strip()
        if style == "Small":
            return s[:200] + ("..." if len(s) > 200 else "")
        if style == "Medium":
            return s[:800] + ("..." if len(s) > 800 else "")
        if style == "Detailed":
            return s[:2000] + ("..." if len(s) > 2000 else "")
        if style == "Bulleted":
            return format_bulleted(s, None)
        return s[:800]
    prefix = {
        "Small": "One-line summary:",
        "Medium": "Short paragraph summary (4-6 sentences):",
        "Detailed": "Detailed summary with reasoning (2-3 paragraphs):",
        "Bulleted": "4-6 bullet points:",
        "Token-aware": "Summarize concisely:"
    }.get(style, "Briefly summarize:")
    prompt = f"{prefix}:\n{text[:4000]}"
    out = llm.generate(prompt, model_name=model_choice, max_tokens=600)
    return out or ""

# ---------------------------
# Synthesize answer & verification
# ---------------------------
def synthesize_answer(llm: Optional[LLMClient], question: str, candidates: List[Dict[str, Any]], include_prev: Optional[str] = None, model_choice: str = "gemini-2.5-flash", summary_type: str = "Small", feedback: Optional[str] = None) -> Tuple[str, str, List[str]]:
    if llm is None:
        return (
            "\n".join([c["source"] for c in candidates[:4]]) or "No relevant passages found.",
            "",
            []
        )
    ctx = ["The following excerpts are from legal documents. Use ONLY these to answer the question."]
    if include_prev:
        ctx.append(f"Context Memory (summarized): {include_prev}")
    ctx.append("DOCUMENT PASSAGES:")
    for i, c in enumerate(candidates):
        meta = c.get("meta", {})
        src = meta.get("file", "Document")
        pg = meta.get("page", 1)
        truncated_source = c["source"][:800] + "..." if len(c["source"]) > 800 else c["source"]
        ctx.append(f"[{i+1}] Source: {src}, Page {pg}\nText: {truncated_source}")
    context = "\n".join(ctx)
    length_prompt = {
        "Small": "Answer in exactly one concise sentence.",
        "Medium": "Answer in 3-5 clear sentences.",
        "Detailed": "Provide a detailed explanation in 2-3 paragraphs.",
        "Bulleted": "List 3-5 key points as bullet points."
    }.get(summary_type, "Be succinct.")
    citation_style = {
        "Small": "Include the passage number(s) [n] at the end of the sentence.",
        "Medium": "Cite relevant passages using [n] within the text.",
        "Detailed": "Use [n] citations throughout to support your points.",
        "Bulleted": "Each bullet must end with the relevant [n] citation."
    }.get(summary_type, "Use [n] to cite.")
    feedback_note = f"\nUSER FEEDBACK ON PREVIOUS ANSWER: {feedback}" if feedback else ""
    prompt = f"""
{context}
INSTRUCTIONS:
1. You are a legal research assistant.
2. Answer the user's question using ONLY the information from the DOCUMENT PASSAGES above.
3. If the passages do not contain the answer, say "Based on the provided documents, I cannot answer that question." and explain why.
4. {length_prompt}
5. {citation_style}
6. Do not invent, assume, or hallucinate any information.
7. {f"User was dissatisfied because: {feedback}. Improve accordingly." if feedback else ""}
USER QUESTION: {question}{feedback_note}
ANSWER:
""".strip()
    answer = llm.generate(prompt, model_name=model_choice, max_tokens=600)
    if not answer:
        answer = "I could not generate an answer based on the retrieved information."
    ver_prompt = f"""
Analyze the following 'ANSWER' and 'DOCUMENT PASSAGES'. For every distinct factual claim in the answer, identify it and list the exact passage numbers ([1], [2], etc.) that support it.
Return the result as a JSON array of objects with keys 'claim' and 'refs'.
Example: [
  {{"claim": "Bribery is illegal.", "refs": [1]}} ,
  {{"claim": "The penalty can include imprisonment.", "refs": [3, 5]}}
]
If no claims can be verified by the passages, return [].
DOCUMENT PASSAGES:
{chr(10).join([f'[{i+1}] {c["source"][:400]}...' for i, c in enumerate(candidates[:6])])}
ANSWER:
{answer}
VERIFICATION:
""".strip()
    try:
        verification_raw = llm.generate(ver_prompt, model_name=model_choice, max_tokens=300)
        try:
            json.loads(verification_raw)
            verification = verification_raw
        except json.JSONDecodeError:
            verification = f"Raw output (not valid JSON):\n{verification_raw}"
    except Exception as e:
        verification = f"Verification failed: {e}"
    followups = []
    try:
        focus_passages = " ".join([c["source"][:300] for c in candidates[:2]])
        fq_prompt = f"""
Based on the initial question '{question}' and the following relevant text excerpt, suggest three insightful follow-up questions a researcher might ask.
Keep each question under 15 words.
EXCERPT: {focus_passages[:600]}...
SUGGESTIONS:
1.
2.
3.
""".strip()
        fq_response = llm.generate(fq_prompt, model_name=model_choice, max_tokens=150)
        lines = [line.strip() for line in fq_response.split('\n') if line.strip()]
        followups = [re.sub(r'^\d+\.\s*', '', line) for line in lines[:3]]
    except Exception:
        followups = []
    return (answer.strip(), verification, followups)

def render_pdf_highlight_bytes(filename: str, page_idx: int, search_text: str, scale: float = 3.0) -> Optional[bytes]:
    if fitz is None or Image is None:
        return None
    path = PDF_DIR / filename
    if not path.exists():
        possible = Path(filename)
        if possible.exists():
            path = possible
        else:
            return None
    try:
        doc = fitz.open(str(path))
        pidx = max(0, min(page_idx, len(doc) - 1))
        page = doc.load_page(pidx)
        needle = (search_text or "").strip()[:120]
        rects = []
        if needle:
            try:
                rects = page.search_for(needle)
            except Exception:
                rects = []
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        if rects and ImageDraw is not None:
            draw = ImageDraw.Draw(img)
            for r in rects:
                try:
                    x0, y0, x1, y1 = r.x0 * scale, r.y0 * scale, r.x1 * scale, r.y1 * scale
                    draw.rectangle([x0, y0, x1, y1], outline="yellow", width=4)
                except Exception:
                    pass
        buf = BytesIO()
        img.save(buf, format="PNG")
        doc.close()
        return buf.getvalue()
    except Exception as e:
        return None

def export_history_json(history: List[Dict[str, Any]]) -> bytes:
    return json.dumps(history, indent=2, ensure_ascii=False).encode("utf-8")

try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    REPORTLAB = True
except Exception:
    REPORTLAB = False

def export_history_pdf(history: List[Dict[str, Any]]) -> Optional[bytes]:
    if not REPORTLAB:
        return None
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    flow = []
    for t in history:
        flow.append(Paragraph(f"Q: {t.get('user','')}", styles["Heading3"]))
        flow.append(Paragraph(f"A: {t.get('ai_answer','')}", styles["BodyText"]))
        flow.append(Spacer(1, 12))
    try:
        doc.build(flow)
        buf.seek(0)
        return buf.read()
    except Exception:
        return None

# ---------------------------
# Session state initialization
# ---------------------------
if "kb" not in st.session_state:
    st.session_state.kb = load_persisted_kb()
if "history" not in st.session_state:
    st.session_state.history = []
if "staged_paths" not in st.session_state:
    st.session_state.staged_paths = []
if "preview_modal" not in st.session_state:
    st.session_state.preview_modal = None
if "llm_client" not in st.session_state:
    st.session_state.llm_client = LLMClient(google_key=GEMINI_KEY, groq_key=GROQ_KEY, openai_key=OPENAI_KEY)
if "followup" not in st.session_state:
    st.session_state.followup = None
if "regenerating" not in st.session_state:
    st.session_state.regenerating = None
if "feedback_text" not in st.session_state:
    st.session_state.feedback_text = ""
if "context_memory" not in st.session_state:
    st.session_state.context_memory = []
if "use_context_memory" not in st.session_state:
    st.session_state.use_context_memory = True
if "memory_window" not in st.session_state:
    st.session_state.memory_window = 5
if "manual_transcript" not in st.session_state:
    st.session_state.manual_transcript = ""

# ---------------------------
# Sidebar UI
# ---------------------------
with st.sidebar:
    st.markdown("<div style='padding:8px;background:linear-gradient(90deg,#ff6aa3,#4f7bfd);color:white;text-align:center'><h3>RAG Assistant</h3></div>", unsafe_allow_html=True)
    ai_options = ["Gemini 2.5 Flash", "Groq Llama 3.1", "OpenAI GPT-4", "OpenAI gpt-3.5"]
    selected_model = st.selectbox("AI Model", ai_options, index=0)
    model_map = {"Gemini 2.5 Flash": "gemini-2.5-flash", "Groq Llama 3.1": "llama-3.1-8b-instant", "OpenAI GPT-4": "gpt-4", "OpenAI gpt-3.5": "gpt-3.5-turbo"}
    model_choice = model_map.get(selected_model, "gemini-2.5-flash")
    if st.button("🔌 Test API Connection"):
        router = st.session_state.llm_client
        with st.spinner("Testing connection..."):
            try:
                res = router.generate("Say hello.", model_name=model_choice)
                st.success(f"✅ Responded: {res[:50]}...")
            except Exception as e:
                st.error(f"❌ Failed: {e}")
    summary_type = st.selectbox("Summary Type", ["Small", "Medium", "Detailed", "Bulleted", "Token-aware"], index=1)
    chunk_method = st.selectbox("Chunking Method", ["sliding", "paragraph", "sentence", "fixed", "recursive", "semantic", "token_aware"], index=0)
    chunk_size = st.slider("Chunk size", 200, 1200, 600, step=50)
    chunk_overlap = st.slider("Overlap", 0, 300, 100, step=10)
    rerank_toggle = st.checkbox("Enable semantic reranking", True)
    web_search_toggle = st.checkbox("Enable web fallback", False)
    grammar_toggle = st.checkbox("Grammar-correct question", True)
    st.markdown("---")
    st.markdown("### Conversation Memory")
    st.checkbox("Enable Context Memory (include summarized history in prompts)", key="use_context_memory")
    st.slider("Memory window (how many recent turns to keep)", 1, 20, key="memory_window")
    st.markdown("---")
    st.markdown("**Upload documents (up to 20)**")
    uploaded_files = st.file_uploader("Upload PDF / PNG / JPG", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True)
    if uploaded_files:
        saved = [save_uploaded_file(f) for f in uploaded_files[:20]]
        st.session_state.staged_paths = saved
        st.success(f"Staged {len(saved)} files.")
    # --- YouTube Transcript Extraction (enhanced 6-method system) ---
    with st.expander("🎥 YouTube Transcript Extraction", expanded=False):
        st.markdown("### 📽️ Enter YouTube URL")
        st.caption("Example: https://www.youtube.com/watch?v=8hly31xKli0")
        youtube_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...", key="youtube_url_input")
        st.markdown("### 📝 Manual Transcript Entry")
        st.caption("Use this if automated extraction fails")
        manual_transcript = st.text_area("Paste transcript text here:", height=150, key="manual_transcript_input")
        # API key info section
        st.markdown("""
        <div class="api-key-info">
        <strong>🔑 YouTube API Key Required</strong><br>
        Make sure your API key is properly configured in <code>.streamlit/secrets.toml</code>:<br>
        <code>YOUTUBE_API_KEY = "your_actual_api_key_here"</code>
        </div>
        """, unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            fetch_btn = st.button("🚀 Extract Transcript", key="fetch_youtube", type="primary")
        with col2:
            manual_btn = st.button("💾 Use Manual Transcript", key="use_manual")
        with col3:
            st.button("🎬 Test with TED Talk", key="test_video", on_click=lambda: st.session_state.update({"youtube_url_input": "https://www.youtube.com/watch?v=8hly31xKli0"}))
        # Process YouTube URL
        if fetch_btn and youtube_url:
            with st.spinner("🔍 Extracting transcript... This may take a moment"):
                transcript_text = fetch_youtube_transcript_safe(youtube_url)
                if transcript_text and len(transcript_text.strip()) > 100:
                    video_id = extract_vid(youtube_url)
                    if video_id:
                        st.success(f"✅ Successfully extracted transcript from video ID: {video_id}")
                        thumb_url = get_youtube_thumbnail_url(video_id)
                        st.image(thumb_url, caption="Video Thumbnail", width=200)

                        # Corrected to use text_area instead of nested expander
                        preview_text = transcript_text[:500] + "..." if len(transcript_text) > 500 else transcript_text
                        st.markdown("**📄 Transcript Preview (First 500 characters):**")
                        st.text_area("", preview_text, height=150, disabled=True, key=f"yt_preview_{video_id}")

                        timestamp = int(time.time())
                        fake_filename = f"yt_{video_id}_{timestamp}.txt"
                        temp_path = PDF_DIR / fake_filename
                        try:
                            with open(temp_path, "w", encoding="utf-8") as f:
                                f.write(transcript_text)
                            st.session_state.staged_paths = [str(temp_path)]
                            word_count = len(transcript_text.split())
                            est_minutes = max(1, round(word_count / 150))
                            st.metric("Word Count", f"{word_count:,}")
                            st.metric("Estimated Duration", f"~{est_minutes} minutes")
                            st.info("✅ Transcript saved and ready for KB building!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"❌ Failed to save transcript: {str(e)}")
                    else:
                        st.error("⚠️ Could not extract video ID from URL. Check URL format.")
                else:
                    st.error("❌ Failed to extract transcript. Please try the manual option below or check your API key configuration.")
        # Process manual transcript
        if manual_btn and manual_transcript:
            if len(manual_transcript.strip()) > 100:
                title_snippet = re.sub(r'[^\w\s-]', '', manual_transcript[:30]).strip().replace(' ', '_')
                timestamp = int(time.time())
                fake_filename = f"manual_{title_snippet}_{timestamp}.txt"
                temp_path = PDF_DIR / fake_filename
                try:
                    with open(temp_path, "w", encoding="utf-8") as f:
                        f.write(manual_transcript)
                    st.session_state.staged_paths = [str(temp_path)]
                    word_count = len(manual_transcript.split())
                    st.metric("Word Count", f"{word_count:,}")
                    st.success("✅ Manual transcript saved successfully!")
                    st.info("Click 'Build KB' to add this transcript to your knowledge base")
                except Exception as e:
                    st.error(f"❌ Failed to save manual transcript: {str(e)}")
            else:
                st.warning("⚠️ Transcript too short. Please provide at least 100 characters of content.")

    if st.button("Build KB", key="build_kb_btn"):
        with st.spinner("Building KB..."):
            st.session_state.kb = build_kb_from_paths(
                st.session_state.staged_paths,
                chunk_mode=chunk_method,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                token_aware=False
            )
        st.success("KB built.")
        st.rerun()
    if st.button("Load persisted KB", key="load_kb_btn"):
        kb = load_persisted_kb()
        if kb.get("chunks"):
            st.session_state.kb = kb
            st.success("Loaded KB.")
            st.rerun()
        else:
            st.info("No KB found.")
    if st.button("Clear KB & chat", key="clear_kb_btn"):
        for p in [CHUNKS_PATH, METAS_PATH, FAISS_INDEX_PATH, BM25_CACHE_PATH, EMBED_CACHE_PATH]:
            if Path(p).exists():
                Path(p).unlink(missing_ok=True)
        st.session_state.kb = {"chunks": [], "metas": [], "vecs": [], "faiss": None, "bm25": None}
        st.session_state.history = []
        st.session_state.preview_modal = None
        st.session_state.staged_paths = []
        st.session_state.regenerating = None
        st.session_state.feedback_text = ""
        st.session_state.context_memory = []
        st.session_state.manual_transcript = ""
        st.success("Cleared all data.")
        st.rerun()

# ---------------------------
# Main header
# ---------------------------
st.markdown("<div class='big-title'>📚 RAG Assistant</div>", unsafe_allow_html=True)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;800;900&family=Exo+2:wght@400;500;600;700&display=swap');
:root { --netflix-red:#e50914; --netflix-dark:#141414; --text:#ffffff; --muted:#b3b3b3; }
html, body, .stApp { background: linear-gradient(135deg,#020202,#141414); color: var(--text); font-family: 'Exo 2', sans-serif; }
.big-title { font-size: 2.2rem; font-weight: 800; background: linear-gradient(90deg,var(--netflix-red),#ff3366); -webkit-background-clip: text; color: transparent; margin: 12px 0; text-align:center; }
.pro-badge { background: var(--netflix-red); color: white; padding:6px 10px; border-radius:40px; font-weight:700; display:inline-block; }
.container-card { background: rgba(20,20,20,0.6); border-radius:10px; padding:12px; margin-bottom:12px; border:1px solid rgba(255,255,255,0.04); }
.ai-box { background: #0f0f0f; padding:12px; border-radius:8px; color:var(--text); }
.small-muted { color: var(--muted); font-size: 0.9rem; }
.netflix-button { background: linear-gradient(90deg,var(--netflix-red),#b3070f); color:white; border:none; padding:10px 14px; border-radius:6px; font-weight:700; cursor:pointer; }
</style>
""", unsafe_allow_html=True)

username = st.session_state.get("username", "Guest")
is_logged_in = st.session_state.get("logged_in", False)
if is_logged_in:
    st.markdown(f"<div style='padding:8px;background:#071426;border-radius:8px;margin-top:8px;'>Signed in as <b>{username}</b></div>", unsafe_allow_html=True)

# Document Summaries (cached in session_state so page navigation never blocks)
kb = st.session_state.kb
files_indexed = sorted({m.get("file") for m in kb.get("metas", []) if m.get("file")}) if kb.get("metas") else []
if files_indexed:
    if "doc_summary_cache" not in st.session_state:
        st.session_state.doc_summary_cache = {}
    with st.expander("📄 Document Summaries", expanded=False):
        doc_texts = {}
        for i, ch in enumerate(kb.get("chunks", [])):
            fn = kb.get("metas", [])[i].get("file", "Doc") if i < len(kb["metas"]) else "Doc"
            doc_texts.setdefault(fn, "")
            doc_texts[fn] += "\n" + ch
        if st.button("✨ Generate / Refresh Document Summaries", key="gen_doc_summaries_pro_btn"):
            for fname, text in doc_texts.items():
                cache_k = f"{fname}|{summary_type}|{model_choice}"
                st.session_state.doc_summary_cache[cache_k] = summarize_with_type(
                    text, st.session_state.llm_client, summary_type, model_choice
                )
        for fname, text in doc_texts.items():
            cache_k = f"{fname}|{summary_type}|{model_choice}"
            summary = st.session_state.doc_summary_cache.get(cache_k) or summarize_with_type(
                text, None, summary_type, model_choice
            )
            st.markdown(f"<div class='container-card'><b>{fname}</b> — {summary_type}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='scrollable-summary'>{summary.replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

# ---------------------------
# Chat history rendering
# ---------------------------
def format_verification_display(ver_text: str):
    if not ver_text:
        return None
    s = ver_text.strip()
    try:
        data = json.loads(s)
    except Exception:
        m = re.search(r'(\[.*\])', s, flags=re.S)
        if m:
            try:
                data = json.loads(m.group(1))
            except Exception:
                data = None
        else:
            data = None
    if isinstance(data, list):
        out_lines = []
        for i, item in enumerate(data, 1):
            claim = item.get("claim") if isinstance(item, dict) else str(item)
            refs = item.get("refs") if isinstance(item, dict) else []
            out_lines.append((claim, refs))
        return out_lines
    return s

def build_pdf_data_uri(fname: str) -> Optional[str]:
    if not fname:
        return None
    p = PDF_DIR / fname
    if not p.exists():
        p = Path(fname)
        if not p.exists():
            return None
    try:
        with open(p, "rb") as f:
            pdf_bytes = f.read()
        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        return f"application/pdf;base64,{b64}"
    except Exception:
        return None

for idx, turn in enumerate(st.session_state.history):
    st.markdown(f"<div class='user-box'>{turn.get('user','')}</div>", unsafe_allow_html=True)
    if turn.get("corrected") and turn["corrected"] != turn["user"]:
        st.markdown(f"<div class='small-muted'>Corrected: {turn['corrected']}</div>", unsafe_allow_html=True)
    st.markdown("<div class='answer-section'><div class='answer-header'>Document Answer (Raw Retrieved Passages)</div>", unsafe_allow_html=True)
    doc_ans_id = f"doc_ans_{idx}"
    doc_answer_text = turn.get('document_answer', '')
    st.markdown(f"<div id='{doc_ans_id}' class='ai-box'>{doc_answer_text.replace(chr(10),'<br>')}</div>", unsafe_allow_html=True)
    if st.button("📋 Copy Document Answer", key=f"copy_doc_{idx}"):
        st.session_state.clipboard = doc_answer_text
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='answer-section'><div class='answer-header'>AI Answer ({})</div>".format(selected_model), unsafe_allow_html=True)
    ai_ans_id = f"ai_ans_{idx}"
    ai_answer_text = turn.get('ai_answer', '')
    st.markdown(f"<div id='{ai_ans_id}' class='ai-box'>{ai_answer_text.replace(chr(10),'<br>')}</div>", unsafe_allow_html=True)
    conf = turn.get("confidence", None)
    cost = turn.get("cost_estimate", None)
    if conf is None:
        refs_for_conf = turn.get("refs", []) or []
        scores = []
        for r in refs_for_conf:
            try:
                scores.append(float(r.get("rerank_score", r.get("score", 0.0)) or 0.0))
            except Exception:
                pass
        conf = float(sum(scores) / len(scores)) if scores else 0.0
        st.session_state.history[idx]["confidence"] = conf
    if cost is None:
        words = len(ai_answer_text.split())
        tokens_est = int(max(1, words / 0.75))
        cost_est = round(tokens_est * 0.00002, 6)
        st.session_state.history[idx]["cost_estimate"] = cost_est
        cost = cost_est
    st.markdown(f"<div class='small-muted'>Confidence: {conf:.2f} — Estimated cost: ${cost:.6f}</div>", unsafe_allow_html=True)
    if st.button("📋 Copy AI Answer", key=f"copy_ai_{idx}"):
        st.session_state.clipboard = ai_answer_text
    st.markdown("</div>", unsafe_allow_html=True)
    if turn.get("refs"):
        with st.expander("Explain Retrieval (why these passages?)"):
            st.markdown("<div class='retrieval-explain'>", unsafe_allow_html=True)
            for r_j, r in enumerate(turn.get("refs", [])):
                meta = r.get("meta", {}) if isinstance(r, dict) else {}
                src = meta.get("file", "Doc")
                page = meta.get("page", 1)
                score = r.get("rerank_score", r.get("score", 0.0))
                st.markdown(f"**Passage {r_j+1}** — {src}, page {page} — score: {score:.3f}", unsafe_allow_html=True)
                st.markdown(f"<div style='margin-left:8px'>{(r.get('source') or '')[:800]}...</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    fcols = st.columns([0.85, 0.07, 0.08])
    with fcols[1]:
        if st.button("👍", key=f"like_{idx}", help="This answer was helpful"):
            st.toast("Thanks for the positive feedback!")
    with fcols[2]:
        if st.button("👎", key=f"dislike_{idx}", help="This answer needs improvement"):
            st.session_state.regenerating = idx
            st.session_state.feedback_text = ""
            st.rerun()
    if st.session_state.regenerating == idx:
        st.markdown('<div class="feedback-area">', unsafe_allow_html=True)
        st.text_area("Why was this answer unhelpful?", value=st.session_state.feedback_text, key=f"fb_input_{idx}")
        if st.button("🔄 Regenerate with Feedback", key=f"regen_{idx}"):
            with st.spinner("🔍 Processing query..."):
                feedback = st.session_state.get(f"fb_input_{idx}", "").strip()
                router = st.session_state.llm_client
                kb = st.session_state.kb or {}
                candidates = hybrid_retrieve(turn["user"], kb, topk=8, rerank_topk=6, boost_terms=BOOST_TERMS, reranker_model="cross-encoder/ms-marco-MiniLM-L-6-v2" if rerank_toggle else None)
                refs = list(candidates)
                if web_search_toggle:
                    web_hits = serpapi_search(turn["user"], num_results=4, api_key=SERPAPI_KEY)
                    for w in web_hits:
                        refs.append({"web": True, "title": w["title"], "snippet": w["snippet"], "link": w["link"]})
                refs = _top_k_refs(refs, k=5)
                new_ai_answer, new_verification, new_followups = synthesize_answer(router, turn["user"], [r for r in refs if not r.get("web")], include_prev=None, model_choice=model_choice, summary_type=summary_type, feedback=feedback)
                st.session_state.history[idx]["ai_answer"] = new_ai_answer
                st.session_state.history[idx]["verification"] = new_verification
                st.session_state.history[idx]["followups"] = new_followups
                st.session_state.history[idx]["refs"] = refs
                st.session_state.regenerating = None
                if st.session_state.use_context_memory:
                    mem = summarize_with_type(new_ai_answer, st.session_state.llm_client, style="Small")
                    st.session_state.context_memory.append(mem)
                    st.session_state.context_memory = st.session_state.context_memory[-st.session_state.memory_window:]
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    if turn.get("verification"):
        ver_text = turn.get("verification", "")
        formatted = format_verification_display(ver_text)
        if isinstance(formatted, list):
            st.markdown("### 🧠 AI Insights Summary")
            for i, (claim, refs) in enumerate(formatted, 1):
                refs_str = ", ".join(str(r) for r in refs) if refs else "—"
                st.markdown(f"**{i}. {claim}**")
                st.caption(f"References: {refs_str}")
        else:
            st.markdown("<details><summary>AI insights / verification</summary>", unsafe_allow_html=True)
            st.markdown(f"```\n{formatted}\n```")
            st.markdown("</details>", unsafe_allow_html=True)
        if st.button("📋 Copy insights", key=f"copy_ver_{idx}"):
            st.session_state.clipboard = ver_text
    if turn.get("followups"):
        st.markdown("<div class='small-muted'>Follow-up suggestions:</div>", unsafe_allow_html=True)
        cols = st.columns(len(turn["followups"]))
        for j, s in enumerate(turn["followups"]):
            with cols[j]:
                if st.button(s, key=f"follow_{idx}_{j}"):
                    st.session_state.followup = s
                    st.rerun()
    if turn.get("refs"):
        st.markdown(f"<div class='small-muted'>References ({len(turn['refs'])}):</div>", unsafe_allow_html=True)
        for r_i, r in enumerate(turn.get("refs", [])):
            meta = r.get("meta", {}) if isinstance(r, dict) else {}
            fname = meta.get("file", "Doc")
            page = meta.get("page", 1)
            score = r.get("rerank_score", r.get("score", 0))
            cols = st.columns([7, 2, 1])
            with cols[0]:
                st.markdown(f"**{fname}** — page {page}")
                st.markdown(f"<div class='ref-card'>{(r.get('source') or '')[:400]}...</div>", unsafe_allow_html=True)
            with cols[1]:
                st.markdown(f"<div class='score-badge'>Score: {score:.2f}</div>", unsafe_allow_html=True)
            with cols[2]:
                snippet = (r.get("source") or "")[:160]
                img_bytes = render_pdf_highlight_bytes(fname, page - 1, snippet, scale=3.0)
                if img_bytes:
                    b64img = base64.b64encode(img_bytes).decode("utf-8")
                    pdf_data_uri = build_pdf_data_uri(fname) or ""
                    hover_html = f"""
                    <div class="hover-container" style="display:inline-block; text-align:center;">
                      <span style="cursor:pointer; font-size:18px;" onclick="window.open('{pdf_data_uri}', '_blank')">👁️</span>
                      <div class="hover-preview">
                        <img src="image/png;base64,{b64img}" />
                      </div>
                    </div>
                    """
                    st.markdown(hover_html, unsafe_allow_html=True)
                else:
                    st.caption("Preview not available")

# ---------------------------
# Input & Run Query
# ---------------------------
def run_query(user_question: str):
    if not user_question.strip():
        st.warning("Enter a question.")
        return
    router = st.session_state.llm_client
    corrected = grammar_fix(router, user_question, use_llm=grammar_toggle)
    include_prev = None
    if st.session_state.use_context_memory and st.session_state.context_memory:
        include_prev = " | ".join(st.session_state.context_memory[-st.session_state.memory_window:])
    else:
        include_prev = None
    if st.session_state.history:
        prev_answer = st.session_state.history[-1].get("ai_answer", "")
        try:
            emb = load_embedder()
            if emb is not None and prev_answer:
                v_q = emb.encode([user_question])[0]
                v_prev = emb.encode([prev_answer])[0]
                sim = float(np.dot(v_q, v_prev) / ((np.linalg.norm(v_q) + 1e-12) * (np.linalg.norm(v_prev) + 1e-12)))
                if sim >= 0.60 and not include_prev:
                    include_prev = prev_answer
        except Exception:
            include_prev = include_prev or None
    kb = st.session_state.kb or {}
    candidates = hybrid_retrieve(user_question, kb, topk=8, rerank_topk=6, boost_terms=BOOST_TERMS, reranker_model="cross-encoder/ms-marco-MiniLM-L-6-v2" if rerank_toggle else None)
    refs = list(candidates)
    if web_search_toggle:
        web_hits = serpapi_search(user_question, num_results=4, api_key=SERPAPI_KEY)
        for w in web_hits:
            refs.append({"web": True, "title": w["title"], "snippet": w["snippet"], "link": w["link"]})
    refs = _top_k_refs(refs, k=5)
    document_answer = "\n".join([f"[{i+1}] {c['source']}" for i, c in enumerate(candidates[:4])]) if candidates else "No relevant passages found in documents."
    if router is None:
        top_texts = [r["source"] for r in refs if not r.get("web")]
        joined = "\n".join(top_texts[:4]) if top_texts else ""
        ai_answer = summarize_with_type(joined, None, style=summary_type)
        verification = ""
        followups = []
    else:
        try:
            ai_answer, verification, followups = synthesize_answer(router, user_question, [r for r in refs if not r.get("web")], include_prev=include_prev, model_choice=model_choice, summary_type=summary_type)
            if any(r.get("web") for r in refs):
                ai_answer += "\n— Note: web results were consulted (see References)."
        except Exception as e:
            ai_answer = "\n".join([r["source"] for r in refs[:3]]) if refs else f"LLM error: {e}"
            verification = f"LLM error: {e}"
            followups = []
    scores = []
    for r in refs:
        try:
            scores.append(float(r.get("rerank_score", r.get("score", 0.0)) or 0.0))
        except Exception:
            pass
    confidence = float(sum(scores) / len(scores)) if scores else 0.0
    words = len(ai_answer.split())
    tokens_est = int(max(1, words / 0.75))
    cost_est = round(tokens_est * 0.00002, 6)
    st.session_state.history.append({
        "user": user_question,
        "corrected": corrected,
        "document_answer": document_answer,
        "ai_answer": ai_answer,
        "verification": verification,
        "refs": refs,
        "followups": followups,
        "ts": time.time(),
        "confidence": confidence,
        "cost_estimate": cost_est
    })
    if st.session_state.use_context_memory:
        mem = summarize_with_type(ai_answer, st.session_state.llm_client, style="Small")
        st.session_state.context_memory.append(mem)
        st.session_state.context_memory = st.session_state.context_memory[-st.session_state.memory_window:]

col1, col2 = st.columns([5, 1])
with col1:
    user_q = st.text_input("Ask", value=st.session_state.followup or "", key="q")
with col2:
    ask_clicked = st.button("🔍 Ask")
if ask_clicked and user_q:
    status = st.empty()
    status.info("✏️ Correcting grammar...")
    time.sleep(0.25)
    corrected = grammar_fix(st.session_state.llm_client, user_q, use_llm=grammar_toggle)
    status.info("📚 Retrieving relevant passages...")
    time.sleep(0.25)
    kb = st.session_state.kb or {}
    candidates = hybrid_retrieve(user_q, kb, topk=8, rerank_topk=6, boost_terms=BOOST_TERMS, reranker_model="cross-encoder/ms-marco-MiniLM-L-6-v2" if rerank_toggle else None)
    refs = list(candidates)
    if web_search_toggle:
        status.info("🌐 Searching web (fallback)...")
        time.sleep(0.25)
        web_hits = serpapi_search(user_q, num_results=4, api_key=SERPAPI_KEY)
        for w in web_hits:
            refs.append({"web": True, "title": w["title"], "snippet": w["snippet"], "link": w["link"]})
    refs = _top_k_refs(refs, k=5)
    status.info("💡 Generating final answer...")
    time.sleep(0.25)
    document_answer = "\n".join([f"[{i+1}] {c['source']}" for i, c in enumerate(candidates[:4])]) if candidates else "No relevant passages found in documents."
    include_prev = None
    if st.session_state.use_context_memory and st.session_state.context_memory:
        include_prev = " | ".join(st.session_state.context_memory[-st.session_state.memory_window:])
    else:
        include_prev = None
    if st.session_state.llm_client is None:
        top_texts = [r["source"] for r in refs if not r.get("web")]
        joined = "\n".join(top_texts[:4]) if top_texts else ""
        ai_answer = summarize_with_type(joined, None, style=summary_type)
        verification = ""
        followups = []
    else:
        try:
            ai_answer, verification, followups = synthesize_answer(st.session_state.llm_client, user_q, [r for r in refs if not r.get("web")], include_prev=include_prev, model_choice=model_choice, summary_type=summary_type)
            if any(r.get("web") for r in refs):
                ai_answer += "\n— Note: web results were consulted (see References)."
        except Exception as e:
            ai_answer = "\n".join([r["source"] for r in refs[:3]]) if refs else f"LLM error: {e}"
            verification = f"LLM error: {e}"
            followups = []
    scores = []
    for r in refs:
        try:
            scores.append(float(r.get("rerank_score", r.get("score", 0.0)) or 0.0))
        except Exception:
            pass
    confidence = float(sum(scores) / len(scores)) if scores else 0.0
    words = len(ai_answer.split())
    tokens_est = int(max(1, words / 0.75))
    cost_est = round(tokens_est * 0.00002, 6)
    st.session_state.history.append({
        "user": user_q,
        "corrected": corrected,
        "document_answer": document_answer,
        "ai_answer": ai_answer,
        "verification": verification,
        "refs": refs,
        "followups": followups,
        "ts": time.time(),
        "confidence": confidence,
        "cost_estimate": cost_est
    })
    if st.session_state.use_context_memory:
        mem = summarize_with_type(ai_answer, st.session_state.llm_client, style="Small")
        st.session_state.context_memory.append(mem)
        st.session_state.context_memory = st.session_state.context_memory[-st.session_state.memory_window:]
    status.empty()
    st.session_state.followup = None
    st.rerun()

# ---------------------------
# Export controls
# ---------------------------
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("Export chat JSON"):
        data = export_history_json(st.session_state.history)
        st.download_button("Download JSON", data, file_name="chat_history.json", mime="application/json")
with c2:
    if REPORTLAB:
        pdf_data = export_history_pdf(st.session_state.history)
        if pdf_data: 
            st.download_button("Export PDF", pdf_data, file_name="chat_history.pdf", mime="application/pdf")
        else:
            st.error("PDF export failed.")
    else:
        st.caption("Install reportlab to enable PDF export.")
with c3:
    if st.button("Clear Chat"):
        st.session_state.history = []
        st.rerun()

# ---------------------------
# Clipboard handler
# ---------------------------
if 'clipboard' in st.session_state:
    text = st.session_state.clipboard or ""
    safe_text = text.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${").replace("\n", "\\n").replace("\r", "\\r")
    st.markdown(f'''
    <script>
    async function copyToClipboard() {{
        try {{
            await navigator.clipboard.writeText(`{safe_text}`);
            alert("✅ Copied to clipboard!");
        }} catch (err) {{
            const textarea = document.createElement("textarea");
            textarea.value = `{safe_text}`;
            document.body.appendChild(textarea);
            textarea.select();
            try {{
                document.execCommand("copy");
                alert("✅ Copied to clipboard!");
            }} catch (e) {{
                prompt("Copy failed. Press Ctrl+C to copy:", `{safe_text}`);
            }}
            document.body.removeChild(textarea);
        }}
    }}
    </script>
    ''' , unsafe_allow_html=True)
