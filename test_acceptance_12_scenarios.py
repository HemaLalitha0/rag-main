"""
End-to-End Acceptance Test Suite for Universal AI Mock Interview:
Real-Time Conversation Logs, Audio Capture Monitoring & Question Flow Debugging.

Tests all 12 required acceptance scenarios from Section 12 and dumps real runtime logs.
"""
import io
import json
import math
import struct
import time
import wave

from audio_service import VOICEBOX_PROFILES
from interview_bridge_server import (
    LIVE_SESSION,
    format_activity_logs_as_text,
    get_live_state,
    handle_inactivity_timeout,
    process_candidate_speech_blob,
    reset_live_session,
)
from interview_engine import generate_universal_final_report
from interview_schemas import CandidateProfile, QuestionItem, QuestionSessionRecord


def make_synthetic_speech_wav(duration_sec: float = 1.6, freq_hz: float = 220.0, amplitude: float = 0.35) -> bytes:
    """Create a valid 16kHz 16-bit mono WAV containing harmonic speech-band energy."""
    sr = 16000
    n_samples = int(sr * duration_sec)
    samples = []
    for i in range(n_samples):
        t = i / float(sr)
        # Modulated fundamental + first two formants
        env = 0.6 + 0.4 * math.sin(2.0 * math.pi * 4.0 * t)
        val = amplitude * env * (
            0.6 * math.sin(2.0 * math.pi * freq_hz * t)
            + 0.25 * math.sin(2.0 * math.pi * (freq_hz * 2.0) * t)
            + 0.15 * math.sin(2.0 * math.pi * (freq_hz * 3.0) * t)
        )
        samples.append(max(-32767, min(32767, int(val * 32767))))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buf.getvalue()


def make_silence_wav(duration_sec: float = 1.2) -> bytes:
    """Create a 16kHz mono WAV containing near-zero background silence."""
    sr = 16000
    n_samples = int(sr * duration_sec)
    samples = [0] * n_samples
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buf.getvalue()


SAMPLE_QUESTIONS_3 = [
    {
        "id": 101,
        "text": "Explain how you would optimize a machine learning pipeline for low-latency production inference.",
        "category": "Machine Learning Systems",
        "difficulty": "Advanced",
        "target_competencies": ["ML Pipeline Optimization", "Latency Reduction"],
        "expected_concepts": ["quantization", "batching", "caching", "feature store"],
    },
    {
        "id": 102,
        "text": "How do you detect and mitigate data drift in deployed models?",
        "category": "MLOps & Monitoring",
        "difficulty": "Standard",
        "target_competencies": ["Model Monitoring", "Data Drift"],
        "expected_concepts": ["PSI", "KL divergence", "retraining", "alerts"],
    },
    {
        "id": 103,
        "text": "Describe a time you resolved a critical production outage in a distributed service.",
        "category": "Behavioral (STAR Method)",
        "difficulty": "Standard",
        "target_competencies": ["Incident Response", "Root Cause Analysis"],
        "expected_concepts": ["monitoring", "rollback", "postmortem"],
    },
]


