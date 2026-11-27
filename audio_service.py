"""
Audio Service for AI Mock Interview Platform.
Supports:
1. Audio Quality Inspection, Band-Pass Noise Filtering, and VAD Validation:
   - High-pass rumble removal (>85Hz), RMS/ZCR voice activity verification, and silence rejection.
2. Speech-to-Text (STT) with Hallucination & Noise Rejection:
   - Tier 1: Groq Cloud Whisper (`whisper-large-v3`)
   - Tier 2: Local openai-whisper
   - Tier 3: SpeechRecognition fallback
   - Automatic filtering of Whisper silence/noise hallucinations.
3. Text-to-Speech (TTS) via Shared Voicebox Cloned Profiles:
   - Strictly uses the 4 existing Voicebox voice profiles from SHR_AI_NEWS:
     * Manideep : m7112026-b84e-4e89-a29d-manideepvoice01
     * Chirag   : c7112026-b84e-4e89-a29d-chiragvoice01
     * Hema     : h7112026-b84e-4e89-a29d-hemavoice01
     * Sushma   : s8dz6e36-b84e-4e89-a29d-sushmavoice01
   - Never recreates voices, generates new voice IDs, or falls back to generic voices.
"""
import io
import math
import os
import re
import struct
import tempfile
import threading
import time
import wave
from typing import Any, Dict, Optional, Tuple

# Ensure discovered local ffmpeg is in PATH for local fallback tools
KNOWN_FFMPEG_PATHS = [
    r"C:\Users\lenovo\Downloads\SHR_AI_NEWS",
    r"C:\Users\lenovo\anaconda3\envs\face_recognition\Library\bin",
    r"C:\Users\lenovo\anaconda3\pkgs\ffmpeg-6.1.1-haa678a1_5\Library\bin",
]
for p in KNOWN_FFMPEG_PATHS:
    if os.path.exists(p) and p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")


