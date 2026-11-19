"""
Universal Interview Generator & Evaluator Engine.
Handles:
1. Dynamic profile extraction grounded in resume & target job description
2. Question generation supporting all interview durations (15m=3Q, 30m=5Q, 45m=8Q, 60m=10Q)
   and the 5 interview types:
   - Behavioral (STAR Method)
   - Situational & Scenario Judgment
   - Technical & Domain Deep-Dive
   - HR & Culture Fit
   - Case Study & Structured Problem Solving
3. Multi-criteria unbiased rubric evaluation tailored by industry and role:
   - Technical knowledge, Accuracy, Relevance, Conceptual understanding,
     Problem-solving ability, Communication skills, Clarity & structure,
     Practical experience, Completeness.
   - Answer classification: Answered, Partially Answered, Incorrect, Unanswered, Audio Recognition Failure.
4. Real-time Delivery Analytics (Pacing, WPM, Filler Words, Conciseness)
5. Comprehensive 14-point Final Interview Performance Report
"""
import datetime
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from audio_service import is_whisper_hallucination_or_noise, synthesize_speech
from industry_catalog import INDUSTRY_CATALOG, INTERVIEW_TYPES
from interview_schemas import (
    AnswerEvaluation,
    CandidateProfile,
    DeliveryAnalytics,
    FinalAssessmentReport,
    InterviewPlan,
    QuestionItem,
    QuestionSessionRecord,
    StarFrameworkScore,
)
from llm_client import call_llm, clean_json_response

COMMON_FILLER_WORDS = [
    "um", "uh", "like", "you know", "basically", "actually",
    "literally", "sort of", "kind of", "i mean", "right",
]

# Duration-to-question-count canonical mapping
DURATION_QUESTION_COUNTS: Dict[int, int] = {
    15: 3,
    30: 5,
    45: 8,
    60: 10,
}


def get_question_count_for_duration(duration_minutes: int) -> int:
    """Return the configured question count for a given interview duration in minutes."""
    if duration_minutes in DURATION_QUESTION_COUNTS:
        return DURATION_QUESTION_COUNTS[duration_minutes]
    if duration_minutes <= 15:
        return 3
    if duration_minutes <= 30:
        return 5
    if duration_minutes <= 45:
        return 8
    return 10


def analyze_delivery_metrics(answer_text: str, duration_sec: float = 0.0) -> DeliveryAnalytics:
    """Compute functional delivery diagnostics: word count, WPM pacing, and filler words."""
    words = re.findall(r"\b[a-zA-Z0-9'-]+\b", (answer_text or "").lower())
    total_words = len(words)

    if duration_sec <= 0:
        duration_sec = (total_words / 130.0) * 60.0 if total_words > 0 else 1.0

    minutes = max(duration_sec / 60.0, 0.1)
    wpm = round(total_words / minutes, 1)

    if wpm < 105:
        pacing = "Slow / Hesitant"
    elif wpm > 165:
        pacing = "Rushed / Fast"
    else:
        pacing = "Optimal Pacing (120-160 WPM)"

    filler_counts = {}
    total_fillers = 0
    lower_text = (answer_text or "").lower()
    for fw in COMMON_FILLER_WORDS:
        pattern = r"\b" + re.escape(fw) + r"\b"
        matches = len(re.findall(pattern, lower_text))
        if matches > 0:
            filler_counts[fw] = matches
            total_fillers += matches

    detected_list = [f"{k} (x{v})" for k, v in filler_counts.items()]

    if total_words < 25:
        conciseness = 55.0
    elif total_words > 400:
        conciseness = max(60.0, 100.0 - (total_words - 400) * 0.1)
    else:
        conciseness = 92.0

    return DeliveryAnalytics(
        word_count=total_words,
        estimated_duration_sec=round(duration_sec, 1),
        words_per_minute=wpm,
        pacing_rating=pacing,
        filler_word_count=total_fillers,
        filler_words_detected=detected_list,
        conciseness_score=round(conciseness, 1),
    )


def extract_candidate_profile(
    resume_text: str,
    industry: str,
    target_role: str,
    interview_type: str,
    experience_level: str,
    difficulty_tier: str,
    job_description: Optional[str] = None,
    focus_areas: Optional[List[str]] = None,
) -> CandidateProfile:
    """Analyze resume text and extract candidate profile tailored to the chosen industry and interview type."""
    prompt = f"""
You are an expert talent evaluation specialist for the industry '{industry}'.
Extract structured candidate profile information from this resume for:
Role: {target_role}
Interview Type: {interview_type}
Experience Tier: {experience_level}
Job Description: {job_description or 'Standard industry competencies'}
Focus Areas: {', '.join(focus_areas or [])}

Resume Content:
\"\"\"
{resume_text[:4000]}
\"\"\"

Return ONLY valid JSON matching:
{{
  "candidate_name": string or null,
  "industry": "{industry}",
  "target_role": "{target_role}",
  "interview_type": "{interview_type}",
  "difficulty_tier": "{difficulty_tier}",
  "experience_level": "{experience_level}",
  "years_of_experience": float,
  "skills": ["skill1", "skill2", ...],
  "key_projects": ["project or accomplishment 1", ...],
  "experience_summary": "1-3 sentences summarizing candidate's background",
  "education": "Degree or institution or null"
}}
"""
    try:
        raw = call_llm(
            prompt=prompt,
            system_prompt=f"You are a professional hiring manager in {industry} extracting structured profile data into JSON.",
            json_mode=True,
        )
        parsed = clean_json_response(raw)
        if not isinstance(parsed, dict):
            parsed = {}
    except Exception:
        parsed = {}

    parsed["industry"] = industry
    parsed["target_role"] = target_role
    parsed["interview_type"] = interview_type
    parsed["difficulty_tier"] = difficulty_tier
    parsed["experience_level"] = experience_level
    parsed["job_description"] = job_description
    parsed["focus_areas"] = focus_areas or []
    return CandidateProfile(**parsed)


