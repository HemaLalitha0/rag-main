# Proposed Implementation Plan: Advanced AI Interview Preparation System

**Document Type:** Technical Proposal for Review  
**Purpose:** Proposed next-stage development  
**Status:** Awaiting technical review and feedback

---

## 1. Objective

The objective is to enhance the interview preparation capabilities of the existing application by introducing an interactive, AI-powered mock interview system.

The proposed system will allow a candidate to upload a resume, select a target job role, participate in a simulated interview, answer questions through text or voice, receive feedback on each response, and obtain a final performance report.

The system will go beyond providing information or answering user queries. It will manage the interview process, evaluate candidate responses against predefined criteria, generate relevant follow-up questions, and provide a structured assessment of interview readiness.

This document outlines the proposed workflow, technical approach, technology choices, implementation phases, expected deliverables, and points requiring technical review.

---

## 2. Proposed End-to-End Workflow

The system will follow the workflow below:

1. **Candidate input:** Upload a resume and select the target job role, experience level, and interview difficulty.
2. **Resume analysis:** Extract skills, technologies, work experience, and project details from the resume.
3. **Interview planning:** Generate a structured set of questions based on the resume, job requirements, and relevant technical topics.
4. **Interactive interview:** Ask one question at a time and allow the candidate to submit a response.
5. **Answer evaluation:** Assess each response for technical correctness, completeness, reasoning, and practical understanding.
6. **Adaptive questioning:** Generate follow-up questions based on the candidate’s response when additional assessment is necessary.
7. **Final assessment:** Calculate the overall score using a predefined scoring rubric and agreed passing threshold.
8. **Report generation:** Present the score, strengths, weaknesses, question-level feedback, recommended learning areas, and a Pass/Fail mock-interview recommendation.

---

## 3. Proposed Technical Approach

### 3.1 Resume Processing and Question Generation

**Technique:** Document parsing, structured information extraction, and LLM-based question generation.

**Proposed libraries:**
- `pypdf` for PDF text extraction.
- `python-docx` for DOCX text extraction.
- `Pydantic` for validating structured resume information and generated interview plans.

**Proposed model approach:** Initially evaluate the LLM already available in the application. If it does not provide sufficient question quality or structured outputs, benchmark an alternative instruction-following model based on accuracy, latency, deployment requirements, and cost.

The extracted information will be organized into structured fields, including skills, projects, experience, and technologies. The system will use this information to generate role-relevant interview questions without inventing experience that is not supported by the resume.

**Expected output:** A validated interview plan containing question categories, difficulty levels, expected answer concepts, and evaluation criteria.

### 3.2 Interactive Interview Management

**Technique:** State-based interview orchestration and conversation context management.

The system will maintain an explicit interview state, including the current question, submitted answer, evaluation status, follow-up status, and interview completion status.

The interview controller will manage the sequence of operations rather than relying entirely on the LLM to determine application state.

**Expected output:** A conversational interview experience in which the system asks questions sequentially, processes responses, asks relevant follow-ups, and moves to the next question.

### 3.3 Candidate Interaction: Text and Voice

The interaction layer will support two proposed modes.

#### Text mode
The candidate reads the question, types an answer, and submits it through the application interface.
**Proposed library:** Streamlit chat components, including `st.chat_message` and `st.chat_input`, if compatible with the current interface.

#### Voice mode
The interviewer presents a question as audio, and the candidate responds through a microphone. The spoken response is converted to text and submitted to the same answer-evaluation pipeline used in text mode.

**Proposed speech technologies:**
- `faster-whisper` for speech-to-text transcription.
- `edge-tts` for text-to-speech, subject to network availability and service requirements.
- Piper or another suitable local TTS engine as an alternative if offline operation is required.

**Expected output:** A consistent interview experience across text and voice modes, with a shared question sequence and evaluation process. Voice functionality will be introduced after the text-based interview workflow is validated.

### 3.4 Answer Evaluation and Feedback

**Technique:** Rubric-based evaluation supported by an LLM and structured output validation.

Each answer will be evaluated against criteria appropriate to the question, such as:
- Technical correctness.
- Completeness of the explanation.
- Logical reasoning.
- Practical application and project understanding.

The evaluator will compare the candidate's response with expected concepts and relevant reference material. It will allow technically equivalent explanations instead of requiring exact wording.

Each evaluation will include a score, supporting reasoning, correctly explained concepts, missing or incorrect concepts, and suggested improvements.

**Model approach:** Use the configured LLM for an initial evaluation and validate its performance against manually reviewed sample answers. A separate evaluator model will be considered only if benchmarking demonstrates a clear benefit.

**Expected output:** A structured and explainable evaluation for every submitted answer.

