# pyright: reportOptionalMemberAccess=false, reportPrivateImportUsage=false, reportMissingImports=false
# # AI Study Planner & Performance Agent (B.Tech 2nd Year - Term 1 Edition)
# A multi-agent system (Diagnostic, Scheduler, Evaluator) coordinated by a state-machine orchestrator.
# Configured specifically for B.Tech 2nd Year Term 1:
# - Probability and Statistics (10 Modules)
# - DSA C++ (10 Modules)
# - ADBMS (10 Modules)
# - Fundamentals of AI (FAI) (10 Modules)
# - Multiple Choice Questions (MCQ) Format for all Quizzes
# - Optional File Upload Diagnosis (Past Quizzes, Extra Syllabus, Notes)
# - Interactive AI Doubt Solver Chatbot in Quiz Hub

import calendar
import hashlib
import html
import json
import math
import os
import re
from collections.abc import Callable
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any

import gradio as gr
from pydantic import BaseModel, Field

# ==============================================================================
# API KEY CONFIGURATION (GEMINI & OPENAI)
# ==============================================================================
# Paste your Google Gemini API key below (powers the AI Doubt Solver Chatbot & MCQs):
GEMINI_API_KEY = ""   # <-- PASTE YOUR GEMINI API KEY HERE (e.g. "AIzaSy...")

# Or paste your OpenAI API key below (optional alternative):
OPENAI_API_KEY = ""   # <-- Optional OpenAI key (e.g. "sk-proj-...")
# ==============================================================================

if GEMINI_API_KEY.strip():
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY.strip()

if OPENAI_API_KEY.strip():
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY.strip()
else:
    try:
        from google.colab import userdata  # type: ignore
        os.environ.setdefault("GEMINI_API_KEY", userdata.get("GEMINI_API_KEY", ""))
        os.environ.setdefault("OPENAI_API_KEY", userdata.get("OPENAI_API_KEY", ""))
    except Exception:
        pass

SESSION_MIN, BREAK_MIN, LONG_BREAK_MIN = 45, 10, 20
INTERVALS = [1, 3, 7, 14, 30]       # spaced-repetition ladder (days between reviews)
MAX_HORIZON_DAYS = 180

# ==============================================================================
# B.TECH 2ND YEAR TERM 1 CURRICULUM (10 Modules Each)
# ==============================================================================
CURRICULUM: dict[str, dict[str, tuple[float, list[str]]]] = {
    "Probability and Statistics": {
        "Module I: Introduction to Statistics": (0.35, []),
        "Module II: Introduction to Probability": (0.45, ["Module I: Introduction to Statistics"]),
        "Module III: Random Variables": (0.55, ["Module II: Introduction to Probability"]),
        "Module IV: Discrete Probability Distributions": (0.60, ["Module III: Random Variables"]),
        "Module V: Continuous Probability Distributions": (0.65, ["Module III: Random Variables"]),
        "Module VI: Sampling & Estimation": (0.65, ["Module IV: Discrete Probability Distributions", "Module V: Continuous Probability Distributions"]),
        "Module VII: Testing of Hypothesis – I": (0.70, ["Module VI: Sampling & Estimation"]),
        "Module VIII: Testing of Hypothesis – II": (0.75, ["Module VII: Testing of Hypothesis – I"]),
        "Module IX: Correlation": (0.50, ["Module I: Introduction to Statistics"]),
        "Module X: Regression": (0.60, ["Module IX: Correlation"]),
    },
    "DSA C++": {
        "Module I: Introduction to C++ Programming": (0.30, []),
        "Module II: Control Statements": (0.35, ["Module I: Introduction to C++ Programming"]),
        "Module III: Arrays – 1D": (0.45, ["Module II: Control Statements"]),
        "Module IV: Arrays – 2D": (0.50, ["Module III: Arrays – 1D"]),
        "Module V: String Arrays": (0.50, ["Module III: Arrays – 1D"]),
        "Module VI: Structures": (0.55, ["Module II: Control Statements"]),
        "Module VII: Data Structures performance Analysis": (0.65, ["Module III: Arrays – 1D"]),
        "Module VIII: Stacks": (0.65, ["Module III: Arrays – 1D", "Module VII: Data Structures performance Analysis"]),
        "Module IX: Queues": (0.65, ["Module III: Arrays – 1D", "Module VIII: Stacks"]),
        "Module X: STL Fundamentals & Containers": (0.70, ["Module VIII: Stacks", "Module IX: Queues"]),
    },
    "ADBMS": {
        "Module 1: Relational Query Languages & Extended ER Models": (0.45, []),
        "Module 2: Fundamentals of Normalization": (0.55, ["Module 1: Relational Query Languages & Extended ER Models"]),
        "Module 3: Advanced Normalization": (0.65, ["Module 2: Fundamentals of Normalization"]),
        "Module 4: Transactions in DBMS": (0.60, ["Module 1: Relational Query Languages & Extended ER Models"]),
        "Module 5: Concurrency Control": (0.70, ["Module 4: Transactions in DBMS"]),
        "Module 6: Storage and File Structure": (0.60, []),
        "Module 7: Database Recovery Techniques": (0.70, ["Module 4: Transactions in DBMS"]),
        "Module 8: Introduction to NoSQL Databases and MongoDB": (0.50, []),
        "Module 9: Performing CRUD Operations in MongoDB": (0.55, ["Module 8: Introduction to NoSQL Databases and MongoDB"]),
        "Module 10: Advanced Querying and Data Aggregation in MongoDB": (0.65, ["Module 9: Performing CRUD Operations in MongoDB"]),
    },
    "Fundamentals of AI (FAI)": {
        "Module - I: Introduction to Artificial Intelligence": (0.35, []),
        "Module - II: Uninformed Search Strategies": (0.55, ["Module - I: Introduction to Artificial Intelligence"]),
        "Module - III: Informed Search Strategies": (0.65, ["Module - II: Uninformed Search Strategies"]),
        "Module - IV: Optimal Decisions in Games": (0.65, ["Module - III: Informed Search Strategies"]),
        "Module - V: Inferences": (0.60, ["Module - I: Introduction to Artificial Intelligence"]),
        "Module - VI: Knowledge Representation & Reasoning": (0.65, ["Module - V: Inferences"]),
        "Module - VII: State Space Planning": (0.70, ["Module - VI: Knowledge Representation & Reasoning"]),
        "Module - VIII: Uncertainty in AI": (0.70, ["Module - I: Introduction to Artificial Intelligence"]),
        "Module - IX: General Model of Learning Agents": (0.65, ["Module - I: Introduction to Artificial Intelligence"]),
        "Module - X: Applications of AI": (0.45, ["Module - IX: General Model of Learning Agents"]),
    },
}

# ==============================================================================
# DATA MODELS
# ==============================================================================
class Phase(str, Enum):
    ONBOARDING = "ONBOARDING"
    DIAGNOSED = "DIAGNOSED"
    PLANNED = "PLANNED"
    QUIZ_READY = "QUIZ_READY"
    EVALUATED = "EVALUATED"
    ADAPTING = "ADAPTING"

ALLOWED_TRANSITIONS: dict[Phase, set] = {
    Phase.ONBOARDING: {Phase.DIAGNOSED},
    Phase.DIAGNOSED: {Phase.PLANNED},
    Phase.PLANNED: {Phase.ADAPTING, Phase.QUIZ_READY},
    Phase.ADAPTING: {Phase.PLANNED},
    Phase.QUIZ_READY: {Phase.EVALUATED, Phase.ADAPTING, Phase.PLANNED},
    Phase.EVALUATED: {Phase.ADAPTING, Phase.QUIZ_READY, Phase.PLANNED},
}

class SubjectInput(BaseModel):
    name: str
    confidence: int = Field(ge=1, le=5)
    quiz_score: float = Field(ge=0, le=100)
    exam_weight: int = Field(default=3, ge=1, le=5)
    selected_modules: list[str] = Field(default_factory=list)

class StudentProfile(BaseModel):
    name: str = "Student"
    exam_date: date
    target_score: int = Field(default=85, ge=40, le=100)
    hours_per_day: float = Field(default=2.0, gt=0, le=14)
    start_hour: int = Field(default=17, ge=0, le=23)
    subjects: list[SubjectInput]

class TopicState(BaseModel):
    name: str
    subject: str
    difficulty: float
    prereqs: list[str] = Field(default_factory=list)
    weight: float = 1.0                  # exam weight / 3
    mastery: float = 0.5                 # estimated probability of answering correctly (0..1)
    sessions_needed: int = 2
    sessions_done: int = 0
    review_step: int = 0                 # index into INTERVALS
    next_review: date | None = None
    last_studied: date | None = None

    @property
    def learned(self) -> bool:
        return self.sessions_done >= self.sessions_needed

class StudyBlock(BaseModel):
    day_index: int
    day: date
    slot: int
    kind: str                            # learn | review | recall | mock | break | rest
    subject: str = ""
    topic: str = ""
    minutes: int = 0
    start: str = ""
    note: str = ""
    status: str = "planned"              # planned | done | missed

class StudyPlan(BaseModel):
    version: int = 1
    start: date
    exam_date: date
    blocks: list[StudyBlock] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    changelog: list[str] = Field(default_factory=list)
    coverage: float = 0.0
    projected_mastery: float = 0.0

class PerformanceLog(BaseModel):
    ts: str
    topic: str
    subject: str
    score: float
    max_score: float = 10.0
    mastery_before: float
    mastery_after: float
    feedback: str = ""

class TraceStep(BaseModel):
    ts: str
    agent: str
    kind: str
    text: str

class QuizQuestion(BaseModel):
    topic: str
    subject: str
    question: str
    options: list[str]
    correct_option: str
    explanation: str
    source: str = "offline bank"

class GradeResult(BaseModel):
    topic: str
    subject: str
    question: str
    user_answer: str
    correct_option: str
    score: float
    is_correct: bool
    explanation: str

class Adjustment(BaseModel):
    topic: str
    action: str                          # reinforce | space_out | escalate
    score: float
    reason: str

class AppState(BaseModel):
    phase: Phase = Phase.ONBOARDING
    profile: StudentProfile | None = None
    topics: dict[str, TopicState] = Field(default_factory=dict)
    plan: StudyPlan | None = None
    logs: list[PerformanceLog] = Field(default_factory=list)
    trace: list[TraceStep] = Field(default_factory=list)
    quiz: list[QuizQuestion] = Field(default_factory=list)
    quiz_graded: bool = False
    last_grades: list[GradeResult] = Field(default_factory=list)
    cursor: date = Field(default_factory=date.today)
    fatigue: int = 2
    calibration: dict[str, float] = Field(default_factory=dict)
    weak: list[str] = Field(default_factory=list)
    fragile: list[str] = Field(default_factory=list)
    insight: str = ""
    baseline_mastery: float = 0.0
    uploaded_doc_analysis: dict[str, Any] = Field(default_factory=dict)

def add_trace(state: AppState, agent: str, kind: str, text: str) -> None:
    state.trace.append(TraceStep(ts=datetime.now().strftime("%H:%M:%S"), agent=agent, kind=kind, text=text))

def clamp(x: float, lo: float = 0.02, hi: float = 0.98) -> float:
    return max(lo, min(hi, x))

def priority(t: TopicState) -> float:
    return t.weight * (1.0 - t.mastery) * (0.5 + t.difficulty)

def wmean(topics) -> float:
    ts = list(topics)
    tw = sum(t.weight for t in ts) or 1.0
    return sum(t.weight * t.mastery for t in ts) / tw

def apply_session(t: TopicState, kind: str, d: date) -> None:
    t.last_studied = d
    if kind == "learn":
        t.sessions_done += 1
        t.mastery = clamp(t.mastery + 0.10, hi=0.95)
        if t.learned:
            t.review_step = 0
            t.next_review = d + timedelta(days=INTERVALS[0])
    elif kind == "review":
        t.review_step = min(t.review_step + 1, len(INTERVALS) - 1)
        t.mastery = clamp(t.mastery + 0.04, hi=0.97)
        t.next_review = d + timedelta(days=INTERVALS[t.review_step])
    elif kind == "recall":
        t.mastery = clamp(t.mastery + 0.03, hi=0.97)

# ==============================================================================
# LLM CLIENT (Reads OPENAI_API_KEY directly from code or environment)
# ==============================================================================
class LLMClient:
    MODEL = os.environ.get("STUDY_AGENT_MODEL", "gpt-4o-mini")

    def __init__(self) -> None:
        self._client: Any = None
        self.failures = 0
        self.last_error = ""
        self.refresh()

    def refresh(self, api_key: str = "") -> None:
        key = (api_key or "").strip() or OPENAI_API_KEY.strip() or os.environ.get("OPENAI_API_KEY", "").strip()
        self._client, self.failures = None, 0
        self.last_error = ""
        if key:
            os.environ["OPENAI_API_KEY"] = key
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=key, timeout=25)
            except Exception as exc:
                self.last_error = f"OpenAI client error: {exc}"[:180]

    @property
    def live(self) -> bool:
        if self._client is None:
            self.refresh()
        return self._client is not None

    def json_chat(self, system: str, user: str, temperature: float = 0.8) -> dict | None:
        if not self.live:
            return None
        try:
            r = self._client.chat.completions.create(
                model=self.MODEL,
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}]
            )
            self.failures = 0
            self.last_error = ""
            raw_text = r.choices[0].message.content or ""
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
            raw_text = re.sub(r"\s*```$", "", raw_text.strip(), flags=re.MULTILINE)
            return json.loads(raw_text)
        except Exception as exc:
            err_msg = str(exc)
            if "invalidated" in err_msg.lower() or "invalid api key" in err_msg.lower() or "401" in err_msg:
                self.last_error = "OpenAI Error 401: API key has been invalidated or is invalid. Please supply a valid key from platform.openai.com."
            elif "quota" in err_msg.lower() or "insufficient_quota" in err_msg.lower() or "429" in err_msg:
                self.last_error = "OpenAI Error 429: Account quota exceeded. Check your OpenAI billing or usage limits."
            else:
                self.last_error = f"OpenAI Error: {err_msg[:140]}"
            self.failures += 1
            return None

LLM = LLMClient()

# ==============================================================================
# GOOGLE GEMINI CLIENT (Powers the AI Doubt Solver Chatbot & Dynamic MCQs)
# ==============================================================================
class GeminiClient:
    MODEL = os.environ.get("STUDY_AGENT_GEMINI_MODEL", "gemini-2.5-flash")

    def __init__(self) -> None:
        self._client: Any = None
        self.last_error = ""
        self.refresh()

    def refresh(self, api_key: str = "") -> None:
        key = (api_key or "").strip() or GEMINI_API_KEY.strip() or os.environ.get("GEMINI_API_KEY", "").strip()
        self._client = None
        self.last_error = ""
        if key:
            os.environ["GEMINI_API_KEY"] = key
            try:
                from google import genai  # type: ignore
                self._client = genai.Client(api_key=key)
            except Exception as exc:
                self.last_error = f"Gemini initialization error: {exc}"

    @property
    def live(self) -> bool:
        if self._client is None:
            self.refresh()
        return self._client is not None

    def generate(self, prompt: str, system_instruction: str = "") -> str | None:
        if not self.live:
            return None
        models_to_try = [self.MODEL, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        for m in models_to_try:
            try:
                config = {}
                if system_instruction:
                    config["system_instruction"] = system_instruction
                resp = self._client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=config if config else None
                )
                if resp and resp.text:
                    self.last_error = ""
                    return resp.text
            except Exception as exc:
                self.last_error = str(exc)
                continue
        return None

    def json_chat(self, system: str, user: str) -> dict | None:
        if not self.live:
            return None
        prompt = (
            f"Instructions: {system}\n\n"
            f"User Request: {user}\n\n"
            f"Return ONLY a valid JSON object matching the requested schema. Do NOT wrap in markdown code fences."
        )
        raw = self.generate(prompt)
        if not raw:
            return None
        try:
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
            return json.loads(cleaned)
        except Exception:
            return None

GEMINI = GeminiClient()