def _build_fallback_question_bank(profile: CandidateProfile, num_questions: int) -> List[QuestionItem]:
    """Generate role-specific structured questions if LLM question generation returns fewer than num_questions."""
    role = profile.target_role
    ind = profile.industry
    itype = profile.interview_type
    diff = profile.difficulty_tier
    skills = profile.skills or ["Core Domain Architecture", "Problem Solving", "Production Best Practices"]

    templates = [
        (
            f"Can you walk me through your background and explain your hands-on experience with core tools and workflows as a {role}?",
            ["Domain Experience", "Technical Foundations"],
            ["Core frameworks/tools used", "Real-world project context", "Measurable impact"],
            f"Provide a structured overview of experience relevant to {role}, highlighting specific technologies, workflows, and measurable outcomes.",
        ),
        (
            f"Describe a complex technical or operational challenge you solved in a recent {role} project. How did you diagnose the root cause and implement the solution?",
            ["Problem Solving", "Root Cause Analysis", "Execution"],
            ["Problem context", "Diagnostic methodology", "Trade-offs considered", "Quantifiable result"],
            "Use the STAR framework: define the Situation and Task, detail the diagnostic and engineering Actions taken, and quantify the Result.",
        ),
        (
            f"When designing or executing a high-impact deliverable as a {role}, how do you ensure quality, scalability, and reliability under tight deadlines?",
            ["Quality Assurance", "Scalability", "Reliability"],
            ["Testing/validation strategy", "Performance optimization", "Risk mitigation"],
            "Explain validation protocols, automated checks or review processes, bottleneck mitigation, and monitoring in production.",
        ),
        (
            f"Tell me about a time when requirements changed unexpectedly or a critical dependency failed during a project. How did you adapt your approach?",
            ["Adaptability", "Stakeholder Communication", "Decision Making"],
            ["Prioritization criteria", "Cross-functional alignment", "Iterative delivery"],
            "Detail how you reassessed priorities, communicated trade-offs transparently with stakeholders, and delivered the critical path.",
        ),
        (
            f"How do you approach performance optimization and debugging when a system or workflow in {ind} exhibits unexpected latency or errors?",
            ["Debugging", "Performance Tuning", "Observability"],
            ["Profiling/metrics analysis", "Bottleneck isolation", "Iterative verification"],
            "Describe how you gather telemetry/metrics, isolate the bottleneck systematically, validate the fix, and prevent regressions.",
        ),
        (
            f"In the context of {role}, how do you balance speed of delivery against long-term maintainability and technical or operational standards?",
            ["Architecture & Standards", "Pragmatic Trade-offs"],
            ["Code/process modularity", "Documentation & standards", "Technical debt management"],
            "Discuss how you evaluate short-term vs long-term impact, enforce core quality gates, and schedule incremental refactoring.",
        ),
        (
            f"Can you share an example of a time you had to collaborate with cross-functional partners or resolve a technical disagreement within your team?",
            ["Collaboration", "Communication", "Leadership"],
            ["Active listening", "Data-driven consensus", "Shared team outcome"],
            "Explain the differing perspectives, how you used objective criteria or prototypes to align the team, and the resulting success.",
        ),
        (
            f"What security, compliance, or data-integrity best practices do you consider non-negotiable when working as a {role}?",
            ["Security & Governance", "Data Integrity", "Risk Management"],
            ["Access control & validation", "Data protection", "Auditability & error handling"],
            "Outline defense-in-depth practices, input validation, least-privilege principles, and compliance verification.",
        ),
        (
            f"Walk me through a case where you improved an existing process, architecture, or workflow. What metrics proved your improvement worked?",
            ["Continuous Improvement", "Metrics-Driven Engineering"],
            ["Baseline measurement", "Targeted intervention", "Before/after comparison"],
            "State the baseline bottleneck, the specific optimization introduced, and the exact percentage or time improvement achieved.",
        ),
        (
            f"Looking ahead at emerging trends in {ind}, how do you keep your {role} skills sharp and evaluate whether a new tool or methodology is worth adopting?",
            ["Continuous Learning", "Strategic Evaluation"],
            ["Proof-of-concept benchmarking", "Cost-benefit analysis", "Team adoption readiness"],
            "Describe how you evaluate new technologies against concrete business problems using small benchmarks before full adoption.",
        ),
    ]

    items: List[QuestionItem] = []
    for i in range(num_questions):
        q_txt, comps, concepts, ideal = templates[i % len(templates)]
        items.append(
            QuestionItem(
                id=i + 1,
                category=itype,
                interview_type=itype,
                difficulty=diff,
                question_text=q_txt,
                target_competencies=list(comps) + ([skills[i % len(skills)]] if skills else []),
                expected_concepts=list(concepts),
                sample_ideal_answer=ideal,
            )
        )
    return items


