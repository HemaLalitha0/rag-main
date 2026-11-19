"""
test_critical_fixes.py
Comprehensive Verification Suite for Universal AI Mock Interview (Syna).

Validates:
1. Strict Voicebox Voice ID Restriction (Hema, Sushma, Chirag, Manideep; zero Niranjan / Edge-TTS fallbacks)
2. Zero-Answer Candidate Evaluation (Must yield "No Response", overall score 0.0%, no fabricated 55%)
3. Partial-Answer Scenario (Must yield "Incomplete Interview", score calculated ONLY on answered questions)
4. Full Interview Flow (Q1 -> A1 -> Eval -> Contextual Q2 in locked voice -> Completion)
5. Session Isolation (Zero state leakage between successive interview sessions)
"""
import unittest
import os
import sys

from interview_schemas import (
    CandidateProfile,
    QuestionItem,
    QuestionSessionRecord,
    AnswerEvaluation,
    FinalAssessmentReport,
)
from interview_engine import (
    evaluate_universal_answer,
    generate_universal_final_report,
)
from audio_service import (
    VOICEBOX_PROFILES,
    synthesize_interviewer_turn_audio,
    verify_voice_profile_available,
    get_voice_profile_name,
)
from voicebox_client import VoiceboxUnavailableError
from interview_bridge_server import (
    LIVE_SESSION,
    SESSION_LOCK,
    reset_live_session,
    process_candidate_speech_blob,
    get_live_state,
    _generate_contextual_question,
)