# ==============================================================================
# DOCUMENT EXTRACTION & DIAGNOSTIC ANALYZER
# ==============================================================================
def extract_file_text(file_obj: Any) -> tuple[str, str]:
    if not file_obj:
        return "", ""
    path = file_obj if isinstance(file_obj, str) else getattr(file_obj, "name", str(file_obj))
    if not path or not os.path.exists(path):
        return "", ""
    fname = os.path.basename(path)
    ext = os.path.splitext(path)[1].lower()
    text = ""
    try:
        if ext == ".pdf":
            try:
                import pypdf  # type: ignore
                reader = pypdf.PdfReader(path)
                text = "\n".join(p.extract_text() or "" for p in reader.pages)
            except Exception:
                pass
        if not text:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
    except Exception as exc:
        text = f"[Error reading file: {exc}]"
    return fname, text

def analyze_uploaded_document(file_name: str, file_text: str, llm: LLMClient) -> dict[str, Any]:
    if not file_text or not file_text.strip():
        return {}

    snippet = file_text[:4500]

    if llm.live:
        prompt = (
            f"You are an academic diagnostic coach for B.Tech 2nd Year Term 1 students. "
            f"Analyze the uploaded document (Filename: '{file_name}'). "
            f"Document snippet:\n{snippet}\n\n"
            f"Return ONLY valid JSON matching this schema:\n"
            f'{{"summary": "1-2 sentence overview", '
            f'"detected_topics": ["list of subjects or modules identified"], '
            f'"extra_syllabus": ["topics found that go beyond standard 10 modules"], '
            f'"attempted_scores": [{{"topic": "str", "score": float_0_to_10}}], '
            f'"weak_areas": ["topics or concepts the student struggled with"], '
            f'"recommendation": "clear, actionable advice for their study plan"}}'
        )
        data = llm.json_chat("You are an expert academic evaluator. Output valid JSON only.", prompt)
        if data and isinstance(data, dict):
            data["filename"] = file_name
            return data

    t_lower = file_text.lower()
    detected_topics: list[str] = []
    weak_areas: list[str] = []
    extra_syllabus: list[str] = []
    attempted_scores: list[dict[str, Any]] = []

    for sname, mods in CURRICULUM.items():
        for mname in mods:
            core_words = [w for w in re.sub(r'[^a-zA-Z0-9\s]', ' ', mname).split() if len(w) > 3 and w.lower() not in ("module", "introduction", "fundamentals")]
            if any(w.lower() in t_lower for w in core_words):
                detected_topics.append(mname)

    matches = re.findall(r'(?:score|marks|grade|result|quiz)[^\d]{1,15}(\d{1,3})(?:/100|%|/10)?', t_lower)
    for m in matches[:4]:
        try:
            val = float(m)
            if val <= 10:
                val = val * 10
            top = detected_topics[0] if detected_topics else "Diagnostic Quiz"
            attempted_scores.append({"topic": top, "score": round(val / 10, 1)})
            if val < 60:
                weak_areas.append(f"{top} ({val:.0f}% attempt)")
        except Exception:
            pass

    potential_extras = [
        "Graph Algorithms (Dijkstra/Floyd)", "Dynamic Programming", "Red-Black Tree Deletion",
        "B-Tree Concurrency & Latches", "Distributed Transactions (2PC/Saga)", "Reinforcement Learning & Q-Learning",
        "Deep Neural Networks & Backprop", "Analysis of Variance (ANOVA)", "Non-Parametric Tests (Mann-Whitney)",
        "Query Optimization & Cost Estimation", "NoSQL Sharding & Replication"
    ]
    for ext_topic in potential_extras:
        kw = ext_topic.split()[0].lower()
        if kw in t_lower:
            extra_syllabus.append(ext_topic)

    summary = f"Processed '{file_name}' ({len(file_text.split())} words)."
    if attempted_scores:
        summary += f" Detected past quiz/test scores with an average of {sum(s['score'] for s in attempted_scores)/len(attempted_scores):.1f}/10."
    if extra_syllabus:
        summary += f" Identified {len(extra_syllabus)} advanced/supplementary topics."
    if not attempted_scores and not extra_syllabus:
        summary += f" Matched content against {len(detected_topics)} curriculum modules."

    rec = "We have factored this document into your diagnostic profile. "
    if weak_areas:
        rec += f"Prioritize early revision on: {', '.join(weak_areas[:2])}."
    elif extra_syllabus:
        rec += f"Focus first on your core 10 modules before tackling supplementary topics ({', '.join(extra_syllabus[:2])})."
    else:
        rec += "Your syllabus alignment looks solid; proceed with the spaced-repetition plan."

    return {
        "filename": file_name,
        "summary": summary,
        "detected_topics": list(dict.fromkeys(detected_topics))[:8],
        "extra_syllabus": extra_syllabus,
        "attempted_scores": attempted_scores,
        "weak_areas": weak_areas or (detected_topics[:2] if detected_topics else []),
        "recommendation": rec
    }

# ==============================================================================
# AGENTS ARCHITECTURE (Diagnostic, Scheduler, Evaluator)
# ==============================================================================
class ReActAgent:
    name = "Agent"
    max_steps = 10

    def __init__(self, state: AppState, llm: LLMClient) -> None:
        self.state, self.llm = state, llm
        self.tools: dict[str, tuple[Callable[..., str], str]] = {}

    def log(self, kind: str, text: str) -> None:
        add_trace(self.state, self.name, kind, text)

    def policy(self, mem: dict[str, Any]) -> tuple[str, str, dict[str, Any]] | None:
        raise NotImplementedError

    def loop(self, mem: dict[str, Any]) -> dict[str, Any]:
        self.log("STATE", "Toolbox: " + ", ".join(self.tools))
        for step in range(1, self.max_steps + 1):
            decision = self.policy(mem)
            if decision is None:
                self.log("THOUGHT", "All sub-goals satisfied, so I finish.")
                return mem
            thought, tool, args = decision
            argstr = ", ".join(f"{k}={v!r}" for k, v in args.items())
            self.log("THOUGHT", f"(step {step}) {thought}")
            self.log("ACTION", f"{tool}({argstr})")
            try:
                obs = self.tools[tool][0](mem, **args)
            except Exception as exc:
                self.log("OBSERVATION", f"Tool error {exc!r}; aborting this loop safely.")
                mem["error"] = str(exc)
                return mem
            self.log("OBSERVATION", obs)
        self.log("THOUGHT", "Step budget exhausted; stopping as a safety measure.")
        return mem


class DiagnosticAgent(ReActAgent):
    name = "Diagnostic Agent"

    def __init__(self, state: AppState, llm: LLMClient) -> None:
        super().__init__(state, llm)
        self.tools = {
            "compute_skill_matrix": (self.t_matrix, "Blend quiz score, confidence and uploaded file evidence into per-topic mastery"),
            "detect_calibration_gap": (self.t_calibration, "Compare self-confidence with measured score"),
            "apply_calibration_penalty": (self.t_penalty, "Discount mastery where the student is overconfident"),
            "propagate_prerequisites": (self.t_propagate, "Walk the knowledge graph and flag fragile foundations"),
            "rank_weak_topics": (self.t_rank, "Rank topics by weighted difficulty"),
            "generate_insight": (self.t_insight, "Write a short diagnostic summary (LLM or template)"),
        }

    def run(self) -> None:
        self.log("STATE", f"Goal: turn raw inputs into a ranked skill matrix (engine: {'LLM' if self.llm.live else 'rules'}).")
        self.loop({})

    def policy(self, mem):
        if "matrix" not in mem:
            return ("Build topic-level model for selected modules from subject scores, confidence and uploaded document.", "compute_skill_matrix", {})
        if "calibration" not in mem:
            return ("Compare confidence with the measured quiz score.", "detect_calibration_gap", {})
        if mem.get("overconfident") and not mem.get("penalised"):
            return (f"Overconfidence in {mem['overconfident']}: discount mastery.", "apply_calibration_penalty", {})
        if "propagated" not in mem:
            return ("Propagate mastery through prerequisites in the knowledge graph.", "propagate_prerequisites", {})
        if "weak" not in mem:
            return ("Rank topics by weight x gap x difficulty.", "rank_weak_topics", {})
        if "insight" not in mem:
            return ("Summarise findings for the student and the scheduler.", "generate_insight", {})
        return None

    def t_matrix(self, mem):
        st, prof = self.state, self.state.profile
        st.topics.clear()
        
        doc = st.uploaded_doc_analysis
        doc_weak = [str(w).lower() for w in doc.get("weak_areas", [])]
        
        for s in prof.subjects:
            base = 0.6 * s.quiz_score / 100 + 0.4 * (s.confidence - 1) / 4
            all_mods = CURRICULUM.get(s.name, {})
            target_mods = [m for m in (s.selected_modules or list(all_mods.keys())) if m in all_mods]
            for tname in target_mods:
                diff, pre = all_mods[tname]
                filtered_pre = [p for p in pre if p in target_mods]
                jitter = (int(hashlib.md5(tname.encode()).hexdigest()[:4], 16) / 65535 - 0.5) * 0.24
                m = clamp(base + jitter - 0.15 * (diff - 0.5), 0.05, 0.95)
                
                if any(w in tname.lower() for w in doc_weak):
                    m = clamp(m - 0.10, 0.03, 0.90)
                    
                need = max(1, round(1 + 3 * diff * (1 - m)))
                st.topics[tname] = TopicState(
                    name=tname, subject=s.name, difficulty=diff, prereqs=filtered_pre,
                    weight=s.exam_weight / 3, mastery=m, sessions_needed=need
                )
        mem["matrix"] = True
        return f"Skill matrix built: {len(st.topics)} selected modules across {len(prof.subjects)} subjects, mean mastery {wmean(st.topics.values()):.0%}."

    def t_calibration(self, mem):
        st = self.state
        st.calibration = {s.name: round(s.confidence / 5 - s.quiz_score / 100, 2) for s in st.profile.subjects}
        mem["calibration"] = True
        mem["overconfident"] = [k for k, v in st.calibration.items() if v > 0.25]
        under = [k for k, v in st.calibration.items() if v < -0.25]
        return f"Calibration gaps: {st.calibration}. Overconfident: {mem['overconfident'] or 'none'}. Underconfident: {under or 'none'}."

    def t_penalty(self, mem):
        st, n = self.state, 0
        for t in st.topics.values():
            if t.subject in mem["overconfident"]:
                t.mastery = clamp(t.mastery - 0.06, 0.03, 0.95)
                n += 1
        mem["penalised"] = True
        return f"Lowered mastery by 6 points on {n} topics where self-rating exceeded measured skill."

    def t_propagate(self, mem):
        st, fragile = self.state, []
        for t in st.topics.values():
            if t.prereqs:
                valid_pre = [p for p in t.prereqs if p in st.topics]
                if valid_pre:
                    pm = sum(st.topics[p].mastery for p in valid_pre) / len(valid_pre)
                    t.mastery = clamp(0.75 * t.mastery + 0.25 * pm, 0.03, 0.95)
                    if pm < 0.4 and t.mastery > pm + 0.25:
                        t.mastery = clamp(t.mastery - 0.08, 0.03, 0.95)
                        fragile.append(f"{t.name} (built on weak {', '.join(valid_pre)})")
        known = 0
        for t in st.topics.values():
            t.sessions_needed = max(1, round(1 + 3 * t.difficulty * (1 - t.mastery)))
            if t.mastery >= 0.8:
                t.sessions_done, t.review_step = t.sessions_needed, 2
                t.next_review = st.cursor + timedelta(days=INTERVALS[2])
                known += 1
        st.fragile, mem["propagated"] = fragile, True
        return f"Prerequisite propagation done. Fragile foundations: {len(fragile)}. Already-mastered topics: {known}."

    def t_rank(self, mem):
        st = self.state
        ranked = sorted(st.topics.values(), key=priority, reverse=True)
        st.weak = [t.name for t in ranked[:5]]
        st.baseline_mastery = wmean(st.topics.values())
        mem["weak"] = st.weak
        return "Weakest topics: " + "; ".join(f"{t.name} ({t.mastery:.0%}, need={priority(t):.2f})" for t in ranked[:5])

    def t_insight(self, mem):
        st, prof = self.state, self.state.profile
        doc = st.uploaded_doc_analysis
        facts = {
            "weak_topics": st.weak, "fragile": st.fragile, "calibration": st.calibration,
            "baseline_pct": round(st.baseline_mastery * 100), "target": prof.target_score,
            "days_left": (prof.exam_date - st.cursor).days, "hours_per_day": prof.hours_per_day,
            "uploaded_doc": doc.get("summary", "") if doc else ""
        }
        data = self.llm.json_chat('You are an expert study coach for B.Tech students. Reply ONLY with JSON {"insight": "<=70 words, concrete, encouraging"}.', json.dumps(facts))
        if data and isinstance(data.get("insight"), str):
            st.insight = data["insight"]
            src = "LLM"
        else:
            over = [k for k, v in st.calibration.items() if v > 0.25]
            gap = prof.target_score - round(st.baseline_mastery * 100)
            doc_note = f" Your uploaded file ({doc.get('filename', 'doc')}) was factored into prioritizing these modules." if doc else ""
            st.insight = (f"Focus first on your top priority modules: {', '.join(st.weak[:3])}.{doc_note} "
                          + (f"Confidence in {', '.join(over)} runs ahead of diagnostic quiz score, so review fundamental concepts early. " if over else "")
                          + (f"You are about {gap} points away from your {prof.target_score}% goal, which is fully achievable with regular spaced review." if gap > 0
                             else "You are already near your target; this plan will secure high retention."))
            src = "rule template"
        mem["insight"] = True
        return f"Insight written via {src}."


