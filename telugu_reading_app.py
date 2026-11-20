"""
AksharaMitra (అక్షరమిత్ర) – AI-Powered Bilingual Reading Intelligence & Personalized Learning Platform
An Education Technology Innovation by SHR Trinity
Core Streamlit UI Module
"""
import base64
import os
import time
import textwrap
import pandas as pd
import streamlit as st

import telugu_reading_data as data


def get_shr_trinity_logo_b64() -> str:
    """Load the original SHR Trinity logo as a base64 data URI if available."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "TISC_Pitch_Deck_Assets", "shr_trinity_logo.png"),
        os.path.join(base_dir, "shr_trinity_logo.png"),
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                return f"data:image/png;base64,{encoded}"
            except Exception:
                pass
    return ""


def render_html(html_str: str):
    """Render HTML safely ensuring leading indentation does not trigger markdown code blocks."""
    clean = "\n".join(line.strip() for line in html_str.splitlines())
    st.markdown(clean, unsafe_allow_html=True)


# ============================================================================
# 1. CSS & TYPOGRAPHY INJECTION
# ============================================================================
def inject_custom_styles():
    """Inject modern, government-tech styles with Telugu Unicode font support."""
    st.markdown(
        """
        <style>
        /* Google Fonts Import for English & Telugu */
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Noto+Sans+Telugu:wght@400;500;600;700&display=swap');

        /* Root Variables */
        :root {
            --gov-blue: #1e40af;
            --gov-navy: #0f172a;
            --gov-teal: #0d9488;
            --gov-green: #10b981;
            --gov-bg: #f8fafc;
            --gov-card-border: #e2e8f0;
            --text-dark: #0f172a;
            --text-muted: #64748b;
        }

        /* Global Typography */
        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', 'Noto Sans Telugu', -apple-system, BlinkMacSystemFont, sans-serif;
            color: #0f172a;
        }

        /* Telugu Unicode text class */
        .telugu-text {
            font-family: 'Noto Sans Telugu', 'Plus Jakarta Sans', sans-serif !important;
            letter-spacing: 0.3px;
            line-height: 1.8;
        }

        /* Top Government Banner */
        .gov-top-bar {
            background: linear-gradient(90deg, #1e3a8a 0%, #1e40af 50%, #0d9488 100%);
            color: #ffffff;
            padding: 12px 24px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
            box-shadow: 0 4px 14px rgba(30, 58, 138, 0.12);
        }
        .gov-top-bar h1 {
            font-size: 1.35rem;
            font-weight: 700;
            margin: 0;
            color: #ffffff !important;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .gov-top-bar p {
            font-size: 0.85rem;
            margin: 2px 0 0 0;
            color: #e0e7ff;
            opacity: 0.95;
        }
        .gov-badge {
            background: rgba(255, 255, 255, 0.18);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 20px;
            padding: 5px 14px;
            font-size: 0.78rem;
            font-weight: 600;
            color: #ffffff;
            letter-spacing: 0.5px;
        }

        /* Unified Card Styles */
        .ecr-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 20px 24px;
            margin-bottom: 18px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
            transition: all 0.2s ease-in-out;
        }
        .ecr-card:hover {
            border-color: #cbd5e1;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
        }

        .ecr-card-header {
            font-size: 1.1rem;
            font-weight: 700;
            color: #1e3a8a;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Student Profile Card */
        .student-profile-badge {
            display: flex;
            align-items: center;
            gap: 16px;
            background: linear-gradient(135deg, #f0fdf4 0%, #e0f2fe 100%);
            border: 1px solid #bae6fd;
            border-radius: 14px;
            padding: 16px 20px;
            margin-bottom: 20px;
        }
        .student-avatar {
            font-size: 2.8rem;
            background: #ffffff;
            border-radius: 50%;
            width: 64px;
            height: 64px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
        }

        /* Large Child-Friendly Reading Text Box */
        .reading-box-telugu {
            font-family: 'Noto Sans Telugu', sans-serif !important;
            font-size: 1.55rem;
            line-height: 2.1;
            color: #1e293b;
            background: #ffffff;
            border: 2px solid #93c5fd;
            border-radius: 16px;
            padding: 28px 32px;
            letter-spacing: 0.5px;
            box-shadow: 0 6px 18px rgba(30, 64, 175, 0.06);
        }

        .reading-box-english {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-size: 1.45rem;
            line-height: 2.0;
            color: #1e293b;
            background: #ffffff;
            border: 2px solid #93c5fd;
            border-radius: 16px;
            padding: 28px 32px;
            letter-spacing: 0.3px;
            box-shadow: 0 6px 18px rgba(30, 64, 175, 0.06);
        }

        /* Microphone Recording Pulse Animation */
        .mic-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 24px;
            background: #f8fafc;
            border: 2px dashed #cbd5e1;
            border-radius: 16px;
            margin: 16px 0;
            text-align: center;
        }
        .mic-active {
            border-color: #ef4444;
            background: #fef2f2;
        }
        .pulse-circle {
            width: 72px;
            height: 72px;
            background: #ef4444;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            font-size: 2rem;
            box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
            animation: pulse-red 1.5s infinite;
        }
        @keyframes pulse-red {
            0% {
                transform: scale(0.95);
                box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
            }
            70% {
                transform: scale(1.05);
                box-shadow: 0 0 0 16px rgba(239, 68, 68, 0);
            }
            100% {
                transform: scale(0.95);
                box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);
            }
        }

        /* Soundwave animation bars */
        .wave-box {
            display: flex;
            align-items: center;
            gap: 4px;
            height: 36px;
            margin: 12px 0;
        }
        .wave-bar {
            width: 5px;
            height: 100%;
            background: #ef4444;
            border-radius: 4px;
            animation: wave 1s ease-in-out infinite alternate;
        }
        .wave-bar:nth-child(1) { animation-delay: 0.1s; height: 35%; }
        .wave-bar:nth-child(2) { animation-delay: 0.3s; height: 75%; }
        .wave-bar:nth-child(3) { animation-delay: 0.2s; height: 95%; }
        .wave-bar:nth-child(4) { animation-delay: 0.4s; height: 60%; }
        .wave-bar:nth-child(5) { animation-delay: 0.15s; height: 80%; }
        .wave-bar:nth-child(6) { animation-delay: 0.35s; height: 45%; }
        .wave-bar:nth-child(7) { animation-delay: 0.25s; height: 90%; }
        .wave-bar:nth-child(8) { animation-delay: 0.45s; height: 50%; }

        @keyframes wave {
            0% { transform: scaleY(0.3); }
            100% { transform: scaleY(1.0); }
        }

        /* Color-Coded Word Token Badges for Screen 3 */
        .word-token {
            display: inline-block;
            margin: 4px 5px;
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 1.28rem;
            font-weight: 500;
            line-height: 1.8;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .word-token:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
        }
        .word-correct {
            background-color: #dcfce7;
            color: #15803d;
            border: 1.5px solid #86efac;
        }
        .word-mispronounced {
            background-color: #fee2e2;
            color: #b91c1c;
            border: 1.5px solid #fca5a5;
            text-decoration: underline wavy #ef4444;
        }
        .word-skipped {
            background-color: #ffedd5;
            color: #c2410c;
            border: 1.5px dashed #fdba74;
            opacity: 0.85;
        }
        .word-repeated {
            background-color: #dbeafe;
            color: #1d4ed8;
            border: 1.5px solid #93c5fd;
        }

        /* Legend Pills */
        .legend-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-right: 8px;
            margin-bottom: 8px;
        }

        /* Metric Score Cards for Screen 4 & 5 */
        .metric-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 18px 20px;
            text-align: center;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
            border-top: 4px solid #3b82f6;
        }
        .metric-card.green-top { border-top-color: #10b981; }
        .metric-card.red-top { border-top-color: #ef4444; }
        .metric-card.amber-top { border-top-color: #f59e0b; }
        .metric-card.purple-top { border-top-color: #8b5cf6; }

        .metric-val {
            font-size: 2.1rem;
            font-weight: 800;
            color: #0f172a;
            line-height: 1.1;
            margin: 6px 0;
        }
        .metric-lbl {
            font-size: 0.82rem;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.6px;
        }
        .metric-sub {
            font-size: 0.78rem;
            color: #10b981;
            font-weight: 600;
        }

        /* Status Pills */
        .status-pill {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.78rem;
            font-weight: 700;
        }
        .status-advanced { background: #dcfce7; color: #15803d; }
        .status-proficient { background: #dbeafe; color: #1e40af; }
        .status-needs-support { background: #fee2e2; color: #b91c1c; }

        /* Hide unwanted default margins */
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 3rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================================
# 2. SESSION STATE MANAGEMENT
# ============================================================================
def init_session_state():
    """Initialize state variables with default prototype selections."""
    defaults = {
        "active_screen": "student_dashboard",
        "selected_student_id": "AP-EDU-2026-0412",  # Ananya Reddy
        "selected_grade": "Class 4",
        "selected_language": "Telugu",
        "selected_difficulty": "Intermediate",
        "is_recording": False,
        "recording_elapsed": 42,
        "assessment_submitted": False,
        "active_word_detail": None,
        "teacher_filter_grade": "All",
        "teacher_filter_lang": "All",
        "teacher_filter_status": "All",
        "selected_teacher_student_id": "AP-EDU-2026-0412",
        "reading_font_size": "Large (పిల్లలకు అనుకూలం)",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Check query params for deep-linking, direct navigation, or automated preview
    try:
        requested_screen = st.query_params.get("screen")
        if requested_screen and requested_screen in [
            "student_dashboard",
            "reading_assessment",
            "reading_analysis",
            "assessment_results",
            "teacher_dashboard",
        ]:
            st.session_state["active_screen"] = requested_screen
    except Exception:
        pass


# ============================================================================
# 3. GLOBAL HEADER, SIDEBAR NAVIGATION & FOOTER
# ============================================================================
def render_header():
    """Render the official SHR Trinity — AksharaMitra header."""
    logo_uri = get_shr_trinity_logo_b64()
    logo_html = (
        f'<img src="{logo_uri}" alt="SHR Trinity" style="width: 54px; height: 54px; border-radius: 12px; object-fit: contain; background: #ffffff; padding: 3px; box-shadow: 0 3px 10px rgba(0,0,0,0.22); flex-shrink: 0;" />'
        if logo_uri
        else '<span style="font-size: 2rem;">📖</span>'
    )
    st.markdown(
        f"""
        <div class="gov-top-bar" style="border-bottom: 3px solid #f59e0b;">
            <div style="display: flex; align-items: center; gap: 14px;">
                {logo_html}
                <div>
                    <h1>
                        <span>📖 AksharaMitra (అక్షరమిత్ర)</span>
                        <span style="font-size: 0.95rem; font-weight: 500; opacity: 0.92; color: #fde68a;">| Every Child Heard. Every Reader Empowered.</span>
                    </h1>
                    <p>AI-Powered Bilingual Reading Intelligence &amp; Personalized Learning Platform • An Education Technology Innovation by <b>SHR Trinity</b></p>
                </div>
            </div>
            <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                <span class="gov-badge" style="background: rgba(229, 25, 35, 0.35); border-color: rgba(252, 165, 165, 0.5);">🏢 SHR TRINITY</span>
                <span class="gov-badge" style="background: rgba(16, 185, 129, 0.35);">🟢 AKSHARAMITRA LIVE</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    """Render professional navigation sidebar with AksharaMitra branding, student switch, and quick links."""
    logo_uri = get_shr_trinity_logo_b64()
    sidebar_logo_html = (
        f'<img src="{logo_uri}" alt="SHR Trinity" style="width: 58px; height: 58px; border-radius: 50%; object-fit: contain; background: #ffffff; padding: 3px; border: 2px solid #1e40af; margin-bottom: 6px; box-shadow: 0 3px 8px rgba(0,0,0,0.12);" />'
        if logo_uri
        else '<div style="font-size: 2.2rem; margin-bottom: 4px;">📖</div>'
    )
    with st.sidebar:
        st.markdown(
            f"""
            <div style="text-align: center; padding: 10px 0 16px 0; border-bottom: 1px solid #e2e8f0;">
                {sidebar_logo_html}
                <div style="font-weight: 800; font-size: 1.08rem; color: #1e3a8a;">AksharaMitra (అక్షరమిత్ర)</div>
                <div style="font-size: 0.78rem; font-weight: 600; color: #0d9488; margin-top: 2px;">Every Child Heard. Every Reader Empowered.</div>
                <div style="font-size: 0.74rem; color: #64748b; margin-top: 2px;">An Innovation by <b>SHR Trinity</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### 📌 Navigation Flow")

        nav_options = [
            ("student_dashboard", "1. Student Dashboard", "🏠"),
            ("reading_assessment", "2. Reading Assessment", "🎙️"),
            ("reading_analysis", "3. AI Reading Analysis", "🔍"),
            ("assessment_results", "4. Assessment Results", "📊"),
            ("teacher_dashboard", "5. Teacher Dashboard", "👩‍🏫"),
        ]

        for screen_key, label, icon in nav_options:
            is_active = st.session_state["active_screen"] == screen_key
            button_label = f"{icon} {label}" if not is_active else f"👉 {label}"
            btn_type = "primary" if is_active else "secondary"
            if st.button(button_label, key=f"nav_{screen_key}", use_container_width=True, type=btn_type):
                st.session_state["active_screen"] = screen_key
                st.rerun()

        st.markdown("---")

        # Active Student Selector
        st.markdown("#### 👤 Student Profile Switch")
        student_names = {s["student_id"]: f"{s['avatar']} {s['name']} ({s['grade']})" for s in data.STUDENT_PROFILES}
        current_id = st.session_state["selected_student_id"]
        selected_id = st.selectbox(
            "Select Student Profile:",
            options=list(student_names.keys()),
            format_func=lambda x: student_names[x],
            index=list(student_names.keys()).index(current_id) if current_id in student_names else 0,
            key="student_selector_widget",
        )
        if selected_id != st.session_state["selected_student_id"]:
            st.session_state["selected_student_id"] = selected_id
            curr_student = data.get_student_by_id(selected_id)
            st.session_state["selected_grade"] = curr_student["grade"]
            st.session_state["selected_language"] = curr_student["preferred_lang"]
            st.rerun()

        active_student = data.get_student_by_id(st.session_state["selected_student_id"])
        st.info(
            f"**School:** {active_student['school']}\n\n"
            f"**District:** {active_student['district']}\n\n"
            f"**Reading Level:** {active_student['reading_level']}\n\n"
            f"**Streak:** {active_student['streak_days']} days 🔥"
        )

        st.markdown("---")
        st.markdown("#### ℹ️ About AksharaMitra")
        st.caption(
            "**AksharaMitra (అక్షరమిత్ర)** is a student-focused bilingual reading and learning companion by **SHR Trinity**, "
            "designed to help students in Classes 1–10 improve their Telugu and English reading skills.\n\n"
            "*ప్రతి చిన్నారి స్వరం వినిపించాలి • ప్రతి చదువు మెరుగుపడాలి*"
        )


# ============================================================================
# 4. SCREEN 1: STUDENT DASHBOARD
# ============================================================================
def render_student_dashboard():
    """Render Student Dashboard: Welcome, Profile, Grade, Language, Difficulty selection."""
    student = data.get_student_by_id(st.session_state["selected_student_id"])

    # Welcome Banner
    st.markdown(
        f"""
        <div class="student-profile-badge">
            <div class="student-avatar">{student['avatar']}</div>
            <div style="flex: 1;">
                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                    <h2 style="margin: 0; color: #1e3a8a; font-size: 1.45rem;">
                        స్వాగతం, {student['name_te']}! ({student['name']})
                    </h2>
                    <span class="status-pill status-proficient">{student['reading_level']}</span>
                </div>
                <div style="font-size: 0.88rem; color: #475569; margin-top: 4px;">
                    🏫 <b>{student['school']}</b> • {student['district']} District | <b>Roll No:</b> {student['roll_no']} | <b>ID:</b> {student['student_id']}
                </div>
            </div>
            <div style="text-align: right; border-left: 2px dashed #93c5fd; padding-left: 18px;">
                <div style="font-size: 1.4rem; font-weight: 800; color: #ea580c;">🔥 {student['streak_days']} Days</div>
                <div style="font-size: 0.78rem; color: #64748b; font-weight: 600;">ACTIVE READING STREAK</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3-Column Highlights
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""
            <div class="metric-card green-top">
                <div class="metric-lbl">Assessments Completed</div>
                <div class="metric-val">{student['completed_assessments']}</div>
                <div class="metric-sub">⭐ 100% on schedule</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-lbl">Avg Reading Accuracy</div>
                <div class="metric-val">{student['avg_accuracy']}%</div>
                <div class="metric-sub">📈 +4.2% this term</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="metric-card purple-top">
                <div class="metric-lbl">Reading Speed</div>
                <div class="metric-val">{student['avg_wpm']} <span style="font-size: 1rem;">WPM</span></div>
                <div class="metric-sub">🎯 Target: 75 WPM</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
            <div class="metric-card amber-top">
                <div class="metric-lbl">Badges Earned</div>
                <div class="metric-val">6 🏅</div>
                <div class="metric-sub">Next: Fluent Orator</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Assessment Setup Section
    st.markdown(
        """
        <div class="ecr-card-header">
            <span>🎯 Setup Today's Reading Assessment (నేటి పఠన పరీక్షను ఎంచుకోండి)</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_setup1, col_setup2 = st.columns([1, 1], gap="large")

    with col_setup1:
        st.markdown("#### 1️⃣ Select Grade (తరగతి)")
        grades = [f"Class {i}" for i in range(1, 11)]
        selected_grade = st.select_slider(
            "Grade Selection (Classes 1 to 10):",
            options=grades,
            value=st.session_state["selected_grade"],
            help="Choose the student's current grade band to personalize vocabulary and passage length.",
        )
        st.session_state["selected_grade"] = selected_grade

        st.markdown("#### 2️⃣ Select Language (భాష)")
        lang_cols = st.columns(2)
        with lang_cols[0]:
            is_telugu = st.session_state["selected_language"] == "Telugu"
            if st.button(
                "🇮🇳 తెలుగు (Telugu)\n\nమాతృభాష పఠనం",
                key="btn_lang_te",
                type="primary" if is_telugu else "secondary",
                use_container_width=True,
            ):
                st.session_state["selected_language"] = "Telugu"
                st.rerun()
        with lang_cols[1]:
            is_eng = st.session_state["selected_language"] == "English"
            if st.button(
                "🇬🇧 English\n\nSecond Language Fluency",
                key="btn_lang_en",
                type="primary" if is_eng else "secondary",
                use_container_width=True,
            ):
                st.session_state["selected_language"] = "English"
                st.rerun()

        st.markdown("#### 3️⃣ Select Difficulty Level (స్థాయి)")
        diff_options = ["Beginner", "Intermediate", "Advanced"]
        diff_labels = {
            "Beginner": "🌱 Beginner (ప్రారంభ స్థాయి - Classes 1–3)",
            "Intermediate": "🌿 Intermediate (మధ్యస్థ స్థాయి - Classes 4–7)",
            "Advanced": "🌳 Advanced (ఉన్నత స్థాయి - Classes 8–10)",
        }
        selected_diff = st.radio(
            "Reading Tier:",
            options=diff_options,
            format_func=lambda x: diff_labels[x],
            index=diff_options.index(st.session_state["selected_difficulty"]),
            horizontal=False,
        )
        st.session_state["selected_difficulty"] = selected_diff

    with col_setup2:
        # Passage Preview Card
        curr_passage = data.get_passage(st.session_state["selected_language"], st.session_state["selected_difficulty"])

        st.markdown("#### 📄 Selected Passage Preview")
        st.markdown(
            f"""
            <div class="ecr-card" style="background: #f8fafc; border: 1.5px solid #bfdbfe;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <span class="status-pill status-advanced" style="margin-bottom: 8px;">{curr_passage['grade_band']}</span>
                        <h3 style="margin: 6px 0 2px 0; color: #1e3a8a; font-size: 1.25rem;">{curr_passage['title']}</h3>
                        <p style="color: #64748b; font-size: 0.88rem; margin: 0 0 12px 0;">{curr_passage['subtitle']}</p>
                    </div>
                </div>
                <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px 18px; margin-bottom: 14px; max-height: 140px; overflow-y: auto;">
                    <p style="font-size: 1.05rem; line-height: 1.8; color: #334155; margin: 0;">
                        {curr_passage['reference_text'][:180]}...
                    </p>
                </div>
                <div style="display: flex; gap: 20px; font-size: 0.84rem; color: #475569; margin-bottom: 16px;">
                    <div>⏱️ <b>Expected Time:</b> ~{curr_passage['expected_duration_sec']} sec</div>
                    <div>🎯 <b>Benchmark Speed:</b> {curr_passage['target_wpm']} WPM</div>
                    <div>📝 <b>Word Count:</b> {curr_passage['metrics']['total_words']} words</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(
            "🚀 Start Reading Assessment (పఠన పరీక్ష ప్రారంభించండి) ➔",
            key="btn_start_assessment",
            type="primary",
            use_container_width=True,
        ):
            st.session_state["active_screen"] = "reading_assessment"
            st.session_state["is_recording"] = False
            st.session_state["assessment_submitted"] = False
            st.rerun()

    # Recent assessments history table
    st.markdown("---")
    st.markdown("#### 📜 Recent Assessment History for this Student")
    recent_history = [
        {"Date": "17 Nov 2026", "Language": "Telugu", "Passage": "గోదావరి నది ప్రవాహం", "Grade": "Class 4", "Score": "89/100", "WPM": 76, "Accuracy": "90.9%", "Status": "Proficient"},
        {"Date": "10 Nov 2026", "Language": "Telugu", "Passage": "మన తోటలోని పూలు", "Grade": "Class 4", "Score": "92/100", "WPM": 72, "Accuracy": "94.0%", "Status": "Advanced"},
        {"Date": "03 Nov 2026", "Language": "English", "Passage": "A Sunny Morning", "Grade": "Class 4", "Score": "85/100", "WPM": 68, "Accuracy": "88.2%", "Status": "Proficient"},
    ]
    st.dataframe(pd.DataFrame(recent_history), use_container_width=True, hide_index=True)


# ============================================================================
# 5. SCREEN 2: READING ASSESSMENT SCREEN
# ============================================================================
def render_reading_assessment():
    """Render Reading Assessment: Passage display, Mic recording button, Timer, Progress indicator, Submit."""
    student = data.get_student_by_id(st.session_state["selected_student_id"])
    lang = st.session_state["selected_language"]
    diff = st.session_state["selected_difficulty"]
    passage = data.get_passage(lang, diff)

    # Top Context bar
    col_nav, col_info = st.columns([1, 3])
    with col_nav:
        if st.button("← Back to Dashboard", key="btn_back_to_dash"):
            st.session_state["active_screen"] = "student_dashboard"
            st.rerun()
    with col_info:
        st.markdown(
            f"""
            <div style="text-align: right; font-size: 0.9rem; color: #475569;">
                <b>Student:</b> {student['name']} ({student['grade']}) | <b>Language:</b> {lang} | <b>Tier:</b> {diff}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Header Card for Passage
    st.markdown(
        f"""
        <div style="background: linear-gradient(90deg, #eff6ff 0%, #f0fdf4 100%); border: 1px solid #bfdbfe; border-radius: 14px; padding: 16px 22px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <span class="status-pill status-proficient">{passage['grade_band']}</span>
                    <h2 style="margin: 6px 0 2px 0; color: #1e3a8a; font-size: 1.45rem;">{passage['title']}</h2>
                    <p style="margin: 0; color: #64748b; font-size: 0.92rem;">{passage['subtitle']}</p>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 0.85rem; color: #64748b;">Target Benchmark Pace</div>
                    <div style="font-size: 1.35rem; font-weight: 800; color: #0d9488;">{passage['target_wpm']} Words/Min</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Passage Text Box with Large Child-Friendly Font
    box_class = "reading-box-telugu" if lang == "Telugu" else "reading-box-english"
    st.markdown(
        f"""
        <div class="{box_class}">
            {passage['reference_text']}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption("💡 Student Instruction: Click the microphone below, read the passage clearly aloud at your natural pace, and press 'Submit Reading' when finished.")

    # Recording Console
    st.markdown("<br>", unsafe_allow_html=True)

    col_mic, col_controls = st.columns([1, 1], gap="large")

    with col_mic:
        is_rec = st.session_state["is_recording"]

        if is_rec:
            st.markdown(
                """
                <div class="mic-container mic-active">
                    <div class="pulse-circle">🎙️</div>
                    <div class="wave-box">
                        <div class="wave-bar"></div><div class="wave-bar"></div>
                        <div class="wave-bar"></div><div class="wave-bar"></div>
                        <div class="wave-bar"></div><div class="wave-bar"></div>
                        <div class="wave-bar"></div><div class="wave-bar"></div>
                    </div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #b91c1c; margin-top: 6px;">
                        ● RECORDING LIVE IN PROGRESS...
                    </div>
                    <div style="font-size: 0.88rem; color: #7f1d1d;">Speaking audio is being captured by AI audio buffer</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("⏹ Stop Recording (రికార్డింగ్ ఆపు)", key="btn_stop_rec", type="secondary", use_container_width=True):
                st.session_state["is_recording"] = False
                st.session_state["recording_elapsed"] = 42
                st.rerun()
        else:
            st.markdown(
                """
                <div class="mic-container">
                    <div style="width: 72px; height: 72px; background: #2563eb; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 2rem; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);">
                        🎙️
                    </div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #1e3a8a; margin-top: 10px;">
                        Microphone Ready (మైక్రోఫోన్ సిద్ధంగా ఉంది)
                    </div>
                    <div style="font-size: 0.88rem; color: #64748b;">Click below to begin reading assessment</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("🎤 Start Recording (రికార్డింగ్ ప్రారంభించండి)", key="btn_start_rec", type="primary", use_container_width=True):
                st.session_state["is_recording"] = True
                st.rerun()

    with col_controls:
        st.markdown("#### ⏱️ Reading Progress & Controls")

        # Timer & Recording Status
        timer_display = "00:42" if not st.session_state["is_recording"] else "00:35 (Recording...)"
        st.markdown(
            f"""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px 20px; margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 0.85rem; font-weight: 600; color: #64748b;">TIMER & DURATION</span>
                    <span style="font-size: 1.25rem; font-weight: 800; color: #1e3a8a;">{timer_display} / 01:00 min</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 0.85rem; font-weight: 600; color: #64748b;">RECORDING STATUS</span>
                    <span class="status-pill status-advanced">{'🔴 Active Capture' if is_rec else '✅ Voice Sample Ready'}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Reading progress indicator
        st.markdown("**Passage Progress Tracker:**")
        st.progress(0.91)
        st.caption("38 of 44 words read • 91% passage complete")

        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔄 Restart (మళ్లీ ప్రారంభించు)", key="btn_reset_recording", use_container_width=True):
                st.session_state["is_recording"] = False
                st.session_state["recording_elapsed"] = 0
                st.rerun()
        with col_btn2:
            if st.button("🔊 Play Demo Audio", key="btn_sample_audio", use_container_width=True):
                st.info("Demonstrating model audio playback for classroom pronunciation benchmark.")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(
            "✅ Submit Reading for AI Assessment (సమర్పించండి) ➔",
            key="btn_submit_reading",
            type="primary",
            use_container_width=True,
        ):
            st.session_state["is_recording"] = False
            st.session_state["assessment_submitted"] = True
            st.session_state["active_screen"] = "reading_analysis"
            st.rerun()


# ============================================================================
# 6. SCREEN 3: READING ANALYSIS SCREEN
# ============================================================================
def render_reading_analysis():
    """Render Reading Analysis: Color-coded word highlights, Reference vs Student speech comparison, Observations."""
    student = data.get_student_by_id(st.session_state["selected_student_id"])
    lang = st.session_state["selected_language"]
    diff = st.session_state["selected_difficulty"]
    passage = data.get_passage(lang, diff)
    metrics = passage["metrics"]

    # Top Context bar
    col_nav, col_jump = st.columns([1, 1])
    with col_nav:
        if st.button("← Back to Assessment", key="btn_back_to_assess"):
            st.session_state["active_screen"] = "reading_assessment"
            st.rerun()
    with col_jump:
        if st.button("📊 View Full Scorecard & Report ➔", key="btn_goto_results", type="primary"):
            st.session_state["active_screen"] = "assessment_results"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Title Banner
    st.markdown(
        f"""
        <div style="background: linear-gradient(90deg, #1e3a8a 0%, #0d9488 100%); color: white; padding: 18px 24px; border-radius: 14px; margin-bottom: 22px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <h2 style="margin: 0; font-size: 1.4rem; color: #ffffff;">🔍 AI Reading Analysis (కృత్రిమ మేధ స్వర విశ్లేషణ)</h2>
                    <p style="margin: 4px 0 0 0; color: #e0f2fe; font-size: 0.9rem;">
                        Student: <b>{student['name']}</b> ({student['name_te']}) • Passage: <b>{passage['title']}</b>
                    </p>
                </div>
                <div style="text-align: right;">
                    <span class="gov-badge" style="background: rgba(255, 255, 255, 0.25); font-size: 0.95rem;">
                        Accuracy: {metrics['accuracy_pct']}% • Speed: {metrics['wpm']} WPM
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Legend Card
    st.markdown(
        """
        <div class="ecr-card" style="padding: 14px 20px; background: #ffffff;">
            <div style="font-size: 0.88rem; font-weight: 700; color: #475569; margin-bottom: 8px;">
                COLOR-CODED READING LEGEND (పదాల విశ్లేషణ రంగుల సూచిక):
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                <span class="legend-pill" style="background: #dcfce7; color: #15803d; border: 1px solid #86efac;">
                    🟢 Correctly Read (సరిగ్గా చదివినవి)
                </span>
                <span class="legend-pill" style="background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5;">
                    🔴 Mispronounced (ఉచ్చారణ లోపం)
                </span>
                <span class="legend-pill" style="background: #ffedd5; color: #c2410c; border: 1px dashed #fdba74;">
                    🟠 Skipped (వదిలివేసినవి)
                </span>
                <span class="legend-pill" style="background: #dbeafe; color: #1d4ed8; border: 1px solid #93c5fd;">
                    🔵 Repeated (పునరావృతం)
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Word-by-Word Annotated Reading Viewer
    st.markdown("#### 📑 Word-by-Word Annotated Speech Evaluation")

    word_badges_html = []
    for token in passage["word_tokens"]:
        status = token["status"]
        word = token["word"]
        spoken = token.get("spoken", word)
        note = token.get("note", "")

        css_class = f"word-token word-{status}"
        title_attr = f"{status.capitalize()}: '{word}'"
        if note:
            title_attr += f" ({note})"

        badge_html = f'<span class="{css_class}" title="{title_attr}">{word}</span>'
        word_badges_html.append(badge_html)

    passage_html = " ".join(word_badges_html)

    st.markdown(
        f"""
        <div class="ecr-card" style="background: #ffffff; border: 2px solid #bae6fd; padding: 24px 28px; line-height: 2.3;">
            <div class="telugu-text" style="font-size: 1.35rem;">
                {passage_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Detailed Error Token Inspection Cards
    st.markdown("##### 🔎 Identified Phonetic & Fluency Deviations (లోపాల విశ్లేషణ)")
    deviations = [t for t in passage["word_tokens"] if t["status"] != "correct"]
    if deviations:
        dev_cols = st.columns(len(deviations))
        for idx, dev in enumerate(deviations):
            with dev_cols[idx]:
                status_color = {
                    "mispronounced": "#fee2e2",
                    "skipped": "#ffedd5",
                    "repeated": "#dbeafe",
                }.get(dev["status"], "#f1f5f9")
                border_color = {
                    "mispronounced": "#fca5a5",
                    "skipped": "#fdba74",
                    "repeated": "#93c5fd",
                }.get(dev["status"], "#cbd5e1")
                text_color = {
                    "mispronounced": "#b91c1c",
                    "skipped": "#c2410c",
                    "repeated": "#1d4ed8",
                }.get(dev["status"], "#334155")

                st.markdown(
                    f"""
                    <div style="background: {status_color}; border: 1.5px solid {border_color}; border-radius: 12px; padding: 12px 14px; min-height: 125px;">
                        <span class="status-pill" style="background: white; color: {text_color}; font-size: 0.72rem;">
                            {dev['status'].upper()}
                        </span>
                        <div style="font-size: 1.15rem; font-weight: 700; color: #0f172a; margin: 6px 0 2px 0;">
                            {dev['word']}
                        </div>
                        <div style="font-size: 0.82rem; color: #475569;">
                            <b>Spoken:</b> <span style="color: {text_color};">{dev.get('spoken', '(omitted)')}</span>
                        </div>
                        <div style="font-size: 0.76rem; color: #64748b; margin-top: 4px;">
                            {dev.get('note', '')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("<br>", unsafe_allow_html=True)

    # Side-by-Side: Reference Text vs Student-Recognized Text
    st.markdown("#### ⚖️ Reference Text vs. Student-Recognized Text")
    col_ref, col_rec = st.columns(2, gap="medium")

    with col_ref:
        st.markdown(
            f"""
            <div class="ecr-card" style="border-left: 4px solid #10b981; height: 100%;">
                <div style="display: flex; align-items: center; gap: 8px; font-weight: 700; color: #15803d; margin-bottom: 8px;">
                    <span>📖 Reference Passage (ఆదర్శ పాఠం)</span>
                </div>
                <div class="telugu-text" style="font-size: 1.12rem; line-height: 1.9; color: #1e293b; background: #f8fafc; padding: 14px 18px; border-radius: 8px;">
                    {passage['reference_text']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_rec:
        st.markdown(
            f"""
            <div class="ecr-card" style="border-left: 4px solid #3b82f6; height: 100%;">
                <div style="display: flex; align-items: center; gap: 8px; font-weight: 700; color: #1d4ed8; margin-bottom: 8px;">
                    <span>🎙️ Recognized Speech Output (విద్యార్థి పలికిన తీరు)</span>
                </div>
                <div class="telugu-text" style="font-size: 1.12rem; line-height: 1.9; color: #1e293b; background: #f8fafc; padding: 14px 18px; border-radius: 8px;">
                    {passage['student_recognized_text']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Observations Panel
    st.markdown("#### 🧠 AI Pronunciation & Fluency Diagnostic Observations")
    obs_cols = st.columns(2)
    with obs_cols[0]:
        st.markdown(
            """
            <div class="ecr-card">
                <div class="ecr-card-header">🎯 Phonological & Akshara Insights</div>
            """,
            unsafe_allow_html=True,
        )
        for obs in passage["observations"]:
            st.markdown(f"- {obs}")
        st.markdown("</div>", unsafe_allow_html=True)

    with obs_cols[1]:
        st.markdown(
            """
            <div class="ecr-card">
                <div class="ecr-card-header">💡 Targeted Teaching Recommendations</div>
            """,
            unsafe_allow_html=True,
        )
        for rec in passage["recommendations"]:
            st.markdown(f"- {rec}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📊 View Complete Assessment Results & Scorecard ➔", key="btn_next_results", type="primary", use_container_width=True):
        st.session_state["active_screen"] = "assessment_results"
        st.rerun()


# ============================================================================
# 7. SCREEN 4: ASSESSMENT RESULTS SCREEN
# ============================================================================
def render_assessment_results():
    """Render Assessment Results: Overall score, Core metrics, Word breakdown, Benchmarks, Recommendations."""
    student = data.get_student_by_id(st.session_state["selected_student_id"])
    lang = st.session_state["selected_language"]
    diff = st.session_state["selected_difficulty"]
    passage = data.get_passage(lang, diff)
    metrics = passage["metrics"]

    # Navigation buttons
    col_nav1, col_nav2 = st.columns([1, 1])
    with col_nav1:
        if st.button("← Back to Word Analysis", key="btn_back_to_analysis"):
            st.session_state["active_screen"] = "reading_analysis"
            st.rerun()
    with col_nav2:
        if st.button("👩‍🏫 Open Teacher Dashboard ➔", key="btn_goto_teacher", type="primary"):
            st.session_state["active_screen"] = "teacher_dashboard"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Hero Assessment Certificate Header
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 60%, #047857 100%); color: white; border-radius: 16px; padding: 26px 32px; box-shadow: 0 8px 24px rgba(30, 58, 138, 0.15); margin-bottom: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 2.2rem;">🏅</span>
                        <div>
                            <span class="gov-badge" style="background: rgba(255, 255, 255, 0.2);">AKSHARAMITRA EVALUATION REPORT</span>
                            <h1 style="margin: 4px 0 0 0; font-size: 1.8rem; color: #ffffff;">{student['name']} ({student['name_te']})</h1>
                        </div>
                    </div>
                    <p style="margin: 8px 0 0 0; color: #e0e7ff; font-size: 0.92rem;">
                        <b>{student['school']}</b> • Grade: <b>{student['grade']}</b> | Roll No: <b>{student['roll_no']}</b> | Date: <b>17 Nov 2026</b>
                    </p>
                </div>
                <div style="text-align: center; background: rgba(255, 255, 255, 0.15); border: 1.5px solid rgba(255, 255, 255, 0.35); border-radius: 16px; padding: 14px 28px;">
                    <div style="font-size: 0.82rem; font-weight: 700; letter-spacing: 0.8px; color: #e0f2fe;">OVERALL PROFICIENCY</div>
                    <div style="font-size: 3.2rem; font-weight: 800; line-height: 1.0; margin: 4px 0; color: #ffffff;">{metrics['overall_score']}</div>
                    <div style="font-size: 0.82rem; color: #bbf7d0; font-weight: 700;">LEVEL 3: PROFICIENT READER</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 4 Core Diagnostic Cards
    st.markdown("### 📊 Diagnostic Reading Metrics")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f"""
            <div class="metric-card green-top">
                <div class="metric-lbl">Reading Accuracy</div>
                <div class="metric-val">{metrics['accuracy_pct']}%</div>
                <div class="metric-sub">Class Benchmark: 85%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-lbl">Pronunciation Score</div>
                <div class="metric-val">{metrics['pronunciation_score']}<span style="font-size: 1.1rem; color: #64748b;">/100</span></div>
                <div class="metric-sub">Phoneme Match: High</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="metric-card purple-top">
                <div class="metric-lbl">Fluency Score</div>
                <div class="metric-val">{metrics['fluency_score']}<span style="font-size: 1.1rem; color: #64748b;">/100</span></div>
                <div class="metric-sub">Expression & Cadence</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
            <div class="metric-card amber-top">
                <div class="metric-lbl">Reading Speed (WPM)</div>
                <div class="metric-val">{metrics['wpm']}</div>
                <div class="metric-sub">Target: {passage['target_wpm']} WPM</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Word Breakdown Statistics & Benchmark Charts
    col_breakdown, col_chart = st.columns([1, 1], gap="large")

    with col_breakdown:
        st.markdown("#### 📑 Word-Level Performance Breakdown")
        total = metrics["total_words"]
        cor = metrics["correct_words"]
        mis = metrics["mispronounced_words"]
        skp = metrics["skipped_words"]
        rep = metrics["repeated_words"]

        render_html(
            f"""
            <div class="ecr-card">
                <div style="margin-bottom: 14px;">
                    <div style="display: flex; justify-content: space-between; font-weight: 600; font-size: 0.9rem;">
                        <span style="color: #15803d;">🟢 Correctly Read Words</span>
                        <span><b>{cor}</b> / {total} ({round(cor/total*100, 1)}%)</span>
                    </div>
                    <div style="background: #e2e8f0; height: 10px; border-radius: 6px; overflow: hidden; margin-top: 4px;">
                        <div style="background: #10b981; width: {cor/total*100}%; height: 100%;"></div>
                    </div>
                </div>

                <div style="margin-bottom: 14px;">
                    <div style="display: flex; justify-content: space-between; font-weight: 600; font-size: 0.9rem;">
                        <span style="color: #b91c1c;">🔴 Mispronounced Words</span>
                        <span><b>{mis}</b> / {total} ({round(mis/total*100, 1)}%)</span>
                    </div>
                    <div style="background: #e2e8f0; height: 10px; border-radius: 6px; overflow: hidden; margin-top: 4px;">
                        <div style="background: #ef4444; width: {mis/total*100}%; height: 100%;"></div>
                    </div>
                </div>

                <div style="margin-bottom: 14px;">
                    <div style="display: flex; justify-content: space-between; font-weight: 600; font-size: 0.9rem;">
                        <span style="color: #c2410c;">🟠 Skipped Words</span>
                        <span><b>{skp}</b> / {total} ({round(skp/total*100, 1)}%)</span>
                    </div>
                    <div style="background: #e2e8f0; height: 10px; border-radius: 6px; overflow: hidden; margin-top: 4px;">
                        <div style="background: #f97316; width: {skp/total*100}%; height: 100%;"></div>
                    </div>
                </div>

                <div style="margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; font-weight: 600; font-size: 0.9rem;">
                        <span style="color: #1d4ed8;">🔵 Repeated Words</span>
                        <span><b>{rep}</b> / {total} ({round(rep/total*100, 1)}%)</span>
                    </div>
                    <div style="background: #e2e8f0; height: 10px; border-radius: 6px; overflow: hidden; margin-top: 4px;">
                        <div style="background: #3b82f6; width: {rep/total*100}%; height: 100%;"></div>
                    </div>
                </div>
            </div>
            """
        )

    with col_chart:
        st.markdown("#### 📈 Benchmark Comparison (Student vs Benchmarks)")
        benchmark_df = pd.DataFrame({
            "Metric": ["Accuracy (%)", "Pronunciation", "Fluency", "Speed (WPM)"],
            "Student Score": [metrics["accuracy_pct"], metrics["pronunciation_score"], metrics["fluency_score"], metrics["wpm"]],
            "State Benchmark": [85.0, 80.0, 82.0, passage["target_wpm"]],
            "Class Average": [82.5, 78.0, 80.0, 68.0],
        }).set_index("Metric")
        st.bar_chart(benchmark_df, height=240)

    # Personalized Improvement Suggestions
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🎯 Personalized Improvement Plan (వ్యక్తిగత అభ్యసన ప్రణాళిక)")

    rec_c1, rec_c2 = st.columns(2)
    with rec_c1:
        st.markdown(
            f"""
            <div class="ecr-card" style="border-left: 4px solid #f59e0b; height: 100%;">
                <div class="ecr-card-header">🗣️ Daily Practice Interventions</div>
                <ul style="padding-left: 20px; color: #334155; line-height: 1.8;">
                    <li><b>Consonant Cluster Practice:</b> Spend 5 minutes daily reading compound aksharalu ('స్త', 'శ్య', 'త్మ').</li>
                    <li><b>Syllable Pacing:</b> Segment multi-syllabic words like 'త్ర-యం-బ-కే-శ్వ-రం' before full speed oral reading.</li>
                    <li><b>Connector Focus:</b> Track along words using finger or card ruler to ensure words like 'మరియు' are not skipped.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with rec_c2:
        st.markdown(
            f"""
            <div class="ecr-card" style="border-left: 4px solid #10b981; height: 100%;">
                <div class="ecr-card-header">⭐ Recommended Next Steps</div>
                <ul style="padding-left: 20px; color: #334155; line-height: 1.8;">
                    <li><b>Next Recommended Passage:</b> "కృష్ణానది వైభవం" (Telugu - Intermediate Tier 2).</li>
                    <li><b>Audio Mirror Practice:</b> Listen to the model narrator speech and repeat in echo-mode.</li>
                    <li><b>Teacher Review:</b> Scheduled for weekly classroom oral reading review.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    act_c1, act_c2, act_c3 = st.columns(3)
    with act_c1:
        if st.button("📥 Download Report (PDF Summary)", key="btn_download_pdf", use_container_width=True):
            st.success("Assessment summary generated! Ready for student reading portfolio.")
    with act_c2:
        if st.button("🔄 Retake Assessment", key="btn_retake", use_container_width=True):
            st.session_state["active_screen"] = "reading_assessment"
            st.rerun()
    with act_c3:
        if st.button("👩‍🏫 Go to Teacher Dashboard ➔", key="btn_goto_teacher_sub", type="primary", use_container_width=True):
            st.session_state["active_screen"] = "teacher_dashboard"
            st.rerun()


# ============================================================================
# 8. SCREEN 5: TEACHER DASHBOARD
# ============================================================================
def render_teacher_dashboard():
    """Render Teacher Dashboard: KPIs, Language comparison, Grade analytics, Error patterns, Student tracking."""
    kpi = data.TEACHER_SUMMARY_KPIS

    # Header with District & School Selector
    st.markdown(
        """
        <div style="background: linear-gradient(90deg, #0f172a 0%, #1e3a8a 60%, #0d9488 100%); color: white; border-radius: 14px; padding: 20px 26px; margin-bottom: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <h2 style="margin: 0; font-size: 1.45rem; color: #ffffff;">👩‍🏫 Teacher & School Administrator Dashboard</h2>
                    <p style="margin: 4px 0 0 0; color: #e2e8f0; font-size: 0.92rem;">
                        <b>MPPS Model Primary School, Amaravati</b> • Mandal: Thullur • District: Guntur
                    </p>
                </div>
                <div style="display: flex; gap: 8px;">
                    <span class="gov-badge">ACADEMIC YEAR 2026–27</span>
                    <span class="gov-badge" style="background: rgba(16, 185, 129, 0.4);">LIVE DISTRICT SYNC</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Top KPI Row
    st.markdown("### 📌 Executive School Summary")
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-lbl">Total Students Assessed</div>
                <div class="metric-val">{kpi['total_students_assessed']}</div>
                <div class="metric-sub">Across Classes 1 to 10</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f"""
            <div class="metric-card green-top">
                <div class="metric-lbl">Avg Reading Proficiency</div>
                <div class="metric-val">{kpi['avg_reading_proficiency']}%</div>
                <div class="metric-sub">🎯 State Target: 80% (+4.6%)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f"""
            <div class="metric-card purple-top">
                <div class="metric-lbl">Benchmark Attainment</div>
                <div class="metric-val">{kpi['students_at_benchmark_pct']}%</div>
                <div class="metric-sub">283 / 348 Students Proficient</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f"""
            <div class="metric-card amber-top">
                <div class="metric-lbl">Assessments This Month</div>
                <div class="metric-val">{kpi['assessments_this_month']}</div>
                <div class="metric-sub">📅 ~41 assessments / day</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Telugu vs English Performance Comparison
    st.markdown("### ⚖️ Telugu & English Performance Comparison")
    cmp_c1, cmp_c2 = st.columns([1, 1], gap="large")

    with cmp_c1:
        st.markdown(
            f"""
            <div class="ecr-card" style="border-top: 4px solid #1e3a8a;">
                <div class="ecr-card-header">🇮🇳 Telugu Medium Performance</div>
                <div style="display: flex; justify-content: space-around; margin: 16px 0; text-align: center;">
                    <div>
                        <div style="font-size: 1.8rem; font-weight: 800; color: #1e3a8a;">{kpi['telugu_avg_score']}%</div>
                        <div style="font-size: 0.78rem; color: #64748b; font-weight: 600;">AVG ACCURACY</div>
                    </div>
                    <div>
                        <div style="font-size: 1.8rem; font-weight: 800; color: #0d9488;">{kpi['avg_wpm_telugu']}</div>
                        <div style="font-size: 0.78rem; color: #64748b; font-weight: 600;">AVG WPM</div>
                    </div>
                    <div>
                        <div style="font-size: 1.8rem; font-weight: 800; color: #10b981;">88.2%</div>
                        <div style="font-size: 0.78rem; color: #64748b; font-weight: 600;">FLUENCY INDEX</div>
                    </div>
                </div>
                <p style="font-size: 0.85rem; color: #475569; margin: 0;">
                    <b>Pedagogical note:</b> Telugu pronunciation accuracy is strong on guninthalu. Main remediation area is samyuktakshara vattulu.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with cmp_c2:
        st.markdown(
            f"""
            <div class="ecr-card" style="border-top: 4px solid #0d9488;">
                <div class="ecr-card-header">🇬🇧 English Second Language Performance</div>
                <div style="display: flex; justify-content: space-around; margin: 16px 0; text-align: center;">
                    <div>
                        <div style="font-size: 1.8rem; font-weight: 800; color: #1e3a8a;">{kpi['english_avg_score']}%</div>
                        <div style="font-size: 0.78rem; color: #64748b; font-weight: 600;">AVG ACCURACY</div>
                    </div>
                    <div>
                        <div style="font-size: 1.8rem; font-weight: 800; color: #0d9488;">{kpi['avg_wpm_english']}</div>
                        <div style="font-size: 0.78rem; color: #64748b; font-weight: 600;">AVG WPM</div>
                    </div>
                    <div>
                        <div style="font-size: 1.8rem; font-weight: 800; color: #10b981;">85.4%</div>
                        <div style="font-size: 0.78rem; color: #64748b; font-weight: 600;">FLUENCY INDEX</div>
                    </div>
                </div>
                <p style="font-size: 0.85rem; color: #475569; margin: 0;">
                    <b>Pedagogical note:</b> High reading speed observed. Focus areas: multi-syllabic stress placement and ending phonemes.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Grade-Wise Analytics (Classes 1 to 10)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📊 Grade-Wise Performance Analytics (Classes 1–10)")

    grade_df = pd.DataFrame(data.GRADE_WISE_PERFORMANCE)

    tab_chart, tab_table = st.tabs(["📈 Grade Performance Graph", "📋 Comprehensive Grade Data Table"])
    with tab_chart:
        chart_data = grade_df.set_index("grade")[["telugu_score", "english_score", "avg_wpm"]]
        chart_data.columns = ["Telugu Score (%)", "English Score (%)", "Average WPM"]
        st.line_chart(chart_data, height=280)

    with tab_table:
        st.dataframe(
            grade_df.rename(columns={
                "grade": "Grade",
                "students": "Students Assessed",
                "telugu_score": "Telugu Score (%)",
                "english_score": "English Score (%)",
                "avg_wpm": "Average WPM",
                "fluency": "Fluency Score",
                "accuracy": "Accuracy (%)",
            }),
            use_container_width=True,
            hide_index=True,
        )

    # Common Reading Difficulties Breakdown
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### ⚠️ Common Reading Difficulties & Recommended Interventions")

    for diff_item in data.COMMON_READING_DIFFICULTIES:
        sev_color = "#b91c1c" if "High" in diff_item["severity"] else "#d97706"
        st.markdown(
            f"""
            <div class="ecr-card" style="border-left: 4px solid {sev_color}; padding: 14px 20px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div style="font-weight: 700; color: #0f172a; font-size: 1.02rem;">
                        {diff_item['category']}
                    </div>
                    <div>
                        <span class="status-pill status-proficient" style="margin-right: 6px;">Language: {diff_item['language']}</span>
                        <span class="status-pill status-needs-support">Affected: {diff_item['affected_students_pct']}% Students</span>
                    </div>
                </div>
                <div style="font-size: 0.85rem; color: #475569; margin: 6px 0;">
                    <b>Sample Observed Errors:</b> <code>{diff_item['examples']}</code>
                </div>
                <div style="font-size: 0.85rem; color: #166534; background: #f0fdf4; padding: 6px 12px; border-radius: 6px;">
                    🎯 <b>Targeted Intervention:</b> {diff_item['intervention']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Student-Wise Assessment Records (Filterable Table)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📋 Student-Wise Assessment Records & Registry")

    # Filters
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        filter_grade = st.selectbox(
            "Filter by Grade:",
            ["All", "Class 1", "Class 2", "Class 3", "Class 4", "Class 5", "Class 6", "Class 7", "Class 8"],
            index=0,
            key="filter_grade_widget",
        )
    with f_col2:
        filter_lang = st.selectbox(
            "Filter by Language:",
            ["All", "Telugu", "English"],
            index=0,
            key="filter_lang_widget",
        )
    with f_col3:
        filter_status = st.selectbox(
            "Filter by Proficiency:",
            ["All", "Advanced", "Proficient", "Needs Support"],
            index=0,
            key="filter_status_widget",
        )

    # Filter records
    records = data.TEACHER_STUDENT_RECORDS
    if filter_grade != "All":
        records = [r for r in records if r["grade"] == filter_grade]
    if filter_lang != "All":
        records = [r for r in records if r["language"] == filter_lang]
    if filter_status != "All":
        records = [r for r in records if r["status"] == filter_status]

    display_rows = []
    for r in records:
        display_rows.append({
            "Student ID": r["student_id"],
            "Student Name": r["name"],
            "Grade": r["grade"],
            "Language": r["language"],
            "Difficulty": r["difficulty"],
            "Overall Score": f"{r['overall_score']}/100",
            "Accuracy": f"{r['accuracy_pct']}%",
            "Speed (WPM)": r["wpm"],
            "Status": r["status"],
            "Assessment Date": r["date"],
        })

    st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)

    # Individual Student Progress Tracker
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📈 Individual Student Progress Tracking (విదార్థి పురోగతి ట్రాకింగ్)")

    student_options = {r["student_id"]: f"{r['name']} ({r['grade']})" for r in data.TEACHER_STUDENT_RECORDS}
    selected_tid = st.selectbox(
        "Select Student for Longitudinal Progress View:",
        options=list(student_options.keys()),
        format_func=lambda x: student_options[x],
        index=0,
        key="teacher_student_selector",
    )

    chosen_record = next((r for r in data.TEACHER_STUDENT_RECORDS if r["student_id"] == selected_tid), data.TEACHER_STUDENT_RECORDS[0])

    tcol1, tcol2 = st.columns([1, 1], gap="large")
    with tcol1:
        st.markdown(
            f"""
            <div class="ecr-card">
                <div class="ecr-card-header">👤 {chosen_record['name']}</div>
                <div style="font-size: 0.9rem; color: #334155; line-height: 1.8;">
                    <b>Student ID:</b> {chosen_record['student_id']}<br>
                    <b>Current Grade:</b> {chosen_record['grade']}<br>
                    <b>Assessed Passage:</b> {chosen_record['passage']}<br>
                    <b>Proficiency Level:</b> <span class="status-pill status-proficient">{chosen_record['status']}</span><br>
                    <b>Latest Reading Speed:</b> {chosen_record['wpm']} WPM<br>
                    <b>Latest Accuracy:</b> {chosen_record['accuracy_pct']}%
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with tcol2:
        st.markdown("##### 📈 6-Session Reading Proficiency Trend")
        scores = chosen_record.get("longitudinal_scores", [70, 74, 78, 81, 85, 89])
        trend_df = pd.DataFrame({
            "Session": [f"S{i+1}" for i in range(len(scores))],
            "Proficiency Score": scores,
        }).set_index("Session")
        st.line_chart(trend_df, height=180)


# ============================================================================
# 9. FOOTER & MAIN ORCHESTRATOR
# ============================================================================
def render_footer():
    """Render consistent SHR Trinity | AksharaMitra footer."""
    st.markdown(
        """
        <div style="margin-top: 36px; padding: 16px 24px; background: #ffffff; border: 1px solid #e2e8f0; border-top: 3px solid #1e40af; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; font-size: 0.84rem; color: #475569;">
            <div>
                <b style="color: #1e3a8a;">SHR Trinity | AksharaMitra (అక్షరమిత్ర)</b> — AI-Powered Bilingual Reading Intelligence &amp; Personalized Learning Platform
            </div>
            <div style="color: #0d9488; font-weight: 600;">
                Every Child Heard. Every Reader Empowered. • ప్రతి చిన్నారి స్వరం వినిపించాలి • ప్రతి చదువు మెరుగుపడాలి
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_main_app():
    """Main application router handling styles, header, sidebar, all 5 screens, and footer."""
    inject_custom_styles()
    init_session_state()
    render_header()
    render_sidebar()

    current_screen = st.session_state["active_screen"]

    if current_screen == "student_dashboard":
        render_student_dashboard()
    elif current_screen == "reading_assessment":
        render_reading_assessment()
    elif current_screen == "reading_analysis":
        render_reading_analysis()
    elif current_screen == "assessment_results":
        render_assessment_results()
    elif current_screen == "teacher_dashboard":
        render_teacher_dashboard()
    else:
        render_student_dashboard()

    render_footer()