def generate_universal_interview_plan(
    profile: CandidateProfile,
    num_questions: int = 4,
    synthesize_audio: bool = False,
    voice_profile_id: Optional[str] = None,
) -> InterviewPlan:
    """
    Generate role-appropriate questions tailored to the 5 interview types, selected industry,
    and exact configured question count (e.g. 15m=3, 30m=5, 45m=8, 60m=10).
    Strictly preserves the exact num_questions count without skipping or exceeding it.
    """
    target_count = max(1, int(num_questions))
    ind_config = INDUSTRY_CATALOG.get(profile.industry, INDUSTRY_CATALOG["Other / Custom Profession"])
    type_config = INTERVIEW_TYPES.get(profile.interview_type, INTERVIEW_TYPES["Behavioral (STAR Method)"])
    rubric_desc = json.dumps(ind_config["rubric"])

    prompt = f"""
You are a Principal Hiring Interviewer conducting an authentic mock interview.
Industry: {profile.industry}
Target Role: {profile.target_role}
Interview Type: {profile.interview_type} (Style: {type_config['description']})
Evaluation Focus: {type_config['eval_focus']}
Difficulty Tier: {profile.difficulty_tier}
Experience Level: {profile.experience_level} ({profile.years_of_experience} yrs stated)
Key Skills/Competencies: {', '.join(profile.skills[:8])}
Candidate Projects/Past Roles: {'; '.join(profile.key_projects[:3])}
Custom Job Description: {profile.job_description or 'Standard industry requirements'}
Requested Focus Areas: {', '.join(profile.focus_areas or [ind_config['default_focus']])}

Industry Rubric:
{rubric_desc}

Generate EXACLY {target_count} realistic, distinct, challenging interview questions for {profile.target_role}.
Important Instructions:
1. Every question MUST match the '{profile.interview_type}' structure.
2. Ground questions in the candidate's actual industry ({profile.industry}) and role ({profile.target_role}).
3. Do NOT repeat questions or overlap identical prompts.
4. Keep questions direct, professional, and clear.

Return ONLY valid JSON matching:
{{
  "industry": "{profile.industry}",
  "target_role": "{profile.target_role}",
  "interview_type": "{profile.interview_type}",
  "experience_level": "{profile.experience_level}",
  "difficulty_tier": "{profile.difficulty_tier}",
  "total_questions": {target_count},
  "questions": [
    {{
      "id": 1,
      "category": "{profile.interview_type}",
      "difficulty": "{profile.difficulty_tier}",
      "question_text": "Clear, direct interview question",
      "target_competencies": ["competency 1", "competency 2"],
      "expected_concepts": ["concept 1", "concept 2", "concept 3"],
      "sample_ideal_answer": "Brief outline of a strong response"
    }}
  ]
}}
"""
    parsed: Dict[str, Any] = {}
    try:
        raw = call_llm(
            prompt=prompt,
            system_prompt=f"You generate authentic, role-appropriate interview plans for {profile.target_role} in strict JSON.",
            json_mode=True,
        )
        parsed = clean_json_response(raw)
        if not isinstance(parsed, dict):
            parsed = {}
    except Exception as e:
        print(f"[InterviewPlan LLM Warning]: {e}")
        parsed = {}

    fallback_bank = _build_fallback_question_bank(profile, target_count)
    raw_questions = parsed.get("questions", []) if isinstance(parsed.get("questions"), list) else []

    normalized_questions: List[QuestionItem] = []
    seen_texts = set()
    for idx, q_dict in enumerate(raw_questions):
        if len(normalized_questions) >= target_count:
            break
        if isinstance(q_dict, dict):
            q_text = str(
                q_dict.get("question_text")
                or q_dict.get("question")
                or q_dict.get("text")
                or q_dict.get("prompt")
                or q_dict.get("q_text")
                or ""
            ).strip()
            if not q_text or q_text.lower() in seen_texts:
                continue
            seen_texts.add(q_text.lower())
            fb_item = fallback_bank[len(normalized_questions) % len(fallback_bank)]
            normalized_questions.append(
                QuestionItem(
                    id=len(normalized_questions) + 1,
                    category=q_dict.get("category") or profile.interview_type,
                    interview_type=q_dict.get("interview_type") or profile.interview_type,
                    difficulty=q_dict.get("difficulty") or profile.difficulty_tier,
                    question_text=q_text,
                    target_competencies=q_dict.get("target_competencies") or fb_item.target_competencies,
                    expected_concepts=q_dict.get("expected_concepts") or fb_item.expected_concepts,
                    sample_ideal_answer=q_dict.get("sample_ideal_answer") or fb_item.sample_ideal_answer,
                )
            )

    # Pad with non-duplicate role-specific fallback questions if LLM returned fewer than target_count
    for fb_item in fallback_bank:
        if len(normalized_questions) >= target_count:
            break
        if fb_item.question_text.lower() not in seen_texts:
            seen_texts.add(fb_item.question_text.lower())
            normalized_questions.append(
                QuestionItem(
                    id=len(normalized_questions) + 1,
                    category=fb_item.category,
                    interview_type=fb_item.interview_type,
                    difficulty=fb_item.difficulty,
                    question_text=fb_item.question_text,
                    target_competencies=fb_item.target_competencies,
                    expected_concepts=fb_item.expected_concepts,
                    sample_ideal_answer=fb_item.sample_ideal_answer,
                )
            )

    # Enforce exact question count
    normalized_questions = normalized_questions[:target_count]
    for idx, item in enumerate(normalized_questions):
        item.id = idx + 1

    plan = InterviewPlan(
        industry=profile.industry,
        target_role=profile.target_role,
        interview_type=profile.interview_type,
        experience_level=profile.experience_level,
        difficulty_tier=profile.difficulty_tier,
        total_questions=len(normalized_questions),
        questions=normalized_questions,
    )

    if synthesize_audio:
        for q in plan.questions:
            try:
                q.spoken_audio_bytes = synthesize_speech(q.question_text, voice_profile_id=voice_profile_id)
            except Exception:
                q.spoken_audio_bytes = None

    return plan