class SchedulerAgent(ReActAgent):
    name = "Scheduler Agent"
    max_steps = 16

    def __init__(self, state: AppState, llm: LLMClient) -> None:
        super().__init__(state, llm)
        self.tools = {
            "apply_forgetting_decay": (self.t_decay, "Mark missed blocks, advance the calendar, apply forgetting"),
            "adjust_for_fatigue": (self.t_fatigue, "Convert fatigue into effective daily capacity"),
            "apply_performance_adjustments": (self.t_perf, "Consume Evaluator feedback: reset or lengthen review intervals"),
            "estimate_capacity": (self.t_capacity, "Count study sessions available before the exam"),
            "spaced_repetition_allocator": (self.t_allocate, "Day-by-day allocation: due reviews, new learning, recall, mocks"),
            "validate_plan": (self.t_validate, "Check coverage and projected mastery"),
            "compress_learning": (self.t_compress, "Trade depth for coverage when the plan is infeasible"),
        }

    def run(self, trigger: str, **params: Any) -> dict[str, Any]:
        st, prof = self.state, self.state.profile
        mem: dict[str, Any] = {"trigger": trigger, "hours": prof.hours_per_day, "fatigue_level": st.fatigue, "notes": [], **params}
        self.log("STATE", f"Replan trigger = '{trigger}'. Cursor {st.cursor:%d %b}, exam {prof.exam_date:%d %b}, {prof.hours_per_day:g} h/day, fatigue {st.fatigue}/5.")
        self.loop(mem)
        plan = st.plan
        if plan:
            if trigger != "initial":
                plan.version += 1
            plan.changelog.append(f"v{plan.version} ({trigger}): " + "; ".join(mem["notes"][-4:]))
        return mem

    def policy(self, mem):
        if mem.get("missed_days", 0) > 0 and "decayed" not in mem:
            return (f"The student missed {mem['missed_days']} day(s); reschedule and apply forgetting decay.", "apply_forgetting_decay", {})
        if "fatigue" not in mem:
            return (f"Fatigue is {mem['fatigue_level']}/5; size daily workload accordingly.", "adjust_for_fatigue", {})
        if mem["trigger"] == "performance" and mem.get("adjustments") and "adjusted" not in mem:
            return (f"Update spaced-repetition state using {len(mem['adjustments'])} feedback adjustment(s).", "apply_performance_adjustments", {})
        if "capacity" not in mem:
            return ("Estimate total available sessions before the exam.", "estimate_capacity", {})
        if "allocated" not in mem:
            lvl = mem.get("compressed", 0)
            return ("Allocate sessions day by day with subject interleaving." + (f" (Compression lvl {lvl})" if lvl else ""), "spaced_repetition_allocator", {})
        if "validated" not in mem:
            return ("Verify coverage and projected target mastery.", "validate_plan", {})
        if not mem["valid"] and mem.get("compressed", 0) < 2:
            return ("Plan exceeds capacity; compress learning depth slightly to preserve full topic coverage.", "compress_learning", {})
        return None

    def t_decay(self, mem):
        st, n = self.state, mem["missed_days"]
        start, end = st.cursor, st.cursor + timedelta(days=n)
        marked, topics = 0, set()
        if st.plan:
            for b in st.plan.blocks:
                if start <= b.day < end and b.status == "planned":
                    b.status = "missed"
                    if b.kind not in ("break", "rest"):
                        marked += 1
                        topics.add(b.topic)
        st.cursor = end
        for t in st.topics.values():
            if t.learned and t.last_studied:
                t.mastery = clamp(t.mastery * (1 - 0.01 * n), 0.03)
            if t.next_review and t.next_review < st.cursor:
                t.mastery = clamp(t.mastery - min(0.15, 0.02 * (st.cursor - t.next_review).days), 0.03)
        mem["decayed"] = True
        msg = f"Marked {marked} block(s) missed ({len(topics)} topics), cursor moved to {st.cursor:%a %d %b}."
        mem["notes"].append(f"{n} missed day(s), {marked} blocks rescheduled")
        return msg

    def t_fatigue(self, mem):
        f = int(mem["fatigue_level"])
        mult = {1: 1.0, 2: 1.0, 3: 0.9, 4: 0.75, 5: 0.6}[f]
        mem["hours_eff"] = mem["hours"] * mult
        mem["rest_days"] = {0} if f == 5 else set()
        mem["fatigue"] = True
        if mult < 1:
            mem["notes"].append(f"fatigue {f}/5 scaled capacity to {mult:.0%}" + (", recovery day added" if f == 5 else ""))
        return f"Effective hours/day = {mem['hours']:g} x {mult:.2f} = {mem['hours_eff']:.2f}."

    def t_perf(self, mem):
        st, msgs = self.state, []
        for a in mem["adjustments"]:
            t = st.topics.get(a["topic"])
            if not t:
                continue
            if a["action"] in ("reinforce", "escalate"):
                if t.learned:
                    t.review_step, t.next_review = 0, st.cursor + timedelta(days=1)
                    if a["action"] == "escalate" or a["score"] < 4:
                        t.sessions_done = max(0, t.sessions_needed - 1)
                        msgs.append(f"{t.name}: re-learn session scheduled")
                    else:
                        msgs.append(f"{t.name}: review pulled forward")
                else:
                    msgs.append(f"{t.name}: lower score raised learning priority")
            elif a["action"] == "space_out" and t.learned:
                t.review_step = min(t.review_step + 1, len(INTERVALS) - 1)
                t.next_review = st.cursor + timedelta(days=INTERVALS[t.review_step])
                msgs.append(f"{t.name}: interval lengthened, next review {t.next_review:%d %b}")
        mem["adjusted"] = True
        mem["notes"].append(f"{len(msgs)} performance-driven adjustment(s)")
        return " | ".join(msgs) or "No applicable adjustments."

    def t_capacity(self, mem):
        st, prof = self.state, self.state.profile
        days = max(0, (prof.exam_date - st.cursor).days)
        base = max(1, int(mem["hours_eff"] * 60 // (SESSION_MIN + BREAK_MIN)))
        spd = [0 if i in mem["rest_days"] else base for i in range(days)]
        if spd:
            spd[-1] = min(spd[-1], 2)
        mem["sessions_by_day"] = spd
        learn_demand = sum(max(0, t.sessions_needed - t.sessions_done) for t in st.topics.values() if not t.learned)
        mem["capacity"] = sum(spd)
        return f"{days} day(s) x {base} session(s) = {sum(spd)} sessions available; new learning demand = {learn_demand} sessions."

    @staticmethod
    def _pick(pool: list[TopicState], k: int, used: dict[str, int], today: set, d: date, review: bool = False, momentum: bool = False) -> list[TopicState]:
        out: list[TopicState] = []
        for _ in range(k):
            cands = [t for t in pool if t.name not in today]
            if not cands:
                break
            def key(t: TopicState) -> float:
                bonus = 0.05 * max(0, (d - t.next_review).days) if (review and t.next_review) else 0.0
                bonus += 0.3 if (momentum and t.sessions_done > 0) else 0.0
                return priority(t) + bonus - 0.35 * used.get(t.subject, 0)
            t = max(cands, key=key)
            out.append(t)
            today.add(t.name)
            used[t.subject] = used.get(t.subject, 0) + 1
        return out

    def t_allocate(self, mem):
        st, prof = self.state, self.state.profile
        sims = {k: v.model_copy(deep=True) for k, v in st.topics.items()}
        comp = mem.get("compressed", 0)
        if comp:
            for t in sims.values():
                if not t.learned:
                    t.sessions_needed = max(t.sessions_done + 1, t.sessions_needed - comp)
        start, days, spd = st.cursor, len(mem["sessions_by_day"]), mem["sessions_by_day"]
        base_day = st.plan.start if st.plan else start
        unlearned0 = [t.name for t in sims.values() if not t.learned]
        learned_on: dict[str, date] = {}
        blocks: list[StudyBlock] = []
        order = {"learn": 0, "review": 1, "recall": 2, "mock": 3}
        fmt = lambda m: f"{(m // 60) % 24:02d}:{m % 60:02d}"

        for di in range(days):
            d = start + timedelta(days=di)
            n = spd[di]
            day_no = (d - base_day).days + 1
            if n == 0:
                blocks.append(StudyBlock(day_index=day_no, day=d, slot=1, kind="rest", note="Recovery day: fatigue protection"))
                continue
            final_phase = (days - di) <= 2
            used: dict[str, int] = {}
            today: set = set()
            learned_start = {t.name for t in sims.values() if t.learned}
            picks: list[tuple[str, str, str, str]] = []

            if not final_phase and (di + 1) % 7 == 0 and n >= 2:
                subj_mean: dict[str, list[float]] = {}
                for t in sims.values():
                    subj_mean.setdefault(t.subject, []).append(t.mastery)
                if subj_mean:
                    weakest = min(subj_mean, key=lambda s: sum(subj_mean[s]) / len(subj_mean[s]))
                    picks.append(("mock", weakest, f"Mixed test: {weakest}", "Timed subject test. Check in Quiz Hub."))

            slots = n - len(picks)
            if final_phase:
                rpool, quota = [t for t in sims.values() if t.learned], slots
            else:
                rpool = [t for t in sims.values() if t.learned and t.next_review and t.next_review <= d]
                quota = min(len(rpool), max(1, math.ceil(slots / 2))) if rpool else 0
            for t in self._pick(rpool, quota, used, today, d, review=True):
                note = ("Final revision, weakest first." if final_phase else f"Spaced review box {t.review_step + 1}/{len(INTERVALS)}: active retrieval.")
                picks.append(("review", t.subject, t.name, note))
                apply_session(t, "review", d)
            slots = n - len(picks)

            learn_picks: list[tuple[str, str, str, str, float]] = []
            while slots > 0 and not final_phase:
                unl = [t for t in sims.values() if not t.learned and t.name not in today]
                t1 = [t for t in unl if all(p in learned_start for p in t.prereqs if p in sims)]
                t2 = [t for t in unl if all((p not in sims or sims[p].learned or sims[p].sessions_done > 0) for p in t.prereqs)]
                pool = t1 or t2 or unl
                if not pool:
                    break
                t = self._pick(pool, 1, used, today, d, momentum=True)[0]
                apply_session(t, "learn", d)
                note = f"Learn session {t.sessions_done}/{t.sessions_needed}" + (" (module complete, enters review cycle)" if t.learned else "")
                if t.learned:
                    learned_on[t.name] = d
                learn_picks.append(("learn", t.subject, t.name, note, t.difficulty))
                slots -= 1
            learn_picks.sort(key=lambda p: -p[4])
            picks = [p[:4] for p in learn_picks] + picks

            while slots > 0:
                rec_pool = [t for t in sims.values() if t.learned and t.name not in today]
                if not rec_pool:
                    break
                t = self._pick(rec_pool, 1, used, today, d)[0]
                picks.append(("recall", t.subject, t.name, "Active recall & quick conceptual check."))
                apply_session(t, "recall", d)
                slots -= 1

            picks.sort(key=lambda p: order[p[0]])
            if not picks:
                blocks.append(StudyBlock(day_index=day_no, day=d, slot=1, kind="rest", note="Ahead of schedule; review notes lightly."))
                continue

            clock = prof.start_hour * 60
            for si, (kind, subj, topic, note) in enumerate(picks):
                blocks.append(StudyBlock(day_index=day_no, day=d, slot=si + 1, kind=kind, subject=subj, topic=topic,
                                         minutes=SESSION_MIN, start=fmt(clock), note=note))
                clock += SESSION_MIN
                if si < len(picks) - 1:
                    brk = LONG_BREAK_MIN if (si + 1) % 3 == 0 else BREAK_MIN
                    blocks.append(StudyBlock(day_index=day_no, day=d, slot=si + 1, kind="break", minutes=brk, start=fmt(clock), note="Break (water / walk)"))
                    clock += brk

        ms: list[str] = []
        if unlearned0:
            dates = sorted(learned_on.values())
            for frac in (0.25, 0.5, 0.75, 1.0):
                k = math.ceil(len(unlearned0) * frac)
                if k <= len(dates):
                    ms.append(f"{dates[k - 1]:%a %d %b}: {k} of {len(unlearned0)} modules mastered ({int(frac * 100)}%)")
                elif frac == 1.0:
                    ms.append("Notice: Some modules require additional daily hours before the exam date.")
        mock_days = sorted({b.day for b in blocks if b.kind == "mock"})
        if mock_days:
            ms.append("Mock tests: " + ", ".join(f"{m:%d %b}" for m in mock_days[:6]))
        proj = wmean(sims.values()) if sims else 0.0
        ms.append(f"{prof.exam_date:%a %d %b}: Exam day. Projected mastery {proj:.0%} (Target: {prof.target_score}%).")

        history = [b for b in (st.plan.blocks if st.plan else []) if b.day < st.cursor]
        if st.plan is None:
            st.plan = StudyPlan(start=start, exam_date=prof.exam_date)
        st.plan.blocks = history + blocks
        st.plan.milestones = ms
        st.plan.coverage = sum(1 for t in sims.values() if t.learned) / max(1, len(sims))
        st.plan.projected_mastery = proj
        mem.update(allocated=True, sim=sims, projected=proj)
        n_sessions = sum(1 for b in blocks if b.kind not in ("break", "rest"))
        return f"Allocated {n_sessions} study sessions over {days} days. Coverage {st.plan.coverage:.0%}, projected mastery {proj:.0%}."

    def t_validate(self, mem):
        st, prof, plan = self.state, self.state.profile, self.state.plan
        unl = [t.name for t in mem["sim"].values() if not t.learned]
        proj, target = mem["projected"], prof.target_score / 100
        warns: list[str] = []
        if unl:
            warns.append(f"{len(unl)} module(s) cannot be fully completed before exam: {', '.join(unl[:3])}{'...' if len(unl) > 3 else ''}.")
        if proj < target:
            extra = round(max(0.25, (target - proj) * prof.hours_per_day * 1.5) * 4) / 4
            warns.append(f"Projected mastery ({proj:.0%}) is below your target ({target:.0%}). Increasing daily study by ~{extra:g} h/day will bridge this gap.")
        plan.warnings = warns
        mem["valid"], mem["validated"] = not unl, True
        return ("Plan valid: all selected modules covered." if not unl else f"Plan adjusted with {len(warns)} warning(s).")

    def t_compress(self, mem):
        mem["compressed"] = mem.get("compressed", 0) + 1
        mem.pop("allocated", None)
        mem.pop("validated", None)
        mem["notes"].append(f"compressed learning by {mem['compressed']} session(s) per module")
        return f"Compression level {mem['compressed']}: each module gets fewer sessions to fit the exam timeline."


def generate_procedural_syllabus_mcq(t: TopicState) -> QuizQuestion:
    """Procedurally synthesizes diverse, non-repeating MCQs from syllabus concepts when offline or without an active API key."""
    import random
    clean_name = t.name.split(":")[-1].strip() if ":" in t.name else t.name
    subject = t.subject
    q_type = random.randint(1, 5)

    if "Probability" in subject or "Statistics" in subject:
        if q_type == 1:
            question = f"In Probability and Statistics, what is the fundamental mathematical condition required for '{clean_name}'?"
            options = [
                f"A) Satisfying non-negativity and total probability summation/integration equaling 1 across the sample space of {clean_name}.",
                f"B) Having a continuous uniform density regardless of whether the variable is discrete or continuous in {clean_name}.",
                f"C) Requiring the median and arithmetic mean to always be identical for {clean_name}.",
                f"D) Ensuring that conditional probability P(A|B) is always strictly greater than joint probability P(A ∩ B)."
            ]
            correct = options[0]
            explanation = f"For any probability distribution or random variable concept in '{clean_name}', total probability over the sample space must strictly equal 1 with non-negative density/mass values."
        elif q_type == 2:
            question = f"When evaluating parameter estimations and variance in '{clean_name}', which property holds true?"
            options = [
                f"A) An estimator is unbiased if its expected value equals the true population parameter of {clean_name}.",
                f"B) Sample variance always overestimates population variance when divided by (n - 1) in {clean_name}.",
                f"C) Variance can be negative for distributions with high negative skewness in {clean_name}.",
                f"D) The standard error increases as the sample size n increases."
            ]
            correct = options[0]
            explanation = f"In statistical estimation for '{clean_name}', unbiasedness requires E[θ^] = θ, and sample variance uses (n - 1) degrees of freedom to correct Bessel's bias."
        elif q_type == 3:
            question = f"Which common analytical pitfall must be avoided when modeling real-world data with '{clean_name}'?"
            options = [
                f"A) Confusing correlation with causation and assuming linearity without validating residual distribution in {clean_name}.",
                f"B) Assuming standard deviation is measured in squared units of the original random variable.",
                f"C) Applying the Central Limit Theorem to sample means when sample size n exceeds 30.",
                f"D) Using cumulative distribution functions (CDF) whose limits span from 0 to 1."
            ]
            correct = options[0]
            explanation = f"In '{clean_name}', correlation measures only the strength of linear association and does not imply direct causal dependency."
        elif q_type == 4:
            question = f"In hypothesis testing and sampling theory relevant to '{clean_name}', what is a Type I error (α)?"
            options = [
                f"A) Rejecting the null hypothesis (H0) when it is actually true.",
                f"B) Failing to reject the null hypothesis (H0) when it is false.",
                f"C) Calculating a p-value strictly greater than the chosen significance level.",
                f"D) Setting the power of the test (1 - β) equal to zero."
            ]
            correct = options[0]
            explanation = f"A Type I error (α) represents a false positive — rejecting a true null hypothesis in hypothesis testing."
        else:
            question = f"How does '{clean_name}' contribute to predictive modeling and probabilistic inference in engineering?"
            options = [
                f"A) By characterizing probability density functions and quantifying uncertainty bounds for {clean_name}.",
                f"B) By converting stochastic processes into deterministic linear equations with zero variance.",
                f"C) By guaranteeing that all random outcomes occur with identical uniform probability.",
                f"D) By eliminating the need for independent and identically distributed (i.i.d.) assumptions."
            ]
            correct = options[0]
            explanation = f"'{clean_name}' allows engineers to formalize uncertainty, calculate expected loss, and establish confidence bounds."

    elif "DSA" in subject or "C++" in subject:
        if q_type == 1:
            question = f"In C++ Data Structures and Algorithms, what is the primary asymptotic complexity consideration for '{clean_name}'?"
            options = [
                f"A) Analyzing average vs worst-case Big-O bounds and memory locality for access operations in {clean_name}.",
                f"B) Assuming all insertions and deletions execute in O(1) time irrespective of pointer rebinding.",
                f"C) That memory overhead is always zero when using dynamic heap allocation in C++.",
                f"D) That recursive traversal of {clean_name} requires O(1) auxiliary call stack space."
            ]
            correct = options[0]
            explanation = f"Implementing '{clean_name}' in C++ demands rigorous analysis of Big-O complexity alongside CPU cache performance and continuous memory locality."
        elif q_type == 2:
            question = f"When managing memory and pointers in C++ for '{clean_name}', which best practice prevents leaks?"
            options = [
                f"A) Adhering to RAII principles using smart pointers (std::unique_ptr / std::shared_ptr) or explicit destructor cleanup for {clean_name}.",
                f"B) Never deallocating memory allocated with 'new' to prevent dangling references.",
                f"C) Using raw pointer arithmetic without validating buffer boundary conditions.",
                f"D) Relying on automatic garbage collection in standard unmanaged C++."
            ]
            correct = options[0]
            explanation = f"C++ does not have a garbage collector. Applying Resource Acquisition Is Initialization (RAII) ensures {clean_name} resources are freed deterministically."
        elif q_type == 3:
            question = f"Which algorithmic paradigm or standard container is most effectively paired with '{clean_name}' in modern C++?"
            options = [
                f"A) Standard Template Library (STL) iterators and sequence containers designed for {clean_name}.",
                f"B) Unbounded recursion without a base termination condition.",
                f"C) Global mutable arrays that violate modular encapsulation.",
                f"D) Linear search across sorted data structures instead of logarithmic divide-and-conquer."
            ]
            correct = options[0]
            explanation = f"In modern C++, {clean_name} integrates with STL abstractions, iterators, and generic algorithms (std::sort, std::find) for optimal throughput."
        elif q_type == 4:
            question = f"What is a critical edge case to test when validating an implementation of '{clean_name}' in C++?"
            options = [
                f"A) Empty container states, single-element boundaries, and capacity overflow/underflow in {clean_name}.",
                f"B) Compiling without a main() entry point.",
                f"C) Ensuring integer values never equal zero.",
                f"D) Restricting inputs strictly to powers of 2."
            ]
            correct = options[0]
            explanation = f"Edge cases for {clean_name} invariably include empty boundaries, single nodes, duplicate keys, and memory boundary conditions."
        else:
            question = f"Compared to alternative data structures, what is the core architectural trade-off of '{clean_name}'?"
            options = [
                f"A) Trading space overhead for faster lookup or structured FIFO/LIFO/hierarchical access in {clean_name}.",
                f"B) Sacrificing deterministic ordering for non-deterministic memory addresses.",
                f"C) Forcing all element types to be statically typed as void pointers.",
                f"D) Preventing random access even when underlying storage is contiguous."
            ]
            correct = options[0]
            explanation = f"'{clean_name}' provides specialized access patterns (e.g. LIFO for Stacks, FIFO for Queues, contiguous caching for Arrays) at the cost of specific operational trade-offs."

    elif "ADBMS" in subject or "Database" in subject:
        if q_type == 1:
            question = f"In Advanced Database Management Systems (ADBMS), how does '{clean_name}' ensure transactional correctness?"
            options = [
                f"A) Enforcing ACID properties (Atomicity, Consistency, Isolation, Durability) or serializability during execution of {clean_name}.",
                f"B) Permitting dirty reads (Read Uncommitted) as the mandatory default for financial transactions.",
                f"C) Disabling write-ahead logging (WAL) to minimize disk input/output operations.",
                f"D) Allowing unconstrained cascading rollbacks without recovery checkpoints."
            ]
            correct = options[0]
            explanation = f"In ADBMS, '{clean_name}' maintains database consistency by enforcing ACID guarantees and preventing concurrency anomalies like lost updates and dirty reads."
        elif q_type == 2:
            question = f"When optimizing schema design and relational architecture in '{clean_name}', which objective is paramount?"
            options = [
                f"A) Eliminating insertion, update, and deletion anomalies while minimizing unnecessary data redundancy in {clean_name}.",
                f"B) Maximizing transitive functional dependencies across all non-prime attributes.",
                f"C) Decomposing tables into un-normalized relations with repeated attribute groups.",
                f"D) Ensuring that foreign key constraints are completely disabled."
            ]
            correct = options[0]
            explanation = f"Relational design in '{clean_name}' uses normalization (1NF, 2NF, 3NF, BCNF) to eliminate modification anomalies and preserve dependency preservation."
        elif q_type == 3:
            question = f"What is the difference between pessimistic locking and optimistic concurrency control regarding '{clean_name}'?"
            options = [
                f"A) Pessimistic schemes lock resources beforehand (e.g. 2PL), whereas optimistic schemes validate conflict only at commit time.",
                f"B) Optimistic concurrency control prevents all read operations during transaction execution.",
                f"C) Pessimistic schemes cannot cause deadlocks under any concurrent workload.",
                f"D) Timestamp-based protocols require manual user approval for each SQL query."
            ]
            correct = options[0]
            explanation = f"In ADBMS concurrency control, pessimistic approaches assume conflicts will occur and acquire shared/exclusive locks early, whereas optimistic schemes validate read/write phases before commit."
        elif q_type == 4:
            question = f"How does indexing and storage structure (e.g. B+ Trees, Hashing) impact query execution in '{clean_name}'?"
            options = [
                f"A) B+ Trees provide logarithmic range queries and keep all actual record pointers in leaf nodes for efficient disk block access.",
                f"B) Hash indexing is superior to B+ Trees for range and inequality queries (> and <).",
                f"C) Adding secondary indexes improves the throughput of high-frequency INSERT and DELETE operations.",
                f"D) Clustered indexes alter the logical query syntax without affecting physical disk storage order."
            ]
            correct = options[0]
            explanation = f"In file structures and indexing for '{clean_name}', B+ Trees are standard because leaf nodes are linked sequentially, facilitating O(log N) point queries and high-speed range scans."
        else:
            question = f"In NoSQL systems and MongoDB data aggregation related to '{clean_name}', which paradigm applies?"
            options = [
                f"A) Schema-flexible document models utilizing pipeline stages ($match, $group, $project) for distributed data transformation.",
                f"B) Strict adherence to 3NF relational schemas with mandatory foreign key joins.",
                f"C) Storing data purely as binary relational tables without JSON/BSON representations.",
                f"D) Disallowing horizontal sharding across distributed cluster nodes."
            ]
            correct = options[0]
            explanation = f"In MongoDB and NoSQL architectures for '{clean_name}', document databases utilize BSON aggregation pipelines for high-throughput distributed processing."

    else:  # AI / FAI
        if q_type == 1:
            question = f"In Artificial Intelligence, what is the formal problem formulation associated with '{clean_name}'?"
            options = [
                f"A) Defining initial states, actions, transition models, goal tests, and path cost functions for {clean_name}.",
                f"B) Randomly generating state spaces without any objective or evaluation function.",
                f"C) Assuming that all AI search environments are fully observable, static, and deterministic.",
                f"D) Restricting agent actions to reactive reflex tables without state memory."
            ]
            correct = options[0]
            explanation = f"In AI problem solving for '{clean_name}', classical formulation requires specifying the 5-tuple: Initial State, Action Set, Transition Model, Goal State Test, and Path Cost."
        elif q_type == 2:
            question = f"Regarding heuristic search algorithms (like A*) in '{clean_name}', what does the admissibility condition guarantee?"
            options = [
                f"A) That h(n) ≤ h*(n) (never overestimating the true cost to goal), ensuring optimal solutions in tree search.",
                f"B) That the heuristic value h(n) is always strictly greater than the actual remaining cost.",
                f"C) That memory consumption remains O(1) throughout state space exploration.",
                f"D) That depth-first search explores all branches before evaluating heuristic weights."
            ]
            correct = options[0]
            explanation = f"An admissible heuristic never overestimates the true cost to reach the goal ($h(n) <= h^*(n)$). This is essential for A* optimality."
        elif q_type == 3:
            question = f"In knowledge representation and logical inference relevant to '{clean_name}', which property holds?"
            options = [
                f"A) Sound inference rules guarantee that only sentences that are logically entailed by the knowledge base are derived.",
                f"B) Forward chaining can only be applied to queries with existential quantifiers in propositional logic.",
                f"C) Resolution theorem proving does not require converting sentences into Conjunctive Normal Form (CNF).",
                f"D) A knowledge base is valid if and only if it contains contradictory assertions."
            ]
            correct = options[0]
            explanation = f"Soundness guarantees that an inference mechanism derives only true consequences (entailed sentences) from the knowledge base."
        elif q_type == 4:
            question = f"In adversarial game playing and decision making (Minimax / Alpha-Beta) related to '{clean_name}', what is the effect of pruning?"
            options = [
                f"A) Alpha-Beta pruning eliminates subtrees that cannot influence the final minimax decision without compromising optimality.",
                f"B) Pruning reduces the depth of the game tree rather than branching factor.",
                f"C) Minimax assumes the opponent always plays to maximize the agent's utility.",
                f"D) Pruning guarantees that the game tree is explored in strictly O(1) time."
            ]
            correct = options[0]
            explanation = f"Alpha-Beta pruning returns the exact same optimal minimax value while pruning branches where α ≥ β, doubling the effective search depth in best-case ordering."
        else:
            question = f"What is the principal operational model of a learning agent in '{clean_name}'?"
            options = [
                f"A) Dividing architecture into learning element (improver), performance element (actor), critic (evaluator), and problem generator (explorer).",
                f"B) Eliminating environmental feedback and relying solely on pre-programmed static rules.",
                f"C) Restricting learning exclusively to supervised classification without exploration.",
                f"D) Preventing the agent from altering its internal state representation over time."
            ]
            correct = options[0]
            explanation = f"The standard general model of a learning agent divides functionality into: Critic, Learning Element, Performance Element, and Problem Generator."

    # Randomize the option order so correct answer isn't always A
    import random
    opt_labels = ["A)", "B)", "C)", "D)"]
    raw_texts = [o[3:].strip() for o in options]
    correct_text = raw_texts[0]
    random.shuffle(raw_texts)
    
    final_options = [f"{lbl} {txt}" for lbl, txt in zip(opt_labels, raw_texts)]
    final_correct = next(opt for opt in final_options if correct_text in opt)

    return QuizQuestion(
        topic=t.name, subject=t.subject, question=question,
        options=final_options, correct_option=final_correct, explanation=explanation,
        source="Syllabus Synthesized"
    )

def generate_dynamic_mcq(llm: LLMClient, t: TopicState) -> QuizQuestion:
    """Dynamically generates an MCQ based on syllabus topics using Gemini or OpenAI LLM if available, or syllabus procedural synthesis."""
    import random
    GEMINI.refresh()
    llm.refresh()

    prereqs = CURRICULUM.get(t.subject, {}).get(t.name, (0.5, []))[1]
    prereq_str = f"Relevant syllabus prerequisites: {', '.join(prereqs)}." if prereqs else ""

    angles = [
        "practical scenario and edge-case failure analysis",
        "asymptotic performance, trade-offs, and optimization",
        "formal architectural principles and technical definition",
        "comparative analysis with related engineering mechanisms",
        "common student misconceptions and tricky bug traps"
    ]
    chosen_angle = random.choice(angles)
    seed_id = random.randint(10000, 99999)

    system_prompt = (
        "You are an expert university professor and exam setter for B.Tech Computer Science & Engineering. "
        "Craft an original, fresh, and challenging Multiple Choice Question (MCQ) testing deep conceptual understanding of the "
        "given syllabus module. Reply ONLY with a valid JSON object matching this schema:\n"
        "{\n"
        '  "question": "<detailed question text testing core mechanics, algorithms, formulas, or trade-offs>",\n'
        '  "options": ["A) <opt A>", "B) <opt B>", "C) <opt C>", "D) <opt D>"],\n'
        '  "correct_option": "<exact matching text of the correct option, e.g. A) ...>",\n'
        '  "explanation": "<thorough technical explanation of why the correct option is right and others are incorrect>"\n'
        "}\n"
        "Rules:\n"
        "- Exactly 4 options starting with A), B), C), D).\n"
        "- Ensure all distractors are plausible and pedagogically meaningful.\n"
        "- Output raw JSON only. Do NOT use markdown code fences."
    )

    user_prompt = (
        f"Subject: {t.subject}\n"
        f"Syllabus Module: {t.name}\n"
        f"Difficulty: {t.difficulty:.2f} (0.3=Foundational, 0.7=Advanced B.Tech level)\n"
        f"Question Focus Angle: {chosen_angle}\n"
        f"Random Variation Seed: {seed_id}\n"
        f"{prereq_str}\n\n"
        f"Generate a brand new, unique exam-level Multiple Choice Question for this syllabus module."
    )

    # 1. Try Gemini first
    if GEMINI.live:
        data = GEMINI.json_chat(system_prompt, user_prompt)
        if data and isinstance(data, dict):
            raw_opts = data.get("options")
            if isinstance(raw_opts, list) and len(raw_opts) == 4:
                q_text = str(data.get("question", "")).strip()
                opts = [str(o).strip() for o in raw_opts]
                corr = str(data.get("correct_option", "")).strip()
                expl = str(data.get("explanation", "Standard syllabus reference solution.")).strip()

                if not any(corr.startswith(p) for p in ["A)", "B)", "C)", "D)"]):
                    for opt in opts:
                        if corr.lower() in opt.lower():
                            corr = opt
                            break
                    else:
                        corr = opts[0]

                if q_text and all(opts):
                    return QuizQuestion(
                        topic=t.name, subject=t.subject, question=q_text,
                        options=opts, correct_option=corr, explanation=expl,
                        source="Gemini Generated"
                    )

    # 2. Try OpenAI second
    if llm.live:
        data = llm.json_chat(system_prompt, user_prompt, temperature=0.85)
        if data and isinstance(data, dict):
            raw_opts = data.get("options")
            if isinstance(raw_opts, list) and len(raw_opts) == 4:
                q_text = str(data.get("question", "")).strip()
                opts = [str(o).strip() for o in raw_opts]
                corr = str(data.get("correct_option", "")).strip()
                expl = str(data.get("explanation", "Standard syllabus reference solution.")).strip()

                if not any(corr.startswith(p) for p in ["A)", "B)", "C)", "D)"]):
                    for opt in opts:
                        if corr.lower() in opt.lower():
                            corr = opt
                            break
                    else:
                        corr = opts[0]

                if q_text and all(opts):
                    return QuizQuestion(
                        topic=t.name, subject=t.subject, question=q_text,
                        options=opts, correct_option=corr, explanation=expl,
                        source="OpenAI Generated"
                    )

    # 3. Procedural syllabus fallback
    return generate_procedural_syllabus_mcq(t)


class EvaluatorAgent(ReActAgent):
    name = "Evaluator Agent"

    def __init__(self, state: AppState, llm: LLMClient, notify: Callable[[list[Adjustment]], str]) -> None:
        super().__init__(state, llm)
        self.notify = notify
        self.tools = {
            "select_weak_topics": (self.t_select, "Choose weakest or subject-filtered topics for quiz"),
            "generate_questions": (self.t_generate, "Create targeted Multiple Choice Questions (LLM or bank)"),
            "verify_questions": (self.t_verify, "Verify MCQ options and correct keys are valid"),
            "score_answers": (self.t_score, "Grade each MCQ selection objectively"),
            "update_mastery": (self.t_update, "Update topic mastery and log performance"),
            "diagnose_patterns": (self.t_patterns, "Identify learning patterns to trigger schedule adjustments"),
            "notify_scheduler": (self.t_notify, "Send schedule adjustments to Scheduler Agent"),
        }

    def generate(self, n: int, subject_filter: str = "All Subjects") -> list[QuizQuestion]:
        self.state.quiz, self.state.quiz_graded, self.state.last_grades = [], False, []
        self.loop({"mode": "generate", "n": n, "subject_filter": subject_filter})
        return self.state.quiz

    def grade(self, answers: list[str]) -> list[GradeResult]:
        self.loop({"mode": "grade", "answers": answers})
        return self.state.last_grades

    def policy(self, mem):
        if mem["mode"] == "generate":
            if "selected" not in mem:
                return (f"Pick {mem['n']} topics based on priority and subject filter '{mem.get('subject_filter', 'All')}'.", "select_weak_topics", {})
            if "generated" not in mem:
                return ("Fetch or generate targeted Multiple Choice Questions for selected modules.", "generate_questions", {})
            if "verified" not in mem:
                return ("Verify MCQ questions have valid choices and correct answers.", "verify_questions", {})
            return None
        if "scored" not in mem:
            return ("Grade each MCQ submission objectively against correct options.", "score_answers", {})
        if "updated" not in mem:
            return ("Update topic mastery and record performance logs.", "update_mastery", {})
        if "patterns" not in mem:
            return ("Diagnose recurring errors and determine schedule adjustments.", "diagnose_patterns", {})
        if mem["adjustments"] and "notified" not in mem:
            return (f"Send {len(mem['adjustments'])} schedule adjustment(s) to Scheduler.", "notify_scheduler", {})
        if not mem["adjustments"] and "notified" not in mem:
            mem["notified"] = True
        return None

    def t_select(self, mem):
        import random
        st = self.state
        subj_filter = mem.get("subject_filter", "All Subjects")
        recent = [l.topic for l in st.logs[-12:]]

        candidates = list(st.topics.values())
        if subj_filter and subj_filter != "All Subjects":
            candidates = [t for t in candidates if t.subject == subj_filter]
            if not candidates and subj_filter in CURRICULUM:
                for mod_name, (diff, pre) in CURRICULUM[subj_filter].items():
                    candidates.append(TopicState(name=mod_name, subject=subj_filter, difficulty=diff, weight=1.0, mastery=0.5))

        if not candidates:
            for sname, mods in CURRICULUM.items():
                for mname, (diff, pre) in mods.items():
                    candidates.append(TopicState(name=mname, subject=sname, difficulty=diff, weight=1.0, mastery=0.5))

        # Random shuffle with priority weighting so questions rotate dynamically across all 10 modules
        random.shuffle(candidates)
        # Sort primarily by least recently tested and priority jitter
        def jitter_score(t):
            rec_penalty = 0.40 if t.name in recent else 0.0
            return (priority(t) + random.uniform(-0.15, 0.15)) - rec_penalty

        ranked = sorted(candidates, key=jitter_score, reverse=True)
        chosen: list[TopicState] = []
        n_needed = min(mem["n"], len(ranked))

        if subj_filter == "All Subjects":
            per: dict[str, int] = {}
            for t in ranked:
                if per.get(t.subject, 0) < max(1, n_needed // 3):
                    chosen.append(t)
                    per[t.subject] = per.get(t.subject, 0) + 1
                if len(chosen) == n_needed:
                    break

        for t in ranked:
            if len(chosen) >= n_needed:
                break
            if t not in chosen:
                chosen.append(t)

        mem["topic_objs"] = chosen
        mem["topics"] = [t.name for t in chosen]
        mem["selected"] = True
        return "Selected modules: " + ", ".join(f"{t.name} ({t.subject})" for t in chosen)

    def t_generate(self, mem):
        st, made = self.state, []
        for t in mem.get("topic_objs", []):
            q_final = generate_dynamic_mcq(self.llm, t)
            st.quiz.append(q_final)
            made.append(q_final.source)
        mem["generated"] = True
        llm_count = sum(1 for s in made if "OpenAI" in s or "LLM" in s)
        if llm_count > 0:
            return f"Generated {len(made)} MCQ question(s) dynamically via OpenAI LLM based on syllabus."
        return f"Generated {len(made)} MCQ question(s) dynamically from syllabus."

    def t_verify(self, mem):
        fixed = 0
        for i, q in enumerate(self.state.quiz):
            if len(q.options) < 4 or not q.correct_option:
                t_obj = self.state.topics.get(q.topic) or TopicState(name=q.topic, subject=q.subject, difficulty=0.5)
                self.state.quiz[i] = generate_dynamic_mcq(self.llm, t_obj)
                fixed += 1
        mem["verified"] = True
        return f"Verified all MCQs ({fixed} repaired)."

    def t_score(self, mem):
        st, res = self.state, []
        answers = list(mem["answers"]) + [None] * (len(st.quiz) - len(mem["answers"]))
        for q, a in zip(st.quiz, answers):
            user_choice = str(a).strip() if a else ""
            is_corr = bool(user_choice and (
                user_choice.lower() == q.correct_option.lower() or
                user_choice.lower().startswith(q.correct_option.lower()[:2]) or
                q.correct_option.lower().startswith(user_choice.lower()[:2])
            ))
            score = 10.0 if is_corr else 0.0
            res.append(GradeResult(
                topic=q.topic, subject=q.subject, question=q.question,
                user_answer=user_choice, correct_option=q.correct_option,
                score=score, is_correct=is_corr, explanation=q.explanation
            ))
        st.last_grades, mem["scored"] = res, True
        correct_count = sum(1 for r in res if r.is_correct)
        return f"MCQs scored: {correct_count}/{len(res)} correct."

    def t_update(self, mem):
        st, lines = self.state, []
        for g in st.last_grades:
            if g.topic in st.topics:
                t = st.topics[g.topic]
                before = t.mastery
                if g.is_correct:
                    t.mastery = clamp(before + 0.35 * (1.0 - before))
                else:
                    t.mastery = clamp(before - 0.20 * before, 0.03)
                st.logs.append(PerformanceLog(
                    ts=datetime.now().strftime("%d %b %H:%M"), topic=g.topic, subject=g.subject, score=g.score,
                    mastery_before=before, mastery_after=t.mastery, feedback="Correct" if g.is_correct else "Incorrect"
                ))
                lines.append(f"{g.topic}: {before:.0%} -> {t.mastery:.0%}")
        mem["updated"] = True
        return "Updated mastery: " + ("; ".join(lines) or "no questions attempted.")

    def t_patterns(self, mem):
        st, adjs = self.state, []
        for g in st.last_grades:
            if g.topic not in st.topics:
                continue
            t = st.topics[g.topic]
            hist = [l.score for l in st.logs if l.topic == g.topic]
            if len(hist) >= 2 and hist[-1] < 6 and hist[-2] < 6:
                adjs.append(Adjustment(topic=g.topic, action="escalate", score=g.score, reason="two consecutive missed MCQs"))
            elif not g.is_correct:
                adjs.append(Adjustment(topic=g.topic, action="reinforce", score=g.score, reason=f"incorrect MCQ on {g.topic}"))
            elif g.is_correct and t.learned:
                adjs.append(Adjustment(topic=g.topic, action="space_out", score=g.score, reason="correct MCQ, retention solid"))
        mem["adjustments"], mem["patterns"] = [a.model_dump() for a in adjs], True
        return f"{len(adjs)} schedule adjustments proposed."

    def t_notify(self, mem):
        mem["notified"] = True
        return self.notify([Adjustment(**a) for a in mem["adjustments"]])


class Orchestrator:
    def __init__(self) -> None:
        self.state = AppState()
        self.horizon = 14
        self.diag = DiagnosticAgent(self.state, LLM)
        self.scheduler = SchedulerAgent(self.state, LLM)
        self.evaluator = EvaluatorAgent(self.state, LLM, self._on_adjustments)
        self.last_feedback_note = ""

    def transition(self, new: Phase, why: str) -> bool:
        old = self.state.phase
        if new != old and new not in ALLOWED_TRANSITIONS[old]:
            return False
        self.state.phase = new
        return True

    def onboard(self, profile: StudentProfile, doc_analysis: dict[str, Any] | None = None) -> None:
        st = self.state
        st.profile, st.cursor = profile, date.today()
        if doc_analysis:
            st.uploaded_doc_analysis = doc_analysis
        self.diag.run()
        self.transition(Phase.DIAGNOSED, "skill matrix ready")
        self.scheduler.run("initial")
        self.transition(Phase.PLANNED, "plan created")

    def adapt(self, missed: int, fatigue: int, hours: float, note: str) -> str:
        st, prof = self.state, self.state.profile
        days_left = (prof.exam_date - st.cursor).days
        if days_left <= 0:
            return "The exam date has arrived. Best of luck!"
        missed = int(max(0, min(missed or 0, days_left - 1)))
        fatigue = int(fatigue)
        words = (note or "").lower()
        if fatigue < 4 and any(w in words for w in ("sick", "ill", "fever", "exhaust", "burn", "tired", "stress")):
            fatigue = 4
        st.fatigue = fatigue
        if hours and hours > 0:
            prof.hours_per_day = float(hours)
        self.transition(Phase.ADAPTING, "student update")
        mem = self.scheduler.run("adapt", missed_days=missed)
        self.transition(Phase.PLANNED, "plan rebalanced")
        return f"**Plan v{st.plan.version} updated.** " + " | ".join(mem["notes"]) + (f"\n\n{' '.join(st.plan.warnings)}" if st.plan.warnings else "")

    def complete_today(self) -> str:
        st, prof = self.state, self.state.profile
        d = st.cursor
        if d >= prof.exam_date:
            return "The exam day has arrived. Good luck!"
        n = 0
        for b in st.plan.blocks:
            if b.day == d and b.status == "planned":
                b.status = "done"
                if b.kind in ("learn", "review", "recall") and b.topic in st.topics:
                    apply_session(st.topics[b.topic], b.kind, d)
                    n += 1
        st.cursor = d + timedelta(days=1)
        return f"Logged {n} completed session(s) for {d:%a %d %b}. Spaced repetition schedule advanced to {st.cursor:%a %d %b}."

    def make_quiz(self, n: int, subject_filter: str = "All Subjects") -> list[QuizQuestion]:
        self.transition(Phase.QUIZ_READY, "quiz requested")
        return self.evaluator.generate(n, subject_filter=subject_filter)

    def submit(self, answers: list[str]) -> str:
        st = self.state
        self.transition(Phase.EVALUATED, "answers submitted")
        self.last_feedback_note = ""
        self.evaluator.grade(answers)
        st.quiz_graded = True
        return self.last_feedback_note

    def _on_adjustments(self, adjs: list[Adjustment]) -> str:
        st = self.state
        self.transition(Phase.ADAPTING, "performance feedback")
        self.scheduler.run("performance", adjustments=[a.model_dump() for a in adjs])
        self.transition(Phase.PLANNED, "plan updated from performance")
        self.last_feedback_note = f"Schedule re-tuned to **v{st.plan.version}** based on your quiz results."
        return f"Scheduler updated to v{st.plan.version}."

# ==============================================================================
# DOUBTS CHATBOT KNOWLEDGE ENGINE
# ==============================================================================
DOUBT_KB = {
    "normalization": (
        "### Normalization in Relational Databases (1NF, 2NF, 3NF, BCNF)\n\n"
        "- **1NF:** Attributes must be atomic (no multivalued attributes or repeated groups).\n"
        "- **2NF:** Must be in 1NF and have **no partial dependencies** (every non-prime attribute must depend on the whole candidate key, not part of it).\n"
        "- **3NF:** Must be in 2NF and have **no transitive dependencies** (no non-prime attribute determines another non-prime attribute).\n"
        "- **BCNF (Boyce-Codd):** Stricter than 3NF. For every functional dependency `X -> Y`, `X` must be a superkey.\n\n"
        "💡 *Example:* If `StudentID -> Branch` and `Branch -> HOD`, then `StudentID -> HOD` is transitive. Decompose into `(StudentID, Branch)` and `(Branch, HOD)` for 3NF."
    ),
    "2nf": "### 2NF (Second Normal Form)\n\n**Rule:** Must be in 1NF and contain **no partial functional dependencies**.\n- A partial dependency exists when a non-key attribute depends on only a *portion* of a composite candidate key.\n- *Fix:* Move the partially dependent attributes to a separate relation keyed by that subset.",
    "3nf": "### 3NF (Third Normal Form)\n\n**Rule:** Must be in 2NF and contain **no transitive dependencies**.\n- If `A -> B` and `B -> C`, then `A -> C` transitively. `C` should not depend on non-prime attribute `B`.\n- *Fix:* Split into `(A, B)` and `(B, C)`.",
    "bcnf": "### BCNF (Boyce-Codd Normal Form)\n\n**Rule:** For every non-trivial functional dependency `X -> Y`, `X` **must be a superkey**.\n- 3NF allows `Y` to be a prime attribute even if `X` isn't a superkey; BCNF removes this exception.",
    "a*": (
        "### A* Search Algorithm & Heuristics\n\n"
        "A* evaluates nodes using the evaluation function:\n"
        "$$\\mathbf{f(n) = g(n) + h(n)}$$\n"
        "- $g(n)$: Exact path cost from start node to $n$.\n"
        "- $h(n)$: Estimated heuristic cost from $n$ to goal.\n\n"
        "**Admissibility Condition:** $h(n) <= h^*(n)$ (the heuristic must never overestimate true cost).\n"
        "**Consistency (Monotonicity):** $h(n) <= c(n, a, n') + h(n')$ (satisfies the triangle inequality).\n"
        "If $h$ is admissible, Tree-Search A* is guaranteed optimal!"
    ),
    "admissible": "### Admissible Heuristic in AI Search\n\nA heuristic $h(n)$ is **admissible** if it never overestimates the true cost to reach the goal, meaning $h(n) <= h^*(n)$ for all $n$.\n- If a heuristic overestimates, A* might prematurely prune the true shortest path and return a suboptimal route.",
    "bfs": "### BFS (Breadth-First Search)\n\n- **Mechanism:** Explores level by level using a **FIFO Queue**.\n- **Completeness:** Yes (if branching factor $b$ is finite).\n- **Optimality:** Yes, for uniform step costs.\n- **Time Complexity:** $O(b^d)$\n- **Space Complexity:** $O(b^d)$ (high memory usage).",
    "dfs": "### DFS (Depth-First Search)\n\n- **Mechanism:** Explores deepest unvisited branch first using a **LIFO Stack**.\n- **Completeness:** No (can get stuck in infinite depth loops).\n- **Optimality:** No (may return a deeper non-optimal goal).\n- **Time Complexity:** $O(b^m)$\n- **Space Complexity:** $O(b \\cdot m)$ (very light linear memory).",
    "poisson": (
        "### Poisson Distribution\n\n"
        "Models the number of independent events occurring in a fixed interval of time or space at an average constant rate $\\lambda$.\n"
        "- **PMF:** $P(X = k) = \\frac{\\lambda^k e^{-\\lambda}}{k!}$\n"
        "- **Mean:** $E[X] = \\lambda$\n"
        "- **Variance:** $Var(X) = \\lambda$\n\n"
        "💡 *Poisson Approximation to Binomial:* When $n$ is very large ($n \\ge 100$) and $p$ is very small ($p <= 0.01$), Binomial($n, p$) is approximated by Poisson with $\\lambda = n \\cdot p$."
    ),
    "binomial": "### Binomial Distribution\n\nModels the number of successes in $n$ independent Bernoulli trials with constant success probability $p$.\n- **PMF:** $P(X = k) = \\binom{n}{k} p^k (1-p)^{n-k}$\n- **Mean:** $np$\n- **Variance:** $np(1-p)$",
    "central limit": (
        "### Central Limit Theorem (CLT)\n\n"
        "Regardless of the population's underlying distribution (skewed, uniform, etc.), the distribution of the sample mean $\\bar{X}$ approaches a **Normal Distribution** as sample size $n$ becomes sufficiently large (typically $n \\ge 30$):\n"
        "$$\\bar{X} \\sim \\mathcal{N}\\left(\\mu, \\frac{\\sigma^2}{n}\\right)$$\n"
        "Standardized: $Z = \\frac{\\bar{X} - \\mu}{\\sigma / \\sqrt{n}} \\sim \\mathcal{N}(0, 1)$."
    ),
    "stack": (
        "### Stacks in C++ (LIFO: Last-In, First-Out)\n\n"
        "- **Operations:** `push()` $O(1)$, `pop()` $O(1)$, `top()` $O(1)$.\n"
        "- **Applications:**\n"
        "  1. Function call recursion stack\n"
        "  2. Infix to Postfix expression conversion and evaluation\n"
        "  3. Undo operations in editors\n"
        "  4. Balanced parenthesis checking `{[()]}`."
    ),
    "queue": (
        "### Queues in C++ (FIFO: First-In, First-Out)\n\n"
        "- **Operations:** `push()` (enqueue at rear) $O(1)$, `pop()` (dequeue from front) $O(1)$, `front()` $O(1)$.\n"
        "- **Circular Queue:** Uses modulo `(rear + 1) % capacity` to reuse freed front positions, avoiding false overflow.\n"
        "- **Applications:** CPU job scheduling, printer spooling, BFS graph traversal."
    ),
    "vector": (
        "### C++ STL: std::vector vs std::list\n\n"
        "- **std::vector:** Contiguous dynamic array. $O(1)$ random index access (`v[i]`), amortized $O(1)$ `push_back()`. Expensive $O(n)$ middle insertions.\n"
        "- **std::list:** Doubly linked list. Non-contiguous nodes. $O(1)$ arbitrary insertions/deletions once iterator is found. No random access ($O(n)$ access)."
    ),
}

def resolve_doubt_offline(query: str, orch: Orchestrator | None) -> str:
    q_low = query.lower().strip()

    # Handle greetings conversationally
    clean_words = set(re.findall(r'\b[a-zA-Z]+\b', q_low))
    greetings = {"hi", "hello", "hey", "hola", "namaste", "greetings", "morning", "afternoon", "evening"}
    if clean_words & greetings or q_low in ("hi", "hello", "hey", "hi there", "hello tutor"):
        return (
            "### 👋 Hello! How can I help you with your B.Tech studies today?\n\n"
            "I am your **AI Study Companion & Doubt Tutor** for Term 1!\n\n"
            "You can ask me anything about:\n"
            "- **Probability and Statistics** (Distributions, Hypothesis Testing, Sampling, Regression)\n"
            "- **DSA C++** (Arrays, Pointers, Stacks, Queues, STL Containers, Big-O Analysis)\n"
            "- **ADBMS** (Relational Algebra, Normalization 1NF-BCNF, Transactions, Concurrency, MongoDB)\n"
            "- **Fundamentals of AI (FAI)** (Search Strategies, A*, Minimax, Knowledge Representation)\n\n"
            "💡 *Enter your Gemini API key above to chat live with Google Gemini for any question!*"
        )

    if orch and orch.state.last_grades and any(w in q_low for w in ("quiz", "grade", "my answer", "q1", "q2", "q3", "q4", "q5", "question", "wrong", "option", "mcq")):
        last_g = orch.state.last_grades
        out = ["### 📝 Explanation of Your Recent MCQ Performance:\n"]
        for idx, g in enumerate(last_g, 1):
            if f"q{idx}" in q_low or str(idx) in q_low or len(last_g) == 1 or "all" in q_low:
                status = "✅ Correct" if g.is_correct else "❌ Incorrect"
                out.append(
                    f"**Question {idx}: {g.topic}** ({g.subject}) — {status}\n"
                    f"- **Question:** {g.question}\n"
                    f"- **Your Selection:** `{g.user_answer or 'Skipped'}`\n"
                    f"- **Correct Option:** `{g.correct_option}`\n"
                    f"- **Concept Explanation:**\n> {g.explanation}\n"
                )
        if len(out) > 1:
            return "\n\n".join(out)

    for k, v in DOUBT_KB.items():
        if k in q_low:
            return v

    for subj, mods in CURRICULUM.items():
        for mod_name, (diff, prereqs) in mods.items():
            core_topic = mod_name.split(":")[-1].strip().lower()
            if core_topic in q_low or any(word in q_low for word in core_topic.split() if len(word) > 4):
                prereq_str = ", ".join(prereqs) if prereqs else "None (Foundational Module)"
                return (
                    f"### 📘 Syllabus Concept Guide: {mod_name} ({subj})\n\n"
                    f"- **Subject:** {subj}\n"
                    f"- **Module:** {mod_name}\n"
                    f"- **Difficulty Rating:** {int(diff * 100)}%\n"
                    f"- **Prerequisites:** {prereq_str}\n\n"
                    f"💡 *Exam Tip:* Focus on the core algorithmic steps, formulas, and typical exam questions for {mod_name}."
                )

    return (
        f"### 💡 Query Received: '{query}'\n\n"
        "To get an interactive, in-depth AI explanation for this exact question, please connect your **Gemini API Key** above!\n\n"
        "*(Once Gemini is connected, you can ask any question — from general conversation, debugging C++ code, to complex B.Tech exam problems — and receive instant answers!)*"
    )

def connect_gemini_key(key: str) -> str:
    key_str = (key or "").strip()
    if not key_str:
        return "ℹ️ *Please enter your Gemini API key (starts with AIzaSy...)*"
    GEMINI.refresh(key_str)
    if GEMINI.live:
        test_reply = GEMINI.generate("Reply with 'Connected' in one word.")
        if test_reply:
            return "🟢 **Gemini AI Connected & Active!** You can now ask any question."
        elif GEMINI.last_error:
            return f"⚠️ **Connection Error:** {GEMINI.last_error}"
    return "⚠️ Could not connect to Gemini with this key. Check key format."

def answer_doubt(history: list[dict[str, str]], user_msg: str, orch: Orchestrator | None, api_key_input: str = "") -> tuple[list[dict[str, str]], str, Any]:
    if not user_msg or not user_msg.strip():
        return history, "", gr.update()

    query = user_msg.strip()
    history = list(history or [])
    history.append({"role": "user", "content": query})

    # Dynamically refresh Gemini with input key if provided
    if api_key_input and api_key_input.strip() and not GEMINI.live:
        GEMINI.refresh(api_key_input.strip())

    sys_prompt = (
        "You are an encouraging, expert B.Tech Computer Science & Engineering professor and conversational AI tutor. "
        "Engage with the student in a clear, friendly, and natural conversational manner. "
        "If the student says 'hi', 'hello', or greets you, respond warmly and ask what concept, doubt, or code they would like help with today. "
        "If the student asks a specific technical doubt, provide a thorough, accurate step-by-step explanation. "
        "Include math formulas, C++ code snippets, or database schemas where relevant. "
        "Curriculum Subjects: Probability and Statistics, DSA C++, ADBMS, Fundamentals of AI."
    )

    # 1. Try Gemini API (Primary engine)
    if not GEMINI.live and GEMINI_API_KEY.strip():
        GEMINI.refresh(GEMINI_API_KEY.strip())

    if GEMINI.live:
        context_lines = []
        for m in history[-6:]:
            speaker = "Student" if m["role"] == "user" else "Tutor"
            context_lines.append(f"{speaker}: {m['content']}")
        chat_context = "\n".join(context_lines)
        prompt = (
            f"Conversation History:\n{chat_context}\n\n"
            f"Student's Latest Input: {query}\n\n"
            f"Respond directly, conversationally, and helpfully to the student:"
        )
        bot_reply = GEMINI.generate(prompt, system_instruction=sys_prompt)
        if bot_reply and bot_reply.strip():
            history.append({"role": "assistant", "content": bot_reply.strip()})
            return history, "", "🟢 **Gemini AI Active**"

    # 2. Try OpenAI API as fallback
    if LLM.live:
        chat_msgs = [{"role": "system", "content": sys_prompt}]
        for m in history[-6:]:
            chat_msgs.append({"role": m["role"], "content": m["content"]})
        try:
            r = LLM._client.chat.completions.create(
                model=LLM.MODEL,
                temperature=0.6,
                messages=chat_msgs
            )
            bot_reply = r.choices[0].message.content
            if bot_reply and bot_reply.strip():
                history.append({"role": "assistant", "content": bot_reply.strip()})
                return history, "", "🟢 **OpenAI Active**"
        except Exception:
            pass

    # 3. Offline knowledge base and greeting handler
    bot_reply = resolve_doubt_offline(query, orch)
    history.append({"role": "assistant", "content": bot_reply})
    status_note = (
        f"⚠️ **Gemini Error:** {GEMINI.last_error}" if GEMINI.last_error
        else "ℹ️ *Offline Mode (Enter Gemini API key above to activate live AI answers)*"
    )
    return history, "", status_note

# ==============================================================================
# UI RENDERING HELPERS
# ==============================================================================
SUBJECT_COLORS = {
    "Probability and Statistics": "#2563eb",  # Blue
    "DSA C++": "#0891b2",                     # Cyan
    "ADBMS": "#d97706",                       # Amber
    "Fundamentals of AI (FAI)": "#7c3aed",    # Purple
}

KIND_META = {
    "learn": ("📘", "Learn"), "review": ("🔁", "Review"), "recall": ("🧠", "Active recall"),
    "mock": ("📝", "Mock test"), "break": ("☕", "Break"), "rest": ("🌙", "Rest")
}
E = html.escape

def mcolor(m: float) -> str:
    return "#dc2626" if m < 0.45 else "#d97706" if m < 0.7 else "#059669"

def cards(items: list[tuple[str, str]]) -> str:
    return "<div class='cards'>" + "".join(f"<div class='card'><div class='v'>{v}</div><div class='k'>{E(k)}</div></div>" for k, v in items) + "</div>"

def bar(label: str, sub: str, m: float) -> str:
    return (f"<div class='barrow'><span class='bl'><i style='background:{SUBJECT_COLORS.get(sub, '#64748b')}'></i>{E(label)}</span>"
            f"<div class='bar'><div style='width:{m * 100:.0f}%;background:{mcolor(m)}'></div></div><span class='bp'>{m:.0%}</span></div>")

EMPTY = "<div class='card muted'>Nothing generated yet. Select your modules and build your plan in the first tab.</div>"

def render_uploaded_doc_box(doc_diag: dict[str, Any]) -> str:
    if not doc_diag:
        return ""
    fname = E(doc_diag.get("filename", "Uploaded File"))
    summary = E(doc_diag.get("summary", ""))
    rec = E(doc_diag.get("recommendation", ""))
    
    parts = [
        "<div class='box' style='border-left: 4.5px solid #0f766e; background: rgba(15,118,110,0.06);'>",
        "<div style='display:flex; justify-content:space-between; align-items:center;'>",
        f"<b style='font-size:0.95rem; color:#0f766e;'>📁 Document Diagnostic: {fname}</b>",
        "<span class='chip' style='background:#0f766e; color:#fff; font-size:0.75rem;'>File Analyzed</span>",
        "</div>",
        f"<p style='margin: 6px 0;'>{summary}</p>"
    ]
    
    scores = doc_diag.get("attempted_scores", [])
    if scores:
        parts.append("<b>Identified Past Quiz / Test Performance:</b><ul>")
        for sc in scores:
            topic = E(str(sc.get("topic", "")))
            score = sc.get("score", 0)
            parts.append(f"<li>{topic}: <b>{score}/10</b></li>")
        parts.append("</ul>")
        
    extra = doc_diag.get("extra_syllabus", [])
    if extra:
        extra_chips = "".join(f"<span class='chip' style='border-color:#d97706; color:#b45309;'>+ {E(x)}</span>" for x in extra)
        parts.append(f"<div style='margin: 8px 0;'><b>Identified Extra / Supplementary Syllabus:</b><div>{extra_chips}</div></div>")
        
    weak = doc_diag.get("weak_areas", [])
    if weak:
        parts.append(f"<p style='color:#dc2626; margin: 4px 0;'><b>⚠️ Detected Vulnerabilities:</b> {E(', '.join(weak))}</p>")
        
    if rec:
        parts.append(f"<p style='margin-top:6px; font-size:0.88rem;'><b>💡 Diagnostic Advice:</b> {rec}</p>")
        
    parts.append("</div>")
    return "".join(parts)

def render_diag(st: AppState) -> str:
    prof = st.profile
    weak_rows = "".join(f"<tr><td>{E(n)}</td><td>{E(st.topics[n].subject)}</td><td>{st.topics[n].mastery:.0%}</td><td>{priority(st.topics[n]):.2f}</td></tr>" for n in st.weak if n in st.topics)
    cal = "".join(f"<span class='chip' style='border-color:{'#dc2626' if v > .25 else '#059669' if abs(v) <= .25 else '#d97706'}'>{E(k)}: {v:+.0%}</span>" for k, v in st.calibration.items())
    frag = "".join(f"<li>{E(f)}</li>" for f in st.fragile) or "<li>None detected (solid prerequisites).</li>"
    bars = ""
    for s in prof.subjects:
        mods_in_sub = [t for t in st.topics.values() if t.subject == s.name]
        if mods_in_sub:
            bars += f"<h4>{E(s.name)} ({len(mods_in_sub)} Modules Selected)</h4>" + "".join(bar(t.name, t.subject, t.mastery) for t in mods_in_sub)
    
    doc_box = render_uploaded_doc_box(st.uploaded_doc_analysis)
    
    return (cards([("Days to exam", str((prof.exam_date - st.cursor).days)), ("Selected Modules", str(len(st.topics))),
                   ("Baseline mastery", f"{st.baseline_mastery:.0%}"), ("Target score", f"{prof.target_score}%"), ("Daily study", f"{prof.hours_per_day:g} hrs")])
            + doc_box
            + f"<div class='box'><b>Coach's Read</b><p>{E(st.insight)}</p></div>"
            + f"<div class='box'><b>Priority Modules to Target First</b><table><tr><th>Module</th><th>Subject</th><th>Mastery</th><th>Need Score</th></tr>{weak_rows}</table></div>"
            + f"<div class='box'><b>Confidence vs Quiz Calibration</b><div>{cal}</div><b>Prerequisite Foundations</b><ul>{frag}</ul></div>"
            + f"<div class='box'><b>Diagnosed Skill Matrix</b>{bars}</div>")

def render_timeline(st: AppState) -> str:
    plan, prof = st.plan, st.profile
    by_day: dict[date, list[StudyBlock]] = {}
    for b in plan.blocks:
        by_day.setdefault(b.day, []).append(b)
    first, cells = plan.start, []
    cells += [f"<div class='hd'>{w}</div>" for w in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")]
    cells += ["<div></div>"] * first.weekday()
    d = first
    while d <= prof.exam_date:
        cls = "day" + (" today" if d == st.cursor else "") + (" past" if d < st.cursor else "") + (" exam" if d == prof.exam_date else "")
        label = f"{d.day} {d:%b}" if (d.day == 1 or d == first) else str(d.day)
        dots = ""
        if d == prof.exam_date:
            dots = "<div class='ex'>🎯 Exam</div>"
        for b in by_day.get(d, []):
            if b.kind == "break":
                continue
            if b.kind == "rest":
                dots += "<span title='Rest day'>🌙</span>"
                continue
            c = SUBJECT_COLORS.get(b.subject, "#64748b")
            style = {"learn": f"background:{c}", "review": f"background:transparent;border:2.5px solid {c}",
                     "recall": f"background:{c}55;border:2px dotted {c}", "mock": f"background:{c};border-radius:3px;transform:rotate(45deg)"}.get(b.kind, f"background:{c}")
            dots += f"<span class='dot {b.status}' style='{style}' title='{E(KIND_META.get(b.kind, ('',''))[1])}: {E(b.topic)} ({b.status})'></span>"
        cells.append(f"<div class='{cls}'><div class='n'>{label}</div><div class='dots'>{dots}</div></div>")
        d += timedelta(days=1)
    legend = "".join(f"<span class='chip'><i style='background:{c}'></i>{E(s)}</span>" for s, c in SUBJECT_COLORS.items() if any(t.subject == s for t in st.topics.values()))
    key = ("<span class='chip'>● Learn</span><span class='chip'>◯ Spaced Review</span><span class='chip'>◌ Active Recall</span>"
           "<span class='chip'>◆ Mock Test</span><span class='chip' style='border-color:#dc2626'>Red: Missed</span>")
    return f"<div class='legend'>{legend}</div><div class='legend'>{key}</div><div class='tl'>{''.join(cells)}</div>"

def render_table(st: AppState, horizon: int) -> str:
    plan, prof = st.plan, st.profile
    start = max(plan.start, st.cursor - timedelta(days=3))
    end = min(prof.exam_date, st.cursor + timedelta(days=horizon))
    by_day: dict[date, list[StudyBlock]] = {}
    for b in plan.blocks:
        by_day.setdefault(b.day, []).append(b)
    rows = ["| Day | Date | Daily Schedule | Study Minutes |", "|---|---|---|---|"]
    d = start
    while d <= end:
        parts, mins = [], 0
        for b in sorted(by_day.get(d, []), key=lambda x: (x.slot, x.kind == "break")):
            mark = {"done": " ✅", "missed": " ⚠️ missed", "planned": ""}[b.status]
            icon, label = KIND_META.get(b.kind, ("📘", b.kind.capitalize()))
            if b.kind == "break":
                parts.append(f"{icon} {b.minutes} min break")
            elif b.kind == "rest":
                parts.append(f"{icon} {b.note}")
            else:
                mins += b.minutes
                parts.append(f"`{b.start}` {icon} **{label}**: {b.subject}, {b.topic} ({b.minutes} min){mark}<br>&nbsp;&nbsp;&nbsp;<sub>{b.note}</sub>")
        if d == prof.exam_date:
            parts = ["🎯 **Term 1 Exam Day**"]
        day_no = (d - plan.start).days + 1
        datecell = f"**▶ {d:%a %d %b}**" if d == st.cursor else f"{d:%a %d %b}"
        rows.append(f"| {day_no} | {datecell} | {'<br>'.join(parts) or '-'} | {mins} min |")
        d += timedelta(days=1)
    return "\n".join(rows)

def render_summary(st: AppState) -> str:
    plan, prof = st.plan, st.profile
    left = sum(1 for b in plan.blocks if b.day >= st.cursor and b.kind not in ("break", "rest"))
    done = sum(1 for b in plan.blocks if b.status == "done" and b.kind not in ("break", "rest"))
    out = cards([("Days left", str(max(0, (prof.exam_date - st.cursor).days))), ("Sessions ahead", str(left)), ("Sessions done", str(done)),
                 ("Module coverage", f"{plan.coverage:.0%}"), ("Projected mastery", f"{plan.projected_mastery:.0%}"), ("Plan version", f"v{plan.version}")])
    out += "<div class='box'><b>Syllabus Milestones</b><ul>" + "".join(f"<li>{E(m)}</li>" for m in plan.milestones) + "</ul></div>"
    if plan.warnings:
        out += "<div class='box warn'><b>Advisory Alerts</b><ul>" + "".join(f"<li>{E(w)}</li>" for w in plan.warnings) + "</ul></div>"
    out += "<div class='box'><b>Plan History</b><ul>" + "".join(f"<li>{E(c)}</li>" for c in plan.changelog[-5:]) + "</ul></div>"
    return out

def sparkline(vals: list[float]) -> str:
    if len(vals) < 2:
        return "<p class='muted'>Submit 2 or more quizzes to see your trend line.</p>"
    w, h = 300, 70
    pts = [(5 + i * (w - 10) / (len(vals) - 1), h - 6 - (v / 10) * (h - 12)) for i, v in enumerate(vals)]
    path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    dots = "".join(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='3.5' fill='#0f766e'/>" for x, y in pts)
    return f"<svg viewBox='0 0 {w} {h}' width='100%' height='{h}'><path d='{path}' fill='none' stroke='#0f766e' stroke-width='2.5'/>{dots}</svg>"

def render_analytics(st: AppState) -> str:
    logs = st.logs
    avg = sum(l.score for l in logs) / len(logs) * 10 if logs else 0
    last = logs[-1].score * 10 if logs else 0
    out = cards([("MCQs graded", str(len(logs))), ("Average score", f"{avg:.0f}%" if logs else "-"), ("Latest score", f"{last:.0f}%" if logs else "-"),
                 ("Current mastery", f"{wmean(st.topics.values()):.0%}" if st.topics else "-"),
                 ("Since baseline", f"{(wmean(st.topics.values()) - st.baseline_mastery) * 100:+.0f} pts" if st.topics else "-")])
    out += f"<div class='box'><b>Quiz Score Trend (out of 10)</b>{sparkline([l.score for l in logs[-12:]])}</div>"
    subj: dict[str, list[float]] = {}
    for t in st.topics.values():
        subj.setdefault(t.subject, []).append(t.mastery)
    out += "<div class='box'><b>Mastery by Subject</b>" + "".join(bar(s, s, sum(v) / len(v)) for s, v in subj.items()) + "</div>"
    if logs:
        rows = "".join(f"<tr><td>{E(l.ts)}</td><td>{E(l.subject)} - {E(l.topic)}</td><td>{l.score:.0f}/10</td><td>{l.mastery_before:.0%} to {l.mastery_after:.0%}</td></tr>" for l in reversed(logs[-8:]))
        out += f"<div class='box'><b>Recent Quiz Results</b><table><tr><th>When</th><th>Module</th><th>Score</th><th>Mastery Change</th></tr>{rows}</table></div>"
    return out

def render_feedback(grades: list[GradeResult], note: str) -> str:
    out = []
    total_score = sum(g.score for g in grades)
    max_score = len(grades) * 10
    pct = (total_score / max(1, max_score)) * 100
    correct_count = sum(1 for g in grades if g.is_correct)
    
    out.append(f"## 📊 Quiz Score: {total_score:.0f}/{max_score} ({pct:.0f}%) — {correct_count}/{len(grades)} Correct\n")
    for i, g in enumerate(grades, 1):
        status_icon = "✅ **Correct** (+10 pts)" if g.is_correct else "❌ **Incorrect** (0 pts)"
        user_choice = g.user_answer or "*No option selected (Skipped)*"
        out.append(
            f"### Q{i}: {g.topic} &nbsp; {status_icon}\n"
            f"**Subject:** `{g.subject}`\n\n"
            f"**Question:** {g.question}\n\n"
            f"- **Your Choice:** `{user_choice}`\n"
            f"- **Correct Answer:** `{g.correct_option}`\n\n"
            f"> **💡 Explanation:** {g.explanation}\n"
        )
    if note:
        out.append(f"\n---\n**🤖 Agent Schedule Adjustment:** {note}")
    return "\n".join(out)

def render_calendar_html(exam_str: str) -> str:
    try:
        exam_d = date.fromisoformat(str(exam_str).strip())
    except Exception:
        exam_d = date.today() + timedelta(days=30)
    today = date.today()
    days_left = (exam_d - today).days

    cal_year = today.year
    cal_month = today.month
    cal = calendar.monthcalendar(cal_year, cal_month)
    month_name = calendar.month_name[cal_month]

    html_out = [
        "<div class='cal-card-box' style='background:rgba(15,118,110,0.1);border:1.5px solid #0f766e;border-radius:12px;padding:14px 12px;margin-top:10px;'>",
        "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;'>",
        f"<span style='font-weight:700;color:#2dd4bf;font-size:0.98rem;display:flex;align-items:center;gap:6px;'>🗓️ {month_name} {cal_year}</span>",
        "<span style='background:#0d9488;color:#fff;padding:3px 12px;border-radius:12px;font-size:0.75rem;font-weight:600;box-shadow:0 2px 6px rgba(13,148,136,0.4);'>",
        f"{'⏳ ' + str(days_left) + ' Days to Exam' if days_left > 0 else '🎯 Exam Day!' if days_left == 0 else 'Exam passed'}",
        "</span></div>",
        "<table class='cal-table' style='width:100% !important;table-layout:fixed !important;border-collapse:separate !important;border-spacing:0 !important;border:none !important;margin:0 auto !important;'>",
        "<thead><tr style='border:none !important;border-bottom:1px solid rgba(20,184,166,0.2) !important;'>",
    ]

    for day_name in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]:
        html_out.append(f"<th style='width:14.285% !important;text-align:center !important;vertical-align:middle !important;padding:6px 0 !important;font-size:0.76rem !important;font-weight:600 !important;color:#94a3b8 !important;border:none !important;background:transparent !important;'>{day_name}</th>")
    html_out.append("</tr></thead><tbody>")

    for week in cal:
        html_out.append("<tr style='border:none !important;background:transparent !important;'>")
        for d in week:
            if d == 0:
                html_out.append("<td style='width:14.285% !important;height:36px !important;border:none !important;background:transparent !important;padding:2px 0 !important;'></td>")
            else:
                curr_d = date(cal_year, cal_month, d)
                base_style = "display:inline-flex !important;align-items:center !important;justify-content:center !important;width:30px !important;height:30px !important;margin:0 auto !important;border-radius:8px !important;font-size:0.82rem !important;box-sizing:border-box !important;line-height:1 !important;"
                title = f"{curr_d.strftime('%Y-%m-%d')}"
                if curr_d == today:
                    cell_cls = "cal-day-span cal-day-today"
                    extra_style = "background:#0d9488 !important;color:#ffffff !important;font-weight:700 !important;box-shadow:0 0 8px rgba(13,148,136,0.6) !important;"
                    title += " (Today)"
                elif curr_d == exam_d:
                    cell_cls = "cal-day-span cal-day-exam"
                    extra_style = "background:#d97706 !important;color:#ffffff !important;font-weight:700 !important;box-shadow:0 0 8px rgba(217,119,6,0.7) !important;"
                    title += " (Exam Day)"
                elif today < curr_d < exam_d:
                    cell_cls = "cal-day-span cal-day-prep"
                    extra_style = "background:rgba(20,184,166,0.18) !important;color:#2dd4bf !important;font-weight:600 !important;border:1px solid rgba(20,184,166,0.35) !important;"
                else:
                    cell_cls = "cal-day-span cal-day-normal"
                    extra_style = "color:#94a3b8 !important;opacity:0.8 !important;"
                
                html_out.append(
                    f"<td style='width:14.285% !important;height:36px !important;text-align:center !important;vertical-align:middle !important;padding:2px 0 !important;border:none !important;background:transparent !important;'>"
                    f"<span class='{cell_cls}' style='{base_style}{extra_style}' title='{title}'>{d}</span>"
                    f"</td>"
                )
        html_out.append("</tr>")

    html_out.append("</tbody></table>")
    html_out.append(
        "<div style='margin-top:12px;padding-top:8px;border-top:1px solid rgba(20,184,166,0.15);font-size:0.74rem;display:flex;justify-content:space-around;align-items:center;opacity:0.9;color:#94a3b8;'>"
        "<span style='display:inline-flex;align-items:center;gap:5px;'><span style='display:inline-block;width:8px;height:8px;border-radius:50%;background:#0d9488;'></span>Today</span>"
        "<span style='display:inline-flex;align-items:center;gap:5px;'><span style='display:inline-block;width:8px;height:8px;border-radius:50%;background:#d97706;'></span>Exam Day</span>"
        "<span style='display:inline-flex;align-items:center;gap:5px;'><span style='display:inline-block;width:8px;height:8px;border-radius:50%;background:#2dd4bf;'></span>Prep Window</span>"
        "</div></div>"
    )
    return "".join(html_out)

def view(o: Orchestrator | None) -> tuple:
    """(timeline, table, summary, analytics)"""
    if o is None or o.state.plan is None:
        return (EMPTY, "_No plan yet. Build your plan in the first tab._", EMPTY, EMPTY)
    st = o.state
    return (render_timeline(st), render_table(st, o.horizon), render_summary(st), render_analytics(st))

# ==============================================================================
# CSS & STYLES
# ==============================================================================
CSS = """
.gradio-container{max-width:1200px!important;margin:auto}
.hero{background:linear-gradient(115deg,#0b3b3c,#0f766e 60%,#b45309);color:#fff;padding:22px 26px;border-radius:14px;margin-bottom:12px}
.hero h1{margin:0;font-size:1.75rem;color:#fff}.hero p{margin:6px 0 0;opacity:.92;max-width:75ch}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(125px,1fr));gap:10px;margin:8px 0}
.card{background:var(--background-fill-secondary,#f8fafc);border:1px solid var(--border-color-primary,#e2e8f0);border-radius:10px;padding:10px 12px}
.card .v{font-size:1.45rem;font-weight:700}.card .k{font-size:.78rem;opacity:.7}
.box{border:1px solid var(--border-color-primary,#e2e8f0);border-radius:10px;padding:10px 14px;margin:8px 0}
.box.warn{border-color:#d97706;background:rgba(217,119,6,.08)}.box table{width:100%;border-collapse:collapse}
.box td,.box th{padding:4px 6px;text-align:left;border-bottom:1px solid var(--border-color-primary,#e2e8f0);font-size:.88rem}
.muted{opacity:.65;font-size:.85rem}
.chip{display:inline-flex;align-items:center;gap:5px;border:1.5px solid var(--border-color-primary,#cbd5e1);border-radius:999px;padding:2px 10px;margin:2px 4px 2px 0;font-size:.8rem}
.chip i,.bl i{width:10px;height:10px;border-radius:50%;display:inline-block}
.legend{margin:6px 0}
.barrow{display:grid;grid-template-columns:minmax(180px,280px) 1fr 44px;gap:8px;align-items:center;margin:3px 0;font-size:.85rem}
.bl{display:flex;align-items:center;gap:6px}.bar{height:9px;border-radius:5px;background:rgba(100,116,139,.2);overflow:hidden}.bar div{height:100%}
.bp{text-align:right;font-variant-numeric:tabular-nums}
.tl{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px;margin-top:6px}
.tl .hd{font-size:.72rem;text-align:center;opacity:.6}
.tl .day{min-height:62px;border:1px solid var(--border-color-primary,#e2e8f0);border-radius:8px;padding:4px 6px;background:var(--background-fill-secondary,#f8fafc)}
.tl .today{outline:2.5px solid #0f766e}.tl .past{opacity:.6}.tl .exam{background:linear-gradient(135deg,#fde68a,#fdba74);color:#1f2937}
.tl .n{font-size:.72rem;opacity:.75}.dots{display:flex;flex-wrap:wrap;gap:3px;margin-top:4px}
.dot{width:11px;height:11px;border-radius:50%;display:inline-block;box-sizing:border-box}
.dot.missed{opacity:.4;outline:1.5px solid #dc2626}.dot.done{opacity:.45}.ex{font-weight:700;font-size:.8rem}
.mcq-container{border:1.5px solid var(--border-color-primary,#e2e8f0);border-radius:10px;padding:12px 16px;margin:10px 0;background:var(--background-fill-secondary,#f8fafc)}

/* Interactive Calendar Card */
.cal-card-box { background: rgba(15,118,110,0.1); border: 1.5px solid #0f766e; border-radius: 12px; padding: 14px 12px; margin-top: 10px; }
.cal-table, .cal-table table, table.cal-table { width: 100% !important; table-layout: fixed !important; border-collapse: separate !important; border-spacing: 0 !important; border: none !important; margin: 4px 0 !important; }
.cal-table thead, .cal-table tbody, .cal-table tr { border: none !important; background: transparent !important; }
.cal-table th { width: 14.285% !important; text-align: center !important; vertical-align: middle !important; padding: 6px 0 !important; font-size: 0.76rem !important; font-weight: 600 !important; color: #94a3b8 !important; border: none !important; background: transparent !important; }
.cal-table td { width: 14.285% !important; height: 36px !important; text-align: center !important; vertical-align: middle !important; padding: 2px 0 !important; border: none !important; background: transparent !important; }
.cal-day-span { display: inline-flex !important; align-items: center !important; justify-content: center !important; width: 30px !important; height: 30px !important; margin: 0 auto !important; border-radius: 8px !important; font-size: 0.82rem !important; box-sizing: border-box !important; transition: all 0.15s ease !important; line-height: 1 !important; }
.cal-day-today { background: #0d9488 !important; color: #ffffff !important; font-weight: 700 !important; box-shadow: 0 0 8px rgba(13,148,136,0.6) !important; }
.cal-day-exam { background: #d97706 !important; color: #ffffff !important; font-weight: 700 !important; box-shadow: 0 0 8px rgba(217,119,6,0.7) !important; }
.cal-day-prep { background: rgba(20,184,166,0.18) !important; color: #2dd4bf !important; font-weight: 600 !important; border: 1px solid rgba(20,184,166,0.35) !important; }
.cal-day-normal { color: #94a3b8 !important; opacity: 0.8 !important; }

"""

THEME = gr.themes.Soft(primary_hue="teal", secondary_hue="amber", neutral_hue="slate",  # type: ignore
                       font=[gr.themes.GoogleFont("DM Sans"), "system-ui", "sans-serif"])  # type: ignore

# B.Tech 2nd Year Term 1 Defaults: (include, confidence, quiz score)
DEFAULT_SUBJECTS = {
    "Probability and Statistics": (True, 4, 60),
    "DSA C++": (True, 4, 65),
    "ADBMS": (True, 3, 55),
    "Fundamentals of AI (FAI)": (True, 3, 50),
}

def _need_plan(o: Orchestrator | None) -> bool:
    return o is None or o.state.plan is None

def build_plan(orch, name, exam_str, target, hours, start_hour, uploaded_file, *rows):
    try:
        LLM.refresh()
        exam = date.fromisoformat(str(exam_str).strip())
        days = (exam - date.today()).days
        if days < 2 or days > MAX_HORIZON_DAYS:
            raise ValueError(f"Exam date must be between 2 and {MAX_HORIZON_DAYS} days from today (you entered {days}).")
        
        fname, ftext = extract_file_text(uploaded_file)
        doc_analysis = analyze_uploaded_document(fname, ftext, LLM) if ftext else {}

        subs = []
        for i, sname in enumerate(CURRICULUM):
            inc, conf, score, sel_mods = rows[4 * i : 4 * i + 4]
            if inc:
                chosen = list(sel_mods) if sel_mods else list(CURRICULUM[sname].keys())
                subs.append(SubjectInput(
                    name=sname,
                    confidence=int(conf),
                    quiz_score=float(score),
                    exam_weight=3,
                    selected_modules=chosen
                ))
        if not subs:
            raise ValueError("Select at least one subject.")
        prof = StudentProfile(
            name=(name or "Student").strip() or "Student",
            exam_date=exam,
            target_score=int(target),
            hours_per_day=float(hours),
            start_hour=int(start_hour),
            subjects=subs
        )
        o = Orchestrator()
        o.onboard(prof, doc_analysis=doc_analysis)
        mode = f"OpenAI {LLM.MODEL}" if LLM.live else "offline rule & rubric engine"
        doc_msg = f" (Incorporated '{fname}' into diagnosis)" if fname else ""
        msg = f"**Plan v1 successfully built!** Scheduled {len(o.state.topics)} modules across {len(subs)} subjects over {days} days (Engine: {mode}){doc_msg}. View your timeline in the **Schedule** tab."
        return (o, msg, render_diag(o.state), *view(o))
    except Exception as exc:
        return (orch, f"**Could not build plan:** {exc}", gr.update(), *[gr.update()] * 4)

def do_adapt(orch, missed, fatigue, hours, note):
    if _need_plan(orch):
        return (orch, "Build a plan first.", *view(orch))
    return (orch, orch.adapt(int(missed), int(fatigue), float(hours or 0), note), *view(orch))

def do_complete(orch):
    if _need_plan(orch):
        return (orch, "Build a plan first.", *view(orch))
    return (orch, orch.complete_today(), *view(orch))

def set_horizon(orch, horizon):
    if _need_plan(orch):
        return orch, gr.update()
    orch.horizon = int(horizon)
    return orch, render_table(orch.state, orch.horizon)

def make_quiz(orch, subject_filter, n):
    LLM.refresh()
    max_q = 10
    if _need_plan(orch):
        subs = [
            SubjectInput(name=sname, confidence=c, quiz_score=sc, exam_weight=3, selected_modules=list(CURRICULUM[sname].keys()))
            for sname, (_, c, sc) in DEFAULT_SUBJECTS.items()
        ]
        prof = StudentProfile(name="Student", exam_date=date.today() + timedelta(days=30), target_score=85, hours_per_day=3.0, start_hour=17, subjects=subs)
        orch = Orchestrator()
        orch.onboard(prof)

    n = int(n)
    qs = orch.make_quiz(n, subject_filter=subject_filter)

    group_updates = []
    title_updates = []
    radio_updates = []

    for i in range(max_q):
        if i < len(qs):
            q = qs[i]
            group_updates.append(gr.update(visible=True))
            tag = "🤖 AI" if q.source == "OpenAI Generated" else "📚 Syllabus"
            title_updates.append(f"### Q{i + 1}. {q.topic} `[{q.subject}]` *({tag})*\n**{q.question}**")
            radio_updates.append(gr.update(visible=True, choices=q.options, value=None, label="Select one option:"))
        else:
            group_updates.append(gr.update(visible=False))
            title_updates.append("")
            radio_updates.append(gr.update(visible=False, choices=[], value=None))

    gemini_count = sum(1 for q in qs if q.source == "Gemini Generated")
    openai_count = sum(1 for q in qs if q.source == "OpenAI Generated")

    for i in range(max_q):
        if i < len(qs):
            q = qs[i]
            if q.source == "Gemini Generated":
                tag = "🤖 Gemini AI"
            elif q.source == "OpenAI Generated":
                tag = "🤖 OpenAI"
            else:
                tag = "📚 Syllabus"
            title_updates[i] = f"### Q{i + 1}. {q.topic} `[{q.subject}]` *({tag})*\n**{q.question}**"

    if gemini_count > 0:
        status_msg = f"**🤖 Dynamically generated by Google Gemini ({GEMINI.MODEL}): {len(qs)} fresh questions.** Select your options and click Submit below."
    elif openai_count > 0:
        status_msg = f"**🤖 Dynamically generated by OpenAI ({LLM.MODEL}): {len(qs)} fresh questions.** Select your options and click Submit below."
    elif GEMINI.last_error or LLM.last_error:
        err = GEMINI.last_error or LLM.last_error
        status_msg = (
            f"**⚠️ AI Notice:** {err}<br>"
            f"*(Generated {len(qs)} diverse questions using dynamic syllabus engine with randomized options.)*"
        )
    else:
        status_msg = f"**📚 Dynamically generated from Syllabus: {len(qs)} Questions.** (Paste your Gemini API key in code to enable live AI generation)."

    return (orch, status_msg, *group_updates, *title_updates, *radio_updates, gr.update(visible=bool(qs)), "", *view(orch))

def submit_quiz(orch, *answers):
    if _need_plan(orch) or not orch.state.quiz:
        return (orch, "Please generate a quiz first.", *view(orch))
    if orch.state.quiz_graded:
        return (orch, "This quiz has already been graded. Generate a new quiz above to practice more.", *view(orch))
    note = orch.submit(list(answers)[: len(orch.state.quiz)])
    return (orch, render_feedback(orch.state.last_grades, note), *view(orch))

def update_cal(exam_str):
    return render_calendar_html(exam_str)

def set_days_ahead(days):
    new_d = (date.today() + timedelta(days=days)).isoformat()
    return new_d, render_calendar_html(new_d)


# ==============================================================================
# GRADIO APPLICATION
# ==============================================================================
with gr.Blocks(theme=THEME, css=CSS, title="AI Study Planner & Performance Agent") as demo:
    orch_state = gr.State(None)
    gr.HTML(
        "<div class='hero'>"
        "<h1>🎓 AI Study Planner &amp; Performance Agent</h1>"
        "<p>Curriculum tailored for <b>Probability &amp; Statistics</b>, <b>DSA C++</b>, <b>ADBMS</b>, and <b>Fundamentals of AI (FAI)</b>. "
        "Diagnose module gaps, build spaced-repetition timelines, take Multiple Choice Quizzes with instant grading, and ask questions to the AI Doubt Solver.</p>"
        "</div>"
    )

    with gr.Tabs():
        # --- TAB 1: Onboarding & Diagnostic ---
        with gr.Tab("Onboarding & Diagnostic"):
            with gr.Row():
                # Left Column: Profile, Interactive Calendar, & Optional File Upload
                with gr.Column(scale=2):
                    s_name = gr.Textbox(label="Your name", value="Alex")
                    s_exam = gr.Textbox(label="Exam date (YYYY-MM-DD)", value=(date.today() + timedelta(days=30)).isoformat())
                    s_target = gr.Slider(50, 100, value=85, step=1, label="Target score (%)")
                    s_hours = gr.Slider(0.75, 10, value=3, step=0.25, label="Study hours per day")
                    s_start = gr.Slider(5, 21, value=17, step=1, label="Daily start hour (24h clock)")

                    # Simple Interactive Calendar Section
                    gr.Markdown("### 📅 Exam Countdown & Calendar")
                    cal_html = gr.HTML(render_calendar_html((date.today() + timedelta(days=30)).isoformat()))
                    with gr.Row():
                        btn_15 = gr.Button("+15 Days", size="sm")
                        btn_30 = gr.Button("+30 Days", size="sm")
                        btn_45 = gr.Button("+45 Days", size="sm")
                        btn_60 = gr.Button("+60 Days", size="sm")

                    # Optional File Upload Section
                    gr.Markdown("### 📂 Upload Syllabus / Past Quizzes (Optional)")
                    gr.Markdown("Upload any past quiz attempt, test scores, or extra syllabus file to get an in-depth diagnosis on it:")
                    upload_file = gr.File(
                        label="Upload Document (PDF, TXT, MD, JSON)",
                        file_types=[".txt", ".pdf", ".docx", ".json", ".csv", ".md"],
                        type="filepath"
                    )

                # Right Column: Subjects & Syllabus Module Selection
                with gr.Column(scale=3):
                    gr.Markdown("**B.Tech 2nd Year Term 1 Subjects.** Click **'📚 Syllabus & Modules'** for each subject to review and select which of the 10 modules you want included in your diagnostic & plan.")
                    subject_inputs: list[Any] = []
                    for sname, (inc, conf, score) in DEFAULT_SUBJECTS.items():
                        all_modules = list(CURRICULUM[sname].keys())
                        with gr.Group():
                            with gr.Row():
                                c_inc = gr.Checkbox(value=inc, label=sname, scale=3)
                                c_conf = gr.Slider(1, 5, value=conf, step=1, label="Confidence (1-5)", scale=2)
                                c_score = gr.Slider(0, 100, value=score, step=1, label="Quiz score (%)", scale=2)
                                s_btn = gr.Button("📚 Syllabus & Modules", variant="secondary", scale=2)

                            with gr.Accordion(f"📋 {sname} Syllabus (10 Modules)", open=False) as s_acc:
                                c_mods = gr.CheckboxGroup(
                                    choices=all_modules,
                                    value=all_modules,
                                    label=f"Select {sname} modules to include in diagnostic & study schedule:"
                                )
                                s_btn.click(lambda: gr.update(open=True), outputs=s_acc)

                        subject_inputs += [c_inc, c_conf, c_score, c_mods]

            build_btn = gr.Button("Diagnose and Build My Plan", variant="primary", size="lg")
            build_status = gr.Markdown()
            diag_html = gr.HTML(EMPTY)

        # --- TAB 2: Schedule ---
        with gr.Tab("Schedule"):
            summary_html = gr.HTML(EMPTY)
            with gr.Accordion("Life happened? Rebalance the plan", open=True):
                with gr.Row():
                    a_missed = gr.Slider(0, 14, value=0, step=1, label="Days I missed")
                    a_fatigue = gr.Slider(1, 5, value=2, step=1, label="Fatigue (1 fresh, 5 exhausted)")
                    a_hours = gr.Slider(0, 10, value=0, step=0.25, label="New hours per day (0 keeps current)")
                a_note = gr.Textbox(label="What happened? (optional)", placeholder="e.g. sick with cold for two days")
                with gr.Row():
                    adapt_btn = gr.Button("Adapt Schedule", variant="primary")
                    done_btn = gr.Button("Complete Today and Advance")
                adapt_msg = gr.Markdown()
            timeline_html = gr.HTML(EMPTY)
            horizon = gr.Slider(7, 30, value=14, step=1, label="Days shown in the table")
            table_md = gr.Markdown("_No plan yet. Start in the first tab._")

        # --- TAB 3: Quiz Hub ---
        with gr.Tab("Quiz Hub"):
            with gr.Row():
                with gr.Column(scale=3):
                    with gr.Row():
                        q_subj = gr.Dropdown(
                            choices=["All Subjects", "Probability and Statistics", "DSA C++", "ADBMS", "Fundamentals of AI (FAI)"],
                            value="All Subjects",
                            label="Quiz Subject Filter",
                            scale=3
                        )
                        q_n = gr.Slider(1, 10, value=5, step=1, label="Number of MCQ Questions", scale=2)
                        q_btn = gr.Button("Generate MCQ Quiz", variant="primary", scale=2)

                    quiz_md = gr.Markdown("_Select a subject (or All Subjects) and click **'Generate MCQ Quiz'** to test your knowledge with multiple choice questions._")

                    # 10 MCQ Question Containers (with question text & radio options)
                    q_groups = []
                    q_titles = []
                    q_radios = []
                    for i in range(10):
                        with gr.Group(visible=False, elem_classes="mcq-container") as qg:
                            qt = gr.Markdown()
                            qr = gr.Radio(choices=[], label="Choose one option:", interactive=True)
                            q_groups.append(qg)
                            q_titles.append(qt)
                            q_radios.append(qr)

                    submit_btn = gr.Button("Submit MCQ Answers for Grading & Analysis", variant="primary", visible=False)
                    feedback_md = gr.Markdown()

                with gr.Column(scale=2):
                    analytics_html = gr.HTML(EMPTY)

            # Interactive AI Doubt Solver Chatbot
            with gr.Accordion("🤖 Gemini AI Doubt Solver & Concept Tutor (Ask any doubt)", open=True):
                gr.Markdown("Have a doubt about an MCQ question, why an option was right or wrong, or any B.Tech concept? Ask below:")

                with gr.Row():
                    gemini_key_input = gr.Textbox(
                        label="🔑 Gemini API Key (Enter key here to chat live with Google Gemini)",
                        placeholder="Paste your Gemini API key (AIzaSy...) here",
                        value=GEMINI_API_KEY,
                        type="password",
                        scale=4
                    )
                    connect_key_btn = gr.Button("Connect Gemini Key", variant="secondary", scale=1)

                chat_status_msg = gr.Markdown(
                    "🟢 **Gemini AI Ready & Connected**" if GEMINI.live
                    else "ℹ️ *Enter your Gemini API key above or in line 32 of code to chat live with Gemini!*"
                )

                chatbot = gr.Chatbot(label="Study Doubts Chatbot", height=320, type="messages")
                with gr.Row():
                    chat_msg = gr.Textbox(
                        placeholder="e.g. Hi / Why is median better than mean for outliers? / Explain 2NF vs 3NF with an example / Write C++ code for Stack",
                        show_label=False,
                        scale=5
                    )
                    send_btn = gr.Button("Ask Doubt", variant="primary", scale=1)
                    clear_btn = gr.Button("Clear Chat", scale=1)

                gr.Markdown("💡 **Quick Concept Prompts:** Click any prompt below to get an instant explanation:")
                with gr.Row():
                    p_btn1 = gr.Button("Explain 2NF vs 3NF with an example", size="sm")
                    p_btn2 = gr.Button("Why must A* heuristic be admissible?", size="sm")
                    p_btn3 = gr.Button("Poisson vs Binomial distribution", size="sm")
                    p_btn4 = gr.Button("Stack vs Queue applications in DSA", size="sm")

# --- Reactive Event Wiring ---
    VIEW = [timeline_html, table_md, summary_html, analytics_html]

    s_exam.change(update_cal, [s_exam], [cal_html])
    btn_15.click(lambda: set_days_ahead(15), outputs=[s_exam, cal_html])
    btn_30.click(lambda: set_days_ahead(30), outputs=[s_exam, cal_html])
    btn_45.click(lambda: set_days_ahead(45), outputs=[s_exam, cal_html])
    btn_60.click(lambda: set_days_ahead(60), outputs=[s_exam, cal_html])

    build_btn.click(
        build_plan,
        [orch_state, s_name, s_exam, s_target, s_hours, s_start, upload_file, *subject_inputs],
        [orch_state, build_status, diag_html, *VIEW]
    )
    adapt_btn.click(do_adapt, [orch_state, a_missed, a_fatigue, a_hours, a_note], [orch_state, adapt_msg, *VIEW])
    done_btn.click(do_complete, [orch_state], [orch_state, adapt_msg, *VIEW])
    horizon.change(set_horizon, [orch_state, horizon], [orch_state, table_md])

    # MCQ Quiz Generation & Submission
    q_btn.click(
        make_quiz,
        [orch_state, q_subj, q_n],
        [orch_state, quiz_md, *q_groups, *q_titles, *q_radios, submit_btn, feedback_md, *VIEW]
    )
    submit_btn.click(
        submit_quiz,
        [orch_state, *q_radios],
        [orch_state, feedback_md, *VIEW]
    )

    # Chatbot Handlers
    connect_key_btn.click(connect_gemini_key, [gemini_key_input], [chat_status_msg])
    gemini_key_input.change(connect_gemini_key, [gemini_key_input], [chat_status_msg])

    send_btn.click(answer_doubt, [chatbot, chat_msg, orch_state, gemini_key_input], [chatbot, chat_msg, chat_status_msg])
    chat_msg.submit(answer_doubt, [chatbot, chat_msg, orch_state, gemini_key_input], [chatbot, chat_msg, chat_status_msg])
    clear_btn.click(list, outputs=[chatbot])

    p_btn1.click(lambda h, o, k: answer_doubt(h, "Explain 2NF vs 3NF with an example", o, k), [chatbot, orch_state, gemini_key_input], [chatbot, chat_msg, chat_status_msg])
    p_btn2.click(lambda h, o, k: answer_doubt(h, "Why must A* heuristic be admissible and what happens if it overestimates?", o, k), [chatbot, orch_state, gemini_key_input], [chatbot, chat_msg, chat_status_msg])
    p_btn3.click(lambda h, o, k: answer_doubt(h, "What is the difference between Poisson and Binomial distributions and when is Poisson used as an approximation?", o, k), [chatbot, orch_state, gemini_key_input], [chatbot, chat_msg, chat_status_msg])
    p_btn4.click(lambda h, o, k: answer_doubt(h, "Explain real-world and systems applications of Stacks versus Queues in C++", o, k), [chatbot, orch_state, gemini_key_input], [chatbot, chat_msg, chat_status_msg])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7860"))
    demo.queue().launch(server_name="0.0.0.0", server_port=port)
