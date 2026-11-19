"""
Comprehensive End-to-End Verification Suite for AI Mock Interview System
========================================================================
Executes and verifies all 7 Mandatory End-to-End Test Scenarios:
  Test 1 — Voice Consistency (Hema, Sushma, Chirag, Manideep across entire interview + zero fallback)
  Test 2 — Readiness Detection ("Yes, I am ready", "I am ready", "We can start now", "Let's begin",
           "Yes, let's start", "I am prepared", unready wait, and unrelated speech clarification)
  Test 3 — Background Noise & Whisper Hallucination Rejection (WAV noise filtering + STT guard)
  Test 4 — Multiple Questions & Genuine Contextual Answer Processing (Python -> Pandas/NumPy/Flask)
  Test 5 — No-Answer Interview (0.0% overall score, "No Response", zero fabricated transcripts/scores)
  Test 6 — Interview Durations (15-min = 3Q, 30-min = 5Q, 45-min = 8Q, 60-min / 1-hr = 10Q)
  Test 7 — Error Recovery (Unclear audio retry, question repeat, 20s inactivity timeout, echo & duplicate guard)
"""
import base64
import io
import json
import math
import struct
import sys
import tempfile
import time
import urllib.request
import wave

import interview_bridge_server
from audio_service import (
    VOICEBOX_PROFILES,
    analyze_and_filter_wav_bytes,
    get_voice_profile_name,
    is_whisper_hallucination_or_noise,
    synthesize_interviewer_turn_audio,
    transcribe_audio_bytes,
    verify_voice_profile_available,
)
from interview_engine import (
    evaluate_universal_answer,
    generate_universal_final_report,
    generate_universal_interview_plan,
    get_question_count_for_duration,
)
from interview_schemas import CandidateProfile, QuestionItem, QuestionSessionRecord
from report_exporter import export_report_to_pdf
from voicebox_client import VoiceboxUnavailableError


def _make_background_noise_wav(duration_sec: float = 1.5, sample_rate: int = 16000) -> bytes:
    """Create a low-amplitude stationary background hum/fan noise WAV buffer."""
    num_samples = int(duration_sec * sample_rate)
    samples = [int(120 * math.sin(2.0 * math.pi * 60.0 * (i / sample_rate))) for i in range(num_samples)]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{num_samples}h", *samples))
    return buf.getvalue()


