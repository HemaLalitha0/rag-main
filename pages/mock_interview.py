"""
AI Mock Interview Studio — Professional Huru-Inspired Interview Platform
========================================================================
- Full-width, studio-grade AI interview workspace with zero Streamlit sidebar clutter.
- Uses the 4 permanent Voicebox cloned voices (Manideep, Chirag, Hema, Sushma) via
  their exact existing Voicebox IDs while keeping internal IDs, engines, and URLs
  completely hidden from the candidate-facing interface.
- Genuine hands-free conversational flow: automatic welcome & question playback,
  continuous browser Web Audio VAD, Whisper STT, RAG + LLM answer evaluation,
  adaptive follow-ups, and automatic question progression.
- Comprehensive Interview Completion report with Overall Score, Communication,
  Technical Knowledge, Confidence & Clarity, Answer Relevance, Strengths,
  Improvement Areas, Recommended Next Steps, Readiness Assessment, and PDF download.
"""

import os
import io
import time
import base64
import tempfile
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="MockMate — AI Interview Studio | SHR Trinity",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from interview_schemas import (
    InterviewState,
    InterviewMode,
    CandidateProfile,
    InterviewPlan,
    QuestionItem,
    QuestionSessionRecord,
    AnswerEvaluation,
    DeliveryAnalytics,
    FinalAssessmentReport,
)
from industry_catalog import INDUSTRY_CATALOG, INTERVIEW_TYPES
from interview_engine import (
    extract_candidate_profile,
    generate_universal_interview_plan,
    evaluate_universal_answer,
    analyze_delivery_metrics,
    generate_universal_final_report,
)
import importlib
import voicebox_client
importlib.reload(voicebox_client)
import audio_service
importlib.reload(audio_service)
import interview_bridge_server
importlib.reload(interview_bridge_server)
from audio_service import (
    transcribe_audio_bytes,
    synthesize_speech,
    verify_voice_profile_available,
    VOICEBOX_PROFILES,
    PERMANENT_VOICE_DESCRIPTIONS,
)
from report_exporter import export_report_to_pdf
import video_components
importlib.reload(video_components)
from video_components import render_interview_stage
from interview_bridge_server import (
    start_interview_bridge_server,
    reset_live_session,
    get_live_state,
    LIVE_SESSION,
)

# Start local WebRTC / VAD audio bridge server on port 8765
start_interview_bridge_server()

# =====================================================================
# 0. AUTHENTICATION GATE (GOOGLE SINGLE SIGN-ON & CREATE ACCOUNT)
# =====================================================================
import auth_guard
importlib.reload(auth_guard)
from auth_guard import render_auth_page, render_user_header

_is_mockmate_authenticated = render_auth_page(
    app_title="Sign in to MockMate AI",
    app_subtitle="Access the AI Mock Interview Studio, personalized resume grounding, and executive rubric analytics.",
    icon_emoji="🎙️",
)
if not _is_mockmate_authenticated:
    st.stop()