def get_secret(name: str) -> Optional[str]:
    """Retrieve secret from Streamlit secrets, environment, or .streamlit/secrets.toml."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass

    env_val = os.getenv(name)
    if env_val:
        return env_val

    try:
        import toml
        toml_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
        if os.path.exists(toml_path):
            data = toml.load(toml_path)
            if name in data:
                return data[name]
    except Exception:
        pass

    return None


# ---------------------------------------------------------
# Noise Filtering, VAD Analysis & Whisper Hallucination Guard
# ---------------------------------------------------------
WHISPER_HALLUCINATION_EXACT = {
    "thank you",
    "thank you.",
    "thanks",
    "thanks.",
    "thank you very much",
    "thank you for watching",
    "thanks for watching",
    "thank you for listening",
    "subtitles by the amara.org community",
    "subtitles by",
    "amara.org",
    "mbc",
    "you",
    "you.",
    "bye",
    "bye.",
    "bye-bye",
    "goodbye",
    "uh",
    "um",
    "hmm",
    "hm",
    "ah",
    "oh",
    "eh",
    "shh",
    "...",
    ".",
}

WHISPER_HALLUCINATION_SUBSTRINGS = [
    "thanks for watching",
    "thank you for watching",
    "subscribe to my channel",
    "please subscribe",
    "like and subscribe",
    "subtitles by",
    "amara.org",
    "translated by",
    "transcribed by",
    "[blank_audio]",
    "[silence]",
    "[music]",
    "[applause]",
    "(music)",
    "(silence)",
    "(background noise)",
]


def is_whisper_hallucination_or_noise(text: str) -> bool:
    """
    Detect common Whisper STT silence/background-noise hallucinations and non-speech artifacts.
    Returns True if the transcript is noise or a known Whisper hallucination.
    """
    if not text or not text.strip():
        return True

    cleaned = text.strip()
    lower = cleaned.lower().strip(" .,!?:;\"'()-[]{}…")
    if not lower:
        return True

    # Must contain at least one ASCII alphabetic character
    alpha_chars = [c for c in lower if c.isalpha()]
    if len(alpha_chars) < 2:
        return True

    if lower in WHISPER_HALLUCINATION_EXACT:
        return True

    for pattern in WHISPER_HALLUCINATION_SUBSTRINGS:
        if pattern in lower:
            return True

    # Check for bracketed/parenthesized sound effects only, e.g. "[cough]" or "(inaudible)"
    stripped_brackets = re.sub(r"\[.*?\]|\(.*?\)|\*.*?\*", "", cleaned).strip()
    if not stripped_brackets or not any(c.isalpha() for c in stripped_brackets):
        return True

    # Check for repetitive single-word loops induced by steady fan noise (e.g. "you you you you")
    words = [w.strip(".,!?:;\"'()") for w in lower.split() if any(c.isalpha() for c in w)]
    if not words:
        return True
    if len(words) >= 4 and len(set(words)) == 1:
        return True

    return False


def analyze_and_filter_wav_bytes(audio_bytes: bytes) -> Tuple[bytes, Dict[str, float]]:
    """
    Inspect WAV audio bytes for genuine human speech energy vs. silence/background noise,
    and apply a 1st-order high-pass filter (~85Hz) to attenuate low-frequency hum/rumble.
    For non-WAV containers (e.g. WebM/Opus), estimates payload density.
    Returns (filtered_audio_bytes, metrics_dict).
    """
    metrics = {
        "is_wav": 0.0,
        "duration_sec": 0.0,
        "rms": 0.0,
        "peak": 0.0,
        "speech_frame_ratio": 0.0,
        "zcr": 0.0,
        "is_likely_speech": 1.0,
    }
    if not audio_bytes or len(audio_bytes) < 100:
        metrics["is_likely_speech"] = 0.0
        return audio_bytes, metrics

    # Check if RIFF/WAV container
    if audio_bytes[:4] == b"RIFF" and b"WAVE" in audio_bytes[:16]:
        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                raw_pcm = wf.readframes(n_frames)

            if sampwidth == 2 and n_frames > 0 and framerate > 0:
                metrics["is_wav"] = 1.0
                total_samples = len(raw_pcm) // 2
                samples = list(struct.unpack(f"<{total_samples}h", raw_pcm[: total_samples * 2]))
                if n_channels > 1:
                    samples = samples[0::n_channels]

                num_s = len(samples)
                duration_sec = num_s / float(framerate)
                metrics["duration_sec"] = round(duration_sec, 3)

                if num_s < int(framerate * 0.15):
                    metrics["is_likely_speech"] = 0.0
                    return audio_bytes, metrics

                # Apply 1st-order high-pass filter at ~85Hz to strip DC offset, AC hum, and desk rumble
                rc = 1.0 / (2.0 * math.pi * 85.0)
                dt = 1.0 / float(framerate)
                alpha = rc / (rc + dt)
                filtered = [0] * num_s
                prev_x = float(samples[0])
                prev_y = 0.0
                sum_sq = 0.0
                peak_val = 0.0
                zero_crossings = 0

                for i, x_int in enumerate(samples):
                    x = float(x_int)
                    y = alpha * (prev_y + x - prev_x)
                    prev_x = x
                    prev_y = y
                    clamped = max(-32768, min(32767, int(y)))
                    filtered[i] = clamped
                    norm_y = abs(clamped) / 32768.0
                    sum_sq += norm_y * norm_y
                    if norm_y > peak_val:
                        peak_val = norm_y
                    if i > 0 and ((filtered[i - 1] >= 0 > clamped) or (filtered[i - 1] < 0 <= clamped)):
                        zero_crossings += 1

                rms = math.sqrt(sum_sq / num_s)
                zcr = zero_crossings / float(num_s)
                metrics["rms"] = round(rms, 5)
                metrics["peak"] = round(peak_val, 5)
                metrics["zcr"] = round(zcr, 4)

                # Frame-level VAD (20ms frames)
                frame_len = max(1, int(framerate * 0.02))
                frame_rms_list = []
                for start in range(0, num_s - frame_len + 1, frame_len):
                    chunk = filtered[start : start + frame_len]
                    f_rms = math.sqrt(sum((c / 32768.0) ** 2 for c in chunk) / frame_len)
                    frame_rms_list.append(f_rms)

                if frame_rms_list:
                    sorted_rms = sorted(frame_rms_list)
                    noise_floor = sorted_rms[max(0, int(len(sorted_rms) * 0.15))]
                    voice_thresh = max(0.012, noise_floor * 2.2)
                    voiced_frames = sum(1 for r in frame_rms_list if r >= voice_thresh)
                    speech_ratio = voiced_frames / float(len(frame_rms_list))
                else:
                    speech_ratio = 0.0

                metrics["speech_frame_ratio"] = round(speech_ratio, 4)

                # Reject pure silence or steady stationary background noise
                if rms < 0.006 or peak_val < 0.025 or speech_ratio < 0.05:
                    metrics["is_likely_speech"] = 0.0
                    return audio_bytes, metrics

                # Normalize audio gain when speech peak is quiet (< 0.55) so STT engines clearly recognize speech
                if 0.015 < peak_val < 0.55:
                    gain = min(4.5, 0.72 / peak_val)
                    filtered = [max(-32768, min(32767, int(s * gain))) for s in filtered]

                # Repack high-pass filtered mono WAV
                out_buf = io.BytesIO()
                with wave.open(out_buf, "wb") as out_wf:
                    out_wf.setnchannels(1)
                    out_wf.setsampwidth(2)
                    out_wf.setframerate(framerate)
                    out_wf.writeframes(struct.pack(f"<{len(filtered)}h", *filtered))
                return out_buf.getvalue(), metrics
        except Exception:
            pass

    # Non-WAV (e.g., WebM/Opus from browser MediaRecorder)
    if len(audio_bytes) < 1200:
        metrics["is_likely_speech"] = 0.0
    else:
        # Check byte entropy / zero-padding
        non_zero = sum(1 for b in audio_bytes[: min(len(audio_bytes), 4096)] if b not in (0, 255))
        if non_zero < 150:
            metrics["is_likely_speech"] = 0.0
    return audio_bytes, metrics


def transcribe_audio_bytes_detailed(
    audio_bytes: bytes, filename_hint: str = "recording.wav"
) -> Dict[str, Any]:
    """
    Transcribe raw audio bytes after noise filtering and VAD validation, returning detailed
    telemetry for real-time activity logging:
      - text: str
      - provider: str
      - duration_ms: float
      - audio_size_bytes: int
      - audio_metrics: dict
      - rejected_reason: Optional[str]
      - error: Optional[str]
    """
    t0 = time.perf_counter()
    size_bytes = len(audio_bytes) if audio_bytes else 0
    result_meta: Dict[str, Any] = {
        "text": "",
        "provider": "None",
        "duration_ms": 0.0,
        "audio_size_bytes": size_bytes,
        "audio_metrics": {},
        "rejected_reason": None,
        "error": None,
    }

    if not audio_bytes or size_bytes < 400:
        result_meta["duration_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
        result_meta["rejected_reason"] = f"Audio buffer too small ({size_bytes} bytes < 400 bytes)"
        return result_meta

    filtered_bytes, audio_metrics = analyze_and_filter_wav_bytes(audio_bytes)
    result_meta["audio_metrics"] = audio_metrics
    if audio_metrics.get("is_likely_speech", 1.0) <= 0.0:
        result_meta["duration_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
        result_meta["rejected_reason"] = (
            f"VAD rejected non-speech/silence (rms={audio_metrics.get('rms', 0):.4f}, "
            f"peak={audio_metrics.get('peak', 0):.4f}, ratio={audio_metrics.get('speech_frame_ratio', 0):.3f})"
        )
        return result_meta

    if audio_metrics.get("is_wav", 0.0) == 1.0:
        filename_hint = "recording.wav"

    groq_key = get_secret("GROQ_API_KEY") or get_secret("GROQ_KEY")
    errors = []

    # Tier 1: Groq Whisper API (Requires NO ffmpeg, runs in ~300ms)
    if groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key, timeout=6.0, max_retries=0)
            name = (
                filename_hint
                if filename_hint.endswith((".wav", ".mp3", ".m4a", ".ogg", ".webm"))
                else "recording.wav"
            )
            transcription = client.audio.transcriptions.create(
                file=(name, filtered_bytes),
                model="whisper-large-v3",
                language="en",
                temperature=0.0,
            )
            text = (transcription.text or "").strip()
            result_meta["provider"] = "Groq Whisper (whisper-large-v3)"
            result_meta["duration_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
            if text and not is_whisper_hallucination_or_noise(text):
                result_meta["text"] = text
                return result_meta
            if text and is_whisper_hallucination_or_noise(text):
                result_meta["rejected_reason"] = f"Whisper hallucination/noise filtered: '{text}'"
                return result_meta
            result_meta["rejected_reason"] = "Groq Whisper returned empty transcript"
            return result_meta
        except Exception as e:
            errors.append(f"Groq Whisper: {type(e).__name__}")

    # Tier 2: Local openai-whisper (requires ffmpeg)
    temp_path = None
    try:
        suffix = os.path.splitext(filename_hint)[1] or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(filtered_bytes)
            temp_path = tmp.name

        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(temp_path, fp16=False, language="en")
        text = (result.get("text", "") or "").strip()
        result_meta["provider"] = "Local OpenAI Whisper (base)"
        result_meta["duration_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
        if text and not is_whisper_hallucination_or_noise(text):
            result_meta["text"] = text
            return result_meta
        if text and is_whisper_hallucination_or_noise(text):
            result_meta["rejected_reason"] = f"Local Whisper hallucination/noise filtered: '{text}'"
            return result_meta
        result_meta["rejected_reason"] = "Local Whisper returned empty transcript"
        return result_meta
    except Exception as e:
        errors.append(f"Local Whisper: {type(e).__name__}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

    # Tier 3: SpeechRecognition fallback
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(filtered_bytes)) as source:
            audio_data = r.record(source)
            text = (r.recognize_google(audio_data) or "").strip()
            result_meta["provider"] = "SpeechRecognition (Google)"
            result_meta["duration_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
            if text and not is_whisper_hallucination_or_noise(text):
                result_meta["text"] = text
                return result_meta
            if text:
                result_meta["rejected_reason"] = f"SpeechRecognition noise filtered: '{text}'"
            else:
                result_meta["rejected_reason"] = "SpeechRecognition returned empty transcript"
            return result_meta
    except Exception as e:
        errors.append(f"SpeechRecognition: {type(e).__name__}")

    result_meta["duration_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
    result_meta["error"] = "; ".join(errors) if errors else "All STT tiers unavailable"
    result_meta["rejected_reason"] = result_meta["error"]
    return result_meta


def transcribe_audio_bytes(audio_bytes: bytes, filename_hint: str = "recording.wav") -> str:
    """
    Transcribe raw audio bytes after noise filtering and VAD validation.
    Uses Groq Cloud Whisper first, with local Whisper and SpeechRecognition fallbacks.
    Automatically filters out Whisper silence/noise hallucinations.
    """
    res = transcribe_audio_bytes_detailed(audio_bytes, filename_hint=filename_hint)
    return res.get("text", "") or ""


# ---------------------------------------------------------
# Text-to-Speech (Shared Voicebox Cloned Profiles Service)
# ---------------------------------------------------------
from voicebox_client import (
    PERMANENT_VOICE_DESCRIPTIONS,
    PERMANENT_VOICE_PROFILES,
    VOICEBOX_BASE_URL,
    VoiceboxClient,
    VoiceboxUnavailableError,
)

VOICEBOX_API_URL = VOICEBOX_BASE_URL

VOICEBOX_PROFILES = dict(PERMANENT_VOICE_PROFILES)

VOICEBOX_PROFILE_NAMES = {v: k for k, v in VOICEBOX_PROFILES.items()}


def get_voice_profile_name(profile_id_or_name: Optional[str]) -> str:
    """Return display name ('Manideep', 'Chirag', 'Hema', 'Sushma') for a profile ID or name."""
    if not profile_id_or_name:
        return "Manideep"
    cleaned = profile_id_or_name.strip()
    if cleaned in VOICEBOX_PROFILES:
        return cleaned
    if cleaned in VOICEBOX_PROFILE_NAMES:
        return VOICEBOX_PROFILE_NAMES[cleaned]
    for name, pid in VOICEBOX_PROFILES.items():
        if cleaned.lower() == name.lower() or cleaned == pid:
            return name
    return cleaned


def get_configured_voice_profile_id() -> str:
    """Retrieve active voice profile id from session state, config, or default to Manideep."""
    try:
        import streamlit as st
        if hasattr(st, "session_state"):
            if st.session_state.get("selected_voice_id"):
                return st.session_state["selected_voice_id"]
            if st.session_state.get("selected_voice_name") in VOICEBOX_PROFILES:
                return VOICEBOX_PROFILES[st.session_state["selected_voice_name"]]
    except Exception:
        pass

    prof_id = get_secret("VOICE_PROFILE_ID")
    if prof_id:
        return prof_id
    prof_name = get_secret("VOICE_PROFILE")
    if prof_name and prof_name in VOICEBOX_PROFILES:
        return VOICEBOX_PROFILES[prof_name]
    return VOICEBOX_PROFILES["Manideep"]


def verify_voice_profile_available(profile_id_or_name: Optional[str] = None) -> tuple[bool, str]:
    """
    Verify that the selected interviewer voice profile is valid and ready for the session.
    Checks the 4 permanent Voicebox profiles (Manideep, Chirag, Hema, Sushma) in Voicebox.
    Returns (is_available: bool, status_or_error_message: str).
    """
    resolved_id = None
    if profile_id_or_name:
        for name, pid in VOICEBOX_PROFILES.items():
            if profile_id_or_name.strip().lower() in (name.lower(), pid.lower()):
                resolved_id = pid
                break
        if not resolved_id:
            return (
                False,
                f"Voice profile '{profile_id_or_name}' is not one of the 4 existing Voicebox profiles "
                f"(Hema, Sushma, Chirag, Manideep). Refusing to substitute another voice.",
            )
    else:
        resolved_id = get_configured_voice_profile_id()

    prof_name = get_voice_profile_name(resolved_id)
    if not any(resolved_id == pid for pid in VOICEBOX_PROFILES.values()):
        return (
            False,
            f"Voice profile '{profile_id_or_name}' is not one of the 4 authorized Voicebox profiles "
            f"(Hema, Sushma, Chirag, Manideep).",
        )

    client = VoiceboxClient(base_url=VOICEBOX_API_URL)
    try:
        profile_id = client.resolve_profile_id(resolved_id)
        prof = client.get_profile(profile_id)
        if prof.get("voice_type") == "preset" or prof.get("preset_engine") == "kokoro":
            return (
                False,
                f"Voice profile '{prof.get('name')}' ({profile_id}) is set to a generic Kokoro preset "
                f"instead of its cloned Voicebox configuration.",
            )
        return (
            True,
            f"Voicebox profile '{prof.get('name', prof_name)}' ({profile_id}) verified and active "
            f"[engine={prof.get('default_engine', 'chatterbox')}].",
        )
    except Exception as e:
        return False, f"Voicebox profile '{prof_name}' ({resolved_id}) failed to load: {e}"


def _synthesize_voicebox(
    text: str,
    profile_id: Optional[str] = None,
    engine: str = "chatterbox",
    timeout_sec: int = 300,
) -> bytes:
    """
    Synthesize speech via Voicebox using the exact existing cloned voice profile.
    Raises VoiceboxUnavailableError if the service or cloned profile fails (never substitutes Kokoro or fallback voice).
    """
    target_id = profile_id or get_configured_voice_profile_id()
    client = VoiceboxClient(base_url=VOICEBOX_API_URL, timeout=timeout_sec)
    return client.generate_bytes(text=text, profile=target_id, engine=engine)


_INFLIGHT_VB_LOCK = threading.Lock()
_INFLIGHT_VB_KEYS = set()


def _bg_cache_voicebox_turn(text: str, profile_id: str) -> None:
    """Background pre-caching of uncached dynamic interview phrases into Voicebox DB and disk cache."""
    key = (profile_id, " ".join(text.strip().split()))
    with _INFLIGHT_VB_LOCK:
        if key in _INFLIGHT_VB_KEYS:
            return
        _INFLIGHT_VB_KEYS.add(key)
    try:
        client = VoiceboxClient(base_url=VOICEBOX_API_URL, timeout=300)
        client.generate_bytes(text=text, profile=profile_id, engine="chatterbox")
    except Exception:
        pass
    finally:
        with _INFLIGHT_VB_LOCK:
            _INFLIGHT_VB_KEYS.discard(key)


def synthesize_interviewer_turn_audio_detailed(
    text: str,
    voice_profile_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Interviewer speech synthesis locked strictly to the selected voice profile, returning
    both audio bytes and detailed TTS telemetry for real-time activity logging:
      - audio_bytes: bytes
      - voice_id: str
      - voice_name: str
      - duration_ms: float
      - source: str ('voicebox_cache_or_db' | 'voicebox_live_chatterbox')
      - audio_size_bytes: int
    """
    t0 = time.perf_counter()
    target_profile_id = voice_profile_id or get_configured_voice_profile_id()
    client = VoiceboxClient(base_url=VOICEBOX_API_URL, timeout=300)

    try:
        resolved_id = client.resolve_profile_id(target_profile_id)
    except Exception as e:
        raise VoiceboxUnavailableError(
            f"Invalid Voicebox profile ID '{target_profile_id}': {e}. "
            f"Must be one of: {list(VOICEBOX_PROFILES.keys())}."
        )

    prof_name = get_voice_profile_name(resolved_id)
    if not text or not text.strip():
        return {
            "audio_bytes": b"",
            "voice_id": resolved_id,
            "voice_name": prof_name,
            "duration_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "source": "empty",
            "audio_size_bytes": 0,
        }

    # 1. Fast path: check Voicebox disk cache and voicebox.db
    cached_wav = client.get_cached_bytes(text=text, profile=resolved_id, engine="chatterbox")
    if cached_wav and len(cached_wav) > 1000:
        return {
            "audio_bytes": cached_wav,
            "voice_id": resolved_id,
            "voice_name": prof_name,
            "duration_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "source": "voicebox_cache_or_db",
            "audio_size_bytes": len(cached_wav),
        }

    # 2. Live Voicebox generation using the profile's Chatterbox conditionals
    if not client.is_running():
        raise VoiceboxUnavailableError(
            f"Voicebox profile '{prof_name}' ({resolved_id}) is unavailable. "
            f"Please ensure Voicebox and its profile conditionals are present."
        )

    wav_bytes, gen_meta = client.generate_with_metadata(text=text, profile=resolved_id, engine="chatterbox")
    return {
        "audio_bytes": wav_bytes,
        "voice_id": resolved_id,
        "voice_name": prof_name,
        "duration_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        "source": "voicebox_live_chatterbox",
        "audio_size_bytes": len(wav_bytes) if wav_bytes else 0,
        "matched_audio_text": (gen_meta or {}).get("matched_audio_text") or text,
    }


