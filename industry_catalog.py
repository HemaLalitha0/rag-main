"""
Comprehensive Profession & Interview Type Catalog.
Includes:
- 10+ Broad Industry Domains & 70+ Granular Job Roles
- Dynamic Custom Role entry with Job Description grounding
- 5 Specialized Interview Types: Behavioral (STAR), Situational, Technical/Domain, HR/Culture Fit, Case Study
- Domain-specific evaluation rubrics & focus areas
"""
from typing import Dict, List, Any

INTERVIEW_TYPES: Dict[str, Dict[str, str]] = {
    "Behavioral (STAR Method)": {
        "description": "Evaluates past experiences, leadership, teamwork, adaptability, and conflict resolution using Situation, Task, Action, and Result.",
        "eval_focus": "STAR Structure (Situation, Task, Action, Result), Ownership, Specificity, and Measurable Outcomes",
        "question_prefix": "Tell me about a time when...",
        "icon": "⭐"
    },
    "Situational & Scenario Judgment": {
        "description": "Tests critical decision-making, ethical dilemmas, safety compliance, and priority management in unexpected real-world situations.",
        "eval_focus": "Immediate Response, Risk Mitigation, Protocol Adherence, and Stakeholder Communication",
        "question_prefix": "Imagine you are faced with a situation where...",
        "icon": "🧭"
    },
    "Technical & Domain Deep-Dive": {
        "description": "Assesses foundational concepts, standard operating procedures, architectural reasoning, tools, and technical problem-solving.",
        "eval_focus": "Domain Precision, Conceptual Accuracy, Trade-off Analysis, and Practical Application",
        "question_prefix": "Explain the principles and practical considerations of...",
        "icon": "⚙️"
    },
    "HR & Culture Fit": {
        "description": "Assesses company values alignment, personal motivation, working style, career trajectory, resilience, and growth mindset.",
        "eval_focus": "Self-Awareness, Cultural Contribution, Motivation, Clarity of Purpose, and Interpersonal Fit",
        "question_prefix": "What motivates you to pursue this role, and how do you handle...",
        "icon": "🤝"
    },
    "Case Study & Structured Problem Solving": {
        "description": "Presents a multi-step organizational, clinical, financial, or engineering challenge requiring structured diagnosis and strategic recommendations.",
        "eval_focus": "Problem Decomposition, Root-Cause Analysis, Feasibility, and Strategic Action Plan",
        "question_prefix": "Here is a real-world scenario you need to analyze...",
        "icon": "📊"
    }
}