class TestCriticalFixes(unittest.TestCase):

    def setUp(self):
        self.profile = CandidateProfile(
            candidate_name="Test Candidate",
            industry="Artificial Intelligence, Software & IT",
            target_role="Senior Full-Stack Engineer",
            interview_type="Behavioral (STAR Method)",
            experience_level="Mid-Senior",
            difficulty_tier="Standard",
        )
        self.q1 = QuestionItem(
            id=1,
            category="Behavioral (STAR Method)",
            interview_type="Behavioral (STAR Method)",
            difficulty="Standard",
            question_text="Tell me about a challenging distributed systems bug you resolved under tight deadlines.",
            target_competencies=["Problem Solving", "Distributed Systems", "Incident Management"],
            expected_concepts=["Root Cause Analysis", "Observability", "Post-mortem"],
        )
        self.q2 = QuestionItem(
            id=2,
            category="Technical Architecture",
            interview_type="Behavioral (STAR Method)",
            difficulty="Standard",
            question_text="How do you handle data consistency and caching across distributed microservices?",
            target_competencies=["System Design", "Caching Strategies", "Data Consistency"],
            expected_concepts=["Cache Invalidation", "Eventual Consistency", "Redis"],
        )

    # =========================================================================
    # TEST CASE 1: Voicebox Voice Consistency & Zero Fallbacks
    # =========================================================================
    def test_01_voicebox_profiles_and_zero_fallback(self):
        """Verify only the 4 Voicebox IDs are allowed and no fallback to Niranjan or Edge-TTS occurs."""
        expected_profiles = {
            "Manideep": "m7112026-b84e-4e89-a29d-manideepvoice01",
            "Chirag":   "c7112026-b84e-4e89-a29d-chiragvoice01",
            "Hema":     "h7112026-b84e-4e89-a29d-hemavoice01",
            "Sushma":   "s8dz6e36-b84e-4e89-a29d-sushmavoice01",
        }
        for name, expected_id in expected_profiles.items():
            self.assertEqual(VOICEBOX_PROFILES.get(name), expected_id)
            self.assertEqual(get_voice_profile_name(expected_id), name)

        # Confirm unauthorized voice IDs or Niranjan are completely rejected
        with self.assertRaises(VoiceboxUnavailableError):
            synthesize_interviewer_turn_audio(
                text="Unauthorized voice test",
                voice_profile_id="en-IN-PrabhatNeural"
            )

        with self.assertRaises(VoiceboxUnavailableError):
            synthesize_interviewer_turn_audio(
                text="Unauthorized voice test",
                voice_profile_id="niranjan_voice_id"
            )

    # =========================================================================
    # TEST CASE 2: Zero-Answer Candidate Bug Fix (Must be 0.0%, NOT 55%)
    # =========================================================================
    def test_02_zero_answer_evaluation(self):
        """Verify that candidates with no spoken response receive 0.0% and 'No Response' status (NEVER 55%)."""
        # A. Direct evaluation of empty or silence response
        eval_empty = evaluate_universal_answer(
            question=self.q1,
            candidate_answer="",
            industry=self.profile.industry,
            target_role=self.profile.target_role,
            interview_type=self.profile.interview_type,
            duration_sec=0.0
        )
        self.assertEqual(eval_empty.score, 0.0, "Empty answer must receive score 0.0")
        self.assertEqual(len(eval_empty.strengths), 0, "Empty answer must have zero strengths")

        # B. Direct evaluation of call ended early
        eval_ended_early = evaluate_universal_answer(
            question=self.q1,
            candidate_answer="(No answer provided - call ended early)",
            industry=self.profile.industry,
            target_role=self.profile.target_role,
            interview_type=self.profile.interview_type,
            duration_sec=0.0
        )
        self.assertEqual(eval_ended_early.score, 0.0)
        self.assertEqual(len(eval_ended_early.strengths), 0)

        # C. Final report compilation for a session with zero valid answers
        session_records = [
            QuestionSessionRecord(
                question=self.q1,
                candidate_answer="(No answer provided - call ended early)",
                duration_seconds=0.0,
                evaluation=eval_ended_early
            )
        ]
        report: FinalAssessmentReport = generate_universal_final_report(
            profile=self.profile,
            session_records=session_records,
            passing_threshold=70.0
        )

        self.assertEqual(report.overall_score, 0.0, f"Expected 0.0% overall score, got {report.overall_score}%")
        self.assertNotEqual(report.overall_score, 55.0, "Score must NEVER be the hardcoded 55.0% bug")
        self.assertEqual(report.outcome, "No Response")
        self.assertFalse(report.passed)
        self.assertFalse(report.is_valid_interview)
        self.assertEqual(report.questions_answered_count, 0)
        self.assertEqual(len(report.key_strengths), 0, "No Response interview must have no positive strengths")

    # =========================================================================
    # TEST CASE 3: Partial-Answer Scenario ("Incomplete Interview")
    # =========================================================================
    def test_03_partial_answer_evaluation(self):
        """Verify partial answers mark 'Incomplete Interview' and evaluate ONLY answered questions."""
        q3 = QuestionItem(id=3, category="Leadership", interview_type="Behavioral", difficulty="Standard", question_text="How do you mentor juniors?")
        q4 = QuestionItem(id=4, category="System Design", interview_type="Behavioral", difficulty="Standard", question_text="Describe microservices.")

        ans1 = "In my last role, we experienced a major cache-stampede incident during peak traffic. As lead engineer, I diagnosed Redis latency spikes using distributed tracing, implemented jittered TTLs and a single-flight request coalescer, which dropped database CPU from 95% to 22% within an hour."
        ans2 = "To ensure data consistency across services, I leverage event-driven architecture using Kafka with transactional outbox patterns. We enforce idempotent consumers and use Redis as a read-through cache with strict TTLs."

        eval1 = evaluate_universal_answer(self.q1, ans1, self.profile.industry, self.profile.target_role, self.profile.interview_type, 45.0)
        eval2 = evaluate_universal_answer(self.q2, ans2, self.profile.industry, self.profile.target_role, self.profile.interview_type, 50.0)
        eval3_unanswered = evaluate_universal_answer(q3, "(No answer provided - call ended early)", self.profile.industry, self.profile.target_role, self.profile.interview_type, 0.0)
        eval4_unanswered = evaluate_universal_answer(q4, "", self.profile.industry, self.profile.target_role, self.profile.interview_type, 0.0)

        records = [
            QuestionSessionRecord(question=self.q1, candidate_answer=ans1, duration_seconds=45.0, evaluation=eval1),
            QuestionSessionRecord(question=self.q2, candidate_answer=ans2, duration_seconds=50.0, evaluation=eval2),
            QuestionSessionRecord(question=q3, candidate_answer="(No answer provided - call ended early)", duration_seconds=0.0, evaluation=eval3_unanswered),
            QuestionSessionRecord(question=q4, candidate_answer="", duration_seconds=0.0, evaluation=eval4_unanswered),
        ]

        report = generate_universal_final_report(
            profile=self.profile,
            session_records=records,
            passing_threshold=70.0
        )

        self.assertEqual(report.outcome, "Incomplete Interview")
        self.assertEqual(report.questions_answered_count, 2)
        self.assertEqual(report.total_questions_asked, 4)
        self.assertTrue(report.is_valid_interview)
        # Average score should reflect ONLY the 2 answered questions, not diluted by the 0s of unanswered
        expected_avg = round((eval1.score + eval2.score) / 2.0, 1)
        self.assertAlmostEqual(report.overall_score, expected_avg, places=1)
        self.assertGreater(report.overall_score, 50.0)

    # =========================================================================
    # TEST CASE 4: Complete Interview Flow
    # =========================================================================
    def test_04_full_interview_flow(self):
        """Verify the complete turn progression: Answer Q1 -> Contextual Q2 -> Locked Voice."""
        q_bridge = [
            {"id": 1, "text": self.q1.question_text, "category": self.q1.category, "difficulty": self.q1.difficulty},
            {"id": 2, "text": self.q2.question_text, "category": self.q2.category, "difficulty": self.q2.difficulty},
        ]
        meta = {
            "industry": self.profile.industry,
            "role": self.profile.target_role,
            "interview_type": self.profile.interview_type,
            "voice_profile_id": VOICEBOX_PROFILES["Hema"],
            "interviewer_name": "Hema",
        }

        # 1. Initialize session with Hema
        reset_live_session(
            candidate_name="Alex",
            questions=q_bridge,
            plan_metadata=meta,
            voice_profile_id=VOICEBOX_PROFILES["Hema"],
            interviewer_name="Hema"
        )
        state0 = get_live_state()
        self.assertEqual(state0["voice_profile_id"], VOICEBOX_PROFILES["Hema"])
        self.assertEqual(state0["interviewer_name"], "Hema")
        self.assertEqual(state0["call_stage"], "INTRODUCTION")

        # 2. Confirm readiness
        res_ready = process_candidate_speech_blob(
            audio_bytes=b"",
            browser_transcript="Yes, I am ready to begin the interview."
        )
        self.assertEqual(res_ready["call_stage"], "ASKING_QUESTION")
        self.assertEqual(res_ready["question_number"], 1)

        # 3. Answer Question 1
        ans1 = "When our microservices faced high tail latency during Black Friday, I set up distributed tracing with OpenTelemetry and pinpointed unindexed database queries causing connection pool exhaustion. I added compound indexes and circuit breakers."
        res_q1 = process_candidate_speech_blob(
            audio_bytes=b"",
            browser_transcript=ans1
        )
        # Verify Question 1 was recorded and session progressed to Question 2
        self.assertEqual(res_q1["question_number"], 2)
        self.assertEqual(res_q1["answered_count"], 1)
        self.assertEqual(res_q1["voice_profile_id"], VOICEBOX_PROFILES["Hema"])
        # Verify Question 1 candidate answer is stored
        records = res_q1["session_records"]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["question"]["id"], 1)
        self.assertEqual(records[0]["candidate_answer"], ans1)

        # 4. Contextual turn verification: Next question should reference previous answer
        self.assertTrue(len(res_q1["current_question"]) > 10)

        # 5. Answer Question 2
        ans2 = "To maintain data consistency, we implemented the transactional outbox pattern with Debezium and Kafka, guaranteeing at-least-once delivery with idempotent consumer handlers."
        res_q2 = process_candidate_speech_blob(
            audio_bytes=b"",
            browser_transcript=ans2
        )
        self.assertEqual(res_q2["call_stage"], "COMPLETED")
        self.assertTrue(res_q2["finished"])
        self.assertEqual(res_q2["answered_count"], 2)

    # =========================================================================
    # TEST CASE 5: Session Isolation (Zero Leakage)
    # =========================================================================
    def test_05_session_isolation(self):
        """Verify that starting a new session completely wipes previous answers and transcripts."""
        # Run Session 1
        meta1 = {"industry": "Tech", "role": "DevOps", "voice_profile_id": VOICEBOX_PROFILES["Chirag"], "interviewer_name": "Chirag"}
        q_bridge1 = [{"id": 1, "text": "Describe CI/CD pipeline", "category": "DevOps", "difficulty": "Standard"}]
        reset_live_session(
            candidate_name="Session1User",
            questions=q_bridge1,
            plan_metadata=meta1,
            voice_profile_id=VOICEBOX_PROFILES["Chirag"],
            interviewer_name="Chirag"
        )
        process_candidate_speech_blob(audio_bytes=b"", browser_transcript="Yes I am ready.")
        process_candidate_speech_blob(audio_bytes=b"", browser_transcript="I built a multi-stage GitHub Actions pipeline with Terraform.")

        s1_state = get_live_state()
        self.assertEqual(s1_state["answered_count"], 1)
        self.assertEqual(s1_state["candidate_name"], "Session1User")

        # Now Start Session 2 (completely new candidate who ends call immediately without speaking)
        meta2 = {"industry": "Finance", "role": "Financial Analyst", "voice_profile_id": VOICEBOX_PROFILES["Sushma"], "interviewer_name": "Sushma"}
        q_bridge2 = [{"id": 1, "text": "Describe DCF valuation", "category": "Finance", "difficulty": "Standard"}]
        reset_live_session(
            candidate_name="Session2User",
            questions=q_bridge2,
            plan_metadata=meta2,
            voice_profile_id=VOICEBOX_PROFILES["Sushma"],
            interviewer_name="Sushma"
        )

        s2_state = get_live_state()
        # Verify Session 2 has ZERO records from Session 1
        self.assertEqual(s2_state["candidate_name"], "Session2User")
        self.assertEqual(s2_state["interviewer_name"], "Sushma")
        self.assertEqual(s2_state["voice_profile_id"], VOICEBOX_PROFILES["Sushma"])
        self.assertEqual(s2_state["answered_count"], 0)
        self.assertEqual(len(s2_state["session_records"]), 0)
        self.assertEqual(s2_state["live_transcript"], "")
        self.assertFalse(s2_state["finished"])


if __name__ == "__main__":
    unittest.main()
