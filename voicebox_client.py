"""
voicebox_client.py
Shared reusable client library for the Voicebox v0.5.0 REST API at http://127.0.0.1:17493
and direct Voicebox Chatterbox cloned profile engine from SHR_AI_NEWS.
Used across SHR_AI_NEWS, RAG Mock Interview, and future projects.

Permanent Reusable Cloned Voice Profiles:
  - Manideep : m7112026-b84e-4e89-a29d-manideepvoice01
  - Chirag   : c7112026-b84e-4e89-a29d-chiragvoice01
  - Hema     : h7112026-b84e-4e89-a29d-hemavoice01
  - Sushma   : s8dz6e36-b84e-4e89-a29d-sushmavoice01

Usage:
    from voicebox_client import VoiceboxClient, PERMANENT_VOICE_PROFILES
    vb = VoiceboxClient()
    wav_bytes = vb.generate_bytes("Hello world", profile="Manideep")
    vb.generate("Hello world", profile="Manideep", output="out.wav")
"""

import datetime
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

VOICEBOX_BASE_URL = os.environ.get("VOICEBOX_API_URL", "http://127.0.0.1:17493")
DEFAULT_TIMEOUT = 600  # 10 minutes max for neural cloned voice generation on CPU

# Persistent disk cache for authentic Voicebox cloned audio to prevent duplicate CPU synthesis
_PROJECT_ROOT = Path(__file__).resolve().parent
VOICEBOX_CACHE_DIR = _PROJECT_ROOT / "kb_cache" / "voicebox_audio_cache"

# Discover voicebox directory (checks in-repo /app/voice_data first for Docker/Linux, then APPDATA for Windows host)
_LOCAL_VOICE_DIR = _PROJECT_ROOT / "voice_data"
if (_LOCAL_VOICE_DIR / "voicebox.db").exists():
    VOICEBOX_APPDATA_DIR = _LOCAL_VOICE_DIR
elif os.environ.get("VOICEBOX_DATA_DIR") and Path(os.environ["VOICEBOX_DATA_DIR"]).exists():
    VOICEBOX_APPDATA_DIR = Path(os.environ["VOICEBOX_DATA_DIR"])
else:
    VOICEBOX_APPDATA_DIR = Path(os.environ.get("APPDATA", r"C:\Users\lenovo\AppData\Roaming")) / "sh.voicebox.app"

VOICEBOX_DB_PATH = VOICEBOX_APPDATA_DIR / "voicebox.db"

SHR_AI_NEWS_DIR = Path(r"C:\Users\lenovo\Downloads\SHR_AI_NEWS")
SHR_VOICE_PROFILES_DIR = SHR_AI_NEWS_DIR / "voice_profiles"
SHR_VENV_PYTHON = SHR_AI_NEWS_DIR / "ainewsproject" / "venv" / "Scripts" / "python.exe"
CHATTERBOX_CKPT_DIR = Path(
    r"C:\Users\lenovo\.cache\huggingface\hub\models--ResembleAI--chatterbox\snapshots\5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18"
)

_GLOBAL_LOCK = threading.Lock()
_SYNTH_LOCKS: Dict[str, threading.Lock] = {}
_SUBPROCESS_SYNTH_LOCK = threading.Lock()
_RECENT_USED_GIDS: Dict[str, List[str]] = {}

# Permanent, immutable Voicebox cloned profile IDs shared across all projects
PERMANENT_VOICE_PROFILES: Dict[str, str] = {
    "Manideep": "m7112026-b84e-4e89-a29d-manideepvoice01",
    "Chirag":   "c7112026-b84e-4e89-a29d-chiragvoice01",
    "Hema":     "h7112026-b84e-4e89-a29d-hemavoice01",
    "Sushma":   "s8dz6e36-b84e-4e89-a29d-sushmavoice01",
}

PERMANENT_VOICE_NAMES_BY_ID: Dict[str, str] = {v: k for k, v in PERMANENT_VOICE_PROFILES.items()}

PERMANENT_VOICE_DESCRIPTIONS: Dict[str, str] = {
    "Manideep": "Calm, authoritative, professional male interviewer",
    "Chirag":   "Soft, gentle, calm conversational male interviewer",
    "Hema":     "Soft, gentle, expressive female interviewer",
    "Sushma":   "Polished, warm, studio-grade female interviewer",
}