# =====================================================================
# 1. SESSION STATE INITIALIZATION
# =====================================================================
def init_interview_session_state():
    defaults = {
        "interview_state": InterviewState.SETUP,
        "candidate_profile": None,
        "interview_plan": None,
        "interview_mode": InterviewMode.VIDEO,
        "selected_voice_name": "Manideep",
        "selected_voice_id": VOICEBOX_PROFILES["Manideep"],
        "resume_filename": "",
        "resume_raw_text": "",
        "questions_list": [],
        "current_q_index": 0,
        "session_records": [],
        "final_report": None,
        "company_context": "Enterprise Assessment",
        "duration_minutes": 30,
        "voice_preview_b64": "",
        "voice_preview_name": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_interview_session_state()

is_active_interview = st.session_state.interview_state in (
    InterviewState.ASKING_QUESTION,
    InterviewState.WAITING_FOR_ANSWER,
    InterviewState.SAINA_SPEAKING,
    InterviewState.CANDIDATE_SPEAKING,
)


# =====================================================================
# 2. HURU-INSPIRED GLOBAL STUDIO CSS (SIDEBAR & CHROME REMOVED)
# =====================================================================
st.markdown(
    f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap');

        /* Hide Streamlit default navigation, sidebar, header, and footer */
        [data-testid="stSidebar"],
        [data-testid="stSidebarNav"],
        [data-testid="collapsedControl"],
        header[data-testid="stHeader"],
        footer,
        #MainMenu {{
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            height: 0 !important;
        }}

        html, body, [data-testid="stAppViewContainer"], .stApp {{
            background: radial-gradient(circle at 15% 10%, #111827 0%, #0B0F17 55%, #070A10 100%) !important;
            color: #F8FAFC !important;
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        }}

        .block-container {{
            max-width: {'1440px' if is_active_interview else '1280px'} !important;
            padding-top: {'0.6rem' if is_active_interview else '1.5rem'} !important;
            padding-bottom: {'0.25rem' if is_active_interview else '2.5rem'} !important;
            padding-left: {'1.25rem' if is_active_interview else '2rem'} !important;
            padding-right: {'1.25rem' if is_active_interview else '2rem'} !important;
            margin: 0 auto !important;
        }}

        /* Prevent unnecessary scrolling during an active interview */
        {'body, [data-testid="stAppViewContainer"] { overflow-y: hidden !important; }' if is_active_interview else ''}

        /* Studio Cards */
        .huru-card {{
            background: rgba(17, 24, 39, 0.86);
            border: 1px solid rgba(148, 163, 184, 0.14);
            border-radius: 16px;
            padding: 22px 24px;
            box-shadow: 0 20px 45px -15px rgba(0, 0, 0, 0.6);
            margin-bottom: 16px;
        }}

        .huru-section-label {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #818CF8;
            margin-bottom: 6px;
        }}

        .huru-card-title {{
            font-size: 1.15rem;
            font-weight: 700;
            color: #F8FAFC;
            margin-bottom: 4px;
            letter-spacing: -0.01em;
        }}

        .huru-card-subtitle {{
            font-size: 0.85rem;
            color: #94A3B8;
            margin-bottom: 16px;
            line-height: 1.45;
        }}

        /* Form Controls Styling */
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        textarea {{
            background-color: rgba(15, 23, 42, 0.9) !important;
            border-color: rgba(148, 163, 184, 0.2) !important;
            color: #F8FAFC !important;
            border-radius: 10px !important;
        }}

        label, .stRadio label, .stSelectbox label, .stTextInput label, .stFileUploader label {{
            color: #E2E8F0 !important;
            font-weight: 600 !important;
            font-size: 0.86rem !important;
        }}

        /* Primary CTA Button */
        div.stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%) !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(129, 140, 248, 0.4) !important;
            border-radius: 12px !important;
            padding: 0.68rem 1.4rem !important;
            font-weight: 700 !important;
            font-size: 0.95rem !important;
            letter-spacing: -0.01em !important;
            box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.55) !important;
            transition: all 0.2s ease !important;
        }}
        div.stButton > button[kind="primary"]:hover {{
            background: linear-gradient(135deg, #4338CA 0%, #4F46E5 100%) !important;
            transform: translateY(-1px) !important;
        }}

        /* Secondary Button */
        div.stButton > button[kind="secondary"] {{
            background: rgba(30, 41, 59, 0.85) !important;
            color: #E2E8F0 !important;
            border: 1px solid rgba(148, 163, 184, 0.22) !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 0.84rem !important;
        }}
        div.stButton > button[kind="secondary"]:hover {{
            background: rgba(51, 65, 85, 0.95) !important;
            border-color: rgba(148, 163, 184, 0.4) !important;
        }}

        /* Hide the internal End Call bridge button during active interview */
        .hidden-hangup-trigger {{
            position: fixed !important;
            bottom: -200px !important;
            right: -200px !important;
            width: 1px !important;
            height: 1px !important;
            opacity: 0 !important;
            pointer-events: none !important;
            overflow: hidden !important;
        }}

        /* Metric Cards for Completion Report */
        .score-pill-card {{
            background: linear-gradient(180deg, rgba(30, 41, 59, 0.75) 0%, rgba(15, 23, 42, 0.9) 100%);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 14px;
            padding: 18px 20px;
            height: 100%;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


# =====================================================================
# 3. RESUME PARSING & SESSION FINALIZATION HELPERS
# =====================================================================
def extract_text_from_uploaded_resume(uploaded_file) -> str:
    """Extract clean text from PDF, DOCX, or TXT resume upload."""
    if uploaded_file is None:
        return ""
    name = uploaded_file.name.lower()
    raw_bytes = uploaded_file.read()
    try:
        if name.endswith(".pdf"):
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
            return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        elif name.endswith(".docx"):
            import docx
            doc = docx.Document(io.BytesIO(raw_bytes))
            return "\n".join(p.text for p in doc.paragraphs if p.text).strip()
        else:
            return raw_bytes.decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


def finalize_and_transition_to_report():
    """
    Synchronizes any answers recorded by the hands-free bridge server,
    marks any unreached or unanswered planned questions as Unanswered (score 0.0),
    compiles the FinalAssessmentReport, and transitions to COMPLETED.
    Never invents transcripts or assigns fallback scores (e.g. 55%, 70%, 74%) to unanswered questions.
    """
    profile: CandidateProfile = st.session_state.candidate_profile
    questions = list(st.session_state.questions_list or [])
    compiled_records: list[QuestionSessionRecord] = []
    recorded_q_ids = set()

    raw_bridge_records = list(LIVE_SESSION.get("session_records", []))
    if not raw_bridge_records:
        try:
            import requests as _req
            _r = _req.get("http://127.0.0.1:8765/state", timeout=1.2)
            if _r.status_code == 200:
                raw_bridge_records = list(_r.json().get("session_records", []))
        except Exception:
            pass

    for item in raw_bridge_records:
        if isinstance(item, QuestionSessionRecord):
            compiled_records.append(item)
            recorded_q_ids.add(item.question.id)
        elif isinstance(item, dict):
            q_dict = item.get("question", {})
            q_id = q_dict.get("id", len(compiled_records) + 1)
            # Match against planned QuestionItem if available to preserve expected_concepts & sample_ideal_answer
            matched_planned = next((pq for pq in questions if pq.id == q_id), None)
            q_obj = QuestionItem(
                id=q_id,
                category=q_dict.get("category") or (matched_planned.category if matched_planned else (profile.interview_type if profile else "Behavioral")),
                interview_type=profile.interview_type if profile else "Behavioral (STAR Method)",
                difficulty=q_dict.get("difficulty") or (matched_planned.difficulty if matched_planned else "Standard"),
                question_text=q_dict.get("text") or q_dict.get("question_text") or (matched_planned.question_text if matched_planned else "Interview Question"),
                target_competencies=q_dict.get("target_competencies") or (matched_planned.target_competencies if matched_planned else []),
                expected_concepts=q_dict.get("expected_concepts") or (matched_planned.expected_concepts if matched_planned else []),
                sample_ideal_answer=matched_planned.sample_ideal_answer if matched_planned else None,
            )
            ans_text = (item.get("candidate_answer") or "").strip() or "(No spoken response recorded)"
            dur_sec = float(item.get("duration_seconds", 25.0) or 25.0)

            existing_eval = item.get("evaluation")
            eval_obj = None
            if isinstance(existing_eval, AnswerEvaluation):
                eval_obj = existing_eval
            elif isinstance(existing_eval, dict) and "score" in existing_eval:
                try:
                    eval_obj = AnswerEvaluation(**existing_eval)
                except Exception:
                    eval_obj = None

            if eval_obj is None:
                eval_obj = evaluate_universal_answer(
                    question=q_obj,
                    candidate_answer=ans_text,
                    industry=profile.industry if profile else "Artificial Intelligence, Software & IT",
                    target_role=profile.target_role if profile else "Software Engineer",
                    interview_type=profile.interview_type if profile else "Behavioral (STAR Method)",
                    duration_sec=dur_sec,
                )

            compiled_records.append(
                QuestionSessionRecord(
                    question=q_obj,
                    candidate_answer=ans_text,
                    duration_seconds=dur_sec,
                    evaluation=eval_obj,
                    follow_up_asked=item.get("follow_up_question"),
                    follow_up_answer=item.get("follow_up_answer"),
                )
            )
            recorded_q_ids.add(q_id)

    # Check if there is an unrecorded live transcript from the active question when End Call was clicked
    live_txt = (LIVE_SESSION.get("live_transcript") or "").strip()
    active_q_idx = int(LIVE_SESSION.get("current_question_idx", 0))
    if live_txt and len(live_txt.split()) >= 3 and 0 <= active_q_idx < len(questions):
        active_q_obj = questions[active_q_idx]
        if active_q_obj.id not in recorded_q_ids:
            eval_obj = evaluate_universal_answer(
                question=active_q_obj,
                candidate_answer=live_txt,
                industry=profile.industry if profile else "Artificial Intelligence, Software & IT",
                target_role=profile.target_role if profile else "Software Engineer",
                interview_type=profile.interview_type if profile else "Behavioral (STAR Method)",
                duration_sec=20.0,
            )
            compiled_records.append(
                QuestionSessionRecord(
                    question=active_q_obj,
                    candidate_answer=live_txt,
                    duration_seconds=20.0,
                    evaluation=eval_obj,
                )
            )
            recorded_q_ids.add(active_q_obj.id)

    # Ensure every remaining planned question in the session is explicitly recorded as Unanswered (score = 0.0)
    for pq in questions:
        if pq.id not in recorded_q_ids:
            unanswered_eval = evaluate_universal_answer(
                question=pq,
                candidate_answer="(No answer provided - call ended early)",
                industry=profile.industry if profile else "Artificial Intelligence, Software & IT",
                target_role=profile.target_role if profile else "Software Engineer",
                interview_type=profile.interview_type if profile else "Behavioral (STAR Method)",
                duration_sec=0.0,
            )
            compiled_records.append(
                QuestionSessionRecord(
                    question=pq,
                    candidate_answer="(No answer provided - call ended early)",
                    duration_seconds=0.0,
                    evaluation=unanswered_eval,
                )
            )
            recorded_q_ids.add(pq.id)

    compiled_records.sort(key=lambda r: r.question.id)
    st.session_state.session_records = compiled_records

    if profile and compiled_records:
        st.session_state.final_report = generate_universal_final_report(
            profile=profile,
            session_records=compiled_records,
            interview_mode=st.session_state.interview_mode.value,
        )

    st.session_state.interview_state = InterviewState.COMPLETED


# =====================================================================
# STAGE 1: INTERVIEW CONFIGURATION STUDIO (SETUP)
# =====================================================================
if st.session_state.interview_state == InterviewState.SETUP:

    # Top Studio Navigation Bar
    nav_left, nav_right = st.columns([4, 1])
    with nav_left:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 18px;">
                <div style="width: 44px; height: 44px; border-radius: 12px; background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%); display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.1rem; color: #FFFFFF; box-shadow: 0 10px 24px -6px rgba(99, 102, 241, 0.65);">
                    AI
                </div>
                <div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 1.45rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.02em;">MockMate AI</span>
                        <span style="font-size: 0.72rem; font-weight: 700; color: #818CF8; background: rgba(99, 102, 241, 0.14); border: 1px solid rgba(99, 102, 241, 0.3); padding: 3px 10px; border-radius: 999px; letter-spacing: 0.04em;">SHR TRINITY &bull; LIVE INTERVIEW STUDIO</span>
                    </div>
                    <div style="font-size: 0.86rem; color: #94A3B8; margin-top: 2px;">
                        Realistic, hands-free AI interview simulations with real-time speech analysis and executive competency scoring
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with nav_right:
        if st.button("← Back to Workspace", use_container_width=True):
            st.switch_page("pages/RAG_Assistant.py")

    col_left, col_right = st.columns([1.08, 0.92], gap="large")

    # -----------------------------------------------------------------
    # LEFT COLUMN: Role, Job Context & Session Structure
    # -----------------------------------------------------------------
    with col_left:
        st.markdown(
            """
            <div class="huru-card">
                <div class="huru-section-label">STEP 01 &bull; ROLE &amp; CONTEXT</div>
                <div class="huru-card-title">Target Position &amp; Interview Parameters</div>
                <div class="huru-card-subtitle">Select your target role, company context, and assessment depth. Questions adapt dynamically to your profile and spoken responses.</div>
            """,
            unsafe_allow_html=True,
        )

        industries = list(INDUSTRY_CATALOG.keys())
        c_ind, c_role = st.columns(2)
        with c_ind:
            selected_industry = st.selectbox(
                "Industry / Domain",
                options=industries,
                index=0,
            )

        with c_role:
            roles_in_industry = INDUSTRY_CATALOG[selected_industry].get("roles", [])
            if not roles_in_industry or selected_industry == "Other / Custom Profession":
                selected_role = st.text_input(
                    "Target Job Role",
                    value="Senior AI Engineer",
                    placeholder="e.g., Staff Product Manager",
                )
            else:
                role_choice = st.selectbox(
                    "Target Role",
                    options=roles_in_industry + ["Custom Role..."],
                    index=0,
                )
                if role_choice == "Custom Role...":
                    selected_role = st.text_input(
                        "Enter Custom Role Title",
                        value="Lead Software Engineer",
                    )
                else:
                    selected_role = role_choice

        c_comp, c_type = st.columns([1.15, 0.85])
        with c_comp:
            company_context = st.text_input(
                "Company / Job Context",
                value=st.session_state.company_context,
                placeholder="e.g., Enterprise Technical & Behavioral Round",
            )
            st.session_state.company_context = company_context

        with c_type:
            selected_interview_type = st.selectbox(
                "Interview Style",
                options=list(INTERVIEW_TYPES.keys()),
                index=0,
            )

        DURATION_OPTIONS = {
            "15 Min  •  3 Questions (Focused Sprint)": (15, 3),
            "30 Min  •  5 Questions (Standard Round)": (30, 5),
            "45 Min  •  8 Questions (Deep Dive)": (45, 8),
            "60 Min  •  10 Questions (Full Loop)": (60, 10),
        }
        c_dur, c_diff, c_mode = st.columns([1.25, 0.85, 0.75])
        with c_dur:
            selected_duration_label = st.selectbox(
                "Session Duration & Question Count",
                options=list(DURATION_OPTIONS.keys()),
                index=1,
            )
            duration_mins, total_q_count = DURATION_OPTIONS[selected_duration_label]
            st.session_state.duration_minutes = duration_mins

        with c_diff:
            selected_difficulty = st.selectbox(
                "Difficulty Tier",
                options=[
                    "Standard Industry Interview",
                    "Senior / Executive Bar",
                    "Entry / Foundational",
                ],
                index=0,
            )

        with c_mode:
            studio_mode = st.selectbox(
                "Camera Mode",
                options=["Video + Audio", "Audio Only"],
                index=0,
            )
            enable_video = studio_mode == "Video + Audio"
            st.session_state.interview_mode = InterviewMode.VIDEO if enable_video else InterviewMode.AUDIO

        st.markdown("</div>", unsafe_allow_html=True)

        # Resume & Candidate Profile Card
        st.markdown(
            """
            <div class="huru-card">
                <div class="huru-section-label">STEP 02 &bull; CANDIDATE PROFILE</div>
                <div class="huru-card-title">Candidate Details &amp; Resume Grounding</div>
                <div class="huru-card-subtitle">Upload your resume to personalize technical and behavioral questions around your actual projects and experience.</div>
            """,
            unsafe_allow_html=True,
        )

        # Retrieve candidate name from authenticated user session if available
        auth_user_dict = st.session_state.get("authenticated_user") or {}
        auth_full_name = (
            auth_user_dict.get("full_name")
            or auth_user_dict.get("username")
            or st.session_state.get("username")
            or st.session_state.get("user")
            or ""
        ).strip()

        default_cand_name = (
            st.session_state.candidate_profile.candidate_name
            if st.session_state.candidate_profile and st.session_state.candidate_profile.candidate_name
            else (auth_full_name if auth_full_name else "Candidate")
        )
        candidate_name_input = st.text_input(
            "Your Display Name",
            value=default_cand_name if default_cand_name else "Candidate",
            placeholder="Enter your name for the interview panel",
        )

        uploaded_resume = st.file_uploader(
            "Upload Resume (Optional — PDF, DOCX, TXT)",
            type=["pdf", "docx", "txt"],
        )

        if uploaded_resume is not None:
            if st.session_state.resume_filename != uploaded_resume.name:
                with st.spinner("Analyzing resume experience & core competencies..."):
                    resume_text = extract_text_from_uploaded_resume(uploaded_resume)
                    st.session_state.resume_raw_text = resume_text
                    st.session_state.resume_filename = uploaded_resume.name
                    if resume_text:
                        try:
                            extracted_prof = extract_candidate_profile(
                                resume_text=resume_text,
                                industry=selected_industry,
                                target_role=selected_role,
                                interview_type=selected_interview_type,
                                experience_level="Mid-Level (3-6 yrs)",
                                difficulty_tier=selected_difficulty,
                                job_description=company_context,
                            )
                            st.session_state.candidate_profile = extracted_prof
                        except Exception:
                            pass

        if st.session_state.candidate_profile and st.session_state.resume_filename:
            cp = st.session_state.candidate_profile
            skills_preview = ", ".join(cp.skills[:8]) if cp.skills else "Domain competencies extracted"
            st.markdown(
                f"""
                <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.28); border-radius: 10px; padding: 10px 14px; margin-top: 8px; font-size: 0.82rem; color: #D1FAE5;">
                    <strong style="color: #34D399;">Resume Tailoring Active:</strong> {cp.candidate_name or candidate_name_input} &bull; {cp.experience_level}
                    <div style="color: #94A3B8; font-size: 0.78rem; margin-top: 3px;">Key Skills: {skills_preview}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------
    # RIGHT COLUMN: Interviewer Voice Selection & Session Launch
    # -----------------------------------------------------------------
    with col_right:
        st.markdown(
            """
            <div class="huru-card">
                <div class="huru-section-label">STEP 03 &bull; AI INTERVIEWER PANEL</div>
                <div class="huru-card-title">Select Your Interviewer</div>
                <div class="huru-card-subtitle">Choose the interviewer persona who will conduct your session. Your selected interviewer will speak consistently throughout the entire interview.</div>
            """,
            unsafe_allow_html=True,
        )

        voice_names = list(VOICEBOX_PROFILES.keys())  # ["Manideep", "Chirag", "Hema", "Sushma"]
        VOICE_ROLE_BADGES = {
            "Manideep": ("Executive Technical Lead", "Calm, authoritative & analytical"),
            "Chirag": ("Senior Engineering Manager", "Dynamic, structured & direct"),
            "Hema": ("Principal Hiring Director", "Warm, articulate & thorough"),
            "Sushma": ("Lead Talent & Domain Partner", "Composed, clear & encouraging"),
        }

        selected_voice_name = st.radio(
            "Interviewer Voice Persona",
            options=voice_names,
            index=voice_names.index(st.session_state.selected_voice_name)
            if st.session_state.selected_voice_name in voice_names
            else 0,
            horizontal=True,
        )
        selected_voice_id = VOICEBOX_PROFILES[selected_voice_name]
        st.session_state.selected_voice_name = selected_voice_name
        st.session_state.selected_voice_id = selected_voice_id

        role_title_badge, tone_desc = VOICE_ROLE_BADGES.get(
            selected_voice_name, ("Senior AI Interviewer", "Professional & articulate")
        )
        persona_detail = PERMANENT_VOICE_DESCRIPTIONS.get(selected_voice_name, tone_desc)

        # Selected Interviewer Preview Card (Zero internal IDs or engine details shown)
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%); border: 1px solid rgba(99, 102, 241, 0.35); border-radius: 14px; padding: 16px 18px; margin: 10px 0 14px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div style="width: 36px; height: 36px; border-radius: 50%; background: rgba(99, 102, 241, 0.2); border: 1px solid rgba(99, 102, 241, 0.45); display: flex; align-items: center; justify-content: center; font-weight: 800; color: #A5B4FC; font-size: 0.9rem;">
                            {selected_voice_name[0]}
                        </div>
                        <div>
                            <div style="font-size: 1.0rem; font-weight: 700; color: #F8FAFC;">{selected_voice_name}</div>
                            <div style="font-size: 0.76rem; color: #818CF8; font-weight: 600;">{role_title_badge}</div>
                        </div>
                    </div>
                    <span style="font-size: 0.72rem; font-weight: 600; color: #34D399; background: rgba(16, 185, 129, 0.14); border: 1px solid rgba(16, 185, 129, 0.3); padding: 3px 10px; border-radius: 999px;">
                        Studio Voice Ready
                    </span>
                </div>
                <div style="font-size: 0.82rem; color: #94A3B8; line-height: 1.45; margin-top: 6px;">
                    {persona_detail}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(f"Preview {selected_voice_name}'s Voice", use_container_width=True):
            vb_online, _ = verify_voice_profile_available(selected_voice_id)
            if not vb_online:
                st.error(
                    f"{selected_voice_name}'s interviewer voice service is currently offline. Please ensure the voice service is running."
                )
            else:
                with st.spinner(f"Preparing audio sample for {selected_voice_name}..."):
                    sample_line = (
                        f"Hello, I am {selected_voice_name}. Welcome to your interview session. "
                        f"I look forward to learning about your experience today."
                    )
                    try:
                        wav_bytes = synthesize_speech(
                            sample_line,
                            voice_profile_id=selected_voice_id,
                            allow_fallback=True,
                        )
                        if wav_bytes:
                            st.session_state.voice_preview_b64 = base64.b64encode(wav_bytes).decode("ascii")
                            st.session_state.voice_preview_name = selected_voice_name
                    except Exception:
                        st.error(
                            f"Unable to generate voice preview for {selected_voice_name} right now. Please try again in a moment."
                        )

        if st.session_state.voice_preview_b64 and st.session_state.voice_preview_name == selected_voice_name:
            st.audio(
                base64.b64decode(st.session_state.voice_preview_b64),
                format="audio/wav",
            )

        st.markdown(
            """
            <div style="background: rgba(15, 23, 42, 0.75); border: 1px solid rgba(148, 163, 184, 0.14); border-radius: 12px; padding: 14px 16px; margin-top: 12px;">
                <div style="font-size: 0.8rem; font-weight: 700; color: #E2E8F0; margin-bottom: 8px;">
                    Hands-Free Interview Experience
                </div>
                <div style="font-size: 0.79rem; color: #94A3B8; line-height: 1.6;">
                    &bull; <strong>Automatic Turn-Taking:</strong> Your microphone activates automatically after the interviewer speaks.<br>
                    &bull; <strong>Natural Conversation:</strong> Just speak naturally—voice activity detection senses when you finish answering.<br>
                    &bull; <strong>Executive Report:</strong> Receive a full breakdown of Communication, Technical Accuracy, Confidence, and Readiness.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

        start_clicked = st.button(
            "Enter Live Interview Room →",
            type="primary",
            use_container_width=True,
        )

        if start_clicked:
            vb_ok, _ = verify_voice_profile_available(selected_voice_id)
            if not vb_ok:
                st.error(
                    f"The interviewer voice service for {selected_voice_name} is currently unavailable. "
                    f"Please verify the voice server is active and try again."
                )
            else:
                cand_name_clean = (candidate_name_input or "Candidate").strip()
                if st.session_state.candidate_profile:
                    profile = st.session_state.candidate_profile
                    profile.candidate_name = cand_name_clean
                    profile.industry = selected_industry
                    profile.target_role = selected_role.strip() or "Software Engineer"
                    profile.interview_type = selected_interview_type
                    profile.difficulty_tier = selected_difficulty
                    profile.job_description = company_context
                else:
                    profile = CandidateProfile(
                        candidate_name=cand_name_clean,
                        industry=selected_industry,
                        target_role=selected_role.strip() or "Software Engineer",
                        interview_type=selected_interview_type,
                        difficulty_tier=selected_difficulty,
                        job_description=company_context,
                        experience_level="Mid-Level (3-6 yrs)",
                    )
                st.session_state.candidate_profile = profile

                with st.spinner(f"Preparing your interview room with {selected_voice_name}..."):
                    plan = generate_universal_interview_plan(
                        profile=profile,
                        num_questions=total_q_count,
                        synthesize_audio=False,
                        voice_profile_id=selected_voice_id,
                    )
                    st.session_state.interview_plan = plan
                    st.session_state.questions_list = plan.questions
                    st.session_state.current_q_index = 0
                    st.session_state.session_records = []
                    st.session_state.final_report = None

                    bridge_questions = [
                        {
                            "id": q.id,
                            "text": q.question_text,
                            "category": q.category,
                            "difficulty": q.difficulty,
                            "target_competencies": q.target_competencies,
                            "expected_concepts": q.expected_concepts,
                        }
                        for q in plan.questions
                    ]
                    plan_meta = {
                        "industry": profile.industry,
                        "role": profile.target_role,
                        "interview_type": profile.interview_type,
                        "duration_minutes": duration_mins,
                        "company_context": company_context,
                        "voice_profile_id": selected_voice_id,
                        "interviewer_name": selected_voice_name,
                    }
                    reset_live_session(
                        candidate_name=cand_name_clean,
                        questions=bridge_questions,
                        plan_metadata=plan_meta,
                        voice_profile_id=selected_voice_id,
                        interviewer_name=selected_voice_name,
                        blocking_greeting=False,
                    )
                    try:
                        import requests as _req
                        _req.post(
                            "http://127.0.0.1:8765/init_session",
                            json={
                                "candidate_name": cand_name_clean,
                                "questions": bridge_questions,
                                "plan_metadata": plan_meta,
                                "voice_profile_id": selected_voice_id,
                                "interviewer_name": selected_voice_name,
                            },
                            timeout=1.5,
                        )
                    except Exception:
                        pass

                st.session_state.interview_state = InterviewState.ASKING_QUESTION
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# =====================================================================
# STAGE 2: ACTIVE HANDS-FREE INTERVIEW WORKSPACE
# =====================================================================
elif st.session_state.interview_state in (
    InterviewState.ASKING_QUESTION,
    InterviewState.WAITING_FOR_ANSWER,
    InterviewState.SAINA_SPEAKING,
    InterviewState.CANDIDATE_SPEAKING,
):
    profile: CandidateProfile = st.session_state.candidate_profile
    questions = st.session_state.questions_list or []
    live_state = get_live_state()

    if live_state.get("finished") or live_state.get("exit_requested"):
        finalize_and_transition_to_report()
        st.rerun()

    live_q_num = int(live_state.get("question_number", 1))
    total_q = len(questions) if questions else int(live_state.get("total_questions", 5))

    current_q_obj = (
        questions[min(max(0, live_q_num - 1), len(questions) - 1)]
        if questions
        else QuestionItem(
            id=1,
            category="Behavioral (STAR Method)",
            difficulty="Standard",
            question_text="Tell me about your background and most impactful recent project.",
        )
    )

    interviewer_display_name = st.session_state.selected_voice_name or "Manideep"
    candidate_display_name = (
        profile.candidate_name if profile and profile.candidate_name else "Candidate"
    )

    raw_speaker = live_state.get("active_speaker", "syna")
    mapped_speaker = "interviewer" if raw_speaker in ("syna", "interviewer") else (
        "candidate" if raw_speaker == "candidate" else "waiting"
    )

    spoken_prompt = live_state.get("subtitles") or current_q_obj.question_text
    initial_audio_b64 = live_state.get("current_audio_b64") or ""

    # Render the Full-Width Huru-Inspired Studio Stage
    render_interview_stage(
        interviewer_name=interviewer_display_name,
        candidate_name=candidate_display_name,
        active_speaker=mapped_speaker,
        current_question=spoken_prompt,
        enable_camera=(st.session_state.interview_mode == InterviewMode.VIDEO),
        status_text="Hands-Free Voice Mode • Automatic Turn Detection",
        transcription_text=live_state.get("live_transcript", ""),
        is_loading_room=False,
        loading_seconds_left=0,
        audio_base64=initial_audio_b64,
        height=410,
        role_title=profile.target_role if profile else "Software Engineer",
        company_context=st.session_state.get("company_context", "Enterprise Assessment"),
        question_number=min(live_q_num, max(1, total_q)),
        total_questions=max(1, total_q),
        question_category=f"{current_q_obj.category} • {current_q_obj.difficulty}",
        duration_minutes=st.session_state.get("duration_minutes", 30),
    )

    # Hidden Streamlit bridge button triggered automatically when the user clicks "End Call"
    # inside the studio header or when the interview concludes automatically.
    st.markdown('<div class="hidden-hangup-trigger">', unsafe_allow_html=True)
    if st.button("End Call", key="studio_end_call_bridge_btn"):
        finalize_and_transition_to_report()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# =====================================================================
# STAGE 3: PROFESSIONAL INTERVIEW COMPLETION REPORT
# =====================================================================
elif st.session_state.interview_state == InterviewState.COMPLETED:
    if not st.session_state.final_report:
        finalize_and_transition_to_report()

    report: FinalAssessmentReport = st.session_state.final_report
    profile: CandidateProfile = st.session_state.candidate_profile

    if not report:
        st.session_state.interview_state = InterviewState.SETUP
        st.rerun()

    # Calculate all required competency dimensions (0-100 scale)
    records = report.session_records or []
    valid_records = [
        r for r in records
        if r.evaluation and r.evaluation.score > 0.0 and len(r.candidate_answer.split()) >= 3 and not r.candidate_answer.startswith("(")
    ]
    if valid_records and getattr(report, "outcome", "") != "No Response":
        comm_score = getattr(report, "communication_score", 0.0) or round(
            sum((r.evaluation.communication_and_clarity if r.evaluation else 0.0) for r in valid_records)
            / len(valid_records),
            1,
        )
        tech_score = getattr(report, "technical_knowledge_score", 0.0) or round(
            sum((r.evaluation.technical_or_domain_accuracy if r.evaluation else 0.0) for r in valid_records)
            / len(valid_records),
            1,
        )
        prob_score = getattr(report, "problem_solving_score", 0.0) or round(
            sum((r.evaluation.practical_reasoning_and_scenarios if r.evaluation else 0.0) for r in valid_records)
            / len(valid_records),
            1,
        )
        rel_score = getattr(report, "answer_relevance_score", 0.0) or round(
            sum((r.evaluation.completeness_and_relevance if r.evaluation else 0.0) for r in valid_records)
            / len(valid_records),
            1,
        )
    else:
        comm_score = 0.0
        tech_score = 0.0
        prob_score = 0.0
        rel_score = 0.0

    overall_100 = round(report.overall_score, 1)
    report_outcome = getattr(report, "outcome", "Good Performance")
    overall_readiness_label = getattr(report, "overall_readiness", report_outcome)
    final_assessment_text = getattr(report, "final_assessment_summary", "")

    if report_outcome == "No Response" or not getattr(report, "is_valid_interview", True):
        readiness_badge = "NO RESPONSE • SESSION ENDED EARLY"
        readiness_summary = final_assessment_text or (
            "No candidate speech was captured during this session. "
            "To receive an authentic competency evaluation and score, complete your spoken answers to each interview question."
        )
        readiness_color = "#EF4444"
        readiness_bg = "rgba(239, 68, 68, 0.14)"
        score_subtext = "NO RESPONSE DETECTED (0%)"
    elif report_outcome == "Incomplete Interview":
        ans_count = getattr(report, "questions_answered_count", len(valid_records))
        tot_count = getattr(report, "total_questions_asked", len(records))
        readiness_badge = f"INCOMPLETE INTERVIEW • {ans_count}/{tot_count} QUESTIONS ANSWERED"
        readiness_summary = final_assessment_text or (
            f"{report.candidate_name} completed {ans_count} of {tot_count} interview questions before concluding the session. "
            f"Unanswered questions are marked as Not Attempted (0/100)."
        )
        readiness_color = "#F59E0B"
        readiness_bg = "rgba(245, 158, 11, 0.14)"
        score_subtext = f"{ans_count}/{tot_count} QUESTIONS ANSWERED"
    elif overall_100 >= 80:
        readiness_badge = f"{report_outcome.upper()} • {overall_readiness_label.upper()}"
        readiness_summary = final_assessment_text or (
            f"{report.candidate_name} demonstrated strong domain mastery, structured communication, "
            f"and high readiness for {report.target_role} interviews."
        )
        readiness_color = "#10B981"
        readiness_bg = "rgba(16, 185, 129, 0.14)"
        score_subtext = "AUTHENTIC SCORE"
    elif overall_100 >= 68:
        readiness_badge = f"{report_outcome.upper()} • {overall_readiness_label.upper()}"
        readiness_summary = final_assessment_text or (
            f"{report.candidate_name} showed solid foundational competency for {report.target_role}. "
            f"Refining quantifiable impact and structured examples will elevate interview performance."
        )
        readiness_color = "#38BDF8"
        readiness_bg = "rgba(56, 189, 248, 0.14)"
        score_subtext = "AUTHENTIC SCORE"
    else:
        readiness_badge = f"{report_outcome.upper()} • {overall_readiness_label.upper()}"
        readiness_summary = final_assessment_text or (
            f"{report.candidate_name} is building readiness for {report.target_role}. "
            f"Focus on the recommended study areas and practice delivering complete, structured responses."
        )
        readiness_color = "#F59E0B"
        readiness_bg = "rgba(245, 158, 11, 0.14)"
        score_subtext = "AUTHENTIC SCORE"

    # Top Header Bar
    top_l, top_r = st.columns([3.5, 1.5])
    with top_l:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 14px;">
                <div style="width: 44px; height: 44px; border-radius: 12px; background: linear-gradient(135deg, #10B981 0%, #059669 100%); display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.1rem; color: #FFFFFF;">
                    ✓
                </div>
                <div>
                    <div style="font-size: 1.45rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.02em;">
                        Executive Interview Performance Report
                    </div>
                    <div style="font-size: 0.85rem; color: #94A3B8;">
                        Role: <strong style="color: #E2E8F0;">{report.target_role}</strong> &bull;
                        Interviewer: <strong style="color: #E2E8F0;">{st.session_state.get('selected_voice_name', 'AI Interviewer')}</strong> &bull;
                        Readiness: <strong style="color: #E2E8F0;">{overall_readiness_label}</strong>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with top_r:
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            if st.button("New Interview", type="primary", use_container_width=True):
                st.session_state.interview_state = InterviewState.SETUP
                st.session_state.final_report = None
                st.session_state.session_records = []
                st.rerun()
        with b_col2:
            if st.button("Workspace", use_container_width=True):
                st.switch_page("pages/RAG_Assistant.py")

    # 1. Hero Readiness, Final Assessment & Overall Score Banner
    st.markdown(
        f"""
        <div class="huru-card" style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.92) 0%, rgba(15, 23, 42, 0.96) 100%); border: 1px solid rgba(99, 102, 241, 0.32);">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px;">
                <div style="flex: 1; min-width: 280px;">
                    <div style="display: inline-flex; align-items: center; gap: 8px; font-family: 'JetBrains Mono', monospace; font-size: 0.74rem; font-weight: 700; color: {readiness_color}; background: {readiness_bg}; border: 1px solid {readiness_color}44; padding: 4px 12px; border-radius: 999px; margin-bottom: 10px;">
                        OVERALL INTERVIEW READINESS: {readiness_badge}
                    </div>
                    <div style="font-size: 1.22rem; font-weight: 700; color: #F8FAFC; margin-bottom: 6px;">
                        {report.target_role} &bull; {report.interview_type}
                    </div>
                    <div style="font-size: 0.9rem; color: #CBD5E1; line-height: 1.55;">
                        <strong>Final Assessment:</strong> {readiness_summary}
                    </div>
                </div>
                <div style="background: rgba(9, 13, 22, 0.75); border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 16px; padding: 18px 28px; text-align: center; min-width: 190px;">
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.06em;">
                        OVERALL PERFORMANCE SCORE
                    </div>
                    <div style="font-size: 2.65rem; font-weight: 800; color: #F8FAFC; line-height: 1.15; margin-top: 4px;">
                        {overall_100}<span style="font-size: 1.15rem; color: #64748B; font-weight: 600;">/100</span>
                    </div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: {readiness_color}; margin-top: 4px; font-weight: 700; letter-spacing: 0.04em;">
                        {score_subtext}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Four Required Core Competency Score Cards
    m1, m2, m3, m4 = st.columns(4)
    metrics_spec = [
        (m1, "TECHNICAL KNOWLEDGE", f"{tech_score:.0f}%", f"{tech_score:.1f}/100", "Domain depth, accuracy & conceptual understanding", "#38BDF8"),
        (m2, "COMMUNICATION SCORE", f"{comm_score:.0f}%", f"{comm_score:.1f}/100", "Structure, articulation & vocal clarity", "#6366F1"),
        (m3, "PROBLEM-SOLVING SCORE", f"{prob_score:.0f}%", f"{prob_score:.1f}/100", "Practical reasoning, scenarios & execution", "#10B981"),
        (m4, "ANSWER RELEVANCE", f"{rel_score:.0f}%", f"{rel_score:.1f}/100", "Completeness & alignment with question prompt", "#A855F7"),
    ]
    for col, label, pct_val, raw_str, desc, accent in metrics_spec:
        with col:
            st.markdown(
                f"""
                <div class="score-pill-card" style="border-top: 3px solid {accent};">
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 700; color: #94A3B8; letter-spacing: 0.05em;">
                        {label}
                    </div>
                    <div style="display: flex; align-items: baseline; gap: 8px; margin: 8px 0 4px 0;">
                        <span style="font-size: 1.85rem; font-weight: 800; color: #F8FAFC;">{pct_val}</span>
                        <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: {accent}; font-weight: 700;">({raw_str})</span>
                    </div>
                    <div style="font-size: 0.77rem; color: #94A3B8;">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 3. Row 1: Strengths, Weaknesses, Missing Concepts
    s_col, w_col, mc_col = st.columns(3)
    with s_col:
        strengths_list = report.key_strengths if report.key_strengths else ["No strengths recorded (no responses provided)."]
        strengths_html = "".join(
            f"<li style='margin-bottom: 8px; color: #E2E8F0; font-size: 0.85rem; line-height: 1.45;'>{s}</li>"
            for s in strengths_list
        )
        st.markdown(
            f"""
            <div class="huru-card" style="height: 100%; border-left: 3px solid #10B981;">
                <div class="huru-section-label" style="color: #34D399;">STRENGTHS</div>
                <div class="huru-card-title" style="font-size: 1.02rem; margin-bottom: 10px;">What Stood Out Positively</div>
                <ul style="padding-left: 18px; margin: 0;">{strengths_html}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with w_col:
        weaknesses_list = getattr(report, "weaknesses", None) or report.areas_for_improvement or ["Provide complete, structured examples."]
        weaknesses_html = "".join(
            f"<li style='margin-bottom: 8px; color: #E2E8F0; font-size: 0.85rem; line-height: 1.45;'>{w}</li>"
            for w in weaknesses_list
        )
        st.markdown(
            f"""
            <div class="huru-card" style="height: 100%; border-left: 3px solid #EF4444;">
                <div class="huru-section-label" style="color: #F87171;">WEAKNESSES</div>
                <div class="huru-card-title" style="font-size: 1.02rem; margin-bottom: 10px;">Observed Performance Gaps</div>
                <ul style="padding-left: 18px; margin: 0;">{weaknesses_html}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with mc_col:
        missing_list = getattr(report, "missing_concepts", None) or ["Expand on domain trade-offs and quantifiable impact."]
        missing_html = "".join(
            f"<li style='margin-bottom: 8px; color: #E2E8F0; font-size: 0.85rem; line-height: 1.45;'>{m}</li>"
            for m in missing_list
        )
        st.markdown(
            f"""
            <div class="huru-card" style="height: 100%; border-left: 3px solid #F59E0B;">
                <div class="huru-section-label" style="color: #FBBF24;">MISSING CONCEPTS</div>
                <div class="huru-card-title" style="font-size: 1.02rem; margin-bottom: 10px;">Concepts Omitted or Incomplete</div>
                <ul style="padding-left: 18px; margin: 0;">{missing_html}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # 3B. Row 2: Specific Improvement Recommendations, Skills Needing Preparation, Suggested Learning Topics
    imp_col, sk_col, top_col = st.columns(3)
    with imp_col:
        improvements_html = "".join(
            f"<li style='margin-bottom: 8px; color: #E2E8F0; font-size: 0.85rem; line-height: 1.45;'>{w}</li>"
            for w in (report.areas_for_improvement or ["Incorporate more quantifiable project metrics."])
        )
        st.markdown(
            f"""
            <div class="huru-card" style="height: 100%; border-left: 3px solid #38BDF8;">
                <div class="huru-section-label" style="color: #38BDF8;">IMPROVEMENT RECOMMENDATIONS</div>
                <div class="huru-card-title" style="font-size: 1.02rem; margin-bottom: 10px;">Specific Actionable Recommendations</div>
                <ul style="padding-left: 18px; margin: 0;">{improvements_html}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with sk_col:
        skills_prep_list = getattr(report, "skills_needing_preparation", None) or [
            f"{report.target_role} Core Architecture & Execution",
            "Structured STAR Problem Articulation",
        ]
        skills_html = "".join(
            f"<li style='margin-bottom: 8px; color: #E2E8F0; font-size: 0.85rem; line-height: 1.45;'>{sk}</li>"
            for sk in skills_prep_list
        )
        st.markdown(
            f"""
            <div class="huru-card" style="height: 100%; border-left: 3px solid #A855F7;">
                <div class="huru-section-label" style="color: #C084FC;">SKILLS NEEDING PREPARATION</div>
                <div class="huru-card-title" style="font-size: 1.02rem; margin-bottom: 10px;">Target Competencies to Strengthen</div>
                <ul style="padding-left: 18px; margin: 0;">{skills_html}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with top_col:
        next_steps_html = "".join(
            f"<li style='margin-bottom: 8px; color: #E2E8F0; font-size: 0.85rem; line-height: 1.45;'>{t}</li>"
            for t in (report.recommended_topics_to_study or ["Practice structured STAR responses with measurable impact."])
        )
        st.markdown(
            f"""
            <div class="huru-card" style="height: 100%; border-left: 3px solid #6366F1;">
                <div class="huru-section-label" style="color: #818CF8;">SUGGESTED LEARNING TOPICS</div>
                <div class="huru-card-title" style="font-size: 1.02rem; margin-bottom: 10px;">Recommended Study Plan</div>
                <ul style="padding-left: 18px; margin: 0;">{next_steps_html}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 4. Downloadable PDF Report Banner
    dl_col1, dl_col2 = st.columns([2.6, 1.4])
    with dl_col1:
        st.markdown(
            """
            <div class="huru-card" style="padding: 16px 22px; display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <div style="font-size: 0.98rem; font-weight: 700; color: #F8FAFC;">Download Complete Interview Evaluation Dossier</div>
                    <div style="font-size: 0.8rem; color: #94A3B8;">Includes full competency scores, question-by-question transcripts, expected concepts, and coaching feedback in PDF format.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with dl_col2:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                tmp_pdf_path = tmp_pdf.name
            export_report_to_pdf(report, tmp_pdf_path)
            with open(tmp_pdf_path, "rb") as f:
                pdf_bytes = f.read()
            try:
                os.remove(tmp_pdf_path)
            except Exception:
                pass
            safe_role = report.target_role.replace(" ", "_").lower()
            st.download_button(
                label="⬇ Download Interview Report (PDF)",
                data=pdf_bytes,
                file_name=f"interview_report_{safe_role}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )
        except Exception:
            pass

    # 5. Question-by-Question Detailed Breakdown (All 8 Required Per-Question Fields)
    st.markdown(
        """
        <div style="margin-top: 10px; margin-bottom: 10px;">
            <div class="huru-section-label">QUESTION-BY-QUESTION EVALUATION</div>
            <div style="font-size: 1.1rem; font-weight: 700; color: #F8FAFC;">Complete Breakdown: Question Asked, Candidate Answer, Expected Concepts, Score &amp; Feedback</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for idx, rec in enumerate(records, start=1):
        ev = rec.evaluation
        q_score = ev.score if ev else 0.0
        ans_status = getattr(ev, "answer_status", "Answered" if q_score > 0 else "Unanswered")
        expected_concepts_str = ", ".join(rec.question.expected_concepts or ["Structured domain explanation", "Practical example", "Measurable outcome"])
        what_was_good = "; ".join(ev.strengths) if (ev and ev.strengths) else ("None — question was not answered." if ans_status == "Unanswered" else "Attempted response.")
        what_was_missing = "; ".join(ev.missing_or_incorrect) if (ev and ev.missing_or_incorrect) else "No major gaps identified."
        how_to_improve = ev.improvement_feedback if ev else "Provide a structured, concept-grounded answer."
        ideal_outline = (ev.suggested_ideal_outline if (ev and ev.suggested_ideal_outline) else rec.question.sample_ideal_answer) or expected_concepts_str

        with st.expander(
            f"Question {idx:02d} [{ans_status}]: {rec.question.question_text}  —  Score: {q_score:.0f}/100",
            expanded=(idx == 1),
        ):
            st.markdown(
                f"""
                <div style="font-size: 0.84rem; color: #94A3B8; margin-bottom: 10px;">
                    <strong>Status:</strong> <span style="color: #F8FAFC; font-weight: 700;">{ans_status}</span> &bull;
                    <strong>Score:</strong> <span style="color: #38BDF8; font-weight: 700;">{q_score:.0f}/100</span> &bull;
                    <strong>Technical:</strong> {ev.technical_or_domain_accuracy if ev else 0:.0f}/100 &bull;
                    <strong>Problem-Solving:</strong> {ev.practical_reasoning_and_scenarios if ev else 0:.0f}/100 &bull;
                    <strong>Communication:</strong> {ev.communication_and_clarity if ev else 0:.0f}/100 &bull;
                    <strong>Relevance:</strong> {ev.completeness_and_relevance if ev else 0:.0f}/100
                </div>
                <div style="background: rgba(30, 41, 59, 0.55); border: 1px solid rgba(99, 102, 241, 0.25); border-radius: 10px; padding: 10px 14px; margin-bottom: 8px;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: #A5B4FC; text-transform: uppercase; margin-bottom: 3px;">1. Question Asked</div>
                    <div style="font-size: 0.88rem; color: #F8FAFC; line-height: 1.45;">{rec.question.question_text}</div>
                </div>
                <div style="background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(148, 163, 184, 0.16); border-radius: 10px; padding: 10px 14px; margin-bottom: 8px;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: #34D399; text-transform: uppercase; margin-bottom: 3px;">2. Candidate's Actual Answer</div>
                    <div style="font-size: 0.88rem; color: #F1F5F9; line-height: 1.5;">{rec.candidate_answer}</div>
                </div>
                <div style="background: rgba(15, 23, 42, 0.75); border: 1px solid rgba(56, 189, 248, 0.22); border-radius: 10px; padding: 10px 14px; margin-bottom: 8px;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: #38BDF8; text-transform: uppercase; margin-bottom: 3px;">3. Expected Answer Concepts</div>
                    <div style="font-size: 0.85rem; color: #E2E8F0; line-height: 1.45;">{expected_concepts_str}</div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 8px;">
                    <div style="background: rgba(16, 185, 129, 0.08); border-left: 3px solid #10B981; border-radius: 8px; padding: 10px 12px;">
                        <div style="font-size: 0.72rem; font-weight: 700; color: #34D399; text-transform: uppercase; margin-bottom: 3px;">4. What Was Good</div>
                        <div style="font-size: 0.83rem; color: #E2E8F0; line-height: 1.45;">{what_was_good}</div>
                    </div>
                    <div style="background: rgba(245, 158, 11, 0.08); border-left: 3px solid #F59E0B; border-radius: 8px; padding: 10px 12px;">
                        <div style="font-size: 0.72rem; font-weight: 700; color: #FBBF24; text-transform: uppercase; margin-bottom: 3px;">5. What Was Missing</div>
                        <div style="font-size: 0.83rem; color: #E2E8F0; line-height: 1.45;">{what_was_missing}</div>
                    </div>
                </div>
                <div style="background: rgba(30, 41, 59, 0.65); border-left: 3px solid #6366F1; border-radius: 8px; padding: 10px 14px;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: #A5B4FC; text-transform: uppercase; margin-bottom: 3px;">6. Evaluation Feedback &amp; How to Improve</div>
                    <div style="font-size: 0.84rem; color: #CBD5E1; line-height: 1.5; margin-bottom: 6px;">{how_to_improve}</div>
                    <div style="font-size: 0.8rem; color: #94A3B8; line-height: 1.45;"><strong>Ideal Answer Outline:</strong> {ideal_outline}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if rec.follow_up_asked and rec.follow_up_answer:
                st.markdown(
                    f"""
                    <div style="margin-top: 10px; background: rgba(15, 23, 42, 0.75); border: 1px solid rgba(99, 102, 241, 0.25); border-radius: 10px; padding: 10px 14px;">
                        <div style="font-size: 0.75rem; font-weight: 700; color: #818CF8;">Follow-Up Question: {rec.follow_up_asked}</div>
                        <div style="font-size: 0.84rem; color: #E2E8F0; margin-top: 4px;"><strong>Your Follow-Up Response:</strong> {rec.follow_up_answer}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
