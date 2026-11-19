# test.py
import os
import re
import json
import html
import tempfile
import subprocess
import shutil
import io
import pickle
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

import streamlit as st
import requests

# google oauth / api
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import google.auth.exceptions

# optional community transcript lib (if installed)
try:
    from youtube_transcript_api import YouTubeTranscriptApi
except Exception:
    YouTubeTranscriptApi = None

# === CONFIG ===
APP_TITLE = "YouTube Transcript Ultimate Fetcher"
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
TMP = Path(tempfile.gettempdir()) / "yt_transcript_cleaner"
TMP.mkdir(exist_ok=True)
TOKEN_PICKLE = TMP / "yt_token.pickle"
CLIENT_SECRET = Path("client_secret.json")
TRANSCRIPTS_DIR = Path.cwd() / "transcripts"
TRANSCRIPTS_DIR.mkdir(exist_ok=True)

# Streamlit page config
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title("🎬 " + APP_TITLE)
st.caption("Tries multiple methods: YouTube API (OAuth), youtube-transcript-api, timedtext, scrape, yt-dlp, Whisper fallback.")

# ----------------------------
# Utility helpers
# ----------------------------
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
    if not lines:
        return ""
    cleaned_lines = []
    prev = None
    for ln in lines:
        ln = normalize_whitespace(ln)
        if ln == prev:
            continue
        cleaned_lines.append(ln)
        prev = ln
    text = " ".join(cleaned_lines)
    return normalize_whitespace(text)

def extract_text_from_ttml(ttml: str) -> str:
    parts = re.findall(r"<text[^>]*>(.*?)</text>", ttml, flags=re.S)
    parts = [html.unescape(re.sub(r"\s+", " ", p.replace("\n", " ")).strip()) for p in parts if p.strip()]
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

def save_transcript_file(video_id: str, text: str) -> Path:
    fname = TRANSCRIPTS_DIR / f"{video_id}.txt"
    fname.write_text(text, encoding="utf-8")
    return fname

