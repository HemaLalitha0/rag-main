"""
Report Export Utility
Generates clean, professionally formatted PDF and Markdown reports
of candidate mock interview evaluations across any profession and interview type.
Includes STAR framework scores and delivery pacing analytics.
"""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.pdfgen import canvas
from interview_schemas import FinalAssessmentReport

class ReportCanvas(canvas.Canvas):
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
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 36, page_str)
        self.drawString(54, 36, "Universal AI Mock Interview Platform - Personal Readiness Assessment")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 48, 558, 48)
        self.restoreState()

def export_report_to_pdf(report: FinalAssessmentReport, output_path: str):
    """Build a comprehensive PDF report from a FinalAssessmentReport model."""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=19,
        leading=23,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=6
    )

    sub_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#4A5568"),
        spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12.5,
        leading=16,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=4
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#2D3748"),
        leftIndent=14,
        spaceAfter=3
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("AI Mock Interview Performance Assessment", title_style))
    story.append(Paragraph(
        f"<b>Candidate:</b> {report.candidate_name} &nbsp;|&nbsp; "
        f"<b>Role:</b> {report.target_role} ({report.industry})<br/>"
        f"<b>Type:</b> {report.interview_type} &nbsp;|&nbsp; "
        f"<b>Mode:</b> {report.interview_mode} &nbsp;|&nbsp; "
        f"<b>Date:</b> {report.interview_date}",
        sub_style
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2B6CB0"), spaceAfter=12))

    # Overall Result Card
    status_color = "#276749" if report.passed else "#9B2C2C"
    status_bg = "#C6F6D5" if report.passed else "#FED7D7"
    status_text = getattr(report, "overall_readiness", None) or ("READY FOR INTERVIEW" if report.passed else "NEEDS TARGETED PRACTICE")

    summary_table_data = [
        [
            Paragraph(f"<b>Overall Score:</b> {report.overall_score}/100", body_style),
            Paragraph(f"<b>Technical:</b> {getattr(report, 'technical_knowledge_score', 0.0)}/100", body_style),
            Paragraph(f"<b>Communication:</b> {getattr(report, 'communication_score', 0.0)}/100", body_style),
            Paragraph(f"<b>Problem-Solving:</b> {getattr(report, 'problem_solving_score', 0.0)}/100", body_style),
        ],
        [
            Paragraph(f"<b>Relevance:</b> {getattr(report, 'answer_relevance_score', 0.0)}/100", body_style),
            Paragraph(f"<b>Pacing:</b> {report.average_delivery_pacing}", body_style),
            Paragraph(f"<b>Answered:</b> {report.questions_answered_count}/{report.total_questions_asked}", body_style),
            Paragraph(f"<font color='{status_color}'><b>Readiness:</b> {status_text}</font>", body_style),
        ],
    ]
    sum_table = Table(summary_table_data, colWidths=[125, 125, 125, 129])
    sum_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(status_bg)),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor(status_color)),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(sum_table)
    story.append(Spacer(1, 8))

    if getattr(report, "final_assessment_summary", ""):
        story.append(Paragraph(f"<b>Final Assessment:</b> {report.final_assessment_summary}", body_style))
        story.append(Spacer(1, 6))

    # Category Breakdown Table
    if report.category_scores:
        story.append(Paragraph("Competency & Category Performance", h1_style))
        cat_data = [[
            Paragraph("<b>Competency / Category</b>", body_style),
            Paragraph("<b>Average Score</b>", body_style),
            Paragraph("<b>Readiness Level</b>", body_style)
        ]]
        for cat, sc in report.category_scores.items():
            rating = "Strong Competence" if sc >= 80 else ("Satisfactory" if sc >= 65 else "Developing")
            cat_data.append([
                Paragraph(cat, body_style),
                Paragraph(f"{sc}/100", body_style),
                Paragraph(rating, body_style)
            ])
        t_cat = Table(cat_data, colWidths=[240, 130, 134])
        t_cat.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_cat)
        story.append(Spacer(1, 10))

    # Key Strengths
    story.append(Paragraph("Strengths", h1_style))
    for s in (report.key_strengths or ["None recorded."]):
        story.append(Paragraph(f"• {s}", bullet_style))

    # Weaknesses
    story.append(Paragraph("Weaknesses", h1_style))
    for w in (getattr(report, "weaknesses", None) or report.areas_for_improvement or ["None recorded."]):
        story.append(Paragraph(f"• {w}", bullet_style))

    # Missing Concepts
    if getattr(report, "missing_concepts", None):
        story.append(Paragraph("Missing Concepts", h1_style))
        for mc in report.missing_concepts:
            story.append(Paragraph(f"• {mc}", bullet_style))

    # Specific Improvement Recommendations
    story.append(Paragraph("Specific Improvement Recommendations", h1_style))
    for imp in report.areas_for_improvement:
        story.append(Paragraph(f"• {imp}", bullet_style))

    # Skills Needing Further Preparation
    if getattr(report, "skills_needing_preparation", None):
        story.append(Paragraph("Skills Needing Further Preparation", h1_style))
        for sk in report.skills_needing_preparation:
            story.append(Paragraph(f"• {sk}", bullet_style))

    # Recommended Topics
    story.append(Paragraph("Suggested Learning Topics", h1_style))
    for top in report.recommended_topics_to_study:
        story.append(Paragraph(f"• {top}", bullet_style))

    story.append(Spacer(1, 10))

    # Detailed Question Assessment
    story.append(Paragraph("Question-by-Question Evaluation", h1_style))
    for i, rec in enumerate(report.session_records, 1):
        q = rec.question
        ev = rec.evaluation
        status_lbl = getattr(ev, "answer_status", "Answered" if (ev and ev.score > 0) else "Unanswered")
        story.append(Paragraph(f"<b>Q{i} [{q.category}] ({status_lbl}): {q.question_text}</b>", body_style))
        story.append(Paragraph(f"<b>Candidate Answer:</b> {rec.candidate_answer}", body_style))
        if q.expected_concepts:
            story.append(Paragraph(f"<b>Expected Concepts:</b> {', '.join(q.expected_concepts)}", body_style))
        if ev:
            star_info = ""
            if ev.star_analysis:
                sa = ev.star_analysis
                star_info = f" | <b>STAR Completeness:</b> {int(sa.star_completeness_ratio * 100)}%"
            story.append(
                Paragraph(
                    f"<b>Score:</b> {ev.score}/100 &nbsp;|&nbsp; "
                    f"<b>Technical:</b> {ev.technical_or_domain_accuracy}/100 &nbsp;|&nbsp; "
                    f"<b>Problem-Solving:</b> {ev.practical_reasoning_and_scenarios}/100 &nbsp;|&nbsp; "
                    f"<b>Communication:</b> {ev.communication_and_clarity}/100 &nbsp;|&nbsp; "
                    f"<b>Relevance:</b> {ev.completeness_and_relevance}/100{star_info}",
                    body_style,
                )
            )
            if ev.strengths:
                story.append(Paragraph(f"<b>What Was Good:</b> {'; '.join(ev.strengths)}", body_style))
            if ev.missing_or_incorrect:
                story.append(Paragraph(f"<b>What Was Missing:</b> {'; '.join(ev.missing_or_incorrect)}", body_style))
            story.append(Paragraph(f"<b>Evaluation Feedback &amp; How to Improve:</b> {ev.improvement_feedback}", body_style))
            if ev.suggested_ideal_outline:
                story.append(Paragraph(f"<b>Ideal Answer Outline:</b> {ev.suggested_ideal_outline}", body_style))
        story.append(Spacer(1, 6))

    doc.build(story, canvasmaker=ReportCanvas)
    return output_path
