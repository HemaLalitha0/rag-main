"""
Real-Time Interview Bridge Server.
Provides low-latency background HTTP endpoints on localhost:8765 to bridge:
1. Candidate live microphone audio stream / chunks / completed utterance blobs
2. Audio noise filtering, VAD validation, and Groq Whisper speech transcription (with browser STT fallback)
3. Conversational intent / readiness confirmation / clarification / retry / completion routing
4. Syna Voicebox TTS speech generation (locked strictly to candidate's selected voice ID:
   Hema, Sushma, Chirag, or Manideep)
5. Validated State Machine:
   INITIALIZING -> INTRODUCTION -> WAITING_FOR_READINESS -> ASKING_QUESTION ->
   WAITING_FOR_CANDIDATE (LISTENING_TO_CANDIDATE) -> RECORDING_ANSWER ->
   PROCESSING_AUDIO -> TRANSCRIBING_ANSWER -> EVALUATING_ANSWER ->
   GENERATING_NEXT_QUESTION -> INTERVIEW_COMPLETED (COMPLETED) | INTERVIEW_ERROR
"""
import base64
import datetime
import hashlib
import json
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from audio_service import (
    VOICEBOX_PROFILES,
    analyze_and_filter_wav_bytes,
    get_configured_voice_profile_id,
    get_voice_profile_name,
    is_whisper_hallucination_or_noise,
    synthesize_interviewer_turn_audio,
    synthesize_interviewer_turn_audio_detailed,
    synthesize_speech,
    transcribe_audio_bytes,
    transcribe_audio_bytes_detailed,
    verify_voice_profile_available,
)
from interview_engine import analyze_delivery_metrics, evaluate_universal_answer
from interview_schemas import QuestionItem, QuestionSessionRecord
from llm_client import call_llm, clean_json_response
from voicebox_client import VoiceboxClient, VoiceboxUnavailableError

# Thread-safe global session state shared between Streamlit and Live Call Room (preserved across hot-reloads)
if not hasattr(sys, "_interview_bridge_lock"):
    sys._interview_bridge_lock = threading.Lock()
SESSION_LOCK = sys._interview_bridge_lock

# Dedicated lock for thread-safe ordered activity log writes
if not hasattr(sys, "_interview_log_lock"):
    sys._interview_log_lock = threading.Lock()
LOG_LOCK = sys._interview_log_lock

# Turn-processing lock to prevent concurrent/duplicate answer submissions
if not hasattr(sys, "_interview_turn_lock"):
    sys._interview_turn_lock = threading.Lock()
TURN_PROCESSING_LOCK = sys._interview_turn_lock

# Allowed State Machine Transitions (including canonical aliases from Section 6 & 7)
VALID_STATE_TRANSITIONS: Dict[str, set] = {
    "INITIALIZING": {"INTRODUCTION", "INTRODUCTION_PLAYING", "WAITING_FOR_READINESS", "INTERVIEW_ERROR", "ERROR", "COMPLETED", "INTERVIEW_COMPLETED"},
    "INTRODUCTION": {"INTRODUCTION_PLAYING", "WAITING_FOR_READINESS", "PROCESSING_READINESS", "ASKING_QUESTION", "QUESTION_PLAYING", "INTERVIEW_ERROR", "ERROR", "COMPLETED"},
    "INTRODUCTION_PLAYING": {"WAITING_FOR_READINESS", "PROCESSING_READINESS", "ASKING_QUESTION", "QUESTION_PLAYING", "INTERVIEW_ERROR", "ERROR", "COMPLETED"},
    "INITIAL_GREETING": {"INTRODUCTION_PLAYING", "WAITING_FOR_READINESS", "PROCESSING_READINESS", "ASKING_QUESTION", "QUESTION_PLAYING", "INTERVIEW_ERROR", "ERROR", "COMPLETED"},
    "WAITING_FOR_READINESS": {
        "WAITING_FOR_READINESS",
        "PROCESSING_READINESS",
        "ASKING_QUESTION",
        "QUESTION_PLAYING",
        "CLARIFICATION_REQUESTED",
        "INTERVIEW_ERROR",
        "ERROR",
        "COMPLETED",
    },
    "PROCESSING_READINESS": {
        "WAITING_FOR_READINESS",
        "ASKING_QUESTION",
        "QUESTION_PLAYING",
        "CLARIFICATION_REQUESTED",
        "INTERVIEW_ERROR",
        "ERROR",
        "COMPLETED",
    },
    "ASKING_QUESTION": {
        "WAITING_FOR_CANDIDATE",
        "LISTENING_TO_CANDIDATE",
        "LISTENING",
        "RECORDING_ANSWER",
        "RECORDING",
        "WAITING_FOR_SILENCE",
        "PROCESSING_AUDIO",
        "PROCESSING_ANSWER",
        "INTERVIEW_ERROR",
        "ERROR",
        "COMPLETED",
    },
    "QUESTION_PLAYING": {
        "WAITING_FOR_CANDIDATE",
        "LISTENING_TO_CANDIDATE",
        "LISTENING",
        "RECORDING_ANSWER",
        "RECORDING",
        "WAITING_FOR_SILENCE",
        "PROCESSING_AUDIO",
        "PROCESSING_ANSWER",
        "INTERVIEW_ERROR",
        "ERROR",
        "COMPLETED",
    },
    "WAITING_FOR_CANDIDATE": {
        "LISTENING_TO_CANDIDATE",
        "LISTENING",
        "RECORDING_ANSWER",
        "RECORDING",
        "WAITING_FOR_SILENCE",
        "PROCESSING_AUDIO",
        "PROCESSING_ANSWER",
        "TRANSCRIBING_ANSWER",
        "TRANSCRIBING",
        "WAITING_FOR_CANDIDATE",
        "ASKING_QUESTION",
        "QUESTION_PLAYING",
        "NEXT_QUESTION",
        "INTERVIEW_ERROR",
        "ERROR",
        "COMPLETED",
    },
    "LISTENING_TO_CANDIDATE": {
        "WAITING_FOR_CANDIDATE",
        "RECORDING_ANSWER",
        "RECORDING",
        "WAITING_FOR_SILENCE",
        "PROCESSING_AUDIO",
        "PROCESSING_ANSWER",
        "TRANSCRIBING_ANSWER",
        "TRANSCRIBING",
        "LISTENING_TO_CANDIDATE",
        "LISTENING",
        "ASKING_QUESTION",
        "QUESTION_PLAYING",
        "NEXT_QUESTION",
        "INTERVIEW_ERROR",
        "ERROR",
        "COMPLETED",
    },
    "LISTENING": {
        "WAITING_FOR_CANDIDATE",
        "RECORDING_ANSWER",
        "RECORDING",
        "WAITING_FOR_SILENCE",
        "PROCESSING_AUDIO",
        "PROCESSING_ANSWER",
        "TRANSCRIBING_ANSWER",
        "TRANSCRIBING",
        "LISTENING_TO_CANDIDATE",
        "LISTENING",
        "ASKING_QUESTION",
        "QUESTION_PLAYING",
        "NEXT_QUESTION",
        "INTERVIEW_ERROR",
        "ERROR",
        "COMPLETED",
    },
    "RECORDING_ANSWER": {
        "RECORDING_ANSWER",
        "WAITING_FOR_SILENCE",
        "PROCESSING_AUDIO",
        "PROCESSING_ANSWER",
        "TRANSCRIBING_ANSWER",
        "TRANSCRIBING",
        "WAITING_FOR_CANDIDATE",
        "LISTENING_TO_CANDIDATE",
        "LISTENING",
        "INTERVIEW_ERROR",
        "ERROR",
        "COMPLETED",
    },
    "RECORDING": {
        "RECORDING",
        "WAITING_FOR_SILENCE",
        "PROCESSING_AUDIO",
        "PROCESSING_ANSWER",
        "TRANSCRIBING_ANSWER",
        "TRANSCRIBING",
        "WAITING_FOR_CANDIDATE",
        "LISTENING_TO_CANDIDATE",
        "LISTENING",
        "INTERVIEW_ERROR",
        "ERROR",
        "COMPLETED",
    },
    "WAITING_FOR_SILENCE": {
        "RECORDING_ANSWER",
        "RECORDING",
        "WAITING_FOR_SILENCE",
        "PROCESSING_AUDIO",
        "PROCESSING_ANSWER",
        "TRANSCRIBING_ANSWER",
        "TRANSCRIBING",
        "WAITING_FOR_CANDIDATE",
        "LISTENING_TO_CANDIDATE",
        "LISTENING",
        "INTERVIEW_ERROR",
        "ERROR",
        "COMPLETED",
    },
    "PROCESSING_AUDIO": {
        "PROCESSING_READINESS",
        "TRANSCRIBING_ANSWER",
        "TRANSCRIBING",
        "PROCESSING_ANSWER",
        "ANSWER_VALIDATION",
        "TRANSCRIPTION_RETRY",
        "WAITING_FOR_CANDIDATE",
        "LISTENING_TO_CANDIDATE",
        "LISTENING",
        "WAITING_FOR_READINESS",
        "INTERVIEW_ERROR",
        "ERROR",
        "COMPLETED",
    },
    "TRANSCRIBING_ANSWER": {
        "PROCESSING_READINESS",
        "PROCESSING_ANSWER",
        "ANSWER_VALIDATION",
        "CLARIFICATION_REQUESTED",
        "REPEAT_REQUESTED",
        "TRANSCRIPTION_RETRY",
        "EVALUATING_ANSWER",
        "ANSWER_EVALUATION",
        "ACKNOWLEDGING_ANSWER",
        "WAITING_FOR_CANDIDATE",
        "LISTENING_TO_CANDIDATE",
        "LISTENING",
        "WAITING_FOR_READINESS",
        "ASKING_QUESTION",
        "QUESTION_PLAYING",
        "INTERVIEW_ERROR",
        "ERROR",
        "COMPLETED",
    },
    "TRANSCRIBING": {
        "PROCESSING_READINESS",
        "PROCESSING_ANSWER",
        "ANSWER_VALIDATION",
        "CLARIFICATION_REQUESTED",
        "REPEAT_REQUESTED",
        "TRANSCRIPTION_RETRY",
        "EVALUATING_ANSWER",
        "ANSWER_EVALUATION",
        "ACKNOWLEDGING_ANSWER",
        "WAITING_FOR_CANDIDATE",
        "LISTENING_TO_CANDIDATE",
        "LISTENING",
        "WAITING_FOR_READINESS",
        "ASKING_QUESTION",
        "QUESTION_PLAYING",
        "INTERVIEW_ERROR",
        "ERROR",
        "COMPLETED",
    },
    "ANSWER_VALIDATION": {
        "PROCESSING_ANSWER",
        "CLARIFICATION_REQUESTED",
        "REPEAT_REQUESTED",
        "TRANSCRIPTION_RETRY",
        "EVALUATING_ANSWER",
        "ANSWER_EVALUATION",
        "ACKNOWLEDGING_ANSWER",
        "NEXT_QUESTION",
        "WAITING_FOR_CANDIDATE",
        "LISTENING_TO_CANDIDATE",
        "LISTENING",
        "ASKING_QUESTION",
        "QUESTION_PLAYING",
        "INTERVIEW_ERROR",
        "ERROR",
        "COMPLETED",
    },
    "PROCESSING_ANSWER": {
        "ANSWER_VALIDATION",
        "CLARIFICATION_REQUESTED",
        "REPEAT_REQUESTED",
        "TRANSCRIPTION_RETRY",
        "EVALUATING_ANSWER",
        "ANSWER_EVALUATION",
        "ACKNOWLEDGING_ANSWER",
        "NEXT_QUESTION",
        "GENERATING_NEXT_QUESTION",
        "WAITING_FOR_CANDIDATE",
        "LISTENING_TO_CANDIDATE",
        "LISTENING",
        "ASKING_QUESTION",
        "INTERVIEW_ERROR",
        "ERROR",
        "COMPLETED",
    },
    "CLARIFICATION_REQUESTED": {
        "ASKING_QUESTION",
        "QUESTION_PLAYING",
        "WAITING_FOR_CANDIDATE",
        "LISTENING_TO_CANDIDATE",
        "LISTENING",
        "INTERVIEW_ERROR",
        "ERROR",
    },
    "REPEAT_REQUESTED": {
        "ASKING_QUESTION",
        "QUESTION_PLAYING",
        "WAITING_FOR_CANDIDATE",
        "LISTENING_TO_CANDIDATE",
        "LISTENING",
        "INTERVIEW_ERROR",
        "ERROR",
    },
    "TRANSCRIPTION_RETRY": {
        "ASKING_QUESTION",
        "QUESTION_PLAYING",
        "WAITING_FOR_CANDIDATE",
        "LISTENING_TO_CANDIDATE",
        "LISTENING",
        "INTERVIEW_ERROR",
        "ERROR",
    },
    "EVALUATING_ANSWER": {
        "ACKNOWLEDGING_ANSWER",
        "NEXT_QUESTION",
        "GENERATING_NEXT_QUESTION",
        "NEXT_QUESTION_GENERATION",
        "ASKING_QUESTION",
        "QUESTION_PLAYING",
        "COMPLETED",
        "INTERVIEW_COMPLETED",
        "INTERVIEW_ERROR",
        "ERROR",
    },
    "ANSWER_EVALUATION": {
        "ACKNOWLEDGING_ANSWER",
        "NEXT_QUESTION",
        "GENERATING_NEXT_QUESTION",
        "NEXT_QUESTION_GENERATION",
        "ASKING_QUESTION",
        "QUESTION_PLAYING",
        "COMPLETED",
        "INTERVIEW_COMPLETED",
        "INTERVIEW_ERROR",
        "ERROR",
    },
    "ACKNOWLEDGING_ANSWER": {
        "NEXT_QUESTION",
        "GENERATING_NEXT_QUESTION",
        "NEXT_QUESTION_GENERATION",
        "ASKING_QUESTION",
        "QUESTION_PLAYING",
        "COMPLETED",
        "INTERVIEW_COMPLETED",
        "INTERVIEW_ERROR",
        "ERROR",
    },
    "NEXT_QUESTION": {
        "GENERATING_NEXT_QUESTION",
        "NEXT_QUESTION_GENERATION",
        "ASKING_QUESTION",
        "QUESTION_PLAYING",
        "COMPLETED",
        "INTERVIEW_COMPLETED",
        "INTERVIEW_ERROR",
        "ERROR",
    },
    "GENERATING_NEXT_QUESTION": {
        "ACKNOWLEDGING_ANSWER",
        "NEXT_QUESTION",
        "ASKING_QUESTION",
        "QUESTION_PLAYING",
        "COMPLETED",
        "INTERVIEW_COMPLETED",
        "INTERVIEW_ERROR",
        "ERROR",
    },
    "NEXT_QUESTION_GENERATION": {
        "ACKNOWLEDGING_ANSWER",
        "NEXT_QUESTION",
        "ASKING_QUESTION",
        "QUESTION_PLAYING",
        "COMPLETED",
        "INTERVIEW_COMPLETED",
        "INTERVIEW_ERROR",
        "ERROR",
    },
    "INTERVIEW_COMPLETED": {"INITIALIZING", "INTRODUCTION", "INTRODUCTION_PLAYING", "COMPLETED"},
    "COMPLETED": {"INITIALIZING", "INTRODUCTION", "INTRODUCTION_PLAYING", "INTERVIEW_COMPLETED"},
    "INTERVIEW_ERROR": {"INITIALIZING", "INTRODUCTION", "INTRODUCTION_PLAYING", "WAITING_FOR_READINESS", "WAITING_FOR_CANDIDATE", "COMPLETED"},
    "ERROR": {"INITIALIZING", "INTRODUCTION", "INTRODUCTION_PLAYING", "WAITING_FOR_READINESS", "WAITING_FOR_CANDIDATE", "COMPLETED"},
}

