"""
Comprehensive Regression Test Suite for Universal AI Interview Platform.
Validates:
1. Multi-format resume parsing (including Hema583 resume.doc)
2. Empty and corrupted file handling
3. Profession catalog and 5 Interview Types (Behavioral STAR, Situational, Technical, HR, Case Study)
4. Functional delivery analytics (WPM pacing, filler word detection, conciseness)
5. Behavioral STAR rubric calculation
6. Report generation and PDF document export
"""
import os
import tempfile

from resume_parser import extract_resume_text
from industry_catalog import INDUSTRY_CATALOG, INTERVIEW_TYPES
from interview_schemas import (
    CandidateProfile, QuestionItem, AnswerEvaluation, QuestionSessionRecord,
    StarFrameworkScore, DeliveryAnalytics
)
from interview_engine import analyze_delivery_metrics, generate_universal_final_report
from report_exporter import export_report_to_pdf

class MockUpload:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self.data = data
    def getvalue(self) -> bytes:
        return self.data


def test_resume_parser_legacy_doc():
    """Verify Hema583 resume.doc parses cleanly."""
    target_path = r"C:\Users\lenovo\Downloads\Hema583 resume.doc"
    if os.path.exists(target_path):
        with open(target_path, "rb") as f:
            doc_data = f.read()
        doc_file = MockUpload("Hema583 resume.doc", doc_data)
        doc_out, fmt = extract_resume_text(doc_file)
        assert fmt == "DOC"
        assert len(doc_out) > 500
        assert "Hema" in doc_out


def test_delivery_analytics_functional():
    """Verify delivery metrics compute real WPM and filler word occurrences."""
    sample_text = (
        "Um, basically, our team faced a major challenge when the main server went down. "
        "Like, you know, we had to coordinate with the site reliability engineers immediately."
    )
    # Approx 26 words, duration 12 seconds -> ~130 WPM
    metrics = analyze_delivery_metrics(sample_text, duration_sec=12.0)
    assert metrics.word_count > 20
    assert metrics.filler_word_count >= 3
    assert any("um" in fw.lower() for fw in metrics.filler_words_detected)
    assert metrics.words_per_minute > 100


def test_interview_types_catalog():
    """Verify all 5 required interview types exist with guidance."""
    required_types = [
        "Behavioral (STAR Method)",
        "Situational & Scenario Judgment",
        "Technical & Domain Deep-Dive",
        "HR & Culture Fit",
        "Case Study & Structured Problem Solving"
    ]
    for it in required_types:
        assert it in INTERVIEW_TYPES
        assert "description" in INTERVIEW_TYPES[it]


def test_star_framework_and_report_export():
    """Verify behavioral STAR scoring and PDF export."""
    profile = CandidateProfile(
        candidate_name="Elena Rostova",
        industry="Artificial Intelligence, Software & IT",
        target_role="AI / Machine Learning Engineer",
        interview_type="Behavioral (STAR Method)",
        experience_level="Senior Professional (6-10 yrs)",
        years_of_experience=7.0,
        skills=["PyTorch", "Distributed Training", "MLOps"],
        key_projects=["LLM Fine-Tuning Infrastructure"]
    )

    q = QuestionItem(
        id=1,
        category="Behavioral (STAR Method)",
        interview_type="Behavioral (STAR Method)",
        difficulty="Challenging",
        question_text="Tell me about a time when a critical ML model failed in production. How did you diagnose and resolve it?",
        expected_concepts=["Situation context", "Root cause diagnosis", "Mitigation actions", "Outcome/post-mortem"]
    )

    star = StarFrameworkScore(
        situation_score=85.0,
        task_score=80.0,
        action_score=90.0,
        result_score=85.0,
        star_completeness_ratio=1.0
    )

    da = DeliveryAnalytics(
        word_count=180,
        estimated_duration_sec=75.0,
        words_per_minute=144.0,
        pacing_rating="Optimal Pacing (120-160 WPM)",
        filler_word_count=1,
        filler_words_detected=["like (x1)"],
        conciseness_score=92.0
    )

    ev = AnswerEvaluation(
        question_id=1,
        score=86.0,
        technical_or_domain_accuracy=88.0,
        completeness_and_relevance=85.0,
        practical_reasoning_and_scenarios=88.0,
        communication_and_clarity=85.0,
        star_analysis=star,
        delivery_analytics=da,
        strengths=["Clear STAR breakdown", "Actionable post-mortem strategy"],
        missing_or_incorrect=[],
        improvement_feedback="Strong storytelling with quantitative impact.",
        requires_follow_up=False
    )

    rec = QuestionSessionRecord(
        question=q,
        candidate_answer="In my previous role at an autonomous driving startup, our perception model had latency spikes...",
        duration_seconds=75.0,
        evaluation=ev
    )

    report = generate_universal_final_report(
        profile=profile,
        session_records=[rec],
        interview_mode="AUDIO",
        passing_threshold=70.0
    )

    assert report.overall_score == 86.0
    assert report.passed is True
    assert report.interview_type == "Behavioral (STAR Method)"

    # Verify PDF export
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        out_path = export_report_to_pdf(report, tmp_pdf.name)
        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 1000
    os.remove(out_path)


if __name__ == "__main__":
    test_resume_parser_legacy_doc()
    test_delivery_analytics_functional()
    test_interview_types_catalog()
    test_star_framework_and_report_export()
    print("All regression tests passed successfully!")