def _heuristic_rubric_evaluation(
    question: QuestionItem,
    candidate_answer: str,
    target_role: str,
    interview_type: str,
    delivery_stats: DeliveryAnalytics,
) -> AnswerEvaluation:
    """
    Evidence-based deterministic rubric fallback when LLM API is unreachable.
    Evaluates actual concept coverage, technical depth, relevance to question keywords,
    and structural completeness. Never assigns an arbitrary flat score without evidence.
    """
    lower_ans = candidate_answer.lower()
    ans_words = re.findall(r"\b[a-zA-Z0-9_+#.-]+\b", lower_ans)
    word_count = len(ans_words)

    # Check if the candidate explicitly states they don't know or gave an irrelevant/trivial response
    dont_know_phrases = ["i don't know", "i do not know", "no idea", "not sure", "skip this", "pass on this"]
    if any(p in lower_ans for p in dont_know_phrases) and word_count < 18:
        return AnswerEvaluation(
            question_id=question.id,
            score=12.0,
            answer_status="Incorrect",
            technical_or_domain_accuracy=10.0,
            completeness_and_relevance=15.0,
            practical_reasoning_and_scenarios=10.0,
            communication_and_clarity=25.0,
            conceptual_understanding=10.0,
            problem_solving_ability=10.0,
            practical_experience=10.0,
            star_analysis=None,
            delivery_analytics=delivery_stats,
            strengths=[],
            missing_or_incorrect=list(question.expected_concepts or ["Core domain explanation and practical example"]),
            improvement_feedback=(
                f"The response did not address the core concepts for Question {question.id}. "
                f"Review {', '.join(question.expected_concepts[:3]) or target_role + ' fundamentals'} and practice structuring concrete examples."
            ),
            suggested_ideal_outline=question.sample_ideal_answer or "Explain the core mechanism, trade-offs, and a concrete example.",
            requires_follow_up=True,
            follow_up_question=f"Could you share any related concept or practical scenario you have encountered regarding {question.category}?",
        )

    # Extract meaningful keywords from question, expected_concepts, and target_competencies
    stop_words = {
        "the", "and", "for", "with", "that", "this", "from", "your", "have", "you", "how", "what",
        "when", "where", "why", "can", "could", "would", "should", "tell", "about", "describe", "explain",
        "walk", "through", "time", "role", "work", "used", "using", "into", "over", "under", "their",
    }
    q_tokens = {
        w for w in re.findall(r"\b[a-zA-Z]{3,}\b", question.question_text.lower()) if w not in stop_words
    }
    concept_tokens = set()
    for c in (question.expected_concepts or []) + (question.target_competencies or []):
        for w in re.findall(r"\b[a-zA-Z0-9+#-]{2,}\b", c.lower()):
            if w not in stop_words:
                concept_tokens.add(w)

    ans_token_set = set(ans_words)
    q_overlap = len(q_tokens & ans_token_set) / float(max(1, len(q_tokens)))
    c_overlap = len(concept_tokens & ans_token_set) / float(max(1, len(concept_tokens))) if concept_tokens else q_overlap

    # Check domain/practical indicators (metrics, architecture/action verbs, structured reasoning)
    practical_markers = {
        "implemented", "designed", "built", "deployed", "optimized", "reduced", "increased",
        "configured", "diagnosed", "resolved", "tested", "architecture", "pipeline", "production",
        "performance", "latency", "accuracy", "scalable", "database", "api", "service", "model",
        "framework", "pandas", "numpy", "flask", "python", "sql", "cloud", "docker", "cache", "redis",
        "kafka", "tracing", "monitoring", "security", "validation", "workflow", "team", "stakeholder",
    }
    practical_hits = len(practical_markers & ans_token_set)

    # Depth factor based on substantive explanation length
    depth_factor = min(1.0, word_count / 45.0)
    relevance_raw = min(100.0, (q_overlap * 45.0) + (c_overlap * 35.0) + (depth_factor * 25.0) + (min(4, practical_hits) * 5.0))
    tech_raw = min(100.0, (c_overlap * 45.0) + (min(5, practical_hits) * 9.0) + (depth_factor * 25.0))
    problem_raw = min(100.0, (min(5, practical_hits) * 10.0) + (depth_factor * 35.0) + (q_overlap * 20.0))
    comm_raw = min(96.0, max(35.0, 55.0 + (depth_factor * 30.0) + (10.0 if delivery_stats.filler_word_count <= 3 else 0.0)))

    # If the answer has zero overlap with the question AND zero practical markers, score it low as Incorrect
    if q_overlap == 0.0 and c_overlap == 0.0 and practical_hits == 0:
        overall = 24.0
        status = "Incorrect"
        tech_raw, relevance_raw, problem_raw = 20.0, 22.0, 20.0
    else:
        overall = round((tech_raw * 0.35) + (relevance_raw * 0.25) + (problem_raw * 0.25) + (comm_raw * 0.15), 1)
        if overall >= 68.0:
            status = "Answered"
        elif overall >= 40.0:
            status = "Partially Answered"
        else:
            status = "Incorrect"

    matched_concepts = [
        c for c in (question.expected_concepts or [])
        if any(tok in ans_token_set for tok in re.findall(r"\b[a-zA-Z0-9+#-]{2,}\b", c.lower()))
    ]
    missing_concepts = [
        c for c in (question.expected_concepts or []) if c not in matched_concepts
    ]

    strengths = []
    if matched_concepts:
        strengths.append(f"Addressed key expected concepts: {', '.join(matched_concepts[:3])}.")
    if practical_hits >= 2:
        strengths.append("Grounded the response with concrete technical/practical implementation details.")
    if word_count >= 25 and not strengths:
        strengths.append("Provided a structured and clear verbal explanation.")

    if not missing_concepts and status != "Answered":
        missing_concepts = ["Could expand with deeper architectural trade-offs and quantifiable outcomes."]

    return AnswerEvaluation(
        question_id=question.id,
        score=round(overall, 1),
        answer_status=status,
        technical_or_domain_accuracy=round(tech_raw, 1),
        completeness_and_relevance=round(relevance_raw, 1),
        practical_reasoning_and_scenarios=round(problem_raw, 1),
        communication_and_clarity=round(comm_raw, 1),
        conceptual_understanding=round(tech_raw, 1),
        problem_solving_ability=round(problem_raw, 1),
        practical_experience=round(min(100.0, problem_raw + 5.0), 1),
        star_analysis=None,
        delivery_analytics=delivery_stats,
        strengths=strengths,
        missing_or_incorrect=missing_concepts,
        improvement_feedback=(
            f"Good coverage of the prompt. To strengthen your answer further, elaborate on "
            f"{', '.join(missing_concepts[:2]) if missing_concepts else 'measurable production metrics and edge-case trade-offs'}."
        ),
        suggested_ideal_outline=question.sample_ideal_answer or (
            f"Cover {', '.join(question.expected_concepts or ['core concepts'])}, practical implementation steps, and measurable results."
        ),
        requires_follow_up=(status == "Partially Answered" and len(missing_concepts) > 0),
        follow_up_question=(
            f"Could you elaborate on how you handled {missing_concepts[0]} in that scenario?"
            if (status == "Partially Answered" and missing_concepts)
            else None
        ),
    )