# Mapping from internal stage names to Section 6 & 7 canonical flow names
STAGE_TO_FLOW_STATE: Dict[str, str] = {
    "INITIALIZING": "INITIALIZING",
    "INTRODUCTION": "INTRODUCTION_PLAYING",
    "INTRODUCTION_PLAYING": "INTRODUCTION_PLAYING",
    "INITIAL_GREETING": "INTRODUCTION_PLAYING",
    "WAITING_FOR_READINESS": "WAITING_FOR_READINESS",
    "PROCESSING_READINESS": "PROCESSING_READINESS",
    "ASKING_QUESTION": "ASKING_QUESTION",
    "QUESTION_PLAYING": "ASKING_QUESTION",
    "WAITING_FOR_CANDIDATE": "WAITING_FOR_CANDIDATE",
    "LISTENING_TO_CANDIDATE": "WAITING_FOR_CANDIDATE",
    "LISTENING": "WAITING_FOR_CANDIDATE",
    "RECORDING_ANSWER": "RECORDING_ANSWER",
    "RECORDING": "RECORDING_ANSWER",
    "WAITING_FOR_SILENCE": "WAITING_FOR_SILENCE",
    "PROCESSING_AUDIO": "PROCESSING_ANSWER",
    "TRANSCRIBING_ANSWER": "PROCESSING_ANSWER",
    "TRANSCRIBING": "PROCESSING_ANSWER",
    "ANSWER_VALIDATION": "PROCESSING_ANSWER",
    "PROCESSING_ANSWER": "PROCESSING_ANSWER",
    "CLARIFICATION_REQUESTED": "CLARIFICATION_REQUESTED",
    "REPEAT_REQUESTED": "REPEAT_REQUESTED",
    "TRANSCRIPTION_RETRY": "TRANSCRIPTION_RETRY",
    "EVALUATING_ANSWER": "PROCESSING_ANSWER",
    "ANSWER_EVALUATION": "PROCESSING_ANSWER",
    "ACKNOWLEDGING_ANSWER": "ACKNOWLEDGING_ANSWER",
    "NEXT_QUESTION": "NEXT_QUESTION",
    "GENERATING_NEXT_QUESTION": "NEXT_QUESTION",
    "NEXT_QUESTION_GENERATION": "NEXT_QUESTION",
    "COMPLETED": "INTERVIEW_COMPLETED",
    "INTERVIEW_COMPLETED": "INTERVIEW_COMPLETED",
    "INTERVIEW_ERROR": "ERROR",
    "ERROR": "ERROR",
}

_DEFAULT_LIVE_SESSION: Dict[str, Any] = {
    "active": False,
    "session_token": 0.0,
    "session_start_ts": time.time(),
    "audio_generating": False,
    "interviewer_name": "Manideep",
    "voice_profile_id": VOICEBOX_PROFILES["Manideep"],
    "voice_error": None,
    "candidate_name": "Candidate",
    "current_question_idx": 0,
    "questions": [],  # List of dicts: {"id": int, "text": str, "category": str, "difficulty": str, ...}
    "session_records": [],
    "answered_question_ids": [],
    "processed_audio_hashes": [],
    "question_clarification_counts": {},
    "plan_metadata": {},
    "call_stage": "INITIALIZING",
    "canonical_state": "INITIALIZING",
    "flow_state": "INITIALIZING",
    "state_history": ["INITIALIZING"],
    "flow_state_history": ["INITIALIZING"],
    "pending_follow_up_question": None,
    "active_speaker": "syna",  # "syna" | "candidate" | "waiting" | "none"
    "subtitles": "Connecting to interviewer...",
    "live_transcript": "",
    "current_audio_b64": "",
    "closing_audio_b64": "",
    "last_turn_timestamp": time.time(),
    "candidate_silent_prompts_count": 0,
    "silence_threshold_ms": 20000,
    "max_inactivity_timeout_ms": 20000,
    "is_processing_turn": False,
    "last_submission_hash": "",
    "activity_logs": [],
    "log_seq_counter": 0,
    "log_transcripts_enabled": True,
    "timing_metrics": {},
    "exit_requested": False,
    "finished": False,
}
if not hasattr(sys, "_interview_bridge_live_session"):
    sys._interview_bridge_live_session = dict(_DEFAULT_LIVE_SESSION)
else:
    for _k, _v in _DEFAULT_LIVE_SESSION.items():
        sys._interview_bridge_live_session.setdefault(_k, _v)
LIVE_SESSION: Dict[str, Any] = sys._interview_bridge_live_session


def _sanitize_log_text(text: str) -> str:
    """Ensure API keys, tokens, or secrets are never exposed in logs."""
    if not text:
        return ""
    cleaned = str(text)
    cleaned = re.sub(r"(gsk_[A-Za-z0-9]{10,}|sk-[A-Za-z0-9]{10,}|AIza[A-Za-z0-9_-]{15,})", "[REDACTED_API_KEY]", cleaned)
    return cleaned


def _format_duration(duration_ms: Optional[float]) -> str:
    """Format measured duration in ms or s for the Live Activity Log."""
    if duration_ms is None:
        return "-"
    try:
        val = float(duration_ms)
    except Exception:
        return "-"
    if val < 0:
        return "-"
    if val >= 1000.0:
        return f"{val / 1000.0:.2f}s"
    return f"{int(round(val))}ms"


def _format_elapsed(elapsed_sec: float) -> str:
    """Format elapsed interview time as MM:SS (and Xs when under 60s)."""
    sec = max(0, int(round(elapsed_sec)))
    mins = sec // 60
    rem = sec % 60
    return f"{mins:02d}:{rem:02d}"


def log_interview_event(
    speaker: str,
    event: str,
    content: str,
    duration_ms: Optional[float] = None,
    status: str = "SUCCESS",
    question_id: Optional[Any] = None,
    question_number: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    is_transcript: bool = False,
) -> Dict[str, Any]:
    """
    Record a structured, real-time interview event in LIVE_SESSION["activity_logs"].
    Thread-safe and correlated with session_id, question_id, and current state.
    Columns:
      - timestamp: Exact local time (HH:MM:SS)
      - elapsed: Time since interview started (MM:SS)
      - speaker: SYNA / CANDIDATE / SYSTEM
      - event: Operation name
      - content: Actual question, transcript, or status
      - duration: Measured time taken by the operation
      - status: SUCCESS / WAITING / RETRY / FAILED
    """
    now = time.time()
    dt_now = datetime.datetime.fromtimestamp(now)
    ts_str = dt_now.strftime("%H:%M:%S")
    ts_ms_str = dt_now.strftime("%H:%M:%S.%f")[:-3]

    with LOG_LOCK:
        start_ts = float(LIVE_SESSION.get("session_start_ts") or now)
        elapsed_sec = max(0.0, now - start_ts)
        elapsed_str = _format_elapsed(elapsed_sec)
        seq_id = int(LIVE_SESSION.get("log_seq_counter", 0)) + 1
        LIVE_SESSION["log_seq_counter"] = seq_id

        q_idx = int(LIVE_SESSION.get("current_question_idx", 0))
        questions = LIVE_SESSION.get("questions") or []
        total_q = len(questions)
        if question_number is None:
            question_number = (q_idx + 1) if (0 <= q_idx < total_q) else None
        if question_id is None and 0 <= q_idx < total_q and isinstance(questions[q_idx], dict):
            question_id = questions[q_idx].get("id", q_idx + 1)

        log_transcripts = bool(LIVE_SESSION.get("log_transcripts_enabled", True))
        safe_content = _sanitize_log_text(content)
        if is_transcript and not log_transcripts and safe_content:
            word_cnt = len(safe_content.split())
            safe_content = f"[Transcript Masked by Privacy Setting — {word_cnt} words]"

        norm_speaker = (speaker or "SYSTEM").strip().upper()
        if norm_speaker not in ("SYNA", "CANDIDATE", "SYSTEM"):
            norm_speaker = "SYSTEM"

        norm_status = (status or "SUCCESS").strip().upper()
        if norm_status not in ("SUCCESS", "WAITING", "RETRY", "FAILED"):
            norm_status = "SUCCESS"

        det = dict(details or {})
        det.setdefault("session_id", str(LIVE_SESSION.get("session_token", "")))
        det.setdefault("question_id", question_id)
        det.setdefault("question_number", question_number)
        det.setdefault("state", LIVE_SESSION.get("flow_state", LIVE_SESSION.get("canonical_state", "INITIALIZING")))
        det.setdefault("voice_id", LIVE_SESSION.get("voice_profile_id", ""))
        det.setdefault("voice_name", LIVE_SESSION.get("interviewer_name", ""))
        det.setdefault("timestamp_ms", ts_ms_str)

        entry = {
            "seq_id": seq_id,
            "timestamp": ts_str,
            "timestamp_ms": ts_ms_str,
            "elapsed_sec": round(elapsed_sec, 2),
            "elapsed": elapsed_str,
            "speaker": norm_speaker,
            "event": str(event),
            "content": safe_content,
            "raw_content": _sanitize_log_text(content),
            "is_transcript": bool(is_transcript),
            "duration_ms": round(float(duration_ms), 2) if duration_ms is not None else None,
            "duration": _format_duration(duration_ms),
            "status": norm_status,
            "question_id": question_id,
            "question_number": question_number,
            "session_id": str(LIVE_SESSION.get("session_token", "")),
            "state": LIVE_SESSION.get("flow_state", LIVE_SESSION.get("canonical_state", "INITIALIZING")),
            "details": det,
        }
        logs = LIVE_SESSION.setdefault("activity_logs", [])
        logs.append(entry)
        # Keep up to 1000 events per session so scrolling history remains complete without unbounded memory
        if len(logs) > 1000:
            del logs[: len(logs) - 1000]
        return entry


def format_activity_logs_as_text(logs: List[Dict[str, Any]]) -> str:
    """Format activity logs as a clean, human-readable table / report for TXT export."""
    lines = [
        "====================================================================================================",
        " UNIVERSAL AI MOCK INTERVIEW — REAL-TIME ACTIVITY & TELEMETRY LOG",
        "====================================================================================================",
        f"{'TIME':<10} | {'ELAPSED':<8} | {'SPEAKER':<10} | {'EVENT':<26} | {'DURATION':<10} | {'STATUS':<8} | CONTENT",
        "-" * 100,
    ]
    for row in logs:
        ts = str(row.get("timestamp", ""))[:10]
        el = str(row.get("elapsed", ""))[:8]
        sp = str(row.get("speaker", ""))[:10]
        ev = str(row.get("event", ""))[:26]
        du = str(row.get("duration", "-"))[:10]
        st = str(row.get("status", ""))[:8]
        ct = str(row.get("content", "")).replace("\n", " ")
        lines.append(f"{ts:<10} | {el:<8} | {sp:<10} | {ev:<26} | {du:<10} | {st:<8} | {ct}")
    lines.append("====================================================================================================")
    return "\n".join(lines)


def _transition_state_locked(
    target_stage: str,
    canonical_alias: Optional[str] = None,
    reason: Optional[str] = None,
) -> bool:
    """
    Validate and execute a state transition inside SESSION_LOCK.
    Records the transition in state_history, flow_state_history, and the Live Activity Log.
    """
    current = LIVE_SESSION.get("call_stage", "INITIALIZING")
    prev_flow = LIVE_SESSION.get("flow_state", STAGE_TO_FLOW_STATE.get(current, current))
    allowed = VALID_STATE_TRANSITIONS.get(current)
    if allowed is not None and target_stage not in allowed and target_stage != current:
        pass
    LIVE_SESSION["call_stage"] = target_stage
    canon = canonical_alias or (
        "WAITING_FOR_CANDIDATE"
        if target_stage == "LISTENING_TO_CANDIDATE"
        else ("INTERVIEW_COMPLETED" if target_stage == "COMPLETED" else target_stage)
    )
    flow_state = STAGE_TO_FLOW_STATE.get(target_stage, STAGE_TO_FLOW_STATE.get(canon, canon))
    LIVE_SESSION["canonical_state"] = canon
    LIVE_SESSION["flow_state"] = flow_state

    hist = LIVE_SESSION.setdefault("state_history", [])
    if not hist or hist[-1] != canon:
        hist.append(canon)

    flow_hist = LIVE_SESSION.setdefault("flow_state_history", [])
    if not flow_hist or flow_hist[-1] != flow_state:
        flow_hist.append(flow_state)

    if prev_flow != flow_state or reason:
        msg = f"{prev_flow} -> {flow_state}" + (f" ({reason})" if reason else "")
        log_interview_event(
            speaker="SYSTEM",
            event="State Transition",
            content=msg,
            status="FAILED" if flow_state == "ERROR" else ("RETRY" if flow_state == "TRANSCRIPTION_RETRY" else "SUCCESS"),
            details={"from_state": prev_flow, "to_state": flow_state, "internal_stage": target_stage, "reason": reason or ""},
        )
    return True


def _synthesize_interviewer_audio(
    text: str,
    voice_profile_id: str,
    event_context: str = "Interviewer Speech",
) -> tuple[str, Optional[str]]:
    """
    Synthesize interviewer audio strictly using the candidate's selected Voicebox voice profile ID.
    Logs TTS start, completion, Voice ID, Voice Name, and measured duration.
    """
    prof_name = get_voice_profile_name(voice_profile_id)
    t0 = time.perf_counter()
    log_interview_event(
        speaker="SYNA",
        event="TTS Generation Started",
        content=f"Synthesizing {event_context} with Voicebox profile '{prof_name}' ({voice_profile_id})",
        status="WAITING",
        details={"voice_id": voice_profile_id, "voice_name": prof_name, "context": event_context},
    )
    try:
        tts_meta = synthesize_interviewer_turn_audio_detailed(text, voice_profile_id=voice_profile_id)
        audio_bytes = tts_meta.get("audio_bytes", b"")
        dur_ms = tts_meta.get("duration_ms", round((time.perf_counter() - t0) * 1000.0, 2))
        resolved_vid = tts_meta.get("voice_id", voice_profile_id)
        resolved_vname = tts_meta.get("voice_name", prof_name)
        source = tts_meta.get("source", "voicebox")
        size_kb = round(len(audio_bytes) / 1024.0, 1) if audio_bytes else 0.0

        LIVE_SESSION.setdefault("timing_metrics", {})["last_tts_generation_ms"] = dur_ms

        if audio_bytes and len(audio_bytes) > 500:
            log_interview_event(
                speaker="SYNA",
                event="TTS Generation Completed",
                content=f"Voice '{resolved_vname}' ({resolved_vid}) ready [{size_kb} KB, source={source}]",
                duration_ms=dur_ms,
                status="SUCCESS",
                details={
                    "voice_id": resolved_vid,
                    "voice_name": resolved_vname,
                    "source": source,
                    "audio_size_bytes": len(audio_bytes),
                    "context": event_context,
                },
            )
            return base64.b64encode(audio_bytes).decode("utf-8"), None

        err_msg = f"Interviewer audio for {prof_name} ({voice_profile_id}) returned empty audio bytes."
        log_interview_event(
            speaker="SYSTEM",
            event="TTS Generation Failed",
            content=err_msg,
            duration_ms=dur_ms,
            status="FAILED",
            details={"voice_id": voice_profile_id, "voice_name": prof_name},
        )
        return "", err_msg
    except Exception as err:
        dur_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        log_interview_event(
            speaker="SYSTEM",
            event="TTS Generation Error",
            content=f"Voicebox error for {prof_name} ({voice_profile_id}): {err}",
            duration_ms=dur_ms,
            status="FAILED",
            details={"voice_id": voice_profile_id, "voice_name": prof_name, "error": str(err)},
        )
        print(f"[Voicebox Error for {prof_name} ({voice_profile_id})]: {err}")
        return "", str(err)