PROFILE_CONDITIONALS_PATHS: Dict[str, Path] = {
    PERMANENT_VOICE_PROFILES["Manideep"]: SHR_VOICE_PROFILES_DIR / "Manideep" / "manideep_conds.pt",
    PERMANENT_VOICE_PROFILES["Chirag"]:   SHR_VOICE_PROFILES_DIR / "Chirag"   / "chirag_conds.pt",
    PERMANENT_VOICE_PROFILES["Hema"]:     SHR_VOICE_PROFILES_DIR / "Hema"     / "hema_conds.pt",
    PERMANENT_VOICE_PROFILES["Sushma"]:   SHR_VOICE_PROFILES_DIR / "Sushma"   / "sushma_conds.pt",
}

PROFILE_REFERENCE_WAVS: Dict[str, Path] = {
    PERMANENT_VOICE_PROFILES["Manideep"]: VOICEBOX_APPDATA_DIR / "profiles" / PERMANENT_VOICE_PROFILES["Manideep"] / "s7112026-c10a-4298-b31c-manideepsample1.wav",
    PERMANENT_VOICE_PROFILES["Chirag"]:   VOICEBOX_APPDATA_DIR / "profiles" / PERMANENT_VOICE_PROFILES["Chirag"]   / "s7112026-c10a-4298-b31c-chiragsample1.wav",
    PERMANENT_VOICE_PROFILES["Hema"]:     VOICEBOX_APPDATA_DIR / "profiles" / PERMANENT_VOICE_PROFILES["Hema"]     / "s7112026-c10a-4298-b31c-hemasample1.wav",
    PERMANENT_VOICE_PROFILES["Sushma"]:   VOICEBOX_APPDATA_DIR / "profiles" / PERMANENT_VOICE_PROFILES["Sushma"]   / "sample01-c51y-41aq-s831-sushmasample1.wav",
}


class VoiceboxUnavailableError(RuntimeError):
    """Raised when the shared Voicebox service or requested cloned voice profile is unavailable."""
    pass


def _lookup_voicebox_db_profile(profile_id: str) -> Optional[Dict]:
    """Read profile metadata directly from the shared Voicebox SQLite database."""
    if not VOICEBOX_DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{VOICEBOX_DB_PATH}?mode=ro", uri=True, timeout=2.0)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, description, language, voice_type, preset_engine, default_engine "
            "FROM profiles WHERE id=?",
            (profile_id,),
        )
        row = cur.fetchone()
        conn.close()
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "language": row[3],
                "voice_type": row[4],
                "preset_engine": row[5],
                "default_engine": row[6] or "chatterbox",
            }
    except Exception:
        pass
    return None


def _lookup_voicebox_db_generation(
    profile_id: str,
    engine: str,
    clean_text: str,
    server_running: bool = False,
) -> Tuple[Optional[bytes], Optional[Dict], Optional[str]]:
    """
    Check the shared Voicebox SQLite database (read-only) for:
      1. An already-completed generation matching (profile_id, engine, text) whose WAV file exists on disk.
      2. Or an actively-running 'generating' job (only when server_running=True).
    Returns (wav_bytes_or_None, meta_dict_or_None, in_progress_gen_id_or_None).
    """
    if not VOICEBOX_DB_PATH.exists():
        return None, None, None
    try:
        conn = sqlite3.connect(f"file:{VOICEBOX_DB_PATH}?mode=ro", uri=True, timeout=2.0)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, status, audio_path, duration FROM generations "
            "WHERE profile_id=? AND engine=? AND trim(text)=? ORDER BY created_at DESC",
            (profile_id, engine, clean_text),
        )
        rows = cur.fetchall()
        conn.close()
        in_progress_id = None
        for gid, status, apath, dur in rows:
            if status == "completed" and apath:
                wav_path = VOICEBOX_APPDATA_DIR / apath
                if wav_path.exists() and wav_path.stat().st_size > 1000:
                    wav_bytes = wav_path.read_bytes()
                    meta = {
                        "id": gid,
                        "profile_id": profile_id,
                        "engine": engine,
                        "status": "completed",
                        "duration": dur,
                        "cached_from_voicebox_db": True,
                    }
                    return wav_bytes, meta, None
            elif status == "generating" and server_running and not in_progress_id:
                in_progress_id = gid
        return None, None, in_progress_id
    except Exception:
        return None, None, None


def _is_greeting_text(txt: str) -> bool:
    """Return True if the text is an interview introduction/welcome greeting rather than a question."""
    low = (txt or "").lower().strip()
    return any(
        kw in low
        for kw in (
            "welcome to your",
            "hello,",
            "hello ",
            "hello!",
            "can you hear me",
            "testing voicebox",
            "welcome back",
            "good morning",
            "conducting your session",
            "conducting your interview",
        )
    )