def evaluate_universal_answer(
    question: QuestionItem,
    candidate_answer: str,
    industry: str,
    target_role: str,
    interview_type: str,
    duration_sec: float = 0.0,
) -> AnswerEvaluation:
    """
    Evaluate candidate response against profession-specific rubric, STAR criteria, and delivery analytics.
    Distinguishes between:
      - Answered
      - Partially Answered
      - Incorrect
      - Unanswered
      - Audio Recognition Failure
    Never awards marks without evidence and never fabricates transcripts or scores for unanswered questions.
    """
    raw_ans = (candidate_answer or "").strip()
    lower_ans = raw_ans.lower()
    clean_words = [w for w in raw_ans.split() if any(c.isalpha() for c in w)]

    if "audio recognition failure" in lower_ans or "stt failure" in lower_ans:
        return AnswerEvaluation(
            question_id=question.id,
            score=0.0,
            answer_status="Audio Recognition Failure",
            technical_or_domain_accuracy=0.0,
            completeness_and_relevance=0.0,
            practical_reasoning_and_scenarios=0.0,
            communication_and_clarity=0.0,
            conceptual_understanding=0.0,
            problem_solving_ability=0.0,
            practical_experience=0.0,
            star_analysis=None,
            delivery_analytics=DeliveryAnalytics(
                word_count=0,
                estimated_duration_sec=duration_sec,
                words_per_minute=0.0,
                pacing_rating="Audio Recognition Failure",
                filler_word_count=0,
                filler_words_detected=[],
                conciseness_score=0.0,
            ),
            strengths=[],
            missing_or_incorrect=["Audio could not be recognized clearly for this turn."],
            improvement_feedback="Audio recognition failed during this response. Please verify microphone clarity and retry.",
            suggested_ideal_outline=question.sample_ideal_answer or "Provide a structured answer addressing the prompt.",
            requires_follow_up=False,
            follow_up_question=None,
        )

    filler_only = {"uh", "um", "hmm", "hm", "ah", "oh", "eh", "er", "erm", "mm", "huh"}
    meaningful_words = [
        w.strip(".,!?:;\"'()[]{}").lower()
        for w in clean_words
        if w.strip(".,!?:;\"'()[]{}").lower() not in filler_only
        and len(w.strip(".,!?:;\"'()[]{}")) >= 2
    ]

    is_unanswered = (
        len(meaningful_words) < 1
        or raw_ans.startswith("(")
        or "call ended" in lower_ans
        or "no response" in lower_ans
        or "unanswered" in lower_ans
        or "not attempted" in lower_ans
        or "silence" in lower_ans
        or is_whisper_hallucination_or_noise(raw_ans)
    )
    if is_unanswered:
        return AnswerEvaluation(
            question_id=question.id,
            score=0.0,
            answer_status="Unanswered",
            technical_or_domain_accuracy=0.0,
            completeness_and_relevance=0.0,
            practical_reasoning_and_scenarios=0.0,
            communication_and_clarity=0.0,
            conceptual_understanding=0.0,
            problem_solving_ability=0.0,
            practical_experience=0.0,
            star_analysis=None,
            delivery_analytics=DeliveryAnalytics(
                word_count=len(clean_words),
                estimated_duration_sec=duration_sec,
                words_per_minute=0.0,
                pacing_rating="No Response",
                filler_word_count=0,
                filler_words_detected=[],
                conciseness_score=0.0,
            ),
            strengths=[],
            missing_or_incorrect=["No spoken answer was provided for this question."],
            improvement_feedback=(
                f"Question {question.id} was not attempted / unanswered. "
                f"To score marks on this question, address: {', '.join(question.expected_concepts or ['the core question prompt'])}."
            ),
            suggested_ideal_outline=question.sample_ideal_answer or (
                f"Expected concepts: {', '.join(question.expected_concepts or ['Structured explanation and real-world example'])}."
            ),
            requires_follow_up=False,
            follow_up_question=None,
        )

    ind_config = INDUSTRY_CATALOG.get(industry, INDUSTRY_CATALOG["Other / Custom Profession"])
    rubric = ind_config["rubric"]
    delivery_stats = analyze_delivery_metrics(raw_ans, duration_sec)
    is_behavioral = "Behavioral" in interview_type

    prompt = f"""
You are a rigorous, unbiased Senior Technical & Domain Interview Evaluator assessing a candidate for:
Industry: {industry}
Target Role: {target_role}
Interview Type: {interview_type}

Question Asked (ID #{question.id}):
"{question.question_text}"
Target Competencies: {', '.join(question.target_competencies)}
Expected Concepts / Benchmarks: {', '.join(question.expected_concepts)}

Candidate's Actual Transcribed Answer:
\"\"\"
{raw_ans}
\"\"\"

Profession-Specific Rubric Dimensions:
1. {rubric['dim1']} (0-100)
2. {rubric['dim2']} (0-100)
3. {rubric['dim3']} (0-100)
4. {rubric['dim4']} (0-100)

Mandatory Evaluation Criteria:
Evaluate the candidate strictly on evidence in their answer across:
- Technical knowledge & accuracy of the response (`technical_or_domain_accuracy`: 0-100)
- Relevance & completeness (`completeness_and_relevance`: 0-100)
- Conceptual understanding (`conceptual_understanding`: 0-100)
- Problem-solving ability & practical reasoning (`practical_reasoning_and_scenarios` / `problem_solving_ability`: 0-100)
- Practical experience demonstrated (`practical_experience`: 0-100)
- Communication skills, clarity, and structure (`communication_and_clarity`: 0-100)

Strict Unbiased Scoring Rules:
1. Do NOT give marks merely because the candidate spoke. If the answer is irrelevant, off-topic, evasive, or factually incorrect, set "answer_status" to "Incorrect" and score between 0 and 35.
2. If the answer addresses some aspects of the question but misses key expected concepts or lacks depth, set "answer_status" to "Partially Answered" and score between 40 and 69.
3. If the answer is accurate, relevant, and covers the core concepts well, set "answer_status" to "Answered" and score between 70 and 100.
4. Do NOT penalize the candidate for accent, minor spoken grammar/STT transcription quirks, or speaking speed when irrelevant to the assessed skill.

Return ONLY valid JSON:
{{
  "question_id": {question.id},
  "answer_status": "Answered" | "Partially Answered" | "Incorrect",
  "score": float (0-100),
  "technical_or_domain_accuracy": float (0-100),
  "completeness_and_relevance": float (0-100),
  "practical_reasoning_and_scenarios": float (0-100),
  "communication_and_clarity": float (0-100),
  "conceptual_understanding": float (0-100),
  "problem_solving_ability": float (0-100),
  "practical_experience": float (0-100),
  "star_scores": {{
    "situation_score": float (0-100),
    "task_score": float (0-100),
    "action_score": float (0-100),
    "result_score": float (0-100)
  }},
  "strengths": ["what was good in the candidate's answer", "..."],
  "missing_or_incorrect": ["what expected concepts were missing or inaccurate", "..."],
  "improvement_feedback": "Specific, actionable feedback on how the candidate can improve this answer",
  "suggested_ideal_outline": "Concise summary of the expected ideal answer concepts",
  "requires_follow_up": boolean,
  "follow_up_question": string or null
}}
"""
    try:
        raw = call_llm(
            prompt=prompt,
            system_prompt=f"You evaluate candidate answers for {target_role} objectively using evidence-based domain rubrics in strict JSON.",
            json_mode=True,
        )
        parsed = clean_json_response(raw)
        if not isinstance(parsed, dict) or "score" not in parsed:
            raise ValueError("Invalid LLM evaluation payload")
    except Exception:
        return _heuristic_rubric_evaluation(
            question=question,
            candidate_answer=raw_ans,
            target_role=target_role,
            interview_type=interview_type,
            delivery_stats=delivery_stats,
        )

    star_obj = None
    if is_behavioral and isinstance(parsed.get("star_scores"), dict):
        s_data = parsed["star_scores"]
        sit = float(s_data.get("situation_score", 0.0))
        tsk = float(s_data.get("task_score", 0.0))
        act = float(s_data.get("action_score", 0.0))
        res = float(s_data.get("result_score", 0.0))
        ratio = round(((sit > 40) + (tsk > 40) + (act > 40) + (res > 40)) / 4.0, 2)
        star_obj = StarFrameworkScore(
            situation_score=sit,
            task_score=tsk,
            action_score=act,
            result_score=res,
            star_completeness_ratio=ratio,
        )

    score_val = float(parsed.get("score", 0.0))
    tech_val = float(parsed.get("technical_or_domain_accuracy", score_val))
    rel_val = float(parsed.get("completeness_and_relevance", score_val))
    prac_val = float(parsed.get("practical_reasoning_and_scenarios", score_val))
    comm_val = float(parsed.get("communication_and_clarity", score_val))
    conc_val = float(parsed.get("conceptual_understanding", tech_val))
    prob_val = float(parsed.get("problem_solving_ability", prac_val))
    exp_val = float(parsed.get("practical_experience", prac_val))

    raw_status = str(parsed.get("answer_status", "")).strip()
    if raw_status not in ("Answered", "Partially Answered", "Incorrect", "Unanswered", "Audio Recognition Failure"):
        if score_val >= 68.0:
            raw_status = "Answered"
        elif score_val >= 40.0:
            raw_status = "Partially Answered"
        else:
            raw_status = "Incorrect"

    return AnswerEvaluation(
        question_id=question.id,
        score=round(score_val, 1),
        answer_status=raw_status,
        technical_or_domain_accuracy=round(tech_val, 1),
        completeness_and_relevance=round(rel_val, 1),
        practical_reasoning_and_scenarios=round(prac_val, 1),
        communication_and_clarity=round(comm_val, 1),
        conceptual_understanding=round(conc_val, 1),
        problem_solving_ability=round(prob_val, 1),
        practical_experience=round(exp_val, 1),
        star_analysis=star_obj,
        delivery_analytics=delivery_stats,
        strengths=parsed.get("strengths") or [],
        missing_or_incorrect=parsed.get("missing_or_incorrect") or [],
        improvement_feedback=parsed.get("improvement_feedback") or "Focus on structuring your answer with specific concepts and measurable results.",
        suggested_ideal_outline=parsed.get("suggested_ideal_outline") or question.sample_ideal_answer,
        requires_follow_up=bool(parsed.get("requires_follow_up", False)),
        follow_up_question=parsed.get("follow_up_question"),
    )