def synthesize_interviewer_turn_audio(
    text: str,
    voice_profile_id: Optional[str] = None,
) -> bytes:
    """
    Interviewer speech synthesis locked strictly to the selected voice profile:
      - Manideep : m7112026-b84e-4e89-a29d-manideepvoice01
      - Chirag   : c7112026-b84e-4e89-a29d-chiragvoice01
      - Hema     : h7112026-b84e-4e89-a29d-hemavoice01
      - Sushma   : s8dz6e36-b84e-4e89-a29d-sushmavoice01

    Strictly locks to the chosen voice ID throughout the entire interview session.
    1. Checks Voicebox disk cache and SQLite database (voicebox.db) for an authentic
       cloned chatterbox generation matching this profile ID and text (<2ms).
    2. If not cached, generates audio using the exact Voicebox Chatterbox profile.
    3. If the profile cannot load, raises VoiceboxUnavailableError with an explicit error.
       NEVER falls back to Edge-TTS, Niranjan, pyttsx3, or any default voice.
    """
    res = synthesize_interviewer_turn_audio_detailed(text=text, voice_profile_id=voice_profile_id)
    return res.get("audio_bytes", b"") or b""


def synthesize_speech(
    text: str,
    voice: str = "Voicebox",
    voice_profile_id: Optional[str] = None,
    allow_fallback: bool = False,
) -> bytes:
    """
    Generate audio bytes for interview speech playback using the selected Voicebox cloned profile:
      - Manideep (m7112026-b84e-4e89-a29d-manideepvoice01)
      - Chirag   (c7112026-b84e-4e89-a29d-chiragvoice01)
      - Hema     (h7112026-b84e-4e89-a29d-hemavoice01)
      - Sushma   (s8dz6e36-b84e-4e89-a29d-sushmavoice01)

    Does NOT fall back to Edge-TTS, Niranjan, or any default voice.
    Strictly preserves the selected voice ID.
    """
    return synthesize_interviewer_turn_audio(text=text, voice_profile_id=voice_profile_id)