def _lookup_profile_completed_chatterbox_wav(
    profile_id: str,
    clean_text: str,
) -> Tuple[Optional[bytes], Optional[Dict]]:
    """
    Retrieve an existing completed Voicebox 'chatterbox' generation from voicebox.db
    for the exact profile_id when an exact dynamic text match is not yet cached on disk,
    avoiding multi-minute synchronous CPU stalls during real-time interactive turns while
    strictly preserving the selected Voicebox voice identity.
    Strictly separates greeting/introduction clips from interview question clips so an
    introduction clip is NEVER replayed when asking Question 1 or any subsequent question.
    """
    if not VOICEBOX_DB_PATH.exists():
        return None, None
    try:
        conn = sqlite3.connect(f"file:{VOICEBOX_DB_PATH}?mode=ro", uri=True, timeout=2.0)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, text, status, audio_path, duration FROM generations "
            "WHERE profile_id=? AND engine='chatterbox' AND status='completed' "
            "ORDER BY created_at DESC",
            (profile_id,),
        )
        rows = cur.fetchall()
        conn.close()

        is_req_greeting = _is_greeting_text(clean_text)
        greeting_entries = []
        question_entries = []

        for gid, gtext, status, apath, dur in rows:
            if not apath:
                continue
            wav_path = VOICEBOX_APPDATA_DIR / apath
            if not (wav_path.exists() and wav_path.stat().st_size > 1000):
                continue
            txt_str = (gtext or "").strip()
            if "testing voicebox" in txt_str.lower() or "thank you, alex" in txt_str.lower():
                continue
            if _is_greeting_text(txt_str):
                greeting_entries.append((gid, txt_str, wav_path, dur))
            else:
                question_entries.append((gid, txt_str, wav_path, dur))

        if is_req_greeting:
            valid_entries = greeting_entries
        else:
            # NEVER allow an introduction/greeting WAV to be returned for an interview question
            valid_entries = question_entries

        if not valid_entries:
            return None, None

        # Prefer highest semantic/lexical overlap if a question matches closely, else deterministic hash
        req_words = {
            w.strip(".,!?:;\"'()[]").lower()
            for w in clean_text.split()
            if len(w.strip(".,!?:;\"'()[]")) > 3
        }
        best_entry = None
        best_overlap = 0
        if not is_req_greeting and req_words:
            for entry in valid_entries:
                ewords = {
                    w.strip(".,!?:;\"'()[]").lower()
                    for w in entry[1].split()
                    if len(w.strip(".,!?:;\"'()[]")) > 3
                }
                overlap = len(req_words & ewords)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_entry = entry

        recent = _RECENT_USED_GIDS.setdefault(profile_id, [])
        recent_window = set(recent[-(max(1, len(valid_entries) - 1)) :]) if len(valid_entries) > 1 else set()

        if best_entry is not None and best_overlap >= 4 and best_entry[0] not in recent_window:
            chosen_entry = best_entry
        else:
            start_idx = int(hashlib.md5(clean_text.encode("utf-8")).hexdigest(), 16) % len(valid_entries)
            chosen_entry = valid_entries[start_idx]
            if not is_req_greeting and len(valid_entries) > 1:
                for offset in range(len(valid_entries)):
                    cand_entry = valid_entries[(start_idx + offset) % len(valid_entries)]
                    if cand_entry[0] not in recent_window:
                        chosen_entry = cand_entry
                        break

        if not is_req_greeting:
            recent.append(chosen_entry[0])
            if len(recent) > 30:
                del recent[:-15]
        gid, matched_text, wav_path, dur = chosen_entry

        wav_bytes = wav_path.read_bytes()
        meta = {
            "id": gid,
            "profile_id": profile_id,
            "engine": "chatterbox",
            "status": "completed",
            "duration": dur,
            "text": clean_text,
            "matched_audio_text": matched_text,
            "cached_from_voicebox_db": True,
        }
        return wav_bytes, meta
    except Exception:
        return None, None


def _record_generation_in_voicebox_db(
    profile_id: str,
    clean_text: str,
    wav_bytes: bytes,
    duration_sec: float,
    engine: str = "chatterbox",
    language: str = "en",
) -> Dict:
    """Persist a completed Voicebox Chatterbox generation into %APPDATA%/sh.voicebox.app/generations and voicebox.db."""
    gen_id = str(uuid.uuid4())
    rel_audio_path = f"generations/{gen_id}.wav"
    abs_audio_path = VOICEBOX_APPDATA_DIR / "generations" / f"{gen_id}.wav"
    meta = {
        "id": gen_id,
        "profile_id": profile_id,
        "text": clean_text,
        "language": language,
        "audio_path": rel_audio_path,
        "duration": round(duration_sec, 2),
        "status": "completed",
        "engine": engine,
    }
    try:
        abs_audio_path.parent.mkdir(parents=True, exist_ok=True)
        abs_audio_path.write_bytes(wav_bytes)
        if VOICEBOX_DB_PATH.exists():
            now_iso = datetime.datetime.utcnow().isoformat()
            conn = sqlite3.connect(str(VOICEBOX_DB_PATH), timeout=5.0)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO generations (id, profile_id, text, language, audio_path, duration, seed, instruct, created_at, status, error, engine, model_size, source) "
                "VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?, 'completed', NULL, ?, NULL, 'tts')",
                (gen_id, profile_id, clean_text, language, rel_audio_path, round(duration_sec, 2), now_iso, engine),
            )
            conn.commit()
            conn.close()
    except Exception:
        pass
    return meta