INDUSTRY_CATALOG: Dict[str, Dict[str, Any]] = {
    "Artificial Intelligence, Software & IT": {
        "roles": [
            "AI / Machine Learning Engineer",
            "Data Scientist / Analytics Lead",
            "Full Stack Software Engineer",
            "Backend Systems Engineer (Python / Go / Java)",
            "Cloud Platform & DevOps Engineer (AWS / GCP / K8s)",
            "Cybersecurity & SOC Analyst",
            "Data Engineer & Pipeline Architect",
            "IT Systems & Network Support Specialist"
        ],
        "rubric": {
            "dim1": "Algorithmic & System Correctness",
            "dim2": "Scalability, Performance & Resource Efficiency",
            "dim3": "Troubleshooting, Debugging & Trade-offs",
            "dim4": "Architecture Design & Clean Code Standards"
        },
        "default_focus": "System Scalability & Algorithmic Reasoning"
    },
    "Healthcare, Nursing & Medicine": {
        "roles": [
            "Registered Nurse (RN) / ICU Specialist",
            "Clinical Physician / Medical Resident",
            "Pharmacist / Clinical Pharmacologist",
            "Medical Laboratory Technologist",
            "Healthcare Administrator & Operations Lead",
            "Physical Therapist & Rehabilitation Specialist",
            "Public Health Officer / Epidemiologist"
        ],
        "rubric": {
            "dim1": "Clinical Protocol & Patient Safety Standards",
            "dim2": "Triage, Critical Incident & Emergency Judgment",
            "dim3": "Empathy, Bedside Manner & Interprofessional Communication",
            "dim4": "Medical Ethics, Confidentiality (HIPAA) & Compliance"
        },
        "default_focus": "Patient Safety Protocols & Clinical Judgment"
    },
    "Education, Teaching & Academia": {
        "roles": [
            "K-12 Subject Teacher (Elementary / High School)",
            "University Lecturer / Assistant Professor",
            "Instructional Designer / E-Learning Specialist",
            "Special Education Needs (SEN) Coordinator",
            "Academic Researcher / Postdoctoral Fellow",
            "Corporate Learning & Development Manager"
        ],
        "rubric": {
            "dim1": "Pedagogical Strategy & Lesson Structuring",
            "dim2": "Differentiated Instruction & Inclusive Learning",
            "dim3": "Classroom Dynamics & Student Engagement",
            "dim4": "Formative Assessment & Constructive Feedback"
        },
        "default_focus": "Differentiated Instruction & Student Engagement"
    },
    "Finance, Banking, Accounting & Audit": {
        "roles": [
            "Financial Analyst (FP&A)",
            "Chartered Accountant / External Auditor",
            "Investment Banking Analyst / Associate",
            "Risk Management & Anti-Money Laundering (AML) Officer",
            "Commercial Credit Underwriter",
            "Tax Compliance Specialist",
            "Actuary / Quantitative Risk Analyst"
        ],
        "rubric": {
            "dim1": "Financial Modeling & Statutory Accounting (GAAP/IFRS)",
            "dim2": "Risk Assessment, Due Diligence & Fraud Controls",
            "dim3": "Quantitative Precision & Data Interpretation",
            "dim4": "Fiduciary Responsibility & Regulatory Governance"
        },
        "default_focus": "Regulatory Compliance & Risk Assessment"
    },
    "Business, Management, Marketing & Sales": {
        "roles": [
            "Product Manager (B2B / B2C)",
            "Human Resources Generalist / Talent Partner",
            "Enterprise Account Executive (B2B SaaS Sales)",
            "Digital Marketing Lead (SEO / Growth / Performance)",
            "Operations & Supply Chain Manager",
            "Customer Success Manager / Client Strategist",
            "Management Consultant / Business Analyst"
        ],
        "rubric": {
            "dim1": "Commercial Acumen & Data-Driven Decision Making",
            "dim2": "Stakeholder Alignment & Cross-Functional Leadership",
            "dim3": "Conflict Resolution & Negotiation Strategy",
            "dim4": "Executive Presence & Persuasive Communication"
        },
        "default_focus": "Commercial Strategy & Stakeholder Communication"
    },
    "Engineering, Manufacturing & Skilled Trades": {
        "roles": [
            "Project Engineer / Construction Manager",
            "Mechanical Design & CAD Engineer",
            "Certified Industrial Electrician",
            "Civil / Structural Site Engineer",
            "Quality Assurance / Six Sigma Specialist",
            "Environmental Health & Safety (EHS / OSHA) Officer",
            "CNC Machinist / Maintenance Technician"
        ],
        "rubric": {
            "dim1": "Schematic / Blueprint Interpretation & Technical Specs",
            "dim2": "Jobsite Safety Protocols & Hazard Prevention (OSHA)",
            "dim3": "Diagnostics, Root-Cause Analysis & Preventive Maintenance",
            "dim4": "Material Science & Quality Assurance Standards"
        },
        "default_focus": "Jobsite Safety Standards & Technical Troubleshooting"
    },
    "Law, Legal Services & Public Administration": {
        "roles": [
            "Corporate Paralegal / Legal Researcher",
            "Government Regulatory & Policy Analyst",
            "Public Administration Officer",
            "Contract Management Specialist",
            "Case Worker / Social Services Specialist",
            "Compliance & Ethics Director"
        ],
        "rubric": {
            "dim1": "Statutory Interpretation & Legal Precedent",
            "dim2": "Procedural Fairness, Impartiality & Governance",
            "dim3": "Fact-Finding, Evidence Synthesis & Case Prep",
            "dim4": "Precise Written & Oral Argumentation"
        },
        "default_focus": "Statutory Interpretation & Procedural Fairness"
    },
    "Hospitality, Retail, Tourism & Customer Service": {
        "roles": [
            "Hotel General Manager / Front Desk Supervisor",
            "Customer Support Team Lead / Omnichannel Lead",
            "Retail Store Manager / Merchandiser",
            "Food & Beverage Director / Executive Chef",
            "Event Planner & Conference Coordinator",
            "Flight Attendant / Passenger Services Specialist"
        ],
        "rubric": {
            "dim1": "Customer Experience & Service Recovery Protocol",
            "dim2": "De-escalation & High-Stress Composure",
            "dim3": "Team Leadership, Shift Scheduling & Resource Allocation",
            "dim4": "Active Listening & Empathetic Engagement"
        },
        "default_focus": "Service Recovery & Customer De-escalation"
    },
    "Fresh Graduates, Interns & Career Transitions": {
        "roles": [
            "Entry-Level Generalist / Management Trainee",
            "Graduate Research Assistant",
            "Career Switcher (Transitioning into a New Field)",
            "Summer Intern / Co-op Candidate"
        ],
        "rubric": {
            "dim1": "Transferable Skills & Foundational Aptitude",
            "dim2": "Learning Agility & Curiosity",
            "dim3": "Self-Motivation & Structured Problem Solving",
            "dim4": "Communication Clarity & Professional Demeanor"
        },
        "default_focus": "Learning Agility & Transferable Skills"
    },
    "Other / Custom Profession": {
        "roles": [
            "Other / Custom Role"
        ],
        "rubric": {
            "dim1": "Domain Knowledge & Best Practice Mastery",
            "dim2": "Practical Execution & Problem Decomposition",
            "dim3": "Critical Thinking & Sound Judgment",
            "dim4": "Clarity of Explanation & Communication"
        },
        "default_focus": "Role-Specific Competencies & Practical Scenarios"
    }
}

EXPERIENCE_LEVELS = [
    "Fresher / Student (0-1 yrs)",
    "Entry-Level (1-3 yrs)",
    "Mid-Level (3-6 yrs)",
    "Senior Professional (6-10 yrs)",
    "Lead / Principal / Executive (10+ yrs)"
]

INTERVIEW_DIFFICULTIES = [
    "Warm-up / Baseline",
    "Standard Industry Interview",
    "Challenging / High-Bar",
    "Elite / FAANG / Top-Tier"
]
