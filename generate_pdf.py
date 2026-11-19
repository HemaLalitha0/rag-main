import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#718096"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 755, "Technical Proposal: Advanced AI Interview Preparation System")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(54, 747, 558, 747)
            
        # Footer
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 36, page_str)
        self.drawString(54, 36, "Confidential - For Internal Technical Review Only")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 48, 558, 48)
        self.restoreState()

def create_proposal_pdf(output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=21,
        leading=25,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=10
    )

    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#4A5568"),
        spaceAfter=12
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor("#2D3748"),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#2D3748"),
        leftIndent=15,
        spaceAfter=3
    )

    th_style = ParagraphStyle(
        'THStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    td_style = ParagraphStyle(
        'TDStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#2D3748")
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("Proposed Implementation Plan:<br/>Advanced AI Interview Preparation System", title_style))
    story.append(Paragraph(
        "<b>Document Type:</b> Technical Proposal for Review &nbsp;|&nbsp; "
        "<b>Purpose:</b> Next-Stage Engineering Roadmap &nbsp;|&nbsp; "
        "<b>Status:</b> Awaiting Technical Feedback",
        meta_style
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2B6CB0"), spaceAfter=14))

    # 1. Objective
    story.append(Paragraph("1. Objective", h1_style))
    story.append(Paragraph(
        "The objective is to enhance the interview preparation capabilities of the existing application by introducing "
        "an interactive, AI-powered mock interview system.", body_style
    ))
    story.append(Paragraph(
        "The proposed system will allow a candidate to upload a resume, select a target job role, participate in a simulated interview, "
        "answer questions through text or voice, receive feedback on each response, and obtain a final performance report.", body_style
    ))
    story.append(Paragraph(
        "The system will go beyond providing information or answering user queries. It will manage the interview process, evaluate candidate "
        "responses against predefined criteria, generate relevant follow-up questions, and provide a structured assessment of interview readiness.", body_style
    ))

    # 2. End-to-End Workflow
    story.append(Paragraph("2. Proposed End-to-End Workflow", h1_style))
    workflow_steps = [
        ("1. Candidate input:", "Upload a resume and select target job role, experience level, and interview difficulty."),
        ("2. Resume analysis:", "Extract skills, technologies, work experience, and project details from the resume."),
        ("3. Interview planning:", "Generate a structured set of questions based on resume, job role requirements, and technical topics."),
        ("4. Interactive interview:", "Ask one question at a time and allow the candidate to submit a response."),
        ("5. Answer evaluation:", "Assess each response for technical correctness, completeness, reasoning, and practical understanding."),
        ("6. Adaptive questioning:", "Generate follow-up questions based on candidate response when deeper assessment is needed."),
        ("7. Final assessment:", "Calculate overall score using a predefined scoring rubric and agreed passing threshold."),
        ("8. Report generation:", "Present score, strengths, weaknesses, question-level feedback, study areas, and Pass/Fail recommendation.")
    ]
    for label, desc in workflow_steps:
        story.append(Paragraph(f"• <b>{label}</b> {desc}", bullet_style))

    story.append(Spacer(1, 8))

    # 3. Technical Approach
    story.append(Paragraph("3. Proposed Technical Approach", h1_style))
    
    story.append(Paragraph("3.1 Resume Processing and Question Generation", h2_style))
    story.append(Paragraph(
        "<b>Technique:</b> Document parsing, structured information extraction, and LLM-based question generation.<br/>"
        "<b>Libraries:</b> <code>pypdf</code> for PDF text extraction, <code>python-docx</code> for DOCX, and <code>Pydantic</code> for validating structured resume schema.<br/>"
        "<b>Model approach:</b> Initially evaluate the LLM already available in the application. Benchmarking against instruction-following models will occur if schema validation or reasoning fidelity requires enhancement.",
        body_style
    ))

    story.append(Paragraph("3.2 Interactive Interview Management", h2_style))
    story.append(Paragraph(
        "<b>Technique:</b> State-based interview orchestration and conversation context management.<br/>"
        "The system will maintain an explicit interview state machine (Current Question, Submitted Answer, Evaluation Status, Follow-up Status, Interview Completion Status). "
        "The deterministic Python controller manages transitions rather than relying on LLM autonomy.",
        body_style
    ))

    story.append(Paragraph("3.3 Candidate Interaction: Text and Voice", h2_style))
    story.append(Paragraph(
        "• <b>Text Mode:</b> Built using Streamlit chat components (<code>st.chat_message</code>, <code>st.chat_input</code>).<br/>"
        "• <b>Voice Mode:</b> Spoken questions presented as audio via <code>edge-tts</code> or local Piper TTS; candidate speech transcribed via <code>faster-whisper</code> into the shared answer evaluation pipeline.<br/>"
        "<i>Note: Voice functionality will be introduced in Phase 6 after text-based workflows are fully validated.</i>",
        body_style
    ))

    story.append(Paragraph("3.4 Answer Evaluation and Feedback", h2_style))
    story.append(Paragraph(
        "<b>Technique:</b> Rubric-based evaluation supported by an LLM with structured output validation.<br/>"
        "Evaluates responses on: (1) Technical correctness, (2) Completeness, (3) Logical reasoning, and (4) Practical application. "
        "Allows technically equivalent explanations rather than strict keyword matching, providing constructive scoring and actionable suggestions.",
        body_style
    ))

    story.append(Paragraph("3.5 Adaptive Follow-Up Questions", h2_style))
    story.append(Paragraph(
        "<b>Technique:</b> Context-aware question generation driven by the candidate's prior answer. "
        "Triggers a targeted follow-up question (max 1 per main question) when responses are incomplete or ambiguous before progressing to the next topic.",
        body_style
    ))

    story.append(Paragraph("3.6 Final Assessment and Report", h2_style))
    story.append(Paragraph(
        "<b>Technique:</b> Deterministic score aggregation using a configurable scoring rubric (e.g. 70/100 threshold). "
        "Produces overall score, Pass/Fail recommendation, section-wise analysis, candidate strengths/weaknesses, and targeted study roadmaps.",
        body_style
    ))

    # 4. Technology Stack Table
    story.append(Paragraph("4. Proposed Technology Stack", h1_style))
    stack_data = [
        [Paragraph("<b>Component</b>", th_style), Paragraph("<b>Proposed Technology / Technique</b>", th_style), Paragraph("<b>Purpose</b>", th_style)],
        [Paragraph("Resume extraction", td_style), Paragraph("pypdf, python-docx", td_style), Paragraph("Extract resume text and metadata", td_style)],
        [Paragraph("Structured data", td_style), Paragraph("Pydantic", td_style), Paragraph("Validate schemas for plans and evaluations", td_style)],
        [Paragraph("Interview interface", td_style), Paragraph("Streamlit", td_style), Paragraph("Interactive chat UI and report dashboard", td_style)],
        [Paragraph("Question generation", td_style), Paragraph("Configured LLM", td_style), Paragraph("Generate role-tailored questions", td_style)],
        [Paragraph("Interview control", td_style), Paragraph("Python State Machine", td_style), Paragraph("Deterministic flow, state transitions", td_style)],
        [Paragraph("Answer evaluation", td_style), Paragraph("LLM Rubric Evaluation", td_style), Paragraph("Multi-criteria scoring & constructive feedback", td_style)],
        [Paragraph("Speech recognition", td_style), Paragraph("faster-whisper", td_style), Paragraph("Convert spoken answers to text", td_style)],
        [Paragraph("Speech generation", td_style), Paragraph("edge-tts / Piper TTS", td_style), Paragraph("Audio presentation of questions", td_style)],
        [Paragraph("Persistence", td_style), Paragraph("SQLite (users.db)", td_style), Paragraph("Session logging, history, and exports", td_style)],
    ]

    t_stack = Table(stack_data, colWidths=[120, 160, 224])
    t_stack.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#F7FAFC"), colors.white]),
    ]))
    story.append(t_stack)
    story.append(Spacer(1, 10))

    # 5. Implementation Phases Table
    story.append(Paragraph("5. Proposed Implementation Phases and Deliverables", h1_style))
    phases_data = [
        [Paragraph("<b>Phase</b>", th_style), Paragraph("<b>Planned Work</b>", th_style), Paragraph("<b>Expected Deliverable</b>", th_style)],
        [Paragraph("Phase 1", td_style), Paragraph("Technical review & interface design", td_style), Paragraph("Approved engineering backlog & Pydantic schemas", td_style)],
        [Paragraph("Phase 2", td_style), Paragraph("Resume processing & plan generation", td_style), Paragraph("Resume-grounded question generator", td_style)],
        [Paragraph("Phase 3", td_style), Paragraph("Interactive text interview", td_style), Paragraph("Streamlit stateful Q&A chat workflow", td_style)],
        [Paragraph("Phase 4", td_style), Paragraph("Answer evaluation & adaptive follow-ups", td_style), Paragraph("Rubric scores & contextual questioning", td_style)],
        [Paragraph("Phase 5", td_style), Paragraph("Final scoring & report dashboard", td_style), Paragraph("Full assessment report with Pass/Fail status", td_style)],
        [Paragraph("Phase 6", td_style), Paragraph("Voice interaction integration", td_style), Paragraph("Speech-to-text and audio interviewer output", td_style)],
        [Paragraph("Phase 7", td_style), Paragraph("Testing & optimization", td_style), Paragraph("Automated validation suite & latency report", td_style)],
    ]

    t_phases = Table(phases_data, colWidths=[60, 210, 234])
    t_phases.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#F7FAFC"), colors.white]),
    ]))
    story.append(t_phases)
    story.append(Spacer(1, 10))

    # 6. Quality Validation
    story.append(Paragraph("6. Testing and Quality Validation", h1_style))
    story.append(Paragraph(
        "The implementation will be validated through automated tests covering: resume parsing across PDF/DOCX formats, "
        "question-to-resume relevance, state machine progression, evaluation consistency across equivalent answers, "
        "interrupted session recovery, and end-to-end report correctness.",
        body_style
    ))

    # 7. Key Design Considerations
    story.append(Paragraph("7. Key Design Considerations", h1_style))
    story.append(Paragraph("• <b>LLM for Cognition, Logic for Orchestration:</b> Deterministic state machine handles interview flow.", bullet_style))
    story.append(Paragraph("• <b>Transparent Rubric:</b> Scores are explained with constructive strengths and weaknesses.", bullet_style))
    story.append(Paragraph("• <b>Unified Interaction Pipeline:</b> Voice is treated as an input/output layer on top of the text pipeline.", bullet_style))
    story.append(Paragraph("• <b>Realistic Mock Threshold:</b> Pass/Fail indicates mock interview preparedness against benchmark criteria.", bullet_style))

    story.append(Spacer(1, 6))

    # 8. Technical Review Recommendations
    story.append(Paragraph("8. Technical Review & Strategic Recommendations", h1_style))
    rev_points = [
        ("1. Interaction Mode:", "Deliver Text-First (Phases 1-5), introduce Voice in Phase 6 for stability and quick validation."),
        ("2. LLM Model Selection:", "Retain existing application LLM with strict Pydantic schemas; benchmark only if needed."),
        ("3. Model Architecture:", "Use single model with targeted system prompts for generation and evaluation to preserve resources."),
        ("4. Scoring Rubric:", "Recommended: 70% overall pass threshold (40% Technical, 30% Projects, 20% Completeness, 10% Reasoning)."),
        ("5. Question Scope:", "Prioritize Technical + Applied Project Experience first; add HR/Behavioral questions in later iterations."),
        ("6. Deployment Strategy:", "Hybrid architecture with local faster-whisper STT and configurable cloud/local LLM & TTS engines."),
        ("7. Persistence & Export:", "Store completed interview sessions in SQLite (users.db) and support one-click PDF/MD report exports.")
    ]
    for label, desc in rev_points:
        story.append(Paragraph(f"• <b>{label}</b> {desc}", bullet_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully generated at: {output_path}")

if __name__ == "__main__":
    desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    pdf_out = os.path.join(desktop_dir, "AI_Interview_Preparation_System_Proposal.pdf")
    create_proposal_pdf(pdf_out)