def generate_universal_final_report(
    profile: CandidateProfile,
    session_records: List[QuestionSessionRecord],
    interview_mode: str = "AUDIO",
    passing_threshold: float = 70.0,
) -> FinalAssessmentReport:
    """
    Aggregate session scores, delivery diagnostics, and compile the comprehensive 14-point
    final candidate performance report.
    """
    total_questions = len(session_records)
    valid_records: List[QuestionSessionRecord] = []

    for rec in session_records:
        ans = (rec.candidate_answer or "").strip()
        words = [
            w for w in ans.split()
            if any(c.isalnum() for c in w)
            and w.strip(".,!?:;\"'()[]{}").lower() not in {"uh", "um", "hmm", "hm", "ah", "oh", "eh", "er", "erm", "mm", "huh"}
            and len(w.strip(".,!?:;\"'()[]{}")) >= 2
        ]
        ev = rec.evaluation
        ev_status = ev.answer_status if ev else "Unanswered"
        if (
            ev is not None
            and ev_status not in ("Unanswered", "Audio Recognition Failure")
            and len(words) >= 1
            and not ans.startswith("(")
            and "call ended" not in ans.lower()
            and "no response" not in ans.lower()
            and "unanswered" not in ans.lower()
            and "silence" not in ans.lower()
            and not is_whisper_hallucination_or_noise(ans)
        ):
            valid_records.append(rec)
        else:
            # Ensure unanswered record has a 0.0 Unanswered evaluation object
            if rec.evaluation is None or rec.evaluation.score > 0.0:
                rec.evaluation = evaluate_universal_answer(
                    question=rec.question,
                    candidate_answer="",
                    industry=profile.industry,
                    target_role=profile.target_role,
                    interview_type=profile.interview_type,
                    duration_sec=0.0,
                )

    answered_count = len(valid_records)

    # Collect missing concepts across all questions (including unanswered ones)
    all_missing_concepts: List[str] = []
    for rec in session_records:
        for concept in rec.question.expected_concepts or []:
            if rec not in valid_records and concept not in all_missing_concepts:
                all_missing_concepts.append(concept)
        if rec.evaluation and rec.evaluation.missing_or_incorrect:
            for gap in rec.evaluation.missing_or_incorrect:
                if gap and "no spoken answer" not in gap.lower() and gap not in all_missing_concepts:
                    all_missing_concepts.append(gap)

    # CASE 1: No responses provided at all (0 answered questions -> 0.0% score, NEVER 55%)
    if answered_count == 0:
        cat_scores: Dict[str, float] = {}
        for rec in session_records:
            cat_scores[rec.question.category] = 0.0

        unanswered_concepts = []
        for rec in session_records:
            for c in rec.question.expected_concepts or []:
                if c not in unanswered_concepts:
                    unanswered_concepts.append(c)

        return FinalAssessmentReport(
            candidate_name=profile.candidate_name or "Candidate",
            industry=profile.industry,
            target_role=profile.target_role,
            interview_type=profile.interview_type,
            interview_mode=interview_mode,
            interview_date=datetime.date.today().strftime("%B %d, %Y"),
            overall_score=0.0,
            technical_knowledge_score=0.0,
            communication_score=0.0,
            problem_solving_score=0.0,
            answer_relevance_score=0.0,
            passed=False,
            passing_threshold=passing_threshold,
            outcome="No Response",
            overall_readiness="Not Ready — No Responses Recorded",
            final_assessment_summary=(
                f"No candidate responses were recorded during the {profile.target_role} mock interview session "
                f"(0 of {total_questions} questions answered). All questions were marked as Unanswered with a score of 0.0%."
            ),
            total_questions_asked=total_questions,
            questions_answered_count=0,
            is_valid_interview=False,
            category_scores=cat_scores,
            average_delivery_pacing="No Response",
            total_filler_words=0,
            key_strengths=[],
            weaknesses=[
                f"Did not provide spoken answers to any of the {total_questions} interview questions.",
                "No technical, problem-solving, or communication evidence was demonstrated.",
            ],
            missing_concepts=unanswered_concepts or [f"Core {profile.target_role} domain concepts"],
            areas_for_improvement=[
                "No candidate responses were recorded during the interview session.",
                "Speak clearly into the microphone after the interviewer finishes each question to record a complete response.",
            ],
            skills_needing_preparation=[
                f"{profile.target_role} Technical & Domain Fundamentals",
                "Verbal Articulation & Structured Problem Solving",
            ],
            recommended_topics_to_study=[
                f"{profile.target_role} Core Fundamentals",
                "Structured Interview Preparation (STAR Framework)",
            ],
            session_records=session_records,
        )

    # Calculate dimension and overall scores across valid answered questions
    total_score = 0.0
    tech_sum = 0.0
    comm_sum = 0.0
    prob_sum = 0.0
    rel_sum = 0.0
    category_scores: Dict[str, List[float]] = {}
    total_fillers = 0
    pacing_ratings = []

    for rec in valid_records:
        ev = rec.evaluation
        q_score = ev.score if ev else 0.0
        if rec.follow_up_evaluation:
            q_score = (q_score * 0.6) + (rec.follow_up_evaluation.score * 0.4)
        total_score += q_score
        tech_sum += ev.technical_or_domain_accuracy if ev else 0.0
        comm_sum += ev.communication_and_clarity if ev else 0.0
        prob_sum += ev.practical_reasoning_and_scenarios if ev else 0.0
        rel_sum += ev.completeness_and_relevance if ev else 0.0

        cat = rec.question.category
        category_scores.setdefault(cat, []).append(q_score)

        if ev and ev.delivery_analytics:
            total_fillers += ev.delivery_analytics.filler_word_count
            pacing_ratings.append(ev.delivery_analytics.pacing_rating)

    denom = float(max(len(valid_records), 1))
    overall_avg = round(total_score / denom, 1)
    tech_avg = round(tech_sum / denom, 1)
    comm_avg = round(comm_sum / denom, 1)
    prob_avg = round(prob_sum / denom, 1)
    rel_avg = round(rel_sum / denom, 1)

    passed = overall_avg >= passing_threshold and answered_count == total_questions

    category_averages = {
        cat: round(sum(scores) / len(scores), 1)
        for cat, scores in category_scores.items()
    }
    for rec in session_records:
        if rec.question.category not in category_averages:
            category_averages[rec.question.category] = 0.0

    avg_pacing = max(set(pacing_ratings), key=pacing_ratings.count) if pacing_ratings else "Optimal"

    if answered_count < total_questions:
        outcome = "Incomplete Interview"
        readiness = f"Incomplete Session ({answered_count}/{total_questions} Answered) — Further Practice Needed"
    elif overall_avg >= 85.0:
        outcome = "Excellent Performance"
        readiness = "Highly Ready — Strong Hire Signal"
    elif overall_avg >= 75.0:
        outcome = "Strong Performance"
        readiness = "Interview Ready — Solid Competency Demonstrated"
    elif overall_avg >= 65.0:
        outcome = "Good Performance"
        readiness = "Approaching Readiness — Needs Targeted Polish"
    else:
        outcome = "Needs Improvement"
        readiness = "Needs Further Preparation Before Live Interviews"

    eval_summaries = []
    collected_strengths = []
    collected_weaknesses = []
    for r in session_records:
        ev = r.evaluation
        status_str = ev.answer_status if ev else "Unanswered"
        eval_summaries.append(
            f"Q{r.question.id} [{r.question.category}] ({status_str}): {r.question.question_text}\n"
            f"Candidate Answer: {r.candidate_answer}\n"
            f"Score: {ev.score if ev else 0}/100\n"
            f"Strengths: {ev.strengths if ev else []}\n"
            f"Missing/Gaps: {ev.missing_or_incorrect if ev else []}"
        )
        if ev:
            for s in ev.strengths:
                if s and s not in collected_strengths:
                    collected_strengths.append(s)
            for m in ev.missing_or_incorrect:
                if m and m not in collected_weaknesses:
                    collected_weaknesses.append(m)

    summary_prompt = f"""
Candidate: {profile.candidate_name or 'Candidate'}
Industry: {profile.industry} | Role: {profile.target_role}
Interview Type: {profile.interview_type}
Interview Status: {outcome} ({answered_count} of {total_questions} questions answered)
Overall Score: {overall_avg}/100 (Technical: {tech_avg}, Communication: {comm_avg}, Problem-Solving: {prob_avg}, Relevance: {rel_avg})

Question-by-Question Breakdown:
{chr(10).join(eval_summaries)}

Synthesize an evidence-based final assessment in JSON:
1. "key_strengths": 3 concrete strengths demonstrated in the candidate's actual answers
2. "weaknesses": 3 concrete weaknesses or gaps observed
3. "missing_concepts": specific technical/domain concepts missed across the questions
4. "areas_for_improvement": 3 actionable improvement recommendations
5. "skills_needing_preparation": 3 specific skills that need further preparation for {profile.target_role}
6. "recommended_topics_to_study": 3-4 specific learning topics to study next
7. "final_assessment_summary": 2-3 sentence executive summary of the candidate's overall performance and readiness.

Return ONLY valid JSON:
{{
  "key_strengths": ["...", "...", "..."],
  "weaknesses": ["...", "...", "..."],
  "missing_concepts": ["...", "..."],
  "areas_for_improvement": ["...", "...", "..."],
  "skills_needing_preparation": ["...", "...", "..."],
  "recommended_topics_to_study": ["...", "...", "..."],
  "final_assessment_summary": "..."
}}
"""
    try:
        raw_sum = call_llm(
            summary_prompt,
            system_prompt="You synthesize unbiased, evidence-based interview evaluation reports in strict JSON.",
            json_mode=True,
        )
        parsed_sum = clean_json_response(raw_sum)
        if not isinstance(parsed_sum, dict):
            parsed_sum = {}
    except Exception:
        parsed_sum = {}

    strengths = parsed_sum.get("key_strengths") or collected_strengths[:4] or [
        "Engaged directly with the answered interview prompts.",
        "Communicated relevant domain examples clearly.",
    ]
    weaknesses = parsed_sum.get("weaknesses") or collected_weaknesses[:4] or [
        "Some responses could include deeper architectural trade-offs and measurable outcomes.",
    ]
    missing_concepts = parsed_sum.get("missing_concepts") or all_missing_concepts[:6] or [
        f"Advanced {profile.target_role} edge-case handling and quantifiable metrics"
    ]
    improvements = parsed_sum.get("areas_for_improvement") or [
        "Structure answers with clear context, technical actions taken, and measurable impact.",
        f"Address all expected domain concepts for {profile.target_role} systematically.",
    ]
    skills_prep = parsed_sum.get("skills_needing_preparation") or [
        c for rec in session_records for c in (rec.question.target_competencies or [])
    ][:4] or [f"{profile.target_role} System Design & Execution", "Structured Technical Communication"]
    topics = parsed_sum.get("recommended_topics_to_study") or all_missing_concepts[:4] or [
        f"{profile.target_role} Advanced Competencies",
        "Industry Architecture & Problem-Solving Frameworks",
    ]
    final_summary = parsed_sum.get("final_assessment_summary") or (
        f"{profile.candidate_name or 'The candidate'} answered {answered_count} of {total_questions} questions "
        f"for the {profile.target_role} ({profile.interview_type}) interview, achieving an overall score of {overall_avg}% "
        f"(Technical: {tech_avg}%, Communication: {comm_avg}%, Problem-Solving: {prob_avg}%, Relevance: {rel_avg}%). "
        f"Overall readiness: {readiness}."
    )

    if outcome == "Incomplete Interview":
        unanswered_q_nums = [
            f"Q{r.question.id}" for r in session_records if r not in valid_records
        ]
        incomplete_note = (
            f"Interview concluded with {answered_count} of {total_questions} planned questions answered "
            f"(Unanswered: {', '.join(unanswered_q_nums)} scored 0%)."
        )
        if incomplete_note not in improvements:
            improvements.insert(0, incomplete_note)
        if incomplete_note not in weaknesses:
            weaknesses.insert(0, incomplete_note)

    return FinalAssessmentReport(
        candidate_name=profile.candidate_name or "Candidate",
        industry=profile.industry,
        target_role=profile.target_role,
        interview_type=profile.interview_type,
        interview_mode=interview_mode,
        interview_date=datetime.date.today().strftime("%B %d, %Y"),
        overall_score=overall_avg,
        technical_knowledge_score=tech_avg,
        communication_score=comm_avg,
        problem_solving_score=prob_avg,
        answer_relevance_score=rel_avg,
        passed=passed,
        passing_threshold=passing_threshold,
        outcome=outcome,
        overall_readiness=readiness,
        final_assessment_summary=final_summary,
        total_questions_asked=total_questions,
        questions_answered_count=answered_count,
        is_valid_interview=True,
        category_scores=category_averages,
        average_delivery_pacing=avg_pacing,
        total_filler_words=total_fillers,
        key_strengths=strengths,
        weaknesses=weaknesses,
        missing_concepts=missing_concepts,
        areas_for_improvement=improvements,
        skills_needing_preparation=skills_prep,
        recommended_topics_to_study=topics,
        session_records=session_records,
    )