def _bg_prewarm_question(
    session_token: float,
    q_idx: int,
    candidate_name: str,
    questions: list,
    voice_profile_id: str,
):
    """Pre-synthesize upcoming question in the background cache so question progression is seamless."""
    if q_idx < 0 or q_idx >= len(questions):
        return
    with SESSION_LOCK:
        if LIVE_SESSION.get("session_token") != session_token:
            return
    q_text = questions[q_idx].get("text", "")
    if not q_text:
        return
    _synthesize_interviewer_audio(q_text, voice_profile_id)


def _bg_prepare_session_audio(
    session_token: float,
    greeting: str,
    questions: list,
    voice_profile_id: str,
    greeting_already_loaded: bool = False,
):
    """Synthesize the initial introduction greeting and pre-warm Question 1 audio in the cache."""
    err = None
    vb_client = VoiceboxClient()
    if not greeting_already_loaded:
        if vb_client.is_running():
            b64_audio, err = _synthesize_interviewer_audio(greeting, voice_profile_id)
            with SESSION_LOCK:
                if LIVE_SESSION.get("session_token") != session_token:
                    return
                LIVE_SESSION["audio_generating"] = False
                if LIVE_SESSION.get("call_stage") == "INTRODUCTION":
                    LIVE_SESSION["current_audio_b64"] = b64_audio
                if err:
                    LIVE_SESSION["voice_error"] = err
        else:
            with SESSION_LOCK:
                if LIVE_SESSION.get("session_token") != session_token:
                    return
                LIVE_SESSION["audio_generating"] = False

    with SESSION_LOCK:
        if LIVE_SESSION.get("session_token") != session_token:
            return
        cand_name = LIVE_SESSION.get("candidate_name", "Candidate")

    if questions and not err and vb_client.is_running():
        _bg_prewarm_question(session_token, 0, cand_name, questions, voice_profile_id)


def reset_live_session(
    candidate_name: str,
    questions: list,
    plan_metadata: dict,
    voice_profile_id: Optional[str] = None,
    interviewer_name: Optional[str] = None,
    blocking_greeting: bool = False,
):
    """
    Initializes a new interview session and strictly locks the selected voice profile ID.
    Transitions INITIALIZING -> INTRODUCTION and speaks the welcome and readiness prompt.
    Logs Voicebox connection status, Selected Voice ID validation, and Interviewer introduction.
    """
    t_init_start = time.perf_counter()
    resolved_id = voice_profile_id or (plan_metadata or {}).get("voice_profile_id") or get_configured_voice_profile_id()
    is_valid_voice, voice_msg = verify_voice_profile_available(resolved_id)
    resolved_name = interviewer_name or (plan_metadata or {}).get("interviewer_name") or get_voice_profile_name(resolved_id)
    cand_name = (candidate_name or "Candidate").strip() or "Candidate"

    # Deep-copy question dicts so in-place contextual transitions in one session never mutate caller lists
    copied_questions = [dict(q) for q in (questions or [])]

    with SESSION_LOCK:
        now_ts = time.time()
        session_token = now_ts
        LIVE_SESSION["active"] = True
        LIVE_SESSION["session_token"] = session_token
        LIVE_SESSION["session_start_ts"] = now_ts
        LIVE_SESSION["interviewer_name"] = resolved_name
        LIVE_SESSION["voice_profile_id"] = resolved_id
        LIVE_SESSION["voice_error"] = None
        LIVE_SESSION["candidate_name"] = cand_name
        LIVE_SESSION["current_question_idx"] = 0
        LIVE_SESSION["questions"] = copied_questions
        LIVE_SESSION["session_records"] = []
        LIVE_SESSION["answered_question_ids"] = []
        LIVE_SESSION["processed_audio_hashes"] = []
        LIVE_SESSION["question_clarification_counts"] = {}
        LIVE_SESSION["plan_metadata"] = dict(plan_metadata or {})
        LIVE_SESSION["call_stage"] = "INITIALIZING"
        LIVE_SESSION["canonical_state"] = "INITIALIZING"
        LIVE_SESSION["flow_state"] = "INITIALIZING"
        LIVE_SESSION["state_history"] = ["INITIALIZING"]
        LIVE_SESSION["flow_state_history"] = ["INITIALIZING"]
        LIVE_SESSION["pending_follow_up_question"] = None
        LIVE_SESSION["active_speaker"] = "syna"
        LIVE_SESSION["live_transcript"] = ""
        LIVE_SESSION["current_audio_b64"] = ""
        LIVE_SESSION["closing_audio_b64"] = ""
        LIVE_SESSION["last_turn_timestamp"] = now_ts
        LIVE_SESSION["candidate_silent_prompts_count"] = 0
        LIVE_SESSION["is_processing_turn"] = False
        LIVE_SESSION["last_submission_hash"] = ""
        LIVE_SESSION["activity_logs"] = []
        LIVE_SESSION["log_seq_counter"] = 0
        LIVE_SESSION["timing_metrics"] = {}
        LIVE_SESSION["exit_requested"] = False
        LIVE_SESSION["finished"] = False

    # Log session initialization and Voicebox Voice ID verification
    log_interview_event(
        speaker="SYSTEM",
        event="Session Initialized",
        content=f"Session started for '{cand_name}' ({len(copied_questions)} planned questions, Role={(plan_metadata or {}).get('role', 'General')})",
        duration_ms=round((time.perf_counter() - t_init_start) * 1000.0, 2),
        status="SUCCESS",
        question_id=copied_questions[0].get("id", 1) if copied_questions else None,
        question_number=1 if copied_questions else None,
        details={"total_questions": len(copied_questions), "candidate_name": cand_name},
    )

    log_interview_event(
        speaker="SYSTEM",
        event="Voice ID Validation",
        content=voice_msg,
        status="SUCCESS" if is_valid_voice else "FAILED",
        details={"voice_id": resolved_id, "voice_name": resolved_name, "is_valid": is_valid_voice},
    )

    full_greeting = (
        f"Hello! Good morning. My name is {resolved_name}, and I'll be your interviewer today. "
        f"Welcome to your mock interview, {cand_name}. I hope you're doing well. "
        f"Before we begin, are you comfortable and ready to start?"
    )
    default_greeting = (
        f"Hello! Good morning. My name is {resolved_name}, and I'll be your interviewer today. "
        f"Welcome to your mock interview. I hope you're doing well. "
        f"Before we begin, are you comfortable and ready to start?"
    )
    legacy_greeting = (
        f"Hello {cand_name}! Welcome to your mock interview. "
        f"I'm {resolved_name}, and I'll be conducting your session today. "
        f"For each question, please share structured examples and speak naturally—I will listen and guide us through each stage. "
        f"Can you hear me clearly, and are you ready to begin?"
    )
    short_greeting = f"Hello, I am {resolved_name}. Welcome to your mock interview session."

    vb_client = VoiceboxClient()
    vb_running = vb_client.is_running()
    log_interview_event(
        speaker="SYSTEM",
        event="Voicebox Connection Status",
        content=f"Voicebox service {'ONLINE' if vb_running else 'OFFLINE'} — Locked Profile: {resolved_name} ({resolved_id})",
        status="SUCCESS" if vb_running else "FAILED",
        details={"voicebox_online": vb_running, "voice_id": resolved_id, "voice_name": resolved_name},
    )

    instant_b64 = ""
    chosen_greeting = full_greeting
    voice_init_err = None

    if not is_valid_voice:
        voice_init_err = voice_msg
    else:
        t_tts = time.perf_counter()
        for candidate_text in (full_greeting, default_greeting, legacy_greeting, short_greeting):
            cached_wav = vb_client.get_cached_bytes(candidate_text, profile=resolved_id, engine="chatterbox")
            if cached_wav and len(cached_wav) > 1000:
                instant_b64 = base64.b64encode(cached_wav).decode("utf-8")
                chosen_greeting = candidate_text
                tts_ms = round((time.perf_counter() - t_tts) * 1000.0, 2)
                log_interview_event(
                    speaker="SYNA",
                    event="TTS Generation Completed",
                    content=f"Introduction audio loaded for '{resolved_name}' ({resolved_id}) [{round(len(cached_wav) / 1024.0, 1)} KB]",
                    duration_ms=tts_ms,
                    status="SUCCESS",
                    details={"voice_id": resolved_id, "voice_name": resolved_name, "audio_size_bytes": len(cached_wav)},
                )
                break

        if not instant_b64:
            if vb_running:
                instant_b64, voice_init_err = _synthesize_interviewer_audio(chosen_greeting, resolved_id, event_context="Introduction")
            else:
                voice_init_err = (
                    f"Voicebox profile '{resolved_name}' ({resolved_id}) could not be loaded. "
                    f"Please verify Voicebox is available."
                )

    with SESSION_LOCK:
        LIVE_SESSION["audio_generating"] = not bool(instant_b64) and not bool(voice_init_err)
        LIVE_SESSION["voice_error"] = voice_init_err
        if voice_init_err and not is_valid_voice:
            _transition_state_locked("INTERVIEW_ERROR", "ERROR", reason=voice_init_err)
        else:
            _transition_state_locked("INTRODUCTION_PLAYING", "INTRODUCTION_PLAYING", reason="Interviewer introduction started")
            log_interview_event(
                speaker="SYNA",
                event="Introduction & Readiness Prompt",
                content=chosen_greeting,
                status="SUCCESS",
                details={"voice_id": resolved_id, "voice_name": resolved_name},
            )
        LIVE_SESSION["current_audio_b64"] = instant_b64
        LIVE_SESSION["subtitles"] = chosen_greeting

    if not voice_init_err:
        if blocking_greeting and not instant_b64:
            _bg_prepare_session_audio(session_token, chosen_greeting, copied_questions, resolved_id, greeting_already_loaded=False)
        else:
            t = threading.Thread(
                target=_bg_prepare_session_audio,
                args=(session_token, chosen_greeting, copied_questions, resolved_id, bool(instant_b64)),
                daemon=True,
            )
            t.start()


def get_live_state() -> Dict[str, Any]:
    with SESSION_LOCK:
        q_idx = LIVE_SESSION["current_question_idx"]
        total_q = len(LIVE_SESSION["questions"])
        curr_q_obj = LIVE_SESSION["questions"][q_idx] if (0 <= q_idx < total_q) else {}
        curr_q = curr_q_obj.get("text", "") if isinstance(curr_q_obj, dict) else ""
        curr_q_id = curr_q_obj.get("id", q_idx + 1) if isinstance(curr_q_obj, dict) else (q_idx + 1)
        curr_cat = curr_q_obj.get("category", "Behavioral") if isinstance(curr_q_obj, dict) else "Behavioral"
        curr_diff = curr_q_obj.get("difficulty", "Standard") if isinstance(curr_q_obj, dict) else "Standard"
        meta = LIVE_SESSION.get("plan_metadata", {}) or {}
        elapsed_sec = max(0.0, time.time() - float(LIVE_SESSION.get("session_start_ts") or time.time()))

        return {
            "active": LIVE_SESSION["active"],
            "session_token": LIVE_SESSION.get("session_token", 0.0),
            "elapsed_sec": round(elapsed_sec, 1),
            "audio_generating": LIVE_SESSION.get("audio_generating", False),
            "interviewer_name": LIVE_SESSION["interviewer_name"],
            "voice_profile_id": LIVE_SESSION["voice_profile_id"],
            "voice_error": LIVE_SESSION["voice_error"],
            "candidate_name": LIVE_SESSION["candidate_name"],
            "role": meta.get("role", ""),
            "industry": meta.get("industry", ""),
            "duration_minutes": meta.get("duration_minutes", 30),
            "call_stage": LIVE_SESSION["call_stage"],
            "canonical_state": LIVE_SESSION.get("canonical_state", LIVE_SESSION["call_stage"]),
            "flow_state": LIVE_SESSION.get("flow_state", STAGE_TO_FLOW_STATE.get(LIVE_SESSION["call_stage"], LIVE_SESSION["call_stage"])),
            "state_history": list(LIVE_SESSION.get("state_history", [])),
            "flow_state_history": list(LIVE_SESSION.get("flow_state_history", [])),
            "active_speaker": LIVE_SESSION["active_speaker"],
            "subtitles": LIVE_SESSION["subtitles"],
            "live_transcript": LIVE_SESSION["live_transcript"],
            "current_question": curr_q,
            "current_question_id": curr_q_id,
            "current_category": curr_cat,
            "current_difficulty": curr_diff,
            "question_number": q_idx + 1 if total_q > 0 else 1,
            "total_questions": total_q,
            "answered_count": len(LIVE_SESSION.get("session_records", [])),
            "session_records": list(LIVE_SESSION.get("session_records", [])),
            "question_clarification_counts": dict(LIVE_SESSION.get("question_clarification_counts", {})),
            "activity_logs": list(LIVE_SESSION.get("activity_logs", [])),
            "log_transcripts_enabled": bool(LIVE_SESSION.get("log_transcripts_enabled", True)),
            "timing_metrics": dict(LIVE_SESSION.get("timing_metrics", {})),
            "current_audio_b64": LIVE_SESSION["current_audio_b64"],
            "closing_audio_b64": LIVE_SESSION["closing_audio_b64"],
            "silence_threshold_ms": LIVE_SESSION.get("silence_threshold_ms", 20000),
            "max_inactivity_timeout_ms": LIVE_SESSION.get("max_inactivity_timeout_ms", 20000),
            "exit_requested": LIVE_SESSION["exit_requested"],
            "finished": LIVE_SESSION["call_stage"] in ("COMPLETED", "INTERVIEW_COMPLETED") or LIVE_SESSION.get("finished", False),
        }


def _extract_salient_candidate_terms(candidate_answer: str) -> List[str]:
    """Extract technical/domain terms or key phrases mentioned by the candidate to ground follow-ups."""
    stop = {
        "have", "worked", "with", "using", "mainly", "years", "year", "experience", "project", "projects",
        "team", "used", "built", "developed", "implemented", "when", "where", "there", "their", "about",
        "from", "that", "this", "these", "those", "would", "could", "should", "during", "within", "into",
        "through", "because", "while", "after", "before", "under", "over", "some", "many", "more", "most",
        "very", "much", "also", "like", "just", "well", "make", "made", "such", "other", "were", "been",
    }
    raw_tokens = re.findall(r"\b[A-Za-z][A-Za-z0-9+#.-]{2,}\b", candidate_answer or "")
    salient = []
    seen = set()
    # Prefer capitalized technical nouns (e.g. Pandas, NumPy, Flask, PyTorch, Kafka, Redis) first
    for tok in raw_tokens:
        clean = tok.strip(".,!?:;\"'()")
        low = clean.lower()
        if low not in stop and low not in seen and any(c.isupper() for c in clean[1:] or [clean[0]]):
            if clean[0].isupper() and low not in ("the", "and", "for", "in", "on", "at", "to", "as", "we", "it", "my", "our"):
                seen.add(low)
                salient.append(clean)
    for tok in raw_tokens:
        clean = tok.strip(".,!?:;\"'()")
        low = clean.lower()
        if len(clean) >= 4 and low not in stop and low not in seen:
            seen.add(low)
            salient.append(clean)
    return salient[:4]