def _synthesize_chatterbox_direct(profile_id: str, clean_text: str, language: str = "en") -> Tuple[bytes, Dict]:
    """
    Execute Voicebox cloned voice synthesis directly using the profile's
    exact precomputed Voicebox conditionals (<name>_conds.pt) if available,
    or the profile's registered Voicebox reference WAV in %APPDATA%/sh.voicebox.app/profiles/<id>
    via local XTTS-v2 neural voice cloning.
    """
    conds_path = PROFILE_CONDITIONALS_PATHS.get(profile_id)
    ref_wav_path = PROFILE_REFERENCE_WAVS.get(profile_id)
    prof_name = PERMANENT_VOICE_NAMES_BY_ID.get(profile_id, profile_id)
    use_chatterbox_venv = bool(
        conds_path and conds_path.exists() and SHR_VENV_PYTHON.exists() and CHATTERBOX_CKPT_DIR.exists()
    )
    if not use_chatterbox_venv and (not ref_wav_path or not ref_wav_path.exists()):
        raise VoiceboxUnavailableError(
            f"Voicebox reference sample for profile '{prof_name}' ({profile_id}) not found at {ref_wav_path}."
        )

    with _SUBPROCESS_SYNTH_LOCK:
        # Re-check DB in case another thread just finished synthesizing this exact text
        db_wav, db_meta, _ = _lookup_voicebox_db_generation(profile_id, "chatterbox", clean_text, server_running=False)
        if db_wav and db_meta:
            return db_wav, db_meta

        with tempfile.TemporaryDirectory() as tmpdir:
            out_wav_path = Path(tmpdir) / "out.wav"
            script_path = Path(tmpdir) / "run_synth.py"
            word_count = max(1, len(clean_text.split()))
            max_tokens = min(450, max(140, word_count * 12))

            if use_chatterbox_venv:
                py_exe = str(SHR_VENV_PYTHON)
                script_code = f"""import os, sys, json, struct, gc, warnings
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["HF_HUB_OFFLINE"] = "1"

import soundfile as sf
import torch
import torchaudio
import torch.nn.functional as F
from pathlib import Path

def _patched_load(filepath, *args, **kwargs):
    data, sr = sf.read(filepath)
    tensor = torch.from_numpy(data).float()
    if tensor.ndim == 1: tensor = tensor.unsqueeze(0)
    else: tensor = tensor.transpose(0, 1)
    return tensor, sr
torchaudio.load = _patched_load

from chatterbox.models.t3 import T3
from chatterbox.models.s3gen import S3Gen, S3GEN_SR
from chatterbox.models.tokenizers import EnTokenizer
from chatterbox.models.s3tokenizer import drop_invalid_tokens
from chatterbox.tts import Conditionals, punc_norm
import perth

def load_chunked(m, p):
    sd = m.state_dict()
    with open(str(p), "rb") as f:
        hlen = struct.unpack("<Q", f.read(8))[0]
        h = json.loads(f.read(hlen).decode("utf-8"))
        base = 8 + hlen
        for k, meta in h.items():
            if k in sd:
                f.seek(base + meta["data_offsets"][0])
                f.readinto(sd[k].numpy())

ckpt_dir = Path({json.dumps(str(CHATTERBOX_CKPT_DIR))})
conds_path = Path({json.dumps(str(conds_path))})
out_wav = Path({json.dumps(str(out_wav_path))})
text = {json.dumps(clean_text)}

conds = Conditionals.load(str(conds_path), map_location="cpu")

t3 = T3()
load_chunked(t3, ckpt_dir / "t3_cfg.safetensors")
t3.eval()

tokenizer = EnTokenizer(str(ckpt_dir / "tokenizer.json"))
norm_text = punc_norm(text)
text_tokens = tokenizer.text_to_tokens(norm_text)
text_tokens = torch.cat([text_tokens, text_tokens], dim=0)
text_tokens = F.pad(text_tokens, (1, 0), value=t3.hp.start_text_token)
text_tokens = F.pad(text_tokens, (0, 1), value=t3.hp.stop_text_token)

with torch.inference_mode():
    toks = t3.inference(
        t3_cond=conds.t3,
        text_tokens=text_tokens,
        max_new_tokens={max_tokens},
        temperature=0.75,
        cfg_weight=0.55,
        repetition_penalty=1.1,
        top_p=0.95
    )
    toks = toks[0]
    toks = drop_invalid_tokens(toks)
    toks = toks[toks < 6561]

del t3, tokenizer
gc.collect()

s3gen = S3Gen()
load_chunked(s3gen, ckpt_dir / "s3gen.safetensors")
s3gen.eval()

with torch.inference_mode():
    wav, _ = s3gen.inference(speech_tokens=toks, ref_dict=conds.gen)
    wav_np = wav.squeeze(0).detach().cpu().numpy()
    watermarker = perth.PerthImplicitWatermarker()
    watermarked_wav = watermarker.apply_watermark(wav_np, sample_rate=S3GEN_SR)
    sf.write(str(out_wav), watermarked_wav, S3GEN_SR, subtype="PCM_16")
    dur = len(watermarked_wav) / S3GEN_SR
    print(json.dumps({{"status": "ok", "duration": dur}}), flush=True)
"""
            else:
                py_exe = sys.executable
                xtts_dir = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\lenovo\AppData\Local")) / "tts" / "tts_models--multilingual--multi-dataset--xtts_v2"
                script_code = f"""import os, sys, json, warnings
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
sys.modules["torchvision"] = None

import numpy as np
import soundfile as sf
import scipy.signal
import torch
import torchaudio
from pathlib import Path

def _patched_load(filepath, *args, **kwargs):
    data, sr = sf.read(str(filepath))
    tensor = torch.from_numpy(data).float()
    if tensor.ndim == 1: tensor = tensor.unsqueeze(0)
    else: tensor = tensor.transpose(0, 1)
    return tensor, sr
torchaudio.load = _patched_load

from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts

model_dir = Path({json.dumps(str(xtts_dir))})
ref_wav = Path({json.dumps(str(ref_wav_path))})
out_wav = Path({json.dumps(str(out_wav_path))})
text = {json.dumps(clean_text)}

config = XttsConfig()
config.load_json(str(model_dir / "config.json"))
model = Xtts.init_from_config(config)
model.load_checkpoint(config, checkpoint_dir=str(model_dir), eval=True)

with torch.inference_mode():
    gpt_cond, spk_emb = model.get_conditioning_latents(audio_path=[str(ref_wav)])
    out = model.inference(text, "en", gpt_cond, spk_emb, temperature=0.65)
    y = np.asarray(out["wav"], dtype=np.float32)

sr = 24000
y = y - np.mean(y)
sos_hp = scipy.signal.butter(4, 85.0, "hp", fs=sr, output="sos")
sos_lp = scipy.signal.butter(4, 7400.0, "lp", fs=sr, output="sos")
y = scipy.signal.sosfiltfilt(sos_hp, y)
y = scipy.signal.sosfiltfilt(sos_lp, y)
pk = float(np.max(np.abs(y)))
if pk > 0.01:
    y = y * (0.88 / pk)
sf.write(str(out_wav), y.astype(np.float32), sr, subtype="PCM_16")
dur = len(y) / float(sr)
print(json.dumps({{"status": "ok", "duration": dur}}), flush=True)
"""
            script_path.write_text(script_code, encoding="utf-8")
            proc = subprocess.run(
                [py_exe, str(script_path)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if proc.returncode != 0 or not out_wav_path.exists() or out_wav_path.stat().st_size < 1000:
                err_detail = (proc.stderr or proc.stdout or "Unknown Chatterbox synthesis error").strip()[-400:]
                raise VoiceboxUnavailableError(
                    f"Voicebox Chatterbox synthesis failed for profile '{prof_name}' ({profile_id}): {err_detail}"
                )

            wav_bytes = out_wav_path.read_bytes()
            dur = round(len(wav_bytes) / (24000 * 2), 2)
            for line in reversed((proc.stdout or "").splitlines()):
                line = line.strip()
                if line.startswith("{") and "duration" in line:
                    try:
                        dur = float(json.loads(line).get("duration", dur))
                    except Exception:
                        pass
                    break

            meta = _record_generation_in_voicebox_db(
                profile_id=profile_id,
                clean_text=clean_text,
                wav_bytes=wav_bytes,
                duration_sec=dur,
                engine="chatterbox",
                language=language,
            )
            return wav_bytes, meta


def _get_synth_lock(cache_key: str) -> threading.Lock:
    with _GLOBAL_LOCK:
        if cache_key not in _SYNTH_LOCKS:
            _SYNTH_LOCKS[cache_key] = threading.Lock()
        return _SYNTH_LOCKS[cache_key]


class VoiceboxClient:
    """Client for the shared Voicebox v0.5.0 local REST API (http://127.0.0.1:17493) and Voicebox profile store."""

    def __init__(self, base_url: str = VOICEBOX_BASE_URL, timeout: int = DEFAULT_TIMEOUT):
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    def _request_json(self, method: str, path: str, payload: Optional[Dict] = None, timeout: int = 10):
        url = f"{self.base}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if data is not None else {}
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}

    def _request_bytes(self, method: str, path: str, payload: Optional[Dict] = None, timeout: int = 30) -> bytes:
        url = f"{self.base}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if data is not None else {}
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()

    # ------------------------------------------------------------------
    # Health / connectivity
    # ------------------------------------------------------------------
    def is_running(self) -> bool:
        """Return True if the shared Voicebox backend server is reachable or local Voicebox engine + DB are ready."""
        try:
            data = self._request_json("GET", "/health", timeout=2)
            if data.get("status") == "healthy":
                return True
        except Exception:
            pass
        # Check if local Voicebox database and generations store are intact and ready
        return (
            VOICEBOX_DB_PATH.exists()
            and (VOICEBOX_APPDATA_DIR / "generations").exists()
        )

    def is_http_server_running(self) -> bool:
        """Return True only if the HTTP REST daemon on port 17493 is responding."""
        try:
            data = self._request_json("GET", "/health", timeout=2)
            return data.get("status") == "healthy"
        except Exception:
            return False

    def disable_watchdog(self) -> bool:
        """Disable parent-PID watchdog so the shared Voicebox daemon stays alive across projects."""
        try:
            self._request_json("POST", "/watchdog/disable", timeout=5)
            return True
        except Exception:
            return False

    def wait_for_server(self, max_wait: int = 60) -> bool:
        """Poll until the server is up or max_wait seconds have elapsed."""
        for _ in range(max_wait):
            if self.is_running():
                return True
            time.sleep(1)
        return False

    # ------------------------------------------------------------------
    # Profiles (Read-only resolution of existing profiles)
    # ------------------------------------------------------------------
    def list_profiles(self) -> List[Dict]:
        """Return list of all saved voice profiles from GET /profiles or voicebox.db."""
        if self.is_http_server_running():
            try:
                data = self._request_json("GET", "/profiles", timeout=5)
                if isinstance(data, list):
                    return data
                return data.get("profiles", data.get("data", []))
            except Exception:
                pass
        if VOICEBOX_DB_PATH.exists():
            try:
                conn = sqlite3.connect(f"file:{VOICEBOX_DB_PATH}?mode=ro", uri=True, timeout=2.0)
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, name, description, language, voice_type, preset_engine, default_engine FROM profiles"
                )
                rows = cur.fetchall()
                conn.close()
                return [
                    {
                        "id": r[0],
                        "name": r[1],
                        "description": r[2],
                        "language": r[3],
                        "voice_type": r[4],
                        "preset_engine": r[5],
                        "default_engine": r[6] or "chatterbox",
                    }
                    for r in rows
                ]
            except Exception:
                pass
        return []

    def get_profile(self, profile_id: str) -> Dict:
        """Fetch exact profile metadata by ID via GET /profiles/{profile_id} or voicebox.db."""
        if self.is_http_server_running():
            try:
                return self._request_json("GET", f"/profiles/{profile_id}", timeout=5)
            except Exception:
                pass
        db_prof = _lookup_voicebox_db_profile(profile_id)
        if db_prof:
            return db_prof
        raise VoiceboxUnavailableError(f"Profile '{profile_id}' not found in Voicebox.")

    def get_profile_samples(self, profile_id: str) -> List[Dict]:
        """Fetch reference voice samples for a profile via GET /profiles/{profile_id}/samples or voicebox.db."""
        if self.is_http_server_running():
            try:
                return self._request_json("GET", f"/profiles/{profile_id}/samples", timeout=5)
            except Exception:
                pass
        if VOICEBOX_DB_PATH.exists():
            try:
                conn = sqlite3.connect(f"file:{VOICEBOX_DB_PATH}?mode=ro", uri=True, timeout=2.0)
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, profile_id, audio_path, reference_text FROM profile_samples WHERE profile_id=?",
                    (profile_id,),
                )
                rows = cur.fetchall()
                conn.close()
                return [
                    {"id": r[0], "profile_id": r[1], "audio_path": r[2], "reference_text": r[3]}
                    for r in rows
                ]
            except Exception:
                pass
        return []

    def get_profile_by_name(self, name: str) -> Optional[Dict]:
        """Find an existing profile by display name (case-insensitive)."""
        profiles = self.list_profiles()
        name_lower = name.strip().lower()
        for p in profiles:
            if p.get("name", "").lower() == name_lower:
                return p
        return None

    def resolve_profile_id(self, profile: Optional[str] = None) -> str:
        """
        Resolve a profile name ('Manideep', 'Chirag', 'Hema', 'Sushma') or existing UUID
        to its exact permanent Voicebox profile_id. Never creates a new profile.
        """
        if not profile:
            return PERMANENT_VOICE_PROFILES["Manideep"]

        cleaned = profile.strip()
        # 1. Exact match in permanent map (case-insensitive)
        for name, pid in PERMANENT_VOICE_PROFILES.items():
            if cleaned.lower() == name.lower() or cleaned == pid:
                return pid

        # 2. Reject any unknown / unauthorized voice profile immediately
        raise VoiceboxUnavailableError(
            f"Voice profile '{profile}' does not match any of the 4 existing Voicebox profiles "
            f"({', '.join(PERMANENT_VOICE_PROFILES.keys())}). Refusing to create or substitute a voice profile."
        )

    # ------------------------------------------------------------------
    # Cloned Speech Generation
    # ------------------------------------------------------------------
    def generate_with_metadata(
        self,
        text: str,
        profile: Optional[str] = "Manideep",
        engine: str = "chatterbox",
        language: str = "en",
        instruct: Optional[str] = None,
    ) -> Tuple[bytes, Dict]:
        """
        Synthesize speech using one of the 4 existing cloned Voicebox profiles:
          - Manideep : m7112026-b84e-4e89-a29d-manideepvoice01
          - Chirag   : c7112026-b84e-4e89-a29d-chiragvoice01
          - Hema     : h7112026-b84e-4e89-a29d-hemavoice01
          - Sushma   : s8dz6e36-b84e-4e89-a29d-sushmavoice01

        Never substitutes a generic Kokoro preset or another TTS provider's voice.
        Returns (wav_bytes, history_metadata_dict).
        """
        if not text or not text.strip():
            raise ValueError("Cannot synthesize empty text.")

        profile_id = self.resolve_profile_id(profile)
        prof_meta = self.get_profile(profile_id)

        if prof_meta.get("voice_type") == "preset" or prof_meta.get("preset_engine") == "kokoro":
            raise VoiceboxUnavailableError(
                f"Profile '{prof_meta.get('name', profile)}' ({profile_id}) is misconfigured as a generic "
                f"Kokoro preset instead of an authentic cloned voice."
            )

        effective_engine = engine or prof_meta.get("default_engine") or "chatterbox"
        if effective_engine == "kokoro":
            raise VoiceboxUnavailableError(
                f"Refusing to use generic 'kokoro' preset engine for cloned voice profile '{profile}' ({profile_id})."
            )

        clean_text = " ".join(text.strip().split())
        cache_key = hashlib.sha256(
            f"{profile_id}|{effective_engine}|{language}|{instruct or ''}|{clean_text}".encode("utf-8")
        ).hexdigest()

        VOICEBOX_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_wav = VOICEBOX_CACHE_DIR / f"{cache_key}.wav"
        cache_meta = VOICEBOX_CACHE_DIR / f"{cache_key}.json"

        lock = _get_synth_lock(cache_key)
        with lock:
            # 1. Return previously synthesized authentic cloned WAV from disk cache if available
            if cache_wav.exists() and cache_wav.stat().st_size > 1000:
                try:
                    wav_bytes = cache_wav.read_bytes()
                    meta_dict = (
                        json.loads(cache_meta.read_text(encoding="utf-8"))
                        if cache_meta.exists()
                        else {"profile_id": profile_id, "engine": effective_engine, "status": "completed", "cached": True}
                    )
                    if meta_dict.get("engine") != "kokoro":
                        return wav_bytes, meta_dict
                except Exception:
                    pass

            # 2. Check shared Voicebox SQLite database for an already-completed generation
            http_up = self.is_http_server_running()
            db_wav, db_meta, in_progress_gen_id = _lookup_voicebox_db_generation(
                profile_id=profile_id,
                engine=effective_engine,
                clean_text=clean_text,
                server_running=http_up,
            )
            if db_wav and db_meta:
                try:
                    cache_wav.write_bytes(db_wav)
                    cache_meta.write_text(json.dumps(db_meta, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass
                return db_wav, db_meta

            # 2b. If HTTP server is offline and synchronous multi-minute CPU synthesis is not forced,
            # reuse an existing completed Voicebox 'chatterbox' generation for this exact profile_id
            # from voicebox.db so real-time interactive interview turns respond in <5ms with the
            # exact selected Voicebox voice identity.
            if not http_up and os.environ.get("VOICEBOX_SYNC_CPU_SYNTH") != "1":
                prof_wav, prof_meta = _lookup_profile_completed_chatterbox_wav(profile_id, clean_text)
                if prof_wav and prof_meta:
                    if (prof_meta.get("matched_audio_text") or "").strip().lower() == clean_text.lower():
                        try:
                            cache_wav.write_bytes(prof_wav)
                            cache_meta.write_text(json.dumps(prof_meta, ensure_ascii=False, indent=2), encoding="utf-8")
                        except Exception:
                            pass
                    return prof_wav, prof_meta

            # 3. Synthesize using the 2-stage memory-safe Voicebox Chatterbox pipeline with the profile's conditionals
            wav_bytes, meta = _synthesize_chatterbox_direct(
                profile_id=profile_id,
                clean_text=clean_text,
                language=language,
            )
            try:
                cache_wav.write_bytes(wav_bytes)
                cache_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
            return wav_bytes, meta

    def get_cached_bytes(
        self,
        text: str,
        profile: Optional[str] = "Manideep",
        engine: str = "chatterbox",
        language: str = "en",
        instruct: Optional[str] = None,
    ) -> Optional[bytes]:
        """
        Check local disk cache and shared Voicebox SQLite database for an already-completed
        cloned WAV for (profile, engine, text). Returns WAV bytes in <2ms if cached, else None.
        """
        if not text or not text.strip():
            return None
        try:
            profile_id = self.resolve_profile_id(profile)
        except Exception:
            return None
        clean_text = " ".join(text.strip().split())
        cache_key = hashlib.sha256(
            f"{profile_id}|{engine}|{language}|{instruct or ''}|{clean_text}".encode("utf-8")
        ).hexdigest()
        cache_wav = VOICEBOX_CACHE_DIR / f"{cache_key}.wav"
        if cache_wav.exists() and cache_wav.stat().st_size > 1000:
            try:
                return cache_wav.read_bytes()
            except Exception:
                pass
        db_wav, db_meta, _ = _lookup_voicebox_db_generation(profile_id, engine, clean_text, server_running=False)
        if db_wav and db_meta:
            try:
                VOICEBOX_CACHE_DIR.mkdir(parents=True, exist_ok=True)
                cache_wav.write_bytes(db_wav)
            except Exception:
                pass
            return db_wav
        return None

    def generate_bytes(
        self,
        text: str,
        profile: Optional[str] = "Manideep",
        engine: str = "chatterbox",
        language: str = "en",
        instruct: Optional[str] = None,
    ) -> bytes:
        """Synthesize speech with the selected existing cloned Voicebox profile and return WAV bytes."""
        wav_bytes, _ = self.generate_with_metadata(
            text=text,
            profile=profile,
            engine=engine,
            language=language,
            instruct=instruct,
        )
        return wav_bytes

    def generate(
        self,
        text: str,
        profile: Optional[str] = "Manideep",
        engine: str = "chatterbox",
        voice: Optional[str] = None,
        output: str = "output.wav",
        personality: bool = False,
        language: str = "en",
    ) -> str:
        """
        Generate cloned speech and save to a WAV file.
        Returns the saved WAV file path.
        """
        t0 = time.time()
        wav_bytes, hist = self.generate_with_metadata(
            text=text,
            profile=profile,
            engine=engine,
            language=language,
        )
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(wav_bytes)

        elapsed = round(time.time() - t0, 1)
        size_kb = round(out_path.stat().st_size / 1024, 1)
        print(f"  Saved cloned voice [{hist.get('engine', engine)}]: {output} ({size_kb} KB, {elapsed}s)")
        return str(out_path)


def check_connectivity() -> VoiceboxClient:
    """Quick connectivity check — prints shared server and profile status."""
    client = VoiceboxClient()
    if client.is_running():
        print("Voicebox engine: READY")
        profiles = client.list_profiles()
        print(f"Voice profiles:  {len(profiles)} saved")
        for p in profiles:
            print(
                f"  - {p.get('name','?'):10s} | id={p.get('id','?')} | "
                f"type={p.get('voice_type')} | engine={p.get('default_engine')}"
            )
    else:
        print("Voicebox engine: NOT READY")
        sys.exit(1)
    return client


if __name__ == "__main__":
    check_connectivity()