def run_all_12_scenarios():
    results = {}

    # Initialize session with Hema voice
    reset_live_session(
        candidate_name="Aarav",
        questions=SAMPLE_QUESTIONS_3,
        plan_metadata={
            "role": "Senior ML Engineer",
            "industry": "Artificial Intelligence, Software & IT",
            "interview_type": "Technical & System Design",
            "difficulty": "Advanced",
            "duration_minutes": 15,
            "voice_profile_id": VOICEBOX_PROFILES["Hema"],
            "interviewer_name": "Hema",
        },
        voice_profile_id=VOICEBOX_PROFILES["Hema"],
        interviewer_name="Hema",
        blocking_greeting=True,
    )

    # Confirm readiness to move to Question 1 (ID=101)
    ready_res = process_candidate_speech_blob(
        b"",
        browser_transcript="Yes, I am ready to begin.",
        speech_duration_ms=1400.0,
    )
    assert ready_res["status"] == "readiness_confirmed", f"Expected readiness_confirmed, got {ready_res['status']}"
    assert ready_res["current_question_id"] == 101
    assert ready_res["question_number"] == 1

    # -------------------------------------------------------------------------
    # Scenario 2: Candidate asks for clarification
    # -------------------------------------------------------------------------
    clar1_res = process_candidate_speech_blob(
        b"",
        browser_transcript="Sorry, can you explain the question again?",
        speech_duration_ms=1900.0,
    )
    s2_pass = (
        clar1_res["status"] == "question_clarified"
        and clar1_res["question_number"] == 1
        and clar1_res["current_question_id"] == 101
        and clar1_res["answered_count"] == 0
        and "CLARIFICATION_REQUESTED" in clar1_res["flow_state_history"]
    )
    results["Scenario 2: Candidate asks for clarification"] = (
        s2_pass,
        f"status={clar1_res['status']}, q_num={clar1_res['question_number']}, q_id={clar1_res['current_question_id']}, answered={clar1_res['answered_count']}",
    )
    assert s2_pass, f"Scenario 2 failed: {results['Scenario 2: Candidate asks for clarification']}"

    # -------------------------------------------------------------------------
    # Scenario 3: Candidate asks for clarification twice (no question advancement)
    # -------------------------------------------------------------------------
    clar2_res = process_candidate_speech_blob(
        b"",
        browser_transcript="Could you explain that in simple words and give me an example?",
        speech_duration_ms=2300.0,
    )
    s3_pass = (
        clar2_res["status"] == "question_clarified"
        and clar2_res["clarification_count"] == 2
        and clar2_res["question_number"] == 1
        and clar2_res["current_question_id"] == 101
        and clar2_res["answered_count"] == 0
    )
    results["Scenario 3: Candidate asks for clarification twice"] = (
        s3_pass,
        f"status={clar2_res['status']}, clarification_count={clar2_res.get('clarification_count')}, q_num={clar2_res['question_number']}, q_id={clar2_res['current_question_id']}",
    )
    assert s3_pass, f"Scenario 3 failed: {results['Scenario 3: Candidate asks for clarification twice']}"

    # -------------------------------------------------------------------------
    # Scenario 4: Candidate answers after clarification -> evaluated against Q1 (ID=101)
    # -------------------------------------------------------------------------
    ans1_text = (
        "To optimize our machine learning pipeline for low-latency inference, we applied INT8 model quantization "
        "in ONNX Runtime, cached high-frequency feature vectors in Redis, and used dynamic micro-batching, "
        "reducing p99 latency from 180 milliseconds to 28 milliseconds."
    )
    ans1_res = process_candidate_speech_blob(
        b"",
        browser_transcript=ans1_text,
        speech_duration_ms=8500.0,
    )
    rec_0 = ans1_res["session_records"][0] if ans1_res["session_records"] else {}
    s4_pass = (
        ans1_res["status"] == "next_question_asked"
        and ans1_res["answered_count"] == 1
        and rec_0.get("question", {}).get("id") == 101
        and rec_0.get("candidate_answer") == ans1_text
        and ans1_res["question_number"] == 2
        and ans1_res["current_question_id"] == 102
    )
    results["Scenario 4: Candidate answers after clarification"] = (
        s4_pass,
        f"recorded_q_id={rec_0.get('question', {}).get('id')}, score={getattr(rec_0.get('evaluation'), 'score', None)}, next_q_id={ans1_res['current_question_id']}",
    )
    assert s4_pass, f"Scenario 4 failed: {results['Scenario 4: Candidate answers after clarification']}"

    # -------------------------------------------------------------------------
    # Scenario 1: Candidate answers normally (on Q2, ID=102)
    # -------------------------------------------------------------------------
    ans2_text = (
        "We monitor Population Stability Index and KL divergence on input feature distributions daily, "
        "and trigger automated retraining pipelines when drift exceeds our threshold."
    )
    ans2_res = process_candidate_speech_blob(
        b"",
        browser_transcript=ans2_text,
        speech_duration_ms=6400.0,
    )
    rec_1 = ans2_res["session_records"][1] if len(ans2_res["session_records"]) > 1 else {}
    s1_pass = (
        ans2_res["status"] == "next_question_asked"
        and ans2_res["answered_count"] == 2
        and rec_1.get("question", {}).get("id") == 102
        and rec_1.get("candidate_answer") == ans2_text
        and ans2_res["question_number"] == 3
        and ans2_res["current_question_id"] == 103
    )
    results["Scenario 1: Candidate answers normally"] = (
        s1_pass,
        f"recorded_q_id={rec_1.get('question', {}).get('id')}, score={getattr(rec_1.get('evaluation'), 'score', None)}, advanced_to_q={ans2_res['question_number']}",
    )
    assert s1_pass, f"Scenario 1 failed: {results['Scenario 1: Candidate answers normally']}"

    # -------------------------------------------------------------------------
    # Scenario 5: Candidate remains silent (inactivity handling without inventing answer)
    # -------------------------------------------------------------------------
    inact_res = handle_inactivity_timeout()
    s5_pass = (
        inact_res["status"] == "inactivity_prompt"
        and inact_res["question_number"] == 3
        and inact_res["current_question_id"] == 103
        and inact_res["answered_count"] == 2
    )
    results["Scenario 5: Candidate remains silent"] = (
        s5_pass,
        f"status={inact_res['status']}, q_num={inact_res['question_number']}, answered_count={inact_res['answered_count']}",
    )
    assert s5_pass, f"Scenario 5 failed: {results['Scenario 5: Candidate remains silent']}"

    # -------------------------------------------------------------------------
    # Scenario 6: Background noise occurs (not treated as valid answer)
    # -------------------------------------------------------------------------
    silence_wav = make_silence_wav(1.2)
    noise_res1 = process_candidate_speech_blob(
        silence_wav,
        browser_transcript="Thank you for watching.",
        speech_duration_ms=900.0,
    )
    noise_res2 = process_candidate_speech_blob(
        b"",
        browser_transcript="uh um",
        speech_duration_ms=700.0,
    )
    s6_pass = (
        noise_res1["status"] == "empty_transcript"
        and noise_res2["status"] == "noise_ignored"
        and noise_res2["question_number"] == 3
        and noise_res2["current_question_id"] == 103
        and noise_res2["answered_count"] == 2
    )
    results["Scenario 6: Background noise occurs"] = (
        s6_pass,
        f"silence_status={noise_res1['status']}, filler_status={noise_res2['status']}, q_num={noise_res2['question_number']}, answered={noise_res2['answered_count']}",
    )
    assert s6_pass, f"Scenario 6 failed: {results['Scenario 6: Background noise occurs']}"

    # -------------------------------------------------------------------------
    # Scenario 7: Speech-to-text fails -> retry requested, no advancement
    # -------------------------------------------------------------------------
    speech_wav = make_synthetic_speech_wav(duration_sec=2.0, freq_hz=210.0)
    stt_fail_res = process_candidate_speech_blob(
        speech_wav,
        browser_transcript="",
        speech_duration_ms=2100.0,
        simulate_stt_failure=True,
    )
    s7_pass = (
        stt_fail_res["status"] == "retry_requested"
        and stt_fail_res["question_number"] == 3
        and stt_fail_res["current_question_id"] == 103
        and stt_fail_res["answered_count"] == 2
        and "TRANSCRIPTION_RETRY" in stt_fail_res["flow_state_history"]
    )
    results["Scenario 7: Speech-to-text fails"] = (
        s7_pass,
        f"status={stt_fail_res['status']}, q_num={stt_fail_res['question_number']}, q_id={stt_fail_res['current_question_id']}, state_logged=TRANSCRIPTION_RETRY",
    )
    assert s7_pass, f"Scenario 7 failed: {results['Scenario 7: Speech-to-text fails']}"

    # Capture runtime logs snapshot from this rich multi-event session before resetting for Scenarios 8-12
    sample_runtime_logs = list(get_live_state()["activity_logs"])

    # -------------------------------------------------------------------------
    # Scenario 8 & Scenario 9: Short meaningful answer + Duplicate audio submission
    # -------------------------------------------------------------------------
    reset_live_session(
        candidate_name="Aarav",
        questions=SAMPLE_QUESTIONS_3,
        plan_metadata={"role": "Data Scientist", "industry": "AI"},
        voice_profile_id=VOICEBOX_PROFILES["Sushma"],
        interviewer_name="Sushma",
        blocking_greeting=True,
    )
    process_candidate_speech_blob(b"", browser_transcript="I am ready", speech_duration_ms=1100.0)

    # Scenario 8: Short meaningful 2-word answer ("Model quantization")
    short_wav = make_synthetic_speech_wav(duration_sec=1.3, freq_hz=240.0)
    short_res = process_candidate_speech_blob(
        short_wav,
        browser_transcript="Model quantization",
        speech_duration_ms=1300.0,
    )
    s8_pass = (
        short_res["status"] == "next_question_asked"
        and short_res["answered_count"] == 1
        and short_res["session_records"][0]["candidate_answer"] == "Model quantization"
        and short_res["question_number"] == 2
    )
    results["Scenario 8: Candidate gives short meaningful answer"] = (
        s8_pass,
        f"status={short_res['status']}, answer='{short_res['session_records'][0]['candidate_answer']}', answered_count={short_res['answered_count']}",
    )
    assert s8_pass, f"Scenario 8 failed: {results['Scenario 8: Candidate gives short meaningful answer']}"

    # Scenario 9: Duplicate audio submission (sending identical audio bytes or same answer twice)
    dup_audio_res = process_candidate_speech_blob(
        short_wav,  # exact same audio_bytes SHA-256 hash already processed!
        browser_transcript="Some other text",
        speech_duration_ms=1300.0,
    )
    s9_pass = (
        dup_audio_res["status"] == "duplicate_answer_ignored"
        and dup_audio_res["answered_count"] == 1
        and dup_audio_res["question_number"] == 2
    )
    results["Scenario 9: Duplicate audio submission occurs"] = (
        s9_pass,
        f"status={dup_audio_res['status']}, answered_count={dup_audio_res['answered_count']} (not evaluated twice)",
    )
    assert s9_pass, f"Scenario 9 failed: {results['Scenario 9: Duplicate audio submission occurs']}"

    # -------------------------------------------------------------------------
    # Scenario 10: 10-question interview runs (all question IDs, transcripts, evaluations aligned)
    # -------------------------------------------------------------------------
    questions_10 = [
        {
            "id": i,
            "text": f"Question {i}: Explain your technical architecture and trade-offs for system component #{i}.",
            "category": "System Design",
            "difficulty": "Standard",
            "target_competencies": [f"Competency_{i}"],
            "expected_concepts": ["scalability", "latency", "reliability"],
        }
        for i in range(1, 11)
    ]
    reset_live_session(
        candidate_name="Aarav",
        questions=questions_10,
        plan_metadata={"role": "Principal Engineer", "industry": "Technology", "duration_minutes": 60},
        voice_profile_id=VOICEBOX_PROFILES["Chirag"],
        interviewer_name="Chirag",
        blocking_greeting=True,
    )
    process_candidate_speech_blob(b"", browser_transcript="Yes, let's start.", speech_duration_ms=1200.0)

    for i in range(1, 11):
        # On Question 4, also test a clarification before answering
        if i == 4:
            c_res = process_candidate_speech_blob(
                b"",
                browser_transcript="What do you mean by that?",
                speech_duration_ms=1500.0,
            )
            assert c_res["status"] == "question_clarified" and c_res["current_question_id"] == 4
        # On Question 7, test a repeat request before answering
        if i == 7:
            r_res = process_candidate_speech_blob(
                b"",
                browser_transcript="Can you repeat the question?",
                speech_duration_ms=1400.0,
            )
            assert r_res["status"] == "question_repeated" and r_res["current_question_id"] == 7

        ans_i = f"For component #{i}, we designed a horizontally scalable microservice with Redis caching and circuit breakers."
        turn_res = process_candidate_speech_blob(
            b"",
            browser_transcript=ans_i,
            speech_duration_ms=4200.0,
        )
        if i < 10:
            assert turn_res["status"] == "next_question_asked", f"Q{i} expected next_question_asked, got {turn_res['status']}"
            assert turn_res["current_question_id"] == i + 1
        else:
            assert turn_res["status"] == "finished", f"Q10 expected finished, got {turn_res['status']}"
            assert turn_res["finished"] is True

    final_10_state = get_live_state()
    recs_10 = final_10_state["session_records"]
    ids_aligned = [r["question"]["id"] for r in recs_10] == list(range(1, 11))
    transcripts_aligned = all(f"component #{i}" in recs_10[i - 1]["candidate_answer"] for i in range(1, 11))
    evals_present = all(recs_10[i - 1]["evaluation"] is not None for i in range(1, 11))
    s10_pass = len(recs_10) == 10 and ids_aligned and transcripts_aligned and evals_present and final_10_state["finished"]
    results["Scenario 10: 10-question interview runs"] = (
        s10_pass,
        f"records={len(recs_10)}/10, question_ids={[r['question']['id'] for r in recs_10]}, finished={final_10_state['finished']}",
    )
    assert s10_pass, f"Scenario 10 failed: {results['Scenario 10: 10-question interview runs']}"

    # -------------------------------------------------------------------------
    # Scenario 11: Interview ends without answers -> final score 0% and No Response
    # -------------------------------------------------------------------------
    prof_empty = CandidateProfile(
        candidate_name="Aarav",
        industry="Artificial Intelligence, Software & IT",
        target_role="Software Engineer",
        interview_type="Technical & System Design",
        experience_level="Mid-Level (3-5 yrs)",
        difficulty_tier="Standard",
    )
    unanswered_records = [
        QuestionSessionRecord(
            question=QuestionItem(
                id=k,
                category="Technical",
                interview_type="Technical",
                difficulty="Standard",
                question_text=f"Sample question {k}?",
                target_competencies=["Coding"],
                expected_concepts=["algorithms"],
            ),
            candidate_answer="",
            duration_seconds=0.0,
            evaluation=None,
        )
        for k in range(1, 6)
    ]
    zero_report = generate_universal_final_report(
        profile=prof_empty,
        session_records=unanswered_records,
        interview_mode="AUDIO",
    )
    s11_pass = (
        zero_report.overall_score == 0.0
        and zero_report.questions_answered_count == 0
        and zero_report.total_questions_asked == 5
        and zero_report.outcome == "No Response"
    )
    results["Scenario 11: Interview ends without answers"] = (
        s11_pass,
        f"overall_score={zero_report.overall_score}%, answered={zero_report.questions_answered_count}/{zero_report.total_questions_asked}, outcome='{zero_report.outcome}'",
    )
    assert s11_pass, f"Scenario 11 failed: {results['Scenario 11: Interview ends without answers']}"

    # -------------------------------------------------------------------------
    # Scenario 12: All four Voicebox IDs are tested (Hema, Sushma, Chirag, Manideep)
    # -------------------------------------------------------------------------
    voice_checks = {}
    for v_name, v_id in VOICEBOX_PROFILES.items():
        reset_live_session(
            candidate_name="Aarav",
            questions=SAMPLE_QUESTIONS_3[:2],
            plan_metadata={"role": "AI Engineer", "voice_profile_id": v_id, "interviewer_name": v_name},
            voice_profile_id=v_id,
            interviewer_name=v_name,
            blocking_greeting=True,
        )
        r_ready = process_candidate_speech_blob(b"", browser_transcript="I am ready", speech_duration_ms=1100.0)
        r_clar = process_candidate_speech_blob(b"", browser_transcript="Could you explain that?", speech_duration_ms=1300.0)
        r_ans = process_candidate_speech_blob(
            b"",
            browser_transcript="We use quantization and Redis caching to optimize model inference latency.",
            speech_duration_ms=4000.0,
        )
        logs_v = r_ans["activity_logs"]
        tts_events = [e for e in logs_v if "TTS Generation" in e["event"]]
        all_match_vid = len(tts_events) >= 3 and all(e["details"].get("voice_id") == v_id for e in tts_events)
        voice_checks[v_name] = (
            all_match_vid and r_ans["voice_profile_id"] == v_id and not r_ans["voice_error"],
            v_id,
            len(tts_events),
        )

    s12_pass = all(chk[0] for chk in voice_checks.values())
    results["Scenario 12: All four Voicebox IDs tested"] = (
        s12_pass,
        ", ".join(f"{k}({v[1]}: {v[2]} TTS logs)" for k, v in voice_checks.items()),
    )
    assert s12_pass, f"Scenario 12 failed: {results['Scenario 12: All four Voicebox IDs tested']}"

    print("\n" + "=" * 95)
    print(" ALL 12 ACCEPTANCE SCENARIOS VERIFICATION RESULTS")
    print("=" * 95)
    for idx, (sc_name, (passed, detail)) in enumerate(results.items(), 1):
        print(f"[{idx:02d}] {'PASS' if passed else 'FAIL'} | {sc_name:<48} | {detail}")
    print("=" * 95)

    print("\nSAMPLE ACTUAL RUNTIME ACTIVITY LOG TABLE:")
    print(format_activity_logs_as_text(sample_runtime_logs))


if __name__ == "__main__":
    run_all_12_scenarios()
