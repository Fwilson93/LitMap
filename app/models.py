from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Set

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Decision(str, Enum):
    UNREVIEWED = "unreviewed"
    YES = "yes"
    NO = "no"
    DEFER = "defer"


class RetrievalStatus(str, Enum):
    MISSING = "missing"
    AUTO = "auto"
    MANUAL = "manual"
    FAILED = "failed"


class NodeType(str, Enum):
    PAPER = "paper"
    AUTHOR = "author"
    TOPIC = "topic"


class EdgeType(str, Enum):
    PAPER_AUTHOR = "paper-author"
    PAPER_TOPIC = "paper-topic"


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
    pdf_status: RetrievalStatus = RetrievalStatus.MISSING
    local_pdf_path: Optional[str] = None
    si_status: RetrievalStatus = RetrievalStatus.MISSING
    local_si_path: Optional[str] = None


class ExpansionCandidate(BaseModel):
    candidate_id: str
    title: str
    source: str
    source_type: str


class Project(BaseModel):
    project_id: str
    title: str
    description: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    candidates: list[Candidate] = Field(default_factory=list)
    expansion_candidates: list[ExpansionCandidate] = Field(default_factory=list)
    blacklist: Set[str] = Field(default_factory=set)
    graph: Graph = Field(default_factory=Graph)

    @classmethod
    def create(cls, title: str, description: str = "") -> "Project":
        return cls(
            project_id=title.lower().replace(" ", "-"),
            title=title,
            description=description,
        )

    def touch(self) -> None:
        self.updated_at = utc_now()

    def upsert_candidates(self, incoming, query: str = "") -> None:
        existing = {c.candidate_id: c for c in self.candidates}
        merged: dict[str, Candidate] = {}
        for item in incoming:
            previous = existing.get(item.candidate_id)
            if previous is None:
                merged[item.candidate_id] = item
                continue
            merged[item.candidate_id] = item.model_copy(
                update={
                    "decision": previous.decision,
                    "pdf_status": previous.pdf_status,
                    "local_pdf_path": previous.local_pdf_path,
                    "si_status": previous.si_status,
                    "local_si_path": previous.local_si_path,
                }
            )
        for cid, item in existing.items():
            if cid not in merged:
                merged[cid] = item
        self.candidates = list(merged.values())
        self.touch()

    def get_candidate(self, cid):
        for candidate in self.candidates:
            if candidate.candidate_id == cid:
                return candidate
        raise KeyError(cid)

    def set_decision(self, cid, d: Decision):
        candidate = self.get_candidate(cid)
        candidate.decision = d
        self.touch()
        return candidate

    def blacklist_item(self, cid):
        self.blacklist.add(cid)
        self.expansion_candidates = [
            candidate
            for candidate in self.expansion_candidates
            if candidate.candidate_id != cid
        ]
        self.touch()
