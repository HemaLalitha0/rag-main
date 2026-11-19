"""
Universal AI Mock Interview Platform schemas.
Supports all professions, custom roles, multi-modal interaction types (AUDIO, VIDEO, TEXT),
the 5 interview types (Behavioral STAR, Situational, Technical, HR, Case Study),
and delivery analytics (STAR completeness, pacing, filler words).
"""
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, AliasChoices


class InterviewMode(str, Enum):
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    TEXT = "TEXT"


class InterviewState(str, Enum):
    INITIALIZING = "INITIALIZING"
    INTRODUCTION = "INTRODUCTION"
    WAITING_FOR_READINESS = "WAITING_FOR_READINESS"
    ASKING_QUESTION = "ASKING_QUESTION"
    WAITING_FOR_CANDIDATE = "WAITING_FOR_CANDIDATE"
    LISTENING_TO_CANDIDATE = "LISTENING_TO_CANDIDATE"
    RECORDING_ANSWER = "RECORDING_ANSWER"
    PROCESSING_AUDIO = "PROCESSING_AUDIO"
    TRANSCRIBING_ANSWER = "TRANSCRIBING_ANSWER"
    PROCESSING_ANSWER = "PROCESSING_ANSWER"
    EVALUATING_ANSWER = "EVALUATING_ANSWER"
    GENERATING_NEXT_QUESTION = "GENERATING_NEXT_QUESTION"
    INTERVIEW_COMPLETED = "INTERVIEW_COMPLETED"
    INTERVIEW_ERROR = "INTERVIEW_ERROR"
    # Legacy/UI compatibility states
    SETUP = "SETUP"
    CONNECTING = "CONNECTING"
    SAINA_SPEAKING = "SAINA_SPEAKING"
    WAITING_FOR_ANSWER = "WAITING_FOR_ANSWER"
    CANDIDATE_SPEAKING = "CANDIDATE_SPEAKING"
    PROCESSING = "PROCESSING"
    TRANSITION_PROMPT = "TRANSITION_PROMPT"
    FOLLOW_UP = "FOLLOW_UP"
    PAUSED = "PAUSED"
    CONFIRM_END = "CONFIRM_END"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class CandidateProfile(BaseModel):
    """Structured extraction of candidate's profile from resume."""
    candidate_name: Optional[str] = Field(default=None, description="Full name if found")
    industry: str = Field(default="Artificial Intelligence, Software & IT")
    target_role: str = Field(description="Target job title")
    interview_type: str = Field(default="Behavioral (STAR Method)")
    difficulty_tier: str = Field(default="Standard Industry Interview")
    job_description: Optional[str] = Field(default=None, description="Custom job description if provided")
    experience_level: str = Field(default="Mid-Level (3-6 yrs)")
    years_of_experience: Optional[float] = Field(default=0.0)
    skills: List[str] = Field(default_factory=list)
    key_projects: List[str] = Field(default_factory=list)
    experience_summary: str = Field(default="")
    education: Optional[str] = Field(default=None)
    focus_areas: List[str] = Field(default_factory=list)


class QuestionItem(BaseModel):
    """A structured interview question item."""
    id: int = 1
    category: str = "General"
    interview_type: str = "Behavioral (STAR Method)"
    difficulty: str = "Standard"
    question_text: str = Field(
        default="",
        validation_alias=AliasChoices("question_text", "question", "text", "prompt", "q_text"),
    )
    target_competencies: List[str] = Field(default_factory=list)
    expected_concepts: List[str] = Field(default_factory=list)
    sample_ideal_answer: Optional[str] = None
    spoken_audio_bytes: Optional[bytes] = None


class InterviewPlan(BaseModel):
    """The generated plan for the mock interview session."""
    industry: str
    target_role: str
    interview_type: str
    experience_level: str
    difficulty_tier: str
    total_questions: int = 4
    questions: List[QuestionItem] = Field(default_factory=list)