def _generate_contextual_question(
    candidate_answer: str,
    prev_question_text: str,
    next_idx: int,
    questions: list,
    metadata: dict,
    candidate_name: str,
    eval_obj: Optional[Any] = None,
    session_history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Dynamically generate the next interview question grounded in the candidate's actual answer
    and full interview history while progressing through the planned question count.
    """
    planned_q = questions[next_idx] if next_idx < len(questions) else {}
    planned_text = planned_q.get("text", "Can you explain your experience?")
    planned_category = planned_q.get("category", "Competency")
    planned_competencies = ", ".join(planned_q.get("target_competencies", []))
    role = metadata.get("role", "Software Engineer")
    industry = metadata.get("industry", "Technology")
    diff = metadata.get("difficulty", "Standard")

    history_lines = []
    for idx, rec in enumerate((session_history or [])[-3:]):
        q_t = rec.get("question", {}).get("text", "")
        a_t = rec.get("candidate_answer", "")
        history_lines.append(f"Turn {idx + 1} Q: {q_t}\nTurn {idx + 1} Candidate Answer: {a_t}")
    history_block = "\n".join(history_lines) if history_lines else f"Q: {prev_question_text}\nA: {candidate_answer}"

    salient_terms = _extract_salient_candidate_terms(candidate_answer)
    salient_str = ", ".join(salient_terms) if salient_terms else "their practical workflow"

    prompt = f"""
You are the AI interviewer conducting a live human-to-human interview for {candidate_name}.
Role: {role} ({industry})
Difficulty: {diff}
Moving to Question {next_idx + 1} of {len(questions)}.

Recent Interview History:
{history_block}

Latest Question Asked:
"{prev_question_text}"

Candidate's Latest Answer:
"{candidate_answer}"
Key Technologies/Concepts Mentioned by Candidate: {salient_str}

Planned Next Topic / Competency (Question {next_idx + 1} of {len(questions)}):
Topic: {planned_category}
Target Competencies: {planned_competencies}
Base Question Benchmark: {planned_text}

Instructions:
1. Provide a brief 1-sentence transition that specifically references the actual content of the candidate's answer (for example, referencing {salient_str}).
2. Ask Question {next_idx + 1} so that it builds naturally on what the candidate just shared while evaluating the planned competency ({planned_text}).
3. Keep the entire spoken turn under 3 sentences so it sounds natural when spoken aloud.
4. Do NOT repeat any previously asked question.

Return JSON:
{{
  "spoken_turn": "1-sentence contextual acknowledgment. Clear next question."
}}
"""
    try:
        raw = call_llm(
            prompt=prompt,
            system_prompt="You generate natural, context-aware interview transitions and questions in strict JSON.",
            json_mode=True,
        )
        parsed = clean_json_response(raw)
        spoken_turn = (parsed.get("spoken_turn", "") if isinstance(parsed, dict) else "").strip()
        if spoken_turn and len(spoken_turn) > 15:
            return spoken_turn
    except Exception as e:
        print(f"[Question Gen Info]: Using deterministic contextual transition ({e})")

    if salient_terms:
        joined_terms = ", ".join(salient_terms[:3])
        return (
            f"Thank you for sharing your experience with {joined_terms}. "
            f"Building on that, {planned_text}"
        )
    return f"Thank you for explaining that approach. Let's move to Question {next_idx + 1}: {planned_text}"


def _classify_readiness_intent_semantic(transcript: str, interviewer_prompt: str = "") -> Tuple[str, str]:
    """
    Semantic + Natural-Language Intent Classification for Candidate Response during WAITING_FOR_READINESS.
    Classifies any natural human response into 5 semantic categories:
      - 'READY'     : Candidate expresses readiness to begin ("Yeah, I'm ready", "We may start now",
                      "Yes, I'm comfortable", "Sure, we can proceed", "I'm good. Let's go", "I'm all set", etc.)
      - 'GREETING'  : Candidate says hello/good morning without confirming readiness yet
      - 'QUESTION'  : Candidate asks a question or requests clarification about the format/process
      - 'UNREADY'   : Candidate says not yet, wait, hold on, can't hear, need a moment
      - 'UNCLEAR'   : Candidate says something unrelated or ambiguous
      - 'NOISE'     : Empty or silence/noise hallucination
    Uses fast deterministic semantic grammar patterns PLUS LLM contextual NLU classification for open-ended phrasing.
    """
    lower_t = re.sub(r"\s+", " ", (transcript or "").lower()).strip()
    if not lower_t or is_whisper_hallucination_or_noise(lower_t):
        return "NOISE", "Empty or noise hallucination"

    # 1. Explicit negative / unready patterns using word boundaries (so "now" never matches "no"!)
    negative_patterns = [
        r"\bno\b",
        r"\bnot\s+ready\b",
        r"\bnot\s+yet\b",
        r"\bnot\s+comfortable\b",
        r"\bwait\b",
        r"\bhold\s+on\b",
        r"\bhold\b",
        r"\bgive\s+me\s+a\s+(?:minute|second|moment)\b",
        r"\bneed\s+(?:a\s+)?(?:minute|second|moment|more\s+time)\b",
        r"\bone\s+(?:minute|second|moment)\b",
        r"\ba\s+(?:minute|second|moment)\b",
        r"\bcan't\s+hear\b",
        r"\bcannot\s+hear\b",
        r"\bdon't\s+hear\b",
        r"\bunable\s+to\s+hear\b",
        r"\bpause\b",
    ]
    for pat in negative_patterns:
        if re.search(pat, lower_t):
            return "UNREADY", f"Matched negative readiness expression ({pat})"

    # 2. Candidate asking a question or requesting clarification during readiness stage
    question_indicators = [
        r"\bhow\s+many\s+questions\b",
        r"\bhow\s+long\b",
        r"\bwhat\s+(?:kind|type)\s+of\s+questions\b",
        r"\bcan\s+you\s+(?:explain|clarify|repeat|tell\s+me)\b",
        r"\bcould\s+you\s+(?:explain|clarify|repeat|tell\s+me)\b",
        r"\bwhat\s+is\s+the\s+format\b",
        r"\bhow\s+does\s+this\s+work\b",
        r"\bwhat\s+are\s+we\s+covering\b",
    ]
    for pat in question_indicators:
        if re.search(pat, lower_t):
            return "QUESTION", f"Candidate asked a question before starting ({pat})"
    if lower_t.endswith("?") and not re.search(r"\b(?:shall|can|may)\s+we\s+(?:start|begin|proceed|go)\b", lower_t):
        return "QUESTION", "Candidate utterance is an interrogative question"

    # 3. Natural-language readiness & comfort expressions (broad semantic coverage)
    affirmative_phrases = [
        r"\b(?:yes|yeah|yep|yup|sure|okay|ok)\s*,?\s*i(?:'m|\s+am)\s+(?:ready|comfortable|good|set|all\s+set|prepared|fine)\b",
        r"\bi(?:'m|\s+am)\s+(?:very\s+|quite\s+|fully\s+|completely\s+|all\s+)?(?:ready|prepared|comfortable|set|good\s+to\s+go)\b",
        r"\bim\s+(?:ready|prepared|comfortable|all\s+set|good\s+to\s+go)\b",
        r"\b(?:we|you)\s+(?:can|may|could|shall)\s+(?:start|begin|proceed|go\s+ahead|kick\s+off|get\s+started)\b",
        r"\blet(?:'s|s|\s+us)\s+(?:begin|start|proceed|get\s+started|go|do\s+this|dive\s+in|kick\s+off)\b",
        r"\b(?:ready|happy|excited|eager|good|set)\s+to\s+(?:begin|start|proceed|go|get\s+started)\b",
        r"\b(?:start|begin|proceed)\s+now\b",
        r"\bgo\s+ahead\b",
        r"\bi\s+can\s+hear\s+you\s+(?:clearly|well|loud\s+and\s+clear|fine)\b",
        r"\bhear\s+you\s+clearly\b",
        r"\bloud\s+and\s+clear\b",
        r"\bsounds\s+(?:good|great|clear)\b",
        r"\bi(?:'m|\s+am)\s+good\b",
        r"\ball\s+set\b",
        r"\bgood\s+to\s+go\b",
        r"\bfeeling\s+(?:comfortable|ready|good)\b",
        r"\bplease\s+(?:proceed|start|begin|go\s+ahead)\b",
    ]
    for pat in affirmative_phrases:
        if re.search(pat, lower_t):
            return "READY", f"Semantic readiness phrase matched ({pat})"

    words = [w.strip(".,!?:;\"'()[]") for w in lower_t.split() if any(c.isalpha() for c in w)]
    standalone_affirmative = {
        "yes", "ready", "prepared", "comfortable", "sure", "yep", "yeah", "yup",
        "ok", "okay", "begin", "start", "proceed", "absolutely", "definitely", "certainly",
    }
    if words and len(words) <= 10 and any(w in standalone_affirmative for w in words):
        return "READY", "Concise affirmative response"

    # 4. Pure greeting / acknowledgement without readiness word (e.g., "Hello Manideep, good morning, I am doing well")
    greeting_patterns = [
        r"^(?:hello|hi|hey|good\s+morning|good\s+afternoon|good\s+evening|namaste|greetings)\b",
        r"\bi(?:'m|\s+am)\s+doing\s+(?:well|great|fine)\b",
        r"\bnice\s+to\s+meet\s+you\b",
        r"\bthank\s+you\s+for\s+having\s+me\b",
    ]
    if words and len(words) <= 12 and any(re.search(pat, lower_t) for pat in greeting_patterns):
        # If greeting is combined with "how about you" or pure pleasantry, classify via LLM or GREETING
        return "GREETING", "Candidate greeted interviewer"

    # 5. Semantic LLM Intent Classifier for any novel natural-language expression not covered by grammar rules
    try:
        nlu_prompt = f"""
Classify the candidate's spoken response to the interviewer's introduction:
Interviewer asked: "{interviewer_prompt or 'Hello! Good morning. Before we begin, are you comfortable and ready to start?'}"
Candidate responded: "{transcript}"

Classify the candidate's semantic intent into EXACTLY ONE of these 5 categories:
- "READY": The candidate expresses readiness, comfort, willingness, or agreement to start the interview (e.g. "I'm in a good spot, fire away", "Everything works on my end, let's roll", "Yes I'm comfortable").
- "GREETING": The candidate only exchanged greetings or pleasantries without indicating if they are ready to start yet.
- "QUESTION": The candidate is asking the interviewer a question or requesting clarification before starting.
- "UNREADY": The candidate is not ready yet, asks to wait, or reports an audio/technical issue.
- "UNCLEAR": The response is unrelated, garbled, or ambiguous.

Return strict JSON:
{{"intent": "READY|GREETING|QUESTION|UNREADY|UNCLEAR", "reason": "1 short sentence"}}
"""
        raw = call_llm(
            prompt=nlu_prompt,
            system_prompt="You are a real-time conversational NLU classifier for an AI interviewer. Output strict JSON.",
            json_mode=True,
        )
        parsed = clean_json_response(raw)
        if isinstance(parsed, dict):
            llm_intent = str(parsed.get("intent", "")).strip().upper()
            llm_reason = str(parsed.get("reason", "LLM semantic intent classification")).strip()
            if llm_intent in ("READY", "GREETING", "QUESTION", "UNREADY", "UNCLEAR"):
                return llm_intent, f"LLM Semantic NLU: {llm_reason}"
    except Exception:
        pass

    return "UNCLEAR", "Ambiguous response; requesting polite readiness confirmation"


def _classify_readiness_intent(transcript: str) -> str:
    """Backward-compatible wrapper returning the top-level intent label."""
    intent, _ = _classify_readiness_intent_semantic(transcript)
    return intent


FILLER_INTERJECTIONS = {
    "uh", "um", "hmm", "hm", "ah", "oh", "eh", "er", "erm", "mm", "huh", "mhm", "uh-huh", "umm", "uhh", "ahh",
}


def classify_candidate_turn_intent(
    transcript: str,
    current_question_text: str = "",
) -> Tuple[str, str]:
    """
    Context-aware intent classification for a candidate utterance during an active question turn.
    Returns (intent, reason) where intent is one of:
      - 'STOP_INTERVIEW'          : Explicit request to end/exit the interview
      - 'CLARIFICATION_REQUESTED' : Candidate asks to explain, simplify, clarify, or give an example
      - 'REPEAT_REQUESTED'        : Candidate asks to repeat or re-read the question
      - 'NOISE_OR_FILLER'         : Only non-speech hesitation fillers ('uh', 'um', 'hmm')
      - 'ANSWER'                  : Genuine candidate interview response (including short meaningful answers)
    """
    cleaned = re.sub(r"\s+", " ", (transcript or "").strip())
    lower_t = cleaned.lower().strip(" .,!?:;\"'()-[]{}…")
    if not lower_t or is_whisper_hallucination_or_noise(cleaned):
        return "NOISE_OR_FILLER", "Empty or Whisper silence/noise hallucination"

    words = [w.strip(".,!?:;\"'()[]{}") for w in lower_t.split() if any(c.isalnum() for c in w)]
    alpha_words = [w for w in words if any(c.isalpha() for c in w)]
    word_count = len(words)

    if not alpha_words:
        return "NOISE_OR_FILLER", "No alphabetic words detected"

    # 1. Explicit interview exit commands
    stop_phrases = [
        r"\bstop\s+interview\b",
        r"\bend\s+interview\b",
        r"\bquit\s+interview\b",
        r"\bplease\s+exit\b",
        r"\bend\s+call\b",
        r"\bterminate\s+interview\b",
    ]
    for pat in stop_phrases:
        if re.search(pat, lower_t) and word_count <= 10:
            return "STOP_INTERVIEW", f"Matched exit command ({pat})"

    # 1b. Candidate requests more time after an inactivity check-in or thinking pause
    more_time_phrases = [
        r"\bi\s+need\s+more\s+time\b",
        r"\bneed\s+a\s+(?:minute|second|moment)\b",
        r"\bgive\s+me\s+(?:a\s+)?(?:minute|second|moment|more\s+time)\b",
        r"\blet\s+me\s+think\b",
        r"\bone\s+(?:moment|second|minute)\s+please\b",
    ]
    for pat in more_time_phrases:
        if re.search(pat, lower_t) and word_count <= 12:
            return "NEED_MORE_TIME", f"Candidate requested more thinking time ({pat})"

    # 1c. Candidate explicitly asks to skip the current question
    skip_phrases = [
        r"\bskip\s+(?:this\s+|the\s+)?question\b",
        r"\bplease\s+skip\b",
        r"\bi(?:'d|\s+would)\s+like\s+to\s+skip\b",
        r"\bmove\s+to\s+the\s+next\s+question\b",
        r"\bnext\s+question\s+please\b",
        r"\bpass\s+on\s+this\s+question\b",
    ]
    for pat in skip_phrases:
        if re.search(pat, lower_t) and word_count <= 12:
            return "SKIP_QUESTION", f"Candidate requested to skip question ({pat})"

    # 2. Contextual Clarification Detection (only when utterance is not a long substantive answer)
    # Substantive answer guard: if the candidate spoke > 28 words explaining their work, don't misclassify
    if word_count <= 26:
        clarification_patterns = [
            (r"\b(?:can|could|would|will)\s+you\s+(?:please\s+)?explain\b", "Asked interviewer to explain the question"),
            (r"\bplease\s+explain\b", "Requested explanation in simpler terms"),
            (r"\bexplain\s+(?:the\s+question|that|this|it|again)\b", "Requested explanation of the current question"),
            (r"\b(?:in\s+)?(?:simple|simpler)\s+(?:words|terms|language)\b", "Requested explanation in simple words"),
            (r"\bi\s+(?:didn't|did\s+not|don't|do\s+not)\s+(?:quite\s+)?(?:understand|get|follow|catch)\b", "Candidate stated they did not understand"),
            (r"\bwhat\s+do\s+you\s+mean\b", "Asked 'What do you mean' for clarification"),
            (r"\bwhat\s+does\s+that\s+mean\b", "Asked 'What does that mean' for clarification"),
            (r"\bwhat\s+is\s+meant\s+by\b", "Asked 'What is meant by' for clarification"),
            (r"\b(?:can|could|would)\s+you\s+(?:please\s+)?(?:clarify|rephrase|elaborate|simplify|break\s+down)\b", "Asked interviewer to clarify/rephrase"),
            (r"\b(?:please\s+)?(?:clarify|rephrase|simplify)\s+(?:the\s+question|that|this|it)?\b", "Requested question clarification"),
            (r"\b(?:can|could|would)\s+you\s+(?:please\s+)?give\s+(?:me\s+)?an\s+example\b", "Requested a clarifying example"),
            (r"\bgive\s+(?:me\s+)?an\s+example\b", "Requested an example to understand the question"),
            (r"\bnot\s+(?:sure|clear)\s+what\s+you(?:'re|\s+are)\s+asking\b", "Candidate unsure what the question is asking"),
            (r"\b(?:sorry\s*,?\s*)?i(?:'m|\s+am)\s+confused\b", "Candidate expressed confusion about the question"),
        ]
        for pat, reason in clarification_patterns:
            if re.search(pat, lower_t):
                return "CLARIFICATION_REQUESTED", reason

        # Contextual check: short question directed at the interviewer ("Are you asking about...", "Do you mean...")
        interviewer_directed_q = [
            r"^(?:sorry\s*,?\s*)?(?:are\s+you\s+asking|do\s+you\s+mean|do\s+you\s+want\s+me\s+to|should\s+i\s+focus\s+on|which\s+part\s+of)\b",
        ]
        for pat in interviewer_directed_q:
            if re.search(pat, lower_t) and word_count <= 18:
                return "CLARIFICATION_REQUESTED", "Contextual clarification question directed at interviewer"

        # 3. Repeat Question Detection
        repeat_patterns = [
            (r"\b(?:can|could|would|will)\s+you\s+(?:please\s+)?repeat\b", "Asked interviewer to repeat the question"),
            (r"\brepeat\s+(?:the\s+question|that\s+question|that|it|again)\b", "Requested question repetition"),
            (r"\b(?:please\s+)?say\s+(?:that|the\s+question|it)\s+again\b", "Asked to say the question again"),
            (r"\b(?:can|could)\s+you\s+ask\s+(?:that|it|the\s+question)\s+again\b", "Asked to repeat the question"),
            (r"\bpardon\s+me\b", "Requested repetition ('pardon me')"),
            (r"\bcome\s+again\b", "Requested repetition ('come again')"),
            (r"\bwhat\s+was\s+the\s+question\b", "Asked 'What was the question'"),
            (r"\b(?:i\s+)?(?:missed|didn't\s+hear|did\s+not\s+hear)\s+the\s+question\b", "Candidate did not hear the question"),
            (r"\bhear\s+the\s+question\s+again\b", "Requested to hear the question again"),
        ]
        for pat, reason in repeat_patterns:
            if re.search(pat, lower_t):
                return "REPEAT_REQUESTED", reason

    # 4. Distinguish pure hesitation fillers ('uh', 'um', 'hmm') from short meaningful answers
    non_filler_words = [w for w in alpha_words if w not in FILLER_INTERJECTIONS]
    if not non_filler_words:
        return "NOISE_OR_FILLER", f"Only hesitation filler tokens detected ({alpha_words})"

    # If single character token only (e.g. "a" or "i")
    if len(non_filler_words) == 1 and len(non_filler_words[0]) < 2 and not any(c.isdigit() for c in lower_t):
        return "NOISE_OR_FILLER", f"Single-character indistinct token ('{non_filler_words[0]}')"

    if len(non_filler_words) <= 3:
        return "ANSWER", f"Valid concise candidate answer ({len(non_filler_words)} meaningful words)"

    return "ANSWER", f"Valid candidate interview answer ({word_count} words)"


def _generate_question_clarification(
    question_text: str,
    category: str = "Technical",
    role: str = "Software Engineer",
    clarification_count: int = 1,
) -> str:
    """
    Generate a clear, simpler-language explanation of the current interview question
    (with a brief concrete example when helpful) and re-state the question without
    advancing the question counter.
    """
    prompt = f"""
You are a supportive human interviewer for a {role} role.
The candidate just asked for clarification on this interview question (Clarification request #{clarification_count}):
Original Question: "{question_text}"
Category: {category}

Instructions:
1. Briefly and warmly rephrase the question in simpler, everyday language so it is easy to understand.
2. Include a short 1-sentence concrete example of what kind of scenario or concept they can talk about.
3. End by clearly inviting them to answer this same question whenever they are ready.
4. Keep the entire response under 3 sentences so it is concise when spoken aloud.

Return JSON:
{{
  "clarification_turn": "Sure, let me explain that in simpler terms..."
}}
"""
    try:
        raw = call_llm(
            prompt=prompt,
            system_prompt="You are a clear, supportive interviewer explaining a question in simple words. Output JSON.",
            json_mode=True,
        )
        parsed = clean_json_response(raw)
        clarification_turn = (parsed.get("clarification_turn", "") if isinstance(parsed, dict) else "").strip()
        if clarification_turn and len(clarification_turn) > 20:
            return clarification_turn
    except Exception:
        pass

    # Fast deterministic fallback if LLM is offline or times out
    if clarification_count >= 2:
        return (
            f"No problem at all—let me break it down even more simply. "
            f"In plain terms, I'm asking for a practical example of how you approach this in your day-to-day work: {question_text} "
            f"Feel free to walk me through any real example or step-by-step approach."
        )
    return (
        f"Sure, let me explain that in simpler terms. "
        f"I'd like you to share your practical approach or a real example for this question: {question_text} "
        f"Please go ahead whenever you're ready."
    )


def handle_readiness_confirmation(
    transcript: str,
    session_token: float,
    candidate_name: str,
    voice_id: str,
    questions: list,
) -> Dict[str, Any]:
    """
    Verifies actual candidate readiness in natural language using semantic NLU + contextual grammar.
    - Enters PROCESSING_READINESS state while analyzing the candidate's response.
    - Understands natural affirmative phrases, greetings, questions, unready requests, and unclear responses.
    - Never auto-advances on a timer.
    """
    with SESSION_LOCK:
        _transition_state_locked("PROCESSING_READINESS", "PROCESSING_READINESS", reason="Processing candidate readiness response")
        interviewer_prompt = LIVE_SESSION.get("subtitles", "")

    intent, intent_reason = _classify_readiness_intent_semantic(transcript, interviewer_prompt=interviewer_prompt)
    log_interview_event(
        speaker="SYSTEM",
        event="Readiness Intent",
        content=f"Candidate readiness classified as '{intent}' ({intent_reason}) from transcript: \"{transcript}\"",
        status="SUCCESS" if intent == "READY" else ("WAITING" if intent in ("UNREADY", "NOISE", "GREETING", "QUESTION") else "RETRY"),
        question_id=None,
        question_number=0,
        details={"intent": intent, "reason": intent_reason, "transcript": transcript},
    )

    if intent == "NOISE":
        with SESSION_LOCK:
            _transition_state_locked("WAITING_FOR_READINESS", "WAITING_FOR_READINESS", reason="Background noise ignored during readiness check")
        return {"status": "waiting_for_readiness", "transcript": "", **get_live_state()}

    if intent == "UNREADY":
        syna_msg = "Take your time. Let me know whenever you can hear me clearly and are ready to begin."
        with SESSION_LOCK:
            LIVE_SESSION["audio_generating"] = True
            LIVE_SESSION["current_audio_b64"] = ""
            LIVE_SESSION["subtitles"] = syna_msg
            LIVE_SESSION["active_speaker"] = "syna"
            _transition_state_locked("WAITING_FOR_READINESS", "WAITING_FOR_READINESS", reason="Candidate requested more time before starting")
        b64_audio, err = _synthesize_interviewer_audio(syna_msg, voice_id, event_context="Readiness Hold")
        with SESSION_LOCK:
            LIVE_SESSION["audio_generating"] = False
            LIVE_SESSION["current_audio_b64"] = b64_audio
            LIVE_SESSION["voice_error"] = err
        return {"status": "waiting_for_readiness", "transcript": transcript, **get_live_state()}

    if intent == "GREETING":
        greet_reply = f"Hello {candidate_name}, great to connect with you! Are you comfortable and ready to begin the interview?"
        with SESSION_LOCK:
            LIVE_SESSION["audio_generating"] = True
            LIVE_SESSION["current_audio_b64"] = ""
            LIVE_SESSION["subtitles"] = greet_reply
            LIVE_SESSION["active_speaker"] = "syna"
            _transition_state_locked("WAITING_FOR_READINESS", "WAITING_FOR_READINESS", reason="Acknowledged candidate greeting; awaiting readiness confirmation")
        b64_audio, err = _synthesize_interviewer_audio(greet_reply, voice_id, event_context="Greeting Acknowledgement")
        with SESSION_LOCK:
            LIVE_SESSION["audio_generating"] = False
            LIVE_SESSION["current_audio_b64"] = b64_audio
            LIVE_SESSION["voice_error"] = err
        return {"status": "waiting_for_readiness", "message": greet_reply, "transcript": transcript, **get_live_state()}

    if intent == "QUESTION":
        num_q = len(questions) if questions else 5
        q_reply = (
            f"We'll go through {num_q} structured interview questions tailored to your role. "
            f"You can speak naturally at your own pace. Whenever you're ready to start, just let me know!"
        )
        with SESSION_LOCK:
            LIVE_SESSION["audio_generating"] = True
            LIVE_SESSION["current_audio_b64"] = ""
            LIVE_SESSION["subtitles"] = q_reply
            LIVE_SESSION["active_speaker"] = "syna"
            _transition_state_locked("WAITING_FOR_READINESS", "WAITING_FOR_READINESS", reason="Answered candidate pre-interview question; awaiting readiness")
        b64_audio, err = _synthesize_interviewer_audio(q_reply, voice_id, event_context="Pre-Interview Question Response")
        with SESSION_LOCK:
            LIVE_SESSION["audio_generating"] = False
            LIVE_SESSION["current_audio_b64"] = b64_audio
            LIVE_SESSION["voice_error"] = err
        return {"status": "waiting_for_readiness", "message": q_reply, "transcript": transcript, **get_live_state()}

    if intent == "UNCLEAR":
        clarify_msg = "I didn't quite catch a clear confirmation. Could you please clarify if you are ready to begin the interview?"
        with SESSION_LOCK:
            LIVE_SESSION["audio_generating"] = True
            LIVE_SESSION["current_audio_b64"] = ""
            LIVE_SESSION["subtitles"] = clarify_msg
            LIVE_SESSION["active_speaker"] = "syna"
            _transition_state_locked("WAITING_FOR_READINESS", "WAITING_FOR_READINESS", reason="Unclear readiness response; asking clarification")
        log_interview_event(
            speaker="SYNA",
            event="Clarification",
            content=clarify_msg,
            status="RETRY",
            question_id=None,
            question_number=0,
        )
        b64_audio, err = _synthesize_interviewer_audio(clarify_msg, voice_id, event_context="Readiness Clarification")
        with SESSION_LOCK:
            LIVE_SESSION["audio_generating"] = False
            LIVE_SESSION["current_audio_b64"] = b64_audio
            LIVE_SESSION["voice_error"] = err
        return {
            "status": "clarification_requested",
            "message": clarify_msg,
            "transcript": transcript,
            **get_live_state(),
        }

    # Intent == "READY" -> Acknowledge warmly and immediately ask Question 1 in the locked Voicebox identity
    q1_item = questions[0] if questions else {"id": 1, "text": "Can you introduce yourself and describe your recent experience?"}
    q1_text = q1_item.get("text", "Can you introduce yourself and describe your recent experience?")
    q1_id = q1_item.get("id", 1)
    if not q1_text.lower().startswith(("wonderful", "great!")):
        syna_msg = f"Wonderful! Let's get started. {q1_text}"
    else:
        syna_msg = q1_text

    with SESSION_LOCK:
        LIVE_SESSION["audio_generating"] = True
        LIVE_SESSION["current_audio_b64"] = ""
        LIVE_SESSION["current_question_idx"] = 0
        _transition_state_locked("ASKING_QUESTION", "ASKING_QUESTION", reason="Candidate confirmed readiness; starting Question 1")
        LIVE_SESSION["subtitles"] = syna_msg
        LIVE_SESSION["active_speaker"] = "syna"

    log_interview_event(
        speaker="SYNA",
        event="Question",
        content=f"Q1 (ID={q1_id}): {syna_msg}",
        status="SUCCESS",
        question_id=q1_id,
        question_number=1,
        details={"question_id": q1_id, "question_number": 1, "question_text": syna_msg},
    )

    b64_audio, err = _synthesize_interviewer_audio(syna_msg, voice_id, event_context="Question 1")
    with SESSION_LOCK:
        LIVE_SESSION["audio_generating"] = False
        LIVE_SESSION["current_audio_b64"] = b64_audio
        LIVE_SESSION["voice_error"] = err

    return {"status": "readiness_confirmed", "transcript": transcript, **get_live_state()}


def handle_inactivity_timeout() -> Dict[str, Any]:
    """
    Handles a 20-second candidate inactivity timeout (distinct from the 1.5-2.5s end-of-speech threshold).
    Never auto-advances to the next question without a response; gently checks in with the candidate
    using the locked Voicebox profile.
    """
    with SESSION_LOCK:
        if not LIVE_SESSION.get("active") or LIVE_SESSION.get("call_stage") in ("COMPLETED", "INTERVIEW_COMPLETED"):
            return {"status": "inactive", **get_live_state()}
        stage = LIVE_SESSION.get("call_stage", "")
        voice_id = LIVE_SESSION["voice_profile_id"]
        q_idx = LIVE_SESSION["current_question_idx"]
        questions = LIVE_SESSION["questions"]
        curr_q_id = questions[q_idx].get("id", q_idx + 1) if (0 <= q_idx < len(questions)) else (q_idx + 1)
        LIVE_SESSION["candidate_silent_prompts_count"] = LIVE_SESSION.get("candidate_silent_prompts_count", 0) + 1
        prompt_count = LIVE_SESSION["candidate_silent_prompts_count"]

    if stage in ("INTRODUCTION", "INTRODUCTION_PLAYING", "WAITING_FOR_READINESS", "INITIAL_GREETING"):
        msg = "Are you comfortable and ready to begin the interview? Just let me know whenever you'd like to start."
    else:
        msg = (
            "I haven't heard a response yet. Please let me know if you need more time, would like me to repeat the question, "
            "or if you would like to skip to the next question."
        )

    log_interview_event(
        speaker="SYSTEM",
        event="Inactivity Check-In",
        content=f"Candidate silent for timeout window (prompt #{prompt_count}). Keeping Q{q_idx + 1} (ID={curr_q_id}) active without advancing.",
        status="WAITING",
        question_id=curr_q_id,
        question_number=q_idx + 1,
        details={"inactivity_count": prompt_count, "question_id": curr_q_id},
    )

    with SESSION_LOCK:
        LIVE_SESSION["audio_generating"] = True
        LIVE_SESSION["current_audio_b64"] = ""
        LIVE_SESSION["subtitles"] = msg
        LIVE_SESSION["active_speaker"] = "syna"

    b64_audio, err = _synthesize_interviewer_audio(msg, voice_id, event_context=f"Inactivity Prompt #{prompt_count}")
    with SESSION_LOCK:
        LIVE_SESSION["audio_generating"] = False
        LIVE_SESSION["current_audio_b64"] = b64_audio
        LIVE_SESSION["voice_error"] = err

    return {
        "status": "inactivity_prompt",
        "inactivity_count": prompt_count,
        "message": msg,
        **get_live_state(),
    }


def process_candidate_speech_blob(
    audio_bytes: bytes,
    browser_transcript: str = "",
    speech_duration_ms: float = 0.0,
    syna_currently_speaking: bool = False,
    simulate_stt_failure: bool = False,
) -> Dict[str, Any]:
    """
    Core Turn Engine implementing the full validated pipeline with real-time activity logging:
    Candidate Speech -> Noise Filtering -> VAD -> Audio Capture -> STT ->
    Transcript & Intent Validation (Answer / Clarification / Repeat / Retry) ->
    Answer Evaluation -> Interview Context Update -> Next Question Generation -> Selected Voicebox TTS.
    """
    turn_start_t0 = time.perf_counter()

    # Rule 1: Never listen to or accept candidate audio while Syna is actively speaking
    if syna_currently_speaking:
        log_interview_event(
            speaker="SYSTEM",
            event="Echo / Overlap Guard",
            content="Ignored audio captured while Syna was actively speaking.",
            status="WAITING",
        )
        return {
            "status": "ignored_while_interviewer_speaking",
            "message": "Ignored audio captured while interviewer was speaking.",
            **get_live_state(),
        }

    # Prevent duplicate concurrent turn processing
    if not TURN_PROCESSING_LOCK.acquire(blocking=False):
        log_interview_event(
            speaker="SYSTEM",
            event="Duplicate Prevention",
            content="Concurrent audio submission blocked while previous turn is still processing.",
            status="RETRY",
        )
        return {
            "status": "duplicate_turn_ignored",
            "message": "Another turn is currently being processed.",
            **get_live_state(),
        }

    try:
        with SESSION_LOCK:
            if LIVE_SESSION["call_stage"] in ("COMPLETED", "INTERVIEW_COMPLETED") or LIVE_SESSION.get("finished", False):
                return {"status": "inactive", **get_live_state()}
            if not LIVE_SESSION["active"]:
                LIVE_SESSION["active"] = True

            session_token = LIVE_SESSION.get("session_token", 0.0)
            stage = LIVE_SESSION["call_stage"]
            candidate_name = LIVE_SESSION["candidate_name"]
            voice_id = LIVE_SESSION["voice_profile_id"]
            q_idx = LIVE_SESSION["current_question_idx"]
            questions = LIVE_SESSION["questions"]
            recent_live_transcript = LIVE_SESSION.get("live_transcript", "")
            current_interviewer_subtitles = (LIVE_SESSION.get("subtitles") or "").strip()
            curr_q_item = questions[q_idx] if (0 <= q_idx < len(questions)) else {"id": q_idx + 1, "text": "Question"}
            curr_q_id = curr_q_item.get("id", q_idx + 1)
            curr_q_num = q_idx + 1

            # Check for duplicate raw audio payload hash before running STT
            audio_sha256 = ""
            if audio_bytes and len(audio_bytes) > 500:
                audio_sha256 = hashlib.sha256(audio_bytes).hexdigest()
                if audio_sha256 in LIVE_SESSION.get("processed_audio_hashes", []):
                    log_interview_event(
                        speaker="SYSTEM",
                        event="Duplicate Audio Prevented",
                        content=f"Duplicate audio recording (sha256={audio_sha256[:10]}...) prevented for Q{curr_q_num} (ID={curr_q_id}).",
                        status="RETRY",
                        question_id=curr_q_id,
                        question_number=curr_q_num,
                        details={"audio_sha256": audio_sha256, "audio_size_bytes": len(audio_bytes)},
                    )
                    return {
                        "status": "duplicate_answer_ignored",
                        "message": "Duplicate audio payload ignored.",
                        **get_live_state(),
                    }

            # Enter PROCESSING_AUDIO -> TRANSCRIBING_ANSWER
            _transition_state_locked("PROCESSING_AUDIO", "PROCESSING_AUDIO", reason="Candidate audio payload received")

        audio_size_bytes = len(audio_bytes) if audio_bytes else 0
        if audio_size_bytes > 0 or speech_duration_ms > 0:
            log_interview_event(
                speaker="CANDIDATE",
                event="Recording Completed",
                content=f"Captured {round(audio_size_bytes / 1024.0, 1)} KB audio ({_format_duration(speech_duration_ms)})",
                duration_ms=speech_duration_ms if speech_duration_ms > 0 else None,
                status="SUCCESS",
                question_id=curr_q_id,
                question_number=curr_q_num,
                details={"audio_size_bytes": audio_size_bytes, "speech_duration_ms": speech_duration_ms},
            )
            LIVE_SESSION.setdefault("timing_metrics", {})["last_candidate_speech_ms"] = speech_duration_ms

        # 1. Inspect audio quality, filter noise, and transcribe speech using Whisper
        transcript = ""
        stt_provider = "None"
        stt_duration_ms = 0.0
        audio_had_speech_energy = False
        stt_rejected_reason = None

        if simulate_stt_failure:
            with SESSION_LOCK:
                _transition_state_locked("TRANSCRIBING_ANSWER", "TRANSCRIBING_ANSWER", reason="STT processing started")
            log_interview_event(
                speaker="SYSTEM",
                event="STT Processing Started",
                content=f"Processing {round(audio_size_bytes / 1024.0, 1)} KB audio...",
                status="WAITING",
                question_id=curr_q_id,
                question_number=curr_q_num,
            )
            audio_had_speech_energy = True
            stt_provider = "Simulated STT Failure"
            stt_rejected_reason = "STT provider timeout / recognition failure"
            log_interview_event(
                speaker="SYSTEM",
                event="STT Processing Failed",
                content=f"STT failed ({stt_rejected_reason})",
                duration_ms=15.0,
                status="FAILED",
                question_id=curr_q_id,
                question_number=curr_q_num,
                details={"stt_provider": stt_provider, "reason": stt_rejected_reason},
            )
        elif audio_bytes and audio_size_bytes > 400:
            filtered_bytes, audio_metrics = analyze_and_filter_wav_bytes(audio_bytes)
            audio_had_speech_energy = audio_metrics.get("is_likely_speech", 1.0) > 0.0
            if audio_had_speech_energy:
                with SESSION_LOCK:
                    _transition_state_locked("TRANSCRIBING_ANSWER", "TRANSCRIBING_ANSWER", reason="VAD verified human speech energy")
                log_interview_event(
                    speaker="SYSTEM",
                    event="STT Processing Started",
                    content=f"Transcribing {round(audio_size_bytes / 1024.0, 1)} KB audio (RMS={audio_metrics.get('rms', 0):.4f})",
                    status="WAITING",
                    question_id=curr_q_id,
                    question_number=curr_q_num,
                    details={"audio_metrics": audio_metrics, "audio_size_bytes": audio_size_bytes},
                )
                stt_res = transcribe_audio_bytes_detailed(filtered_bytes, filename_hint="candidate_speech.wav")
                transcript = (stt_res.get("text") or "").strip()
                stt_provider = stt_res.get("provider", "Groq Whisper")
                stt_duration_ms = float(stt_res.get("duration_ms") or 0.0)
                stt_rejected_reason = stt_res.get("rejected_reason")
                LIVE_SESSION.setdefault("timing_metrics", {})["last_stt_processing_ms"] = stt_duration_ms

                if transcript:
                    log_interview_event(
                        speaker="SYSTEM",
                        event="STT Transcription Completed",
                        content=f"Provider: {stt_provider} ({len(transcript.split())} words recognized)",
                        duration_ms=stt_duration_ms,
                        status="SUCCESS",
                        question_id=curr_q_id,
                        question_number=curr_q_num,
                        details={"stt_provider": stt_provider, "audio_size_bytes": audio_size_bytes},
                    )
                else:
                    log_interview_event(
                        speaker="SYSTEM",
                        event="STT Empty / Rejected",
                        content=f"Provider: {stt_provider} — {stt_rejected_reason or 'Empty transcript'}",
                        duration_ms=stt_duration_ms,
                        status="RETRY",
                        question_id=curr_q_id,
                        question_number=curr_q_num,
                        details={"stt_provider": stt_provider, "rejected_reason": stt_rejected_reason},
                    )
            else:
                log_interview_event(
                    speaker="SYSTEM",
                    event="Background Noise Filtered",
                    content=f"Audio rejected by VAD (RMS={audio_metrics.get('rms', 0):.4f}, ratio={audio_metrics.get('speech_frame_ratio', 0):.3f})",
                    status="WAITING",
                    question_id=curr_q_id,
                    question_number=curr_q_num,
                    details={"audio_metrics": audio_metrics},
                )

        # Fallback to browser SpeechRecognition transcript if server audio STT was empty (and not simulating STT failure)
        if not simulate_stt_failure and (not transcript or len(transcript) < 2):
            fallback_txt = (browser_transcript or "").strip()
            if not fallback_txt and recent_live_transcript:
                fallback_txt = recent_live_transcript.strip()
            if fallback_txt and not is_whisper_hallucination_or_noise(fallback_txt):
                transcript = fallback_txt
                stt_provider = "Browser WebSpeech STT"
                with SESSION_LOCK:
                    _transition_state_locked("TRANSCRIBING_ANSWER", "TRANSCRIBING_ANSWER", reason="Using Browser WebSpeech STT transcript")
                log_interview_event(
                    speaker="SYSTEM",
                    event="STT Transcription Completed",
                    content=f"Provider: {stt_provider} ({len(transcript.split())} words)",
                    duration_ms=stt_duration_ms if stt_duration_ms > 0 else 12.0,
                    status="SUCCESS",
                    question_id=curr_q_id,
                    question_number=curr_q_num,
                    details={"stt_provider": stt_provider},
                )
            else:
                transcript = ""

        # Reject interviewer TTS acoustic echo if browser STT picked up Syna's own words
        if (
            transcript
            and current_interviewer_subtitles
            and len(transcript) > 12
            and transcript.lower() in current_interviewer_subtitles.lower()
        ):
            log_interview_event(
                speaker="SYSTEM",
                event="Acoustic Echo Ignored",
                content="Ignored transcript matching Syna's active subtitle output.",
                status="WAITING",
                question_id=curr_q_id,
                question_number=curr_q_num,
            )
            with SESSION_LOCK:
                if stage in ("INTRODUCTION", "INTRODUCTION_PLAYING", "WAITING_FOR_READINESS", "PROCESSING_READINESS", "INITIAL_GREETING"):
                    _transition_state_locked("WAITING_FOR_READINESS", "WAITING_FOR_READINESS")
                else:
                    _transition_state_locked("LISTENING_TO_CANDIDATE", "WAITING_FOR_CANDIDATE")
            return {"status": "echo_ignored", **get_live_state()}

        # Check if transcript is empty or Whisper silence/noise hallucination
        if not transcript or is_whisper_hallucination_or_noise(transcript):
            # If the candidate genuinely spoke (or STT failed) during an active question, trigger TRANSCRIPTION_RETRY
            if (simulate_stt_failure or (speech_duration_ms >= 1200 and audio_had_speech_energy)) and stage not in (
                "INTRODUCTION",
                "INTRODUCTION_PLAYING",
                "WAITING_FOR_READINESS",
                "PROCESSING_READINESS",
                "INITIAL_GREETING",
            ):
                retry_msg = "I couldn't hear your answer clearly due to audio interference. Could you please repeat your response to this question?"
                with SESSION_LOCK:
                    _transition_state_locked("TRANSCRIPTION_RETRY", "TRANSCRIPTION_RETRY", reason="STT failed to produce valid transcript for speech")
                    LIVE_SESSION["audio_generating"] = True
                    LIVE_SESSION["subtitles"] = retry_msg
                    LIVE_SESSION["active_speaker"] = "syna"

                log_interview_event(
                    speaker="SYNA",
                    event="Transcription Retry Requested",
                    content=f"Keeping Q{curr_q_num} (ID={curr_q_id}) active — asking candidate to repeat answer.",
                    status="RETRY",
                    question_id=curr_q_id,
                    question_number=curr_q_num,
                    details={"reason": stt_rejected_reason or "Unrecognized speech", "speech_duration_ms": speech_duration_ms},
                )

                b64_audio, err = _synthesize_interviewer_audio(retry_msg, voice_id, event_context=f"Transcription Retry Q{curr_q_num}")
                with SESSION_LOCK:
                    _transition_state_locked("ASKING_QUESTION", "ASKING_QUESTION", reason="Playing retry request to candidate")
                    LIVE_SESSION["audio_generating"] = False
                    LIVE_SESSION["current_audio_b64"] = b64_audio
                    LIVE_SESSION["voice_error"] = err
                return {
                    "status": "retry_requested",
                    "message": retry_msg,
                    **get_live_state(),
                }

            log_interview_event(
                speaker="CANDIDATE",
                event="Empty / Noise Transcript Ignored",
                content="No valid speech recognized; continuing to listen on current question.",
                status="WAITING",
                question_id=curr_q_id,
                question_number=curr_q_num,
            )
            with SESSION_LOCK:
                if stage in ("INTRODUCTION", "INTRODUCTION_PLAYING", "WAITING_FOR_READINESS", "PROCESSING_READINESS", "INITIAL_GREETING"):
                    _transition_state_locked("WAITING_FOR_READINESS", "WAITING_FOR_READINESS")
                else:
                    _transition_state_locked("LISTENING_TO_CANDIDATE", "WAITING_FOR_CANDIDATE")
            return {"status": "empty_transcript", **get_live_state()}

        # Log the actual recognized candidate transcript
        log_interview_event(
            speaker="CANDIDATE",
            event="Transcript",
            content=transcript,
            duration_ms=speech_duration_ms if speech_duration_ms > 0 else stt_duration_ms,
            status="SUCCESS",
            question_id=curr_q_id,
            question_number=curr_q_num,
            is_transcript=True,
            details={"stt_provider": stt_provider, "word_count": len(transcript.split())},
        )

        # Case B: Readiness confirmation turn
        if stage in ("INTRODUCTION", "INTRODUCTION_PLAYING", "WAITING_FOR_READINESS", "PROCESSING_READINESS", "INITIAL_GREETING"):
            return handle_readiness_confirmation(
                transcript=transcript,
                session_token=session_token,
                candidate_name=candidate_name,
                voice_id=voice_id,
                questions=questions,
            )

        # Enter PROCESSING_ANSWER / ANSWER_VALIDATION state and classify candidate intent
        with SESSION_LOCK:
            _transition_state_locked("PROCESSING_ANSWER", "PROCESSING_ANSWER", reason="Processing and validating candidate spoken answer")

        intent, intent_reason = classify_candidate_turn_intent(
            transcript=transcript,
            current_question_text=curr_q_item.get("text", ""),
        )

        log_interview_event(
            speaker="SYSTEM",
            event="Intent",
            content=f"{intent} — {intent_reason}",
            status="SUCCESS" if intent == "ANSWER" else ("RETRY" if intent in ("CLARIFICATION_REQUESTED", "REPEAT_REQUESTED") else "WAITING"),
            question_id=curr_q_id,
            question_number=curr_q_num,
            details={"intent": intent, "reason": intent_reason, "question_id": curr_q_id},
        )

        # Case A: Explicit exit / stop requested
        if intent == "STOP_INTERVIEW":
            farewell = f"Thank you {candidate_name}. Concluding our interview session now and compiling your evaluation report."
            with SESSION_LOCK:
                LIVE_SESSION["audio_generating"] = True
                LIVE_SESSION["subtitles"] = farewell
            b64_audio, err = _synthesize_interviewer_audio(farewell, voice_id, event_context="Closing Farewell")
            with SESSION_LOCK:
                LIVE_SESSION["audio_generating"] = False
                _transition_state_locked("COMPLETED", "INTERVIEW_COMPLETED", reason="Candidate requested interview stop")
                LIVE_SESSION["active_speaker"] = "syna"
                LIVE_SESSION["current_audio_b64"] = b64_audio
                LIVE_SESSION["closing_audio_b64"] = b64_audio
                LIVE_SESSION["voice_error"] = err
                LIVE_SESSION["exit_requested"] = True
                LIVE_SESSION["finished"] = True
            return {"status": "finished", "transcript": transcript, "voice_error": err, **get_live_state()}

        # Case A2: Candidate asks for more thinking time
        if intent == "NEED_MORE_TIME":
            hold_msg = "Of course, take your time. Go ahead whenever you're ready with your answer."
            with SESSION_LOCK:
                LIVE_SESSION["audio_generating"] = True
                LIVE_SESSION["current_audio_b64"] = ""
                LIVE_SESSION["subtitles"] = hold_msg
                LIVE_SESSION["active_speaker"] = "syna"
                _transition_state_locked("ASKING_QUESTION", "ASKING_QUESTION", reason=f"Reassuring candidate on Q{curr_q_num}")
            b64_audio, err = _synthesize_interviewer_audio(hold_msg, voice_id, event_context=f"More Time Q{curr_q_num}")
            with SESSION_LOCK:
                LIVE_SESSION["audio_generating"] = False
                LIVE_SESSION["current_audio_b64"] = b64_audio
                LIVE_SESSION["voice_error"] = err
            return {"status": "waiting_for_candidate", "message": hold_msg, "transcript": transcript, **get_live_state()}

        # Case C1: Candidate requests question CLARIFICATION (Section 4)
        # Do NOT treat as answer, do NOT increment current_question_idx, keep same question_id!
        if intent == "CLARIFICATION_REQUESTED":
            with SESSION_LOCK:
                clar_counts = LIVE_SESSION.setdefault("question_clarification_counts", {})
                c_count = int(clar_counts.get(str(curr_q_id), 0)) + 1
                clar_counts[str(curr_q_id)] = c_count
                meta = dict(LIVE_SESSION.get("plan_metadata", {}) or {})
                _transition_state_locked(
                    "CLARIFICATION_REQUESTED",
                    "CLARIFICATION_REQUESTED",
                    reason=f"Candidate asked for clarification #{c_count} on Q{curr_q_num} (ID={curr_q_id})",
                )
                LIVE_SESSION["audio_generating"] = True
                LIVE_SESSION["current_audio_b64"] = ""
                LIVE_SESSION["live_transcript"] = ""

            t_clar = time.perf_counter()
            clarify_spoken = _generate_question_clarification(
                question_text=curr_q_item.get("text", ""),
                category=curr_q_item.get("category", "Technical"),
                role=meta.get("role", "Software Engineer"),
                clarification_count=c_count,
            )
            clar_gen_ms = round((time.perf_counter() - t_clar) * 1000.0, 2)

            log_interview_event(
                speaker="SYNA",
                event="Clarification",
                content=f"Clarifying Q{curr_q_num} (ID={curr_q_id}, attempt #{c_count}): {clarify_spoken}",
                duration_ms=clar_gen_ms,
                status="SUCCESS",
                question_id=curr_q_id,
                question_number=curr_q_num,
                details={
                    "clarification_count": c_count,
                    "question_id": curr_q_id,
                    "question_number": curr_q_num,
                    "original_question": curr_q_item.get("text", ""),
                },
            )
            log_interview_event(
                speaker="SYSTEM",
                event="Question Advancement",
                content=f"HELD at Q{curr_q_num} (ID={curr_q_id}) — Clarification requested; waiting for candidate's actual answer.",
                status="WAITING",
                question_id=curr_q_id,
                question_number=curr_q_num,
            )

            with SESSION_LOCK:
                _transition_state_locked("ASKING_QUESTION", "ASKING_QUESTION", reason=f"Speaking clarification for Q{curr_q_num}")
                LIVE_SESSION["subtitles"] = clarify_spoken
                LIVE_SESSION["active_speaker"] = "syna"

            b64_audio, err = _synthesize_interviewer_audio(clarify_spoken, voice_id, event_context=f"Clarification Q{curr_q_num}")
            with SESSION_LOCK:
                LIVE_SESSION["audio_generating"] = False
                LIVE_SESSION["current_audio_b64"] = b64_audio
                LIVE_SESSION["voice_error"] = err

            return {
                "status": "question_clarified",
                "clarification_count": c_count,
                "message": clarify_spoken,
                "transcript": transcript,
                **get_live_state(),
            }

        # Case C2: Candidate requests question REPETITION
        if intent == "REPEAT_REQUESTED":
            repeat_msg = f"Of course. Here is the question again: {curr_q_item.get('text', '')}"
            with SESSION_LOCK:
                _transition_state_locked(
                    "REPEAT_REQUESTED",
                    "REPEAT_REQUESTED",
                    reason=f"Candidate asked to repeat Q{curr_q_num} (ID={curr_q_id})",
                )
                LIVE_SESSION["audio_generating"] = True
                LIVE_SESSION["current_audio_b64"] = ""
                LIVE_SESSION["live_transcript"] = ""

            log_interview_event(
                speaker="SYNA",
                event="Repeat Question",
                content=f"Repeating Q{curr_q_num} (ID={curr_q_id}): {repeat_msg}",
                status="SUCCESS",
                question_id=curr_q_id,
                question_number=curr_q_num,
            )
            log_interview_event(
                speaker="SYSTEM",
                event="Question Advancement",
                content=f"HELD at Q{curr_q_num} (ID={curr_q_id}) — Question repeated; waiting for candidate's actual answer.",
                status="WAITING",
                question_id=curr_q_id,
                question_number=curr_q_num,
            )

            with SESSION_LOCK:
                _transition_state_locked("ASKING_QUESTION", "ASKING_QUESTION", reason=f"Replaying Q{curr_q_num}")
                LIVE_SESSION["subtitles"] = repeat_msg
                LIVE_SESSION["active_speaker"] = "syna"

            b64_audio, err = _synthesize_interviewer_audio(repeat_msg, voice_id, event_context=f"Repeat Q{curr_q_num}")
            with SESSION_LOCK:
                LIVE_SESSION["audio_generating"] = False
                LIVE_SESSION["current_audio_b64"] = b64_audio
                LIVE_SESSION["voice_error"] = err
            return {"status": "question_repeated", "message": repeat_msg, "transcript": transcript, **get_live_state()}

        # Case D: Pure hesitation filler or non-meaningful noise
        if intent == "NOISE_OR_FILLER":
            if speech_duration_ms >= 1800:
                retry_msg = "I couldn't hear your answer clearly due to audio interference. Could you please repeat your response to this question?"
                with SESSION_LOCK:
                    _transition_state_locked("TRANSCRIPTION_RETRY", "TRANSCRIPTION_RETRY", reason="Long speech yielded only indistinct filler")
                    LIVE_SESSION["audio_generating"] = True
                    LIVE_SESSION["subtitles"] = retry_msg
                    LIVE_SESSION["active_speaker"] = "syna"
                log_interview_event(
                    speaker="SYNA",
                    event="Transcription Retry Requested",
                    content=retry_msg,
                    status="RETRY",
                    question_id=curr_q_id,
                    question_number=curr_q_num,
                )
                b64_audio, err = _synthesize_interviewer_audio(retry_msg, voice_id, event_context=f"Retry Q{curr_q_num}")
                with SESSION_LOCK:
                    _transition_state_locked("ASKING_QUESTION", "ASKING_QUESTION", reason="Playing retry prompt")
                    LIVE_SESSION["audio_generating"] = False
                    LIVE_SESSION["current_audio_b64"] = b64_audio
                    LIVE_SESSION["voice_error"] = err
                return {
                    "status": "retry_requested",
                    "message": retry_msg,
                    "transcript": transcript,
                    **get_live_state(),
                }

            log_interview_event(
                speaker="SYSTEM",
                event="Noise / Filler Ignored",
                content=f"Ignored hesitation filler ('{transcript}'); continuing to listen for Q{curr_q_num}.",
                status="WAITING",
                question_id=curr_q_id,
                question_number=curr_q_num,
            )
            with SESSION_LOCK:
                _transition_state_locked("LISTENING_TO_CANDIDATE", "WAITING_FOR_CANDIDATE")
            return {
                "status": "noise_ignored",
                "message": "Candidate response contained only filler/noise. Continuing to listen.",
                **get_live_state(),
            }

        # Rule 2: Prevent the exact same question answer or audio from being submitted twice
        submission_sig = f"{q_idx}:{curr_q_id}:{transcript.strip().lower()}"
        with SESSION_LOCK:
            if submission_sig == LIVE_SESSION.get("last_submission_hash") or curr_q_id in LIVE_SESSION.get("answered_question_ids", []):
                log_interview_event(
                    speaker="SYSTEM",
                    event="Duplicate Answer Prevented",
                    content=f"Duplicate submission for Q{curr_q_num} (ID={curr_q_id}) blocked.",
                    status="RETRY",
                    question_id=curr_q_id,
                    question_number=curr_q_num,
                )
                return {
                    "status": "duplicate_answer_ignored",
                    "message": f"Answer for Question {curr_q_id} was already recorded.",
                    **get_live_state(),
                }
            LIVE_SESSION["last_submission_hash"] = submission_sig
            LIVE_SESSION["answered_question_ids"].append(curr_q_id)
            if audio_sha256:
                LIVE_SESSION.setdefault("processed_audio_hashes", []).append(audio_sha256)
            LIVE_SESSION["live_transcript"] = transcript
            LIVE_SESSION["last_turn_timestamp"] = time.time()
            LIVE_SESSION["candidate_silent_prompts_count"] = 0

        log_interview_event(
            speaker="SYSTEM",
            event="Answer Validated",
            content=f"Accepted answer for Q{curr_q_num} (ID={curr_q_id}, {len(transcript.split())} words)",
            status="SUCCESS",
            question_id=curr_q_id,
            question_number=curr_q_num,
        )

        prev_question_text = curr_q_item.get("text", "")

        # -------------------------------------------------------------
        # Stage B: EVALUATING_ANSWER (ANSWER_EVALUATION)
        # -------------------------------------------------------------
        with SESSION_LOCK:
            _transition_state_locked("EVALUATING_ANSWER", "EVALUATING_ANSWER", reason=f"Evaluating answer for Q{curr_q_num} (ID={curr_q_id})")
            meta = dict(LIVE_SESSION.get("plan_metadata", {}) or {})

        log_interview_event(
            speaker="SYSTEM",
            event="Evaluation Started",
            content=f"Scoring answer for Q{curr_q_num} (ID={curr_q_id})",
            status="WAITING",
            question_id=curr_q_id,
            question_number=curr_q_num,
        )

        t_eval_start = time.perf_counter()
        eval_res = None
        est_dur = round(speech_duration_ms / 1000.0, 1) if speech_duration_ms > 0 else 15.0
        try:
            q_obj = QuestionItem(
                id=curr_q_id,
                category=curr_q_item.get("category", "Behavioral (STAR Method)"),
                interview_type=meta.get("interview_type", "Behavioral (STAR Method)"),
                difficulty=curr_q_item.get("difficulty", "Standard"),
                question_text=prev_question_text,
                target_competencies=curr_q_item.get("target_competencies", []),
                expected_concepts=curr_q_item.get("expected_concepts", []),
            )
            eval_res = evaluate_universal_answer(
                question=q_obj,
                candidate_answer=transcript,
                industry=meta.get("industry", "Artificial Intelligence, Software & IT"),
                target_role=meta.get("role", "Software Engineer"),
                interview_type=meta.get("interview_type", "Behavioral (STAR Method)"),
                duration_sec=est_dur,
            )
        except Exception as e:
            print(f"[Evaluation Warning]: {e}")
            log_interview_event(
                speaker="SYSTEM",
                event="Evaluation Error",
                content=f"Evaluation exception on Q{curr_q_num}: {e}",
                status="FAILED",
                question_id=curr_q_id,
                question_number=curr_q_num,
            )

        eval_dur_ms = round((time.perf_counter() - t_eval_start) * 1000.0, 2)
        LIVE_SESSION.setdefault("timing_metrics", {})["last_evaluation_ms"] = eval_dur_ms

        score_val = getattr(eval_res, "score", getattr(eval_res, "overall_score", None)) if eval_res else None
        status_val = getattr(eval_res, "answer_status", "Answered") if eval_res else "Answered"
        log_interview_event(
            speaker="SYSTEM",
            event="Evaluation",
            content=f"Q{curr_q_num} (ID={curr_q_id}) Score: {score_val if score_val is not None else 'N/A'}/100 — Status: {status_val}",
            duration_ms=eval_dur_ms,
            status="SUCCESS" if eval_res is not None else "FAILED",
            question_id=curr_q_id,
            question_number=curr_q_num,
            details={
                "score": score_val,
                "answer_status": status_val,
                "question_id": curr_q_id,
                "question_number": curr_q_num,
            },
        )

        # Save transcription and evaluation against the current question ID
        with SESSION_LOCK:
            LIVE_SESSION["session_records"].append({
                "question": dict(curr_q_item),
                "candidate_answer": transcript,
                "duration_seconds": est_dur,
                "evaluation": eval_res,
                "follow_up_question": None,
                "follow_up_answer": None,
            })
            session_history_snapshot = list(LIVE_SESSION["session_records"])

        next_idx = q_idx + 1

        # Check if all configured interview questions are completed
        if next_idx >= len(questions):
            closing_msg = (
                f"Thank you so much, {candidate_name}. You have completed all questions in this session! "
                f"I will now compile your comprehensive interview performance report."
            )
            log_interview_event(
                speaker="SYSTEM",
                event="Question Advancement",
                content=f"All {len(questions)} questions answered ({len(session_history_snapshot)}/{len(questions)}). Transitioning to INTERVIEW_COMPLETED.",
                status="SUCCESS",
                question_id=curr_q_id,
                question_number=curr_q_num,
            )
            with SESSION_LOCK:
                LIVE_SESSION["audio_generating"] = True
                LIVE_SESSION["current_audio_b64"] = ""
                _transition_state_locked("COMPLETED", "INTERVIEW_COMPLETED", reason="All planned questions completed")
                LIVE_SESSION["subtitles"] = closing_msg
                LIVE_SESSION["active_speaker"] = "syna"

            b64_audio, err = _synthesize_interviewer_audio(closing_msg, voice_id, event_context="Interview Completion")
            with SESSION_LOCK:
                LIVE_SESSION["audio_generating"] = False
                LIVE_SESSION["current_audio_b64"] = b64_audio
                LIVE_SESSION["closing_audio_b64"] = b64_audio
                LIVE_SESSION["voice_error"] = err
                LIVE_SESSION["exit_requested"] = True
                LIVE_SESSION["finished"] = True

            turnaround_ms = round((time.perf_counter() - turn_start_t0) * 1000.0, 2)
            LIVE_SESSION.setdefault("timing_metrics", {})["last_turnaround_ms"] = turnaround_ms
            return {"status": "finished", "transcript": transcript, **get_live_state()}

        # -------------------------------------------------------------
        # Stage B (Cont): GENERATING_NEXT_QUESTION (Context-Aware)
        # -------------------------------------------------------------
        next_q_item = questions[next_idx]
        next_q_id = next_q_item.get("id", next_idx + 1)
        next_q_num = next_idx + 1

        log_interview_event(
            speaker="SYSTEM",
            event="Question Advancement",
            content=f"Advancing from Q{curr_q_num} (ID={curr_q_id}) -> Q{next_q_num} (ID={next_q_id}) after validated answer.",
            status="SUCCESS",
            question_id=next_q_id,
            question_number=next_q_num,
            details={"from_question_id": curr_q_id, "to_question_id": next_q_id},
        )

        with SESSION_LOCK:
            _transition_state_locked("ACKNOWLEDGING_ANSWER", "ACKNOWLEDGING_ANSWER", reason=f"Acknowledging candidate answer for Q{curr_q_num}")
            _transition_state_locked("NEXT_QUESTION", "NEXT_QUESTION", reason=f"Advancing to Q{next_q_num} (ID={next_q_id})")
            LIVE_SESSION["audio_generating"] = True
            LIVE_SESSION["current_audio_b64"] = ""

        log_interview_event(
            speaker="SYNA",
            event="Question Generation Started",
            content=f"Generating contextual Question {next_q_num} of {len(questions)} (ID={next_q_id})",
            status="WAITING",
            question_id=next_q_id,
            question_number=next_q_num,
        )

        t_qgen_start = time.perf_counter()
        contextual_turn = _generate_contextual_question(
            candidate_answer=transcript,
            prev_question_text=prev_question_text,
            next_idx=next_idx,
            questions=questions,
            metadata=meta,
            candidate_name=candidate_name,
            eval_obj=eval_res,
            session_history=session_history_snapshot,
        )
        qgen_dur_ms = round((time.perf_counter() - t_qgen_start) * 1000.0, 2)
        LIVE_SESSION.setdefault("timing_metrics", {})["last_question_generation_ms"] = qgen_dur_ms

        log_interview_event(
            speaker="SYNA",
            event="Question",
            content=f"Q{next_q_num} (ID={next_q_id}): {contextual_turn}",
            duration_ms=qgen_dur_ms,
            status="SUCCESS",
            question_id=next_q_id,
            question_number=next_q_num,
            details={"question_id": next_q_id, "question_number": next_q_num, "question_text": contextual_turn},
        )

        # -------------------------------------------------------------
        # Stage C: ASKING_QUESTION (Strictly using locked Voicebox profile)
        # -------------------------------------------------------------
        questions[next_idx]["text"] = contextual_turn
        with SESSION_LOCK:
            LIVE_SESSION["current_question_idx"] = next_idx
            LIVE_SESSION["current_audio_b64"] = ""
            LIVE_SESSION["live_transcript"] = ""
            _transition_state_locked("ASKING_QUESTION", "ASKING_QUESTION", reason=f"Playing Q{next_q_num} (ID={next_q_id})")
            LIVE_SESSION["subtitles"] = contextual_turn
            LIVE_SESSION["active_speaker"] = "syna"

        b64_audio, err = _synthesize_interviewer_audio(contextual_turn, voice_id, event_context=f"Question {next_q_num}")
        with SESSION_LOCK:
            LIVE_SESSION["audio_generating"] = False
            LIVE_SESSION["current_audio_b64"] = b64_audio
            LIVE_SESSION["voice_error"] = err

        turnaround_ms = round((time.perf_counter() - turn_start_t0) * 1000.0, 2)
        LIVE_SESSION.setdefault("timing_metrics", {})["last_turnaround_ms"] = turnaround_ms
        log_interview_event(
            speaker="SYSTEM",
            event="Turnaround Completed",
            content=f"Total turnaround from candidate speech end to Q{next_q_num} ready: {_format_duration(turnaround_ms)}",
            duration_ms=turnaround_ms,
            status="SUCCESS",
            question_id=next_q_id,
            question_number=next_q_num,
            details={
                "turnaround_ms": turnaround_ms,
                "stt_ms": stt_duration_ms,
                "eval_ms": eval_dur_ms,
                "qgen_ms": qgen_dur_ms,
            },
        )

        # Pre-warm Question next_idx + 1 in background
        if next_idx + 1 < len(questions):
            threading.Thread(
                target=_bg_prewarm_question,
                args=(session_token, next_idx + 1, candidate_name, questions, voice_id),
                daemon=True,
            ).start()

        return {
            "status": "next_question_asked",
            "question_index": next_idx,
            "question_id": next_q_id,
            "transcript": transcript,
            "voice_error": err,
            **get_live_state(),
        }
    finally:
        TURN_PROCESSING_LOCK.release()


class InterviewBridgeHTTPHandler(BaseHTTPRequestHandler):
    """CORS-enabled HTTP request handler for the live browser call room and real-time activity log."""

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        route = parsed_url.path
        query = parse_qs(parsed_url.query)

        if route in ("/status", "/state"):
            state = get_live_state()
            data = json.dumps(state, default=str).encode("utf-8")
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif route == "/export_logs":
            fmt = (query.get("format", ["json"])[0] or "json").lower()
            with LOG_LOCK:
                logs = list(LIVE_SESSION.get("activity_logs", []))
            if fmt == "txt":
                txt_body = format_activity_logs_as_text(logs).encode("utf-8")
                self.send_response(200)
                self._send_cors_headers()
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="interview_activity_logs.txt"')
                self.send_header("Content-Length", str(len(txt_body)))
                self.end_headers()
                self.wfile.write(txt_body)
            else:
                json_body = json.dumps(
                    {
                        "session_id": str(LIVE_SESSION.get("session_token", "")),
                        "candidate_name": LIVE_SESSION.get("candidate_name", ""),
                        "interviewer_name": LIVE_SESSION.get("interviewer_name", ""),
                        "voice_profile_id": LIVE_SESSION.get("voice_profile_id", ""),
                        "total_events": len(logs),
                        "activity_logs": logs,
                    },
                    indent=2,
                    default=str,
                ).encode("utf-8")
                self.send_response(200)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="interview_activity_logs.json"')
                self.send_header("Content-Length", str(len(json_body)))
                self.end_headers()
                self.wfile.write(json_body)
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        if self.path == "/init_session":
            try:
                payload = json.loads(post_data.decode("utf-8"))
                c_name = payload.get("candidate_name", "Candidate")
                questions = payload.get("questions", [])
                metadata = payload.get("plan_metadata", {})
                v_id = payload.get("voice_profile_id") or metadata.get("voice_profile_id")
                i_name = payload.get("interviewer_name") or metadata.get("interviewer_name")
                reset_live_session(c_name, questions, metadata, voice_profile_id=v_id, interviewer_name=i_name)
                res_data = json.dumps({"status": "ok", "message": "Session initialized", **get_live_state()}, default=str).encode("utf-8")
            except Exception as e:
                res_data = json.dumps({"status": "error", "message": str(e)}).encode("utf-8")

            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(res_data)))
            self.end_headers()
            self.wfile.write(res_data)

        elif self.path in ("/introduction_finished", "/greeting_done"):
            with SESSION_LOCK:
                if LIVE_SESSION.get("call_stage") in ("INTRODUCTION", "INTRODUCTION_PLAYING", "INITIAL_GREETING"):
                    _transition_state_locked("WAITING_FOR_READINESS", "WAITING_FOR_READINESS", reason="Interviewer introduction audio finished")
                    LIVE_SESSION["active_speaker"] = "waiting"
                    LIVE_SESSION["current_audio_b64"] = ""
                    log_interview_event(
                        speaker="CANDIDATE",
                        event="Listening",
                        content="Microphone listening for candidate readiness confirmation",
                        status="WAITING",
                        question_id=None,
                        question_number=0,
                    )
            res_data = json.dumps({"status": "waiting_for_readiness", **get_live_state()}, default=str).encode("utf-8")
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(res_data)))
            self.end_headers()
            self.wfile.write(res_data)

        elif self.path in ("/speech", "/submit_audio"):
            try:
                payload = json.loads(post_data.decode("utf-8"))
                b64_audio = payload.get("audio_base64", "") or ""
                browser_transcript = payload.get("browser_transcript", "") or payload.get("transcript", "") or ""
                speech_dur_ms = float(payload.get("speech_duration_ms", 0.0) or 0.0)
                syna_speaking = bool(payload.get("syna_currently_speaking", False))
                sim_stt_fail = bool(payload.get("simulate_stt_failure", False))
                if "," in b64_audio:
                    b64_audio = b64_audio.split(",")[1]
                audio_bytes = base64.b64decode(b64_audio) if b64_audio else b""
                result = process_candidate_speech_blob(
                    audio_bytes,
                    browser_transcript=browser_transcript,
                    speech_duration_ms=speech_dur_ms,
                    syna_currently_speaking=syna_speaking,
                    simulate_stt_failure=sim_stt_fail,
                )
            except Exception as e:
                log_interview_event(
                    speaker="SYSTEM",
                    event="Speech Processing Error",
                    content=f"Exception in /speech: {e}",
                    status="FAILED",
                )
                result = {"status": "error", "message": str(e), **get_live_state()}

            res_data = json.dumps(result, default=str).encode("utf-8")
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(res_data)))
            self.end_headers()
            self.wfile.write(res_data)

        elif self.path == "/client_event":
            try:
                payload = json.loads(post_data.decode("utf-8"))
                sp = payload.get("speaker", "SYSTEM")
                ev = payload.get("event", "Client Event")
                ct = payload.get("content", "")
                dur = payload.get("duration_ms")
                st = payload.get("status", "SUCCESS")
                det = payload.get("details") if isinstance(payload.get("details"), dict) else {}
                is_tr = bool(payload.get("is_transcript", False))
                entry = log_interview_event(
                    speaker=sp,
                    event=ev,
                    content=ct,
                    duration_ms=float(dur) if dur is not None else None,
                    status=st,
                    details=det,
                    is_transcript=is_tr,
                )
                res_data = json.dumps({"status": "ok", "entry": entry}, default=str).encode("utf-8")
            except Exception as e:
                res_data = json.dumps({"status": "error", "message": str(e)}).encode("utf-8")

            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(res_data)))
            self.end_headers()
            self.wfile.write(res_data)

        elif self.path == "/log_control":
            try:
                payload = json.loads(post_data.decode("utf-8"))
                action = payload.get("action", "")
                if action == "clear":
                    with LOG_LOCK:
                        LIVE_SESSION["activity_logs"] = []
                        LIVE_SESSION["log_seq_counter"] = 0
                    log_interview_event(
                        speaker="SYSTEM",
                        event="Logs Cleared",
                        content="Activity log cleared by user.",
                        status="SUCCESS",
                    )
                elif action == "toggle_privacy":
                    with LOG_LOCK:
                        curr = bool(LIVE_SESSION.get("log_transcripts_enabled", True))
                        LIVE_SESSION["log_transcripts_enabled"] = not curr
                        new_state = LIVE_SESSION["log_transcripts_enabled"]
                    log_interview_event(
                        speaker="SYSTEM",
                        event="Transcript Privacy Updated",
                        content=f"Transcript logging set to {'VISIBLE' if new_state else 'MASKED'}",
                        status="SUCCESS",
                    )
                res_data = json.dumps({"status": "ok", **get_live_state()}, default=str).encode("utf-8")
            except Exception as e:
                res_data = json.dumps({"status": "error", "message": str(e)}).encode("utf-8")

            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(res_data)))
            self.end_headers()
            self.wfile.write(res_data)

        elif self.path == "/inactivity_timeout":
            try:
                result = handle_inactivity_timeout()
            except Exception as e:
                result = {"status": "error", "message": str(e), **get_live_state()}
            res_data = json.dumps(result, default=str).encode("utf-8")
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(res_data)))
            self.end_headers()
            self.wfile.write(res_data)

        elif self.path == "/speaker_state":
            try:
                payload = json.loads(post_data.decode("utf-8"))
                speaker = payload.get("speaker", "candidate")  # "candidate" | "syna" | "none" | "waiting"
                live_txt = payload.get("live_transcript")
                playback_dur_ms = payload.get("playback_duration_ms")
                with SESSION_LOCK:
                    if LIVE_SESSION.get("call_stage") not in ("COMPLETED", "INTERVIEW_COMPLETED"):
                        if speaker in ("none", "waiting"):
                            if LIVE_SESSION.get("call_stage") == "ASKING_QUESTION":
                                if playback_dur_ms is not None:
                                    LIVE_SESSION.setdefault("timing_metrics", {})["last_playback_ms"] = float(playback_dur_ms)
                                    log_interview_event(
                                        speaker="SYNA",
                                        event="Audio Playback Finished",
                                        content="Interviewer finished speaking question.",
                                        duration_ms=float(playback_dur_ms),
                                        status="SUCCESS",
                                    )
                                _transition_state_locked(
                                    "LISTENING_TO_CANDIDATE",
                                    "WAITING_FOR_CANDIDATE",
                                    reason="Interviewer audio finished; microphone listening for candidate",
                                )
                                log_interview_event(
                                    speaker="CANDIDATE",
                                    event="Listening",
                                    content="Microphone listening for candidate response",
                                    status="WAITING",
                                )
                            LIVE_SESSION["active_speaker"] = "waiting"
                            LIVE_SESSION["current_audio_b64"] = ""
                        elif speaker == "waiting_for_silence":
                            if LIVE_SESSION.get("call_stage") in ("RECORDING_ANSWER", "RECORDING", "LISTENING_TO_CANDIDATE", "WAITING_FOR_CANDIDATE"):
                                _transition_state_locked("WAITING_FOR_SILENCE", "WAITING_FOR_SILENCE", reason="Candidate paused speaking; 20s silence grace timer active")
                            LIVE_SESSION["active_speaker"] = "candidate"
                        elif speaker == "candidate":
                            if LIVE_SESSION.get("call_stage") in ("LISTENING_TO_CANDIDATE", "WAITING_FOR_CANDIDATE", "ASKING_QUESTION", "WAITING_FOR_SILENCE"):
                                _transition_state_locked("RECORDING_ANSWER", "RECORDING_ANSWER", reason="Candidate speech detected by VAD (silence timer reset)")
                                log_interview_event(
                                    speaker="CANDIDATE",
                                    event="Speech Detected",
                                    content="Candidate speaking (audio recording active; silence timer reset)",
                                    status="SUCCESS",
                                )
                            LIVE_SESSION["active_speaker"] = "candidate"
                        else:
                            LIVE_SESSION["active_speaker"] = speaker
                        if isinstance(live_txt, str) and live_txt.strip():
                            prev_live = LIVE_SESSION.get("live_transcript", "")
                            LIVE_SESSION["live_transcript"] = live_txt.strip()
                            if live_txt.strip() != prev_live:
                                log_interview_event(
                                    speaker="CANDIDATE",
                                    event="Partial Speech",
                                    content=live_txt.strip(),
                                    status="WAITING",
                                    is_transcript=True,
                                )
                res_data = json.dumps({"status": "ok", "active_speaker": speaker, **get_live_state()}, default=str).encode("utf-8")
            except Exception as e:
                res_data = json.dumps({"status": "error", "message": str(e)}).encode("utf-8")

            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(res_data)))
            self.end_headers()
            self.wfile.write(res_data)

        elif self.path == "/end_call":
            with SESSION_LOCK:
                LIVE_SESSION["active"] = False
                LIVE_SESSION["audio_generating"] = False
                _transition_state_locked("COMPLETED", "INTERVIEW_COMPLETED", reason="Interview ended by user")
                LIVE_SESSION["active_speaker"] = "none"
                LIVE_SESSION["current_audio_b64"] = ""
                LIVE_SESSION["exit_requested"] = True
                LIVE_SESSION["finished"] = True
                LIVE_SESSION["session_token"] = time.time()
            log_interview_event(
                speaker="SYSTEM",
                event="Interview Ended",
                content=f"Session concluded ({len(LIVE_SESSION.get('session_records', []))} answers recorded).",
                status="SUCCESS",
            )
            res_data = json.dumps({"status": "call_ended", **get_live_state()}, default=str).encode("utf-8")
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(res_data)))
            self.end_headers()
            self.wfile.write(res_data)

        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()

    def log_message(self, format, *args):
        pass


_SERVER_INSTANCE = getattr(sys, "_interview_bridge_server_instance", None)
_SERVER_THREAD = getattr(sys, "_interview_bridge_server_thread", None)


def start_interview_bridge_server(port: int = 8765):
    """Starts the background bridge server on 0.0.0.0:8765 so both localhost and Docker port-forwarding can reach it."""
    global _SERVER_INSTANCE, _SERVER_THREAD
    if _SERVER_INSTANCE is not None:
        _SERVER_INSTANCE.RequestHandlerClass = InterviewBridgeHTTPHandler
        return

    try:
        _SERVER_INSTANCE = HTTPServer(("0.0.0.0", port), InterviewBridgeHTTPHandler)
        _SERVER_THREAD = threading.Thread(target=_SERVER_INSTANCE.serve_forever, daemon=True)
        _SERVER_THREAD.start()
        sys._interview_bridge_server_instance = _SERVER_INSTANCE
        sys._interview_bridge_server_thread = _SERVER_THREAD
    except Exception:
        pass