### 3.5 Adaptive Follow-Up Questions

**Technique:** Context-aware question generation driven by the current answer and interview plan.

If an answer is incomplete, ambiguous, or requires deeper technical validation, the system can ask a follow-up question. If the response sufficiently addresses the question, the interview proceeds to the next planned topic.

Follow-up questions will remain within the selected job role and interview objectives.

**Expected output:** An interview that adapts to candidate responses rather than following only a fixed list of questions.

### 3.6 Final Assessment and Report

**Technique:** Deterministic score aggregation using a configurable scoring rubric.

The final result will be calculated from the evaluated answers and agreed section weights. A configurable passing threshold will determine the mock-interview Pass/Fail recommendation.

For example, a threshold of 70/100 could be evaluated during testing, subject to review and approval.

The system will distinguish an incomplete interview from a completed interview that falls below the passing threshold.

**Expected report:**
- Overall score.
- Pass/Fail recommendation.
- Section-wise performance.
- Strengths and improvement areas.
- Question-by-question feedback.
- Recommended technical topics to study.
- Interview completion status.

The final decision will be calculated by application logic rather than allowing the LLM to assign an arbitrary final result.

---

## 4. Proposed Technology Stack

| Component | Proposed technology or technique | Purpose |
|---|---|---|
| Resume extraction | pypdf, python-docx | Extract resume content |
| Structured data | Pydantic | Validate generated information |
| Interview interface | Streamlit | Support interactive interviews |
| Question generation | Configured LLM | Generate relevant interview questions |
| Interview control | Python state machine | Manage question sequence and session state |
| Context retrieval | Existing retrieval capabilities | Ground questions and evaluation in relevant information |
| Answer evaluation | LLM-based rubric evaluation | Assess responses and provide feedback |
| Speech recognition | faster-whisper | Convert spoken answers into text |
| Speech generation | edge-tts or a suitable local TTS engine | Present questions as audio |
| Automated testing | pytest | Validate workflow and scoring logic |
| Persistence | Existing storage approach, extended as needed | Save interview sessions and reports |

---

## 5. Proposed Implementation Phases and Deliverables

| Phase | Planned work | Expected deliverable |
|---|---|---|
| 1 | Technical review and interface design | Approved design and implementation backlog |
| 2 | Resume processing and interview planning | Resume-driven question generation |
| 3 | Interactive text interview | Working question-and-answer workflow |
| 4 | Answer evaluation and adaptive follow-ups | Structured answer scores and contextual questioning |
| 5 | Final scoring and report generation | Interview report with a configurable Pass/Fail recommendation |
| 6 | Voice interaction | Speech-based interview capability |
| 7 | Testing and optimization | Validation report, performance measurements, and documented limitations |

---

## 6. Testing and Quality Validation

Testing will include:
- Resume parsing for supported document formats.
- Relevance of questions to the resume and target job role.
- Correct management of interview states and question progression.
- Evaluation of correct, incomplete, incorrect, and alternative valid answers.
- Consistency of scoring across equivalent responses.
- Correct calculation of the final result.
- Recovery from interrupted sessions and failed model responses.
- Voice transcription quality and correction of recognition errors.
- End-to-end completion from resume upload to final report.

A manually reviewed evaluation set will be used to measure scoring consistency and identify cases where model-generated feedback requires improvement.

---

## 7. Key Design Considerations

- The LLM will generate and evaluate language, while application logic will control the interview workflow and calculate final scores.
- Retrieved reference material will support evaluation but will not be treated as the only acceptable answer.
- The system will explain the reasons behind scores instead of returning only a Pass/Fail result.
- Voice will be an additional interaction mode, not a separate interview implementation.
- Resume content and interview responses will be handled with appropriate privacy, access, and deletion controls.
- The Pass/Fail result will represent mock-interview readiness against the configured rubric, not a guarantee of success in an actual hiring process.

---

## 8. Points for Technical Review and Recommendations

1. **Interview interaction:** Recommend starting with text-only in initial release, followed by voice in Phase 6.
2. **LLM selection:** Retain existing configured model initially with strict Pydantic schema validation.
3. **Evaluation strategy:** Single model with targeted prompts for generation and evaluation; reserve dual models for offline benchmarks.
4. **Scoring criteria:** Pass threshold of 70/100 (Technical: 40%, Practical: 30%, Completeness: 20%, Reasoning: 10%).
5. **Interview scope:** Focus on technical and project experience first; add behavioral questions later.
6. **Deployment requirements:** Hybrid architecture with configurable local/cloud LLM and TTS backends.
7. **Report and history:** Persist sessions to SQLite (`users.db`) with downloadable reports.