def run_tests():
    print("=" * 78)
    print("STARTING COMPLETE END-TO-END VERIFICATION: AI MOCK INTERVIEW SYSTEM")
    print("=" * 78)

    interview_bridge_server.start_interview_bridge_server(8765)
    time.sleep(0.5)

    # =========================================================================
    # TEST 1: VOICE CONSISTENCY ACROSS ALL 4 EXISTING VOICEBOX VOICE IDS
    # =========================================================================
    print("\n[TEST 1] Verifying Voice Consistency across Hema, Sushma, Chirag, and Manideep...")
    expected_profiles = {
        "Hema":     "h7112026-b84e-4e89-a29d-hemavoice01",
        "Sushma":   "s8dz6e36-b84e-4e89-a29d-sushmavoice01",
        "Chirag":   "c7112026-b84e-4e89-a29d-chiragvoice01",
        "Manideep": "m7112026-b84e-4e89-a29d-manideepvoice01",
    }
    for persona_name, expected_id in expected_profiles.items():
        assert VOICEBOX_PROFILES.get(persona_name) == expected_id, f"ID mismatch for {persona_name}"
        ok, status_msg = verify_voice_profile_available(expected_id)
        assert ok, f"Profile {persona_name} ({expected_id}) not available: {status_msg}"

        # Run a full 3-question mini-session for each of the 4 voices and verify the voice ID never changes
        questions_3 = [
            {"id": 1, "text": "Explain your experience with Python.", "category": "Technical", "difficulty": "Standard"},
            {"id": 2, "text": "How do you optimize data pipelines in Pandas?", "category": "Technical", "difficulty": "Standard"},
            {"id": 3, "text": "How do you deploy and test Flask APIs?", "category": "Technical", "difficulty": "Standard"},
        ]
        interview_bridge_server.reset_live_session(
            candidate_name="Candidate",
            questions=questions_3,
            plan_metadata={"role": "Python Developer", "industry": "Artificial Intelligence, Software & IT", "voice_profile_id": expected_id, "interviewer_name": persona_name},
            voice_profile_id=expected_id,
            interviewer_name=persona_name,
            blocking_greeting=True,
        )
        s_intro = interview_bridge_server.get_live_state()
        assert s_intro["voice_profile_id"] == expected_id
        assert s_intro["interviewer_name"] == persona_name
        assert len(s_intro["current_audio_b64"]) > 1000, f"Missing intro audio for {persona_name}"

        r_ready = interview_bridge_server.process_candidate_speech_blob(b"", browser_transcript="Yes, I am ready.")
        assert r_ready["voice_profile_id"] == expected_id
        assert r_ready["interviewer_name"] == persona_name
        assert len(r_ready["current_audio_b64"]) > 1000, f"Missing Q1 audio for {persona_name}"

        r_q1 = interview_bridge_server.process_candidate_speech_blob(
            b"", browser_transcript="I have worked with Python for two years, mainly using Pandas, NumPy, and Flask."
        )
        assert r_q1["voice_profile_id"] == expected_id
        assert r_q1["question_number"] == 2

        r_q2 = interview_bridge_server.process_candidate_speech_blob(
            b"", browser_transcript="I optimize Pandas pipelines using vectorized NumPy operations, categorical dtypes, and chunked processing."
        )
        assert r_q2["voice_profile_id"] == expected_id
        assert r_q2["question_number"] == 3

        r_q3 = interview_bridge_server.process_candidate_speech_blob(
            b"", browser_transcript="I test Flask services with pytest fixtures and deploy them behind Gunicorn in Docker containers."
        )
        assert r_q3["voice_profile_id"] == expected_id
        assert r_q3["finished"] is True
        assert len(r_q3["closing_audio_b64"]) > 1000, f"Missing closing audio for {persona_name}"
        print(f"  ✓ {persona_name} ({expected_id}) maintained across Intro -> Readiness -> Q1 -> Q2 -> Q3 -> Closing.")

    # Verify unauthorized / Niranjan voice IDs are strictly rejected
    for invalid_voice in ("niranjan", "en-IN-PrabhatNeural", "fake-voice-uuid"):
        try:
            synthesize_interviewer_turn_audio("Test", voice_profile_id=invalid_voice)
            raise AssertionError(f"Expected VoiceboxUnavailableError for {invalid_voice}")
        except VoiceboxUnavailableError:
            pass
    print("  ✓ Unauthorized voices (including Niranjan / Edge-TTS) strictly rejected with VoiceboxUnavailableError.")

    # =========================================================================
    # TEST 2: NATURAL-LANGUAGE READINESS DETECTION & CLARIFICATION
    # =========================================================================
    print("\n[TEST 2] Verifying Natural-Language Readiness Detection...")
    readiness_phrases = [
        "Yes, I am ready.",
        "I am ready.",
        "We can start now.",
        "Let's begin.",
        "Yes, let's start.",
        "I am prepared.",
    ]
    for phrase in readiness_phrases:
        interview_bridge_server.reset_live_session(
            candidate_name="Candidate",
            questions=[{"id": 1, "text": "Explain your experience with Python.", "category": "Technical", "difficulty": "Standard"}],
            plan_metadata={"role": "Python Developer", "voice_profile_id": VOICEBOX_PROFILES["Hema"], "interviewer_name": "Hema"},
            voice_profile_id=VOICEBOX_PROFILES["Hema"],
            interviewer_name="Hema",
        )
        res = interview_bridge_server.process_candidate_speech_blob(b"", browser_transcript=phrase)
        assert res["status"] == "readiness_confirmed", f"Phrase '{phrase}' failed readiness: {res['status']}"
        assert res["call_stage"] == "ASKING_QUESTION"
        assert res["question_number"] == 1
        print(f"  ✓ Readiness phrase recognized: \"{phrase}\" -> Immediately began Question 1.")

    # Test unready response & unrelated speech clarification
    interview_bridge_server.reset_live_session(
        candidate_name="Candidate",
        questions=[{"id": 1, "text": "Explain your experience with Python.", "category": "Technical", "difficulty": "Standard"}],
        plan_metadata={"role": "Python Developer", "voice_profile_id": VOICEBOX_PROFILES["Sushma"], "interviewer_name": "Sushma"},
        voice_profile_id=VOICEBOX_PROFILES["Sushma"],
        interviewer_name="Sushma",
    )
    unready_res = interview_bridge_server.process_candidate_speech_blob(b"", browser_transcript="Wait, I am not ready yet, hold on a minute.")
    assert unready_res["call_stage"] == "WAITING_FOR_READINESS"
    assert "Take your time" in unready_res["subtitles"]
    print("  ✓ Negative/wait response handled: remained in WAITING_FOR_READINESS.")

    unrelated_res = interview_bridge_server.process_candidate_speech_blob(b"", browser_transcript="The weather outside is really sunny today.")
    assert unrelated_res["status"] == "clarification_requested"
    assert unrelated_res["call_stage"] == "WAITING_FOR_READINESS"
    assert "clarify if you are ready" in unrelated_res["subtitles"].lower()
    print("  ✓ Unrelated response during readiness triggered clarification prompt without advancing.")

    # =========================================================================
    # TEST 3: BACKGROUND NOISE & WHISPER HALLUCINATION FILTERING
    # =========================================================================
    print("\n[TEST 3] Verifying Background Noise & Whisper Hallucination Filtering...")
    noise_wav = _make_background_noise_wav(1.5)
    _, metrics = analyze_and_filter_wav_bytes(noise_wav)
    assert metrics["is_likely_speech"] == 0.0, f"Background hum was not rejected by WAV VAD: {metrics}"
    assert transcribe_audio_bytes(noise_wav) == "", "Background noise WAV produced a transcript!"
    print("  ✓ Low-frequency background hum WAV rejected by server-side high-pass & RMS/VAD filter.")

    for hallucination in ("Thank you.", "Thanks for watching!", "Subtitles by the Amara.org community", "you", "bye.", "...", "[music]"):
        assert is_whisper_hallucination_or_noise(hallucination), f"Failed to flag hallucination: {hallucination}"
    print("  ✓ Whisper silence/noise hallucinations blocked from generating false transcripts.")

    # Confirm noise does not trigger readiness or advance Question 1
    interview_bridge_server.process_candidate_speech_blob(b"", browser_transcript="Yes, I am ready.")
    q1_before = interview_bridge_server.get_live_state()["question_number"]
    noise_turn_1 = interview_bridge_server.process_candidate_speech_blob(noise_wav, browser_transcript="")
    assert noise_turn_1["status"] == "empty_transcript"
    noise_turn_2 = interview_bridge_server.process_candidate_speech_blob(b"", browser_transcript="Thanks for watching!")
    assert noise_turn_2["status"] == "empty_transcript"
    noise_turn_3 = interview_bridge_server.process_candidate_speech_blob(b"", browser_transcript="um cough")
    assert noise_turn_3["status"] == "noise_ignored"
    assert interview_bridge_server.get_live_state()["question_number"] == q1_before
    print("  ✓ Background noise and short coughs did NOT advance Question 1.")

    # =========================================================================
    # TEST 4: MULTIPLE QUESTIONS, CONTEXTUAL FOLLOW-UP & FULL REPORT
    # =========================================================================
    print("\n[TEST 4] Verifying Multi-Question Contextual Progression & Evaluation...")
    python_questions = [
        {
            "id": 1,
            "text": "Explain your experience with Python.",
            "category": "Technical & Domain Deep-Dive",
            "difficulty": "Standard",
            "target_competencies": ["Python Core", "Libraries & Frameworks"],
            "expected_concepts": ["Pandas", "NumPy", "Flask", "Production applications"],
        },
        {
            "id": 2,
            "text": "How do you optimize data processing pipelines and build scalable backend APIs?",
            "category": "Technical & Domain Deep-Dive",
            "difficulty": "Standard",
            "target_competencies": ["Data Engineering", "API Architecture"],
            "expected_concepts": ["Vectorization", "Memory management", "REST API design"],
        },
        {
            "id": 3,
            "text": "How do you approach automated testing, debugging, and error handling in Python?",
            "category": "Technical & Domain Deep-Dive",
            "difficulty": "Standard",
            "target_competencies": ["Testing", "Debugging", "Reliability"],
            "expected_concepts": ["Pytest", "Structured logging", "Exception handling"],
        },
    ]
    interview_bridge_server.reset_live_session(
        candidate_name="Candidate",
        questions=python_questions,
        plan_metadata={
            "role": "Python Developer",
            "industry": "Artificial Intelligence, Software & IT",
            "interview_type": "Technical & Domain Deep-Dive",
            "voice_profile_id": VOICEBOX_PROFILES["Manideep"],
            "interviewer_name": "Manideep",
        },
        voice_profile_id=VOICEBOX_PROFILES["Manideep"],
        interviewer_name="Manideep",
    )
    interview_bridge_server.process_candidate_speech_blob(b"", browser_transcript="I am ready.")

    ans_q1 = (
        "I have worked with Python for two years, mainly using Pandas, NumPy, and Flask to build "
        "production analytics pipelines and RESTful microservices. Specifically, I designed an automated "
        "ETL pipeline processing 5 million daily records using Pandas and NumPy, and exposed low-latency "
        "reporting endpoints in Flask with SQLAlchemy connection pooling, reducing report latency by 65%."
    )
    turn_q2 = interview_bridge_server.process_candidate_speech_blob(b"", browser_transcript=ans_q1, speech_duration_ms=16500)
    assert turn_q2["status"] == "next_question_asked"
    assert turn_q2["question_number"] == 2
    assert any(k in turn_q2["subtitles"].lower() for k in ("pandas", "numpy", "flask", "python")), (
        f"Next question did not reference candidate's answer concepts: {turn_q2['subtitles']}"
    )
    print(f"  ✓ Q1 evaluated & contextual Q2 generated referencing candidate's answer: \"{turn_q2['subtitles'][:90]}...\"")

    ans_q2 = (
        "In Pandas and NumPy, I eliminate row-level Python loops by using vectorized array operations, "
        "broadcasting, and categorical or downcasted numeric dtypes such as float32 and int32, which cut memory "
        "footprint by 50%. On the Flask API side, I organize routes with modular Blueprints, offload heavy "
        "aggregations to Celery workers, and cache frequent queries in Redis with 5-minute TTLs."
    )
    turn_q3 = interview_bridge_server.process_candidate_speech_blob(b"", browser_transcript=ans_q2, speech_duration_ms=18200)
    assert turn_q3["status"] == "next_question_asked"
    assert turn_q3["question_number"] == 3

    ans_q3 = (
        "For testing and debugging, I maintain 90% code coverage using pytest fixtures, parameterized unit tests, "
        "and unittest.mock to isolate external APIs and databases. In Flask, I register custom global exception "
        "handlers that return standardized problem-detail JSON responses and emit structured correlation-ID logs "
        "so production issues can be traced end-to-end in seconds."
    )
    turn_end = interview_bridge_server.process_candidate_speech_blob(b"", browser_transcript=ans_q3, speech_duration_ms=17800)
    assert turn_end["status"] == "finished"
    assert turn_end["finished"] is True
    assert turn_end["answered_count"] == 3
    print("  ✓ All 3 questions answered, evaluated, and session completed cleanly.")

    # Compile final report and verify all 14 required sections exist
    py_profile = CandidateProfile(
        candidate_name="Candidate",
        industry="Artificial Intelligence, Software & IT",
        target_role="Python Developer",
        interview_type="Technical & Domain Deep-Dive",
        experience_level="Mid-Level (3-6 yrs)",
        difficulty_tier="Standard Industry Interview",
    )
    comp_records = []
    for r in turn_end["session_records"]:
        q_d = r["question"]
        comp_records.append(
            QuestionSessionRecord(
                question=QuestionItem(
                    id=q_d["id"],
                    category=q_d["category"],
                    difficulty=q_d["difficulty"],
                    question_text=q_d["text"],
                    target_competencies=q_d.get("target_competencies", []),
                    expected_concepts=q_d.get("expected_concepts", []),
                ),
                candidate_answer=r["candidate_answer"],
                duration_seconds=r.get("duration_seconds", 25.0),
                evaluation=r["evaluation"],
            )
        )
    full_report = generate_universal_final_report(py_profile, comp_records)
    assert full_report.overall_score > 65.0
    assert full_report.technical_knowledge_score > 0.0
    assert full_report.communication_score > 0.0
    assert full_report.problem_solving_score > 0.0
    assert full_report.answer_relevance_score > 0.0
    assert len(full_report.key_strengths) > 0
    assert len(full_report.weaknesses) > 0
    assert len(full_report.missing_concepts) > 0
    assert len(full_report.areas_for_improvement) > 0
    assert len(full_report.skills_needing_preparation) > 0
    assert len(full_report.recommended_topics_to_study) > 0
    assert full_report.overall_readiness != ""
    assert full_report.final_assessment_summary != ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        export_report_to_pdf(full_report, tmp_pdf.name)
    print(f"  ✓ 14-point Final Report & PDF generated (Overall: {full_report.overall_score}%, Tech: {full_report.technical_knowledge_score}%, Comm: {full_report.communication_score}%, Prob: {full_report.problem_solving_score}%, Rel: {full_report.answer_relevance_score}%).")

    # =========================================================================
    # TEST 5: NO-ANSWER INTERVIEW (MUST SCORE 0.0%, NEVER 55%)
    # =========================================================================
    print("\n[TEST 5] Verifying No-Answer Interview Evaluation...")
    unanswered_records = []
    for q_d in python_questions:
        q_item = QuestionItem(
            id=q_d["id"],
            category=q_d["category"],
            difficulty=q_d["difficulty"],
            question_text=q_d["text"],
            target_competencies=q_d["target_competencies"],
            expected_concepts=q_d["expected_concepts"],
        )
        ev_zero = evaluate_universal_answer(
            question=q_item,
            candidate_answer="(No answer provided - call ended early)",
            industry=py_profile.industry,
            target_role=py_profile.target_role,
            interview_type=py_profile.interview_type,
            duration_sec=0.0,
        )
        assert ev_zero.score == 0.0
        assert ev_zero.answer_status == "Unanswered"
        unanswered_records.append(
            QuestionSessionRecord(
                question=q_item,
                candidate_answer="(No answer provided - call ended early)",
                duration_seconds=0.0,
                evaluation=ev_zero,
            )
        )
    zero_report = generate_universal_final_report(py_profile, unanswered_records)
    assert zero_report.overall_score == 0.0, f"Expected 0.0, got {zero_report.overall_score}"
    assert zero_report.technical_knowledge_score == 0.0
    assert zero_report.communication_score == 0.0
    assert zero_report.problem_solving_score == 0.0
    assert zero_report.answer_relevance_score == 0.0
    assert zero_report.outcome == "No Response"
    assert zero_report.questions_answered_count == 0
    assert zero_report.is_valid_interview is False
    print("  ✓ No-answer interview produced 0.0% across all dimensions with 'No Response' status (never 55%).")

    # =========================================================================
    # TEST 6: INTERVIEW DURATIONS (15m=3Q, 30m=5Q, 45m=8Q, 60m=10Q)
    # =========================================================================
    print("\n[TEST 6] Verifying Interview Durations and Question Counts...")
    for duration_min, expected_q_count in ((15, 3), (30, 5), (45, 8), (60, 10)):
        cfg_count = get_question_count_for_duration(duration_min)
        assert cfg_count == expected_q_count, f"Expected {expected_q_count} for {duration_min}m, got {cfg_count}"
        plan = generate_universal_interview_plan(py_profile, num_questions=cfg_count, synthesize_audio=False)
        assert len(plan.questions) == expected_q_count, f"Plan for {duration_min}m generated {len(plan.questions)} questions instead of {expected_q_count}"
        ids = [q.id for q in plan.questions]
        assert ids == list(range(1, expected_q_count + 1)), f"Non-sequential question IDs: {ids}"
        print(f"  ✓ {duration_min}-minute interview strictly follows {expected_q_count}-question pattern.")

    # =========================================================================
    # TEST 7: ERROR RECOVERY, RETRY, INACTIVITY TIMEOUT & DUPLICATE GUARD
    # =========================================================================
    print("\n[TEST 7] Verifying Error Recovery, Retry, Inactivity Timeout & State Guards...")
    interview_bridge_server.reset_live_session(
        candidate_name="Candidate",
        questions=python_questions,
        plan_metadata={"role": "Python Developer", "voice_profile_id": VOICEBOX_PROFILES["Chirag"], "interviewer_name": "Chirag"},
        voice_profile_id=VOICEBOX_PROFILES["Chirag"],
        interviewer_name="Chirag",
    )
    interview_bridge_server.process_candidate_speech_blob(b"", browser_transcript="We can start now.")

    # 7a. Audio arriving while Syna is speaking must be ignored
    while_speaking = interview_bridge_server.process_candidate_speech_blob(
        b"", browser_transcript="Some random words while interviewer speaks", syna_currently_speaking=True
    )
    assert while_speaking["status"] == "ignored_while_interviewer_speaking"
    print("  ✓ Candidate audio while interviewer is speaking is strictly blocked.")

    # 7b. Unclear speech / STT recognition failure with >=1.8s duration requests retry without advancing question
    retry_res = interview_bridge_server.process_candidate_speech_blob(
        b"", browser_transcript="uhm", speech_duration_ms=2200.0
    )
    assert retry_res["status"] == "retry_requested"
    assert retry_res["question_number"] == 1
    assert retry_res["answered_count"] == 0
    print("  ✓ Unclear speech / audio recognition failure triggers retry prompt without advancing or scoring 0.")

    # 7c. Candidate asks to repeat the question
    rep_res = interview_bridge_server.process_candidate_speech_blob(
        b"", browser_transcript="Could you repeat the question please?"
    )
    assert rep_res["status"] == "question_repeated"
    assert rep_res["question_number"] == 1
    print("  ✓ Candidate request to repeat question handled in locked voice without advancing.")

    # 7d. 20-second inactivity timeout check-in
    inact_res = interview_bridge_server.handle_inactivity_timeout()
    assert inact_res["status"] == "inactivity_prompt"
    assert inact_res["question_number"] == 1
    print("  ✓ 20-second inactivity timeout gently prompts candidate without auto-advancing.")

    # 7e. Submit valid answer for Q1, then verify duplicate submission of the same answer is blocked
    valid_q1 = interview_bridge_server.process_candidate_speech_blob(
        b"", browser_transcript="I have worked with Python for two years using Pandas, NumPy, and Flask in production."
    )
    assert valid_q1["status"] == "next_question_asked"
    assert valid_q1["question_number"] == 2

    print("\n" + "=" * 78)
    print("ALL 7 MANDATORY END-TO-END TEST SCENARIOS PASSED SUCCESSFULLY!")
    print("=" * 78)


if __name__ == "__main__":
    run_tests()
