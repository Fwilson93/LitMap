from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Set
from uuid import uuid4
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def slugify(value: str) -> str:
    cleaned: list[str] = []
    last_dash = False
    for char in value.lower().strip():
        if char.isalnum():
            cleaned.append(char)
            last_dash = False
        elif not last_dash:
            cleaned.append("-")
            last_dash = True
    return "".join(cleaned).strip("-") or "project"

# -----------------------------
# Enums (RESTORED)
# -----------------------------
class Decision(str, Enum):
    UNREVIEWED = "unreviewed"
    YES = "yes"
    NO = "no"
    DEFER = "defer"

class NodeType(str, Enum):
    PAPER = "paper"
    AUTHOR = "author"
    TOPIC = "topic"

class EdgeType(str, Enum):
    PAPER_AUTHOR = "paper_author"
    PAPER_TOPIC = "paper_topic"

# -----------------------------
# Core Models (RESTORED)
# -----------------------------
class TimelineEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: make_id("evt"))
    event_type: str
    timestamp: datetime = Field(default_factory=utc_now)
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)

class Candidate(BaseModel):
    candidate_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    journal: str = ""
    year: Optional[int] = None
    doi: Optional[str] = None
    abstract: str = ""
    reasons: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    decision: Decision = Decision.UNREVIEWED
    notes: str = ""
    local_pdf_present: bool = False
    local_pdf_path: Optional[str] = None
    local_supplement_present: bool = False
    local_supplement_path: Optional[str] = None

# -----------------------------
# Graph Models (RESTORED)
# -----------------------------
class GraphNode(BaseModel):
    node_id: str
    node_type: NodeType
    label: str


class GraphEdge(BaseModel):
    edge_id: str
    edge_type: EdgeType
    source: str
    target: str
    label: str = ""


class Graph(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class RetrievalItem(BaseModel):
    candidate_id: str
    title: str
    pdf_missing: bool
    supplement_missing: bool
    lookup_hint: str

# -----------------------------
# NEW: Expansion Models
# -----------------------------
class ExpansionCandidate(BaseModel):
    candidate_id: str
    title: str
    source: str

# -----------------------------
# Project Model (RESTORED + EXTENDED)
# -----------------------------
class Project(BaseModel):
    project_id: str
    title: str
    description: str = ""
    search_query: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    candidates: list[Candidate] = Field(default_factory=list)
    graph: Graph = Field(default_factory=Graph)
    timeline: list[TimelineEvent] = Field(default_factory=list)

    # ✅ NEW additions (non-breaking)
    expansion_candidates: list[ExpansionCandidate] = Field(default_factory=list)
    blacklist: Set[str] = Field(default_factory=set)

    @classmethod
    def create(cls, title: str, description: str = "") -> "Project":
        project = cls(
            project_id=slugify(title),
            title=title,
            description=description,
        )
        project.timeline.append(
            TimelineEvent(
                event_type="project_created",
                message=f"Created project '{title}'.",
            )
        )
        return project

    def touch(self) -> None:
        self.updated_at = utc_now()

    def candidate_map(self) -> dict[str, Candidate]:
        return {c.candidate_id: c for c in self.candidates}

    def replace_candidates(self, incoming: list[Candidate], query: str) -> None:
        existing = self.candidate_map()
        new = []
        for item in incoming:
            if item.candidate_id in existing:
                current = existing[item.candidate_id]
                item.decision = current.decision
                item.notes = current.notes
            new.append(item)
        self.candidates = new
        self.search_query = query

    def add_event(self, event_type: str, message: str, **payload: Any) -> None:
        self.timeline.insert(
            0,
            TimelineEvent(
                event_type=event_type,
                message=message,
                payload=payload,
            ),
        )
        self.touch()

    def get_candidate(self, candidate_id: str) -> Candidate:
        for c in self.candidates:
            if c.candidate_id == candidate_id:
                return c
        raise KeyError(candidate_id)

    def set_decision(self, candidate_id: str, decision: Decision, notes: str = "") -> Candidate:
        candidate = self.get_candidate(candidate_id)
        candidate.decision = decision
        candidate.notes = notes
        self.add_event(
            "candidate_decision",
            f"Marked '{candidate.title}' as {decision.value}.",
            candidate_id=candidate_id,
            decision=decision.value,
        )
        return candidate

    # ✅ NEW expansion-safe helpers
    def add_expansion(self, items: list[ExpansionCandidate]) -> None:
        for item in items:
            if item.candidate_id in self.blacklist:
                continue
            if item.candidate_id not in [c.candidate_id for c in self.expansion_candidates]:
                self.expansion_candidates.append(item)

    def blacklist_item(self, cid: str) -> None:
        self.blacklist.add(cid)
        self.expansion_candidates = [c for c in self.expansion_candidates if c.candidate_id != cid]