class StarFrameworkScore(BaseModel):
    """Specific scoring for behavioral questions using the STAR framework."""
    situation_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Clear context/problem setup")
    task_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Clear responsibility/challenge definition")
    action_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Detailed personal actions taken")
    result_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Measurable outcome or learning")
    star_completeness_ratio: float = Field(default=0.0, ge=0.0, le=1.0)


class DeliveryAnalytics(BaseModel):
    """Speech and pacing diagnostics inspired by modern coaching tools."""
    word_count: int = Field(default=0)
    estimated_duration_sec: float = Field(default=0.0)
    words_per_minute: float = Field(default=0.0)
    pacing_rating: str = Field(default="Optimal", description="Too Fast, Optimal, or Too Slow")
    filler_word_count: int = Field(default=0)
    filler_words_detected: List[str] = Field(default_factory=list)
    conciseness_score: float = Field(default=80.0, ge=0.0, le=100.0)


class AnswerEvaluation(BaseModel):
    """Multi-criteria evaluation tailored to the profession & interview type."""
    question_id: int
    score: float = Field(ge=0.0, le=100.0)
    answer_status: str = Field(
        default="Answered",
        description="Answered | Partially Answered | Incorrect | Unanswered | Audio Recognition Failure",
    )

    # Universal / Role-tailored dimensions
    technical_or_domain_accuracy: float = Field(ge=0.0, le=100.0)
    completeness_and_relevance: float = Field(ge=0.0, le=100.0)
    practical_reasoning_and_scenarios: float = Field(ge=0.0, le=100.0)
    communication_and_clarity: float = Field(ge=0.0, le=100.0)
    conceptual_understanding: float = Field(default=0.0, ge=0.0, le=100.0)
    problem_solving_ability: float = Field(default=0.0, ge=0.0, le=100.0)
    practical_experience: float = Field(default=0.0, ge=0.0, le=100.0)

    # Coaching Analytics
    star_analysis: Optional[StarFrameworkScore] = None
    delivery_analytics: Optional[DeliveryAnalytics] = None

    strengths: List[str] = Field(default_factory=list)
    missing_or_incorrect: List[str] = Field(default_factory=list)
    improvement_feedback: str
    suggested_ideal_outline: Optional[str] = None

    requires_follow_up: bool = False
    follow_up_question: Optional[str] = None


class QuestionSessionRecord(BaseModel):
    """Record of a single question and response cycle."""
    question: QuestionItem
    candidate_answer: str
    duration_seconds: float = 0.0
    evaluation: Optional[AnswerEvaluation] = None
    follow_up_asked: Optional[str] = None
    follow_up_answer: Optional[str] = None
    follow_up_evaluation: Optional[AnswerEvaluation] = None
    transcription_confidence: Optional[str] = None


class FinalAssessmentReport(BaseModel):
    """Comprehensive final mock interview report."""
    candidate_name: Optional[str] = "Candidate"
    industry: str
    target_role: str
    interview_type: str
    interview_mode: str
    interview_date: str
    overall_score: float = Field(ge=0.0, le=100.0)
    technical_knowledge_score: float = Field(default=0.0, ge=0.0, le=100.0)
    communication_score: float = Field(default=0.0, ge=0.0, le=100.0)
    problem_solving_score: float = Field(default=0.0, ge=0.0, le=100.0)
    answer_relevance_score: float = Field(default=0.0, ge=0.0, le=100.0)

    passed: bool
    passing_threshold: float = 70.0
    outcome: str = "Good Performance"
    overall_readiness: str = "Ready for Interviews"
    final_assessment_summary: str = ""
    total_questions_asked: int = 0
    questions_answered_count: int = 0
    is_valid_interview: bool = True

    category_scores: Dict[str, float] = Field(default_factory=dict)
    average_delivery_pacing: str = "Optimal"
    total_filler_words: int = 0
    key_strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)
    areas_for_improvement: List[str] = Field(default_factory=list)
    skills_needing_preparation: List[str] = Field(default_factory=list)
    recommended_topics_to_study: List[str] = Field(default_factory=list)
    session_records: List[QuestionSessionRecord] = Field(default_factory=list)