# ----------------------------
# OAuth and YouTube API helpers
# ----------------------------
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
                st.warning("Missing client_secret.json in current folder. OAuth features are disabled.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)
        try:
            with open(TOKEN_PICKLE, "wb") as f:
                pickle.dump(creds, f)
        except Exception:
            pass
    try:
        service = build("youtube", "v3", credentials=creds)
        return service
    except Exception:
        return None

# ----------------------------
# Fetch methods (return transcript_text_or_None, info_dict)
# ----------------------------
def fetch_via_api(video_id: str) -> Tuple[Optional[str], Dict[str, Any]]:
    info: Dict[str, Any] = {}
    try:
        service = get_youtube_service()
        if not service:
            return None, info
        req = service.captions().list(part="snippet", videoId=video_id)
        resp = req.execute()
        if not resp.get("items"):
            return None, info
        captions = resp["items"]
        chosen = None
        for c in captions:
            lang = c.get("snippet", {}).get("language", "")
            if lang and lang.startswith("en"):
                chosen = c
                break
        if chosen is None:
            chosen = captions[0]
        cap_id = chosen["id"]
        info["method"] = "YouTube Data API (OAuth)"
        try:
            from googleapiclient.http import MediaIoBaseDownload
            download_request = service.captions().download(id=cap_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, download_request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            fh.seek(0)
            raw = fh.read().decode("utf-8", errors="ignore")
            if raw.strip().startswith("<"):
                text = extract_text_from_ttml(raw)
            else:
                text = raw
            text = remove_timestamped_fragments_and_dedup(text)
            return text.strip() or None, info
        except google.auth.exceptions.RefreshError:
            return None, info
        except Exception:
            return None, info
    except Exception:
        return None, info

def fetch_via_youtube_transcript_api(video_id: str) -> Tuple[Optional[str], Dict[str, Any]]:
    info: Dict[str, Any] = {"method": "youtube-transcript-api"}
    if not YouTubeTranscriptApi:
        return None, info
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
        text = " ".join(t["text"] for t in transcript if t.get("text"))
        text = normalize_whitespace(text)
        return text or None, info
    except Exception:
        return None, info

def fetch_via_timedtext(video_id: str) -> Tuple[Optional[str], Dict[str, Any]]:
    info: Dict[str, Any] = {"method": "timedtext"}
    for lang in ("en", "en-US", "a.en"):
        try:
            r = requests.get(f"https://www.youtube.com/api/timedtext?lang={lang}&v={video_id}", timeout=10)
            if r.status_code == 200 and r.text.strip():
                text = extract_text_from_ttml(r.text)
                info["method"] = f"timedtext {lang}"
                return text or None, info
        except Exception:
            continue
    return None, info

def fetch_via_scrape(video_id: str) -> Tuple[Optional[str], Dict[str, Any]]:
    info: Dict[str, Any] = {"method": "scrape"}
    try:
        page = requests.get(
            f"https://www.youtube.com/watch?v={video_id}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        ).text
        m = re.search(r"\"captionTracks\":(\[.*?\])", page)
        if not m:
            return None, info
        tracks = json.loads(m.group(1))
        track = None
        for t in tracks:
            if "languageCode" in t and str(t["languageCode"]).startswith("en"):
                track = t
                break
        if not track:
            track = tracks[0]
        baseUrl = track.get("baseUrl")
        if not baseUrl:
            return None, info
        for suffix in ("&fmt=vtt", "&fmt=srv3", ""):
            try:
                r2 = requests.get(baseUrl + suffix, timeout=10)
                if r2.status_code == 200 and r2.text.strip():
                    if suffix.endswith("srv3") or r2.text.strip().startswith("<"):
                        text = extract_text_from_ttml(r2.text)
                    else:
                        text = clean_vtt_text(r2.text)
                    return text or None, info
            except Exception:
                continue
        return None, info
    except Exception:
        return None, info

def fetch_via_ytdlp(video_url: str, video_id: str) -> Tuple[Optional[str], Dict[str, Any]]:
    info: Dict[str, Any] = {"method": "yt-dlp"}
    tmp = TMP / f"ytdlp_{video_id}"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        cmd = ["yt-dlp", "--write-auto-sub", "--sub-lang", "en", "--skip-download", "-o", "%(id)s.%(ext)s", video_url]
        subprocess.run(cmd, cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        vtt = None
        for f in tmp.glob("*.vtt"):
            vtt = f
            break
        if not vtt:
            candidates = list(tmp.glob("*.en.vtt")) + list(tmp.glob("*.en.*"))
            vtt = candidates[0] if candidates else None
        if vtt and vtt.exists():
            raw = vtt.read_text(encoding="utf-8", errors="ignore")
            text = clean_vtt_text(raw)
            return text or None, info
        return None, info
    except subprocess.TimeoutExpired:
        return None, info
    except Exception:
        return None, info

def fetch_via_whisper(video_url: str, video_id: str) -> Tuple[Optional[str], Dict[str, Any]]:
    info: Dict[str, Any] = {"method": "whisper"}
    tmp = TMP / f"whisper_{video_id}"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        cmd = ["yt-dlp", "-x", "--audio-format", "mp3", "-o", "%(id)s.%(ext)s", video_url]
        proc = subprocess.run(cmd, cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
        audio = None
        for f in tmp.glob("*.mp3"):
            audio = f
            break
        if not audio:
            return None, info
    except Exception:
        return None, info

    try:
        import importlib
        fw = importlib.import_module("faster_whisper")
        WhisperModel = getattr(fw, "WhisperModel", None)
        if WhisperModel:
            model = WhisperModel("tiny", device="cpu")
            segments, _ = model.transcribe(str(audio))
            txt = " ".join(s.text for s in segments)
            return normalize_whitespace(txt) or None, {"method": "faster-whisper"}
    except Exception:
        pass

    try:
        import importlib
        whisper = importlib.import_module("whisper")
        model = whisper.load_model("tiny")
        result = model.transcribe(str(audio))
        txt = result.get("text", "")
        return normalize_whitespace(txt) or None, {"method": "openai-whisper"}
    except Exception:
        return None, info

# ----------------------------
# Master orchestrator (success-only logs)
# ----------------------------
def fetch_all_methods(video_url: str) -> Tuple[Optional[str], Dict[str, Any]]:
    vid = extract_vid(video_url)
    if not vid:
        return None, {"status": "failed"}

    logs: Dict[str, Any] = {}

    def record_success(name: str, txt: Optional[str], info: Dict[str, Any]) -> bool:
        if txt and len(txt.split()) > 8:
            logs["result_method"] = name
            logs["method_label"] = info.get("method", name)
            logs["success_length_words"] = len(txt.split())
            return True
        return False

    # 1. API
    txt, info = fetch_via_api(vid)
    if record_success("fetch_api", txt, info):
        return txt, logs

    # 2. youtube-transcript-api
    txt, info = fetch_via_youtube_transcript_api(vid)
    if record_success("fetch_transcript_api", txt, info):
        return txt, logs

    # 3. timedtext
    txt, info = fetch_via_timedtext(vid)
    if record_success("fetch_timedtext", txt, info):
        return txt, logs

    # 4. scrape
    txt, info = fetch_via_scrape(vid)
    if record_success("fetch_scrape", txt, info):
        return txt, logs

    # 5. yt-dlp
    txt, info = fetch_via_ytdlp(video_url, vid)
    if record_success("fetch_ytdlp", txt, info):
        return txt, logs

    # 6. Whisper
    txt, info = fetch_via_whisper(video_url, vid)
    if record_success("fetch_whisper", txt, info):
        return txt, logs

    return None, {"status": "failed"}

# ----------------------------
# Streamlit UI
# ----------------------------
st.sidebar.header("Setup & OAuth")
st.sidebar.write("client_secret.json present:", CLIENT_SECRET.exists())
if st.sidebar.button("Clear saved OAuth token"):
    try:
        TOKEN_PICKLE.unlink(missing_ok=True)
        st.sidebar.success("Cleared token.")
    except Exception as e:
        st.sidebar.error(f"Could not delete token: {e}")

st.info("1) Place client_secret.json in this folder for API downloads. 2) Add your Google account as a Test user in the OAuth consent screen, or verify the app for public use.")

video_url = st.text_input("Paste YouTube video URL (full watch URL):", value="")
fetch_btn = st.button("Fetch Transcript (try all methods)")

if fetch_btn:
    if not video_url.strip():
        st.warning("Paste a valid YouTube URL and try again.")
    else:
        with st.spinner("Fetching transcript..."):
            transcript_text, success_log = fetch_all_methods(video_url.strip())

        if transcript_text:
            transcript_text = remove_timestamped_fragments_and_dedup(transcript_text)
            transcript_text = re.sub(r"(?m)^\s*\d+\s*$", "", transcript_text)
            transcript_text = normalize_whitespace(transcript_text)

            st.success("✅ Transcript fetched successfully!")
            summary = {
                "method": success_log.get("method_label"),
                "words": success_log.get("success_length_words"),
            }
            st.json(summary)

            vid = extract_vid(video_url)
            file_path = save_transcript_file(vid or "unknown", transcript_text)
            st.write(f"Saved transcript: `{file_path}`")
            st.download_button("Download transcript (.txt)", transcript_text, file_name=file_path.name)
            st.text_area("Transcript preview", transcript_text[:40000], height=420)
        else:
            # No noisy diagnostics — just a simple, user-friendly note.
            st.error("Could not fetch a transcript for this video.")
            st.caption("Tip: Try a different video URL, ensure captions exist, or add client_secret.json for API access.")

st.markdown("---")
st.markdown("Note: OAuth scope should be `youtube.force-ssl` and your account added as a Test user if the app is in Testing.")
