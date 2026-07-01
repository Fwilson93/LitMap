
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
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


class Decision(str, Enum):
    UNREVIEWED = "unreviewed"
    YES = "yes"
    NO = "no"
    DEFER = "defer"


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


class Graph(BaseModel):
    nodes: list[Any] = Field(default_factory=list)
    edges: list[Any] = Field(default_factory=list)


class Project(BaseModel):
    project_id: str
    title: str
    description: str = ""
    search_query: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    candidates: list[Candidate] = Field(default_factory=list)
    graph: Graph = Field(default_factory=Graph)
    timeline: list[Any] = Field(default_factory=list)

    def replace_candidates(self, incoming, query: str) -> None:
        existing = {c.candidate_id: c for c in self.candidates}
        new_candidates = []

        for item in incoming:
            if item.candidate_id in existing:
                current = existing[item.candidate_id]
                item.decision = current.decision
                item.notes = current.notes

            new_candidates.append(item)

        self.candidates = new_candidates
        self.search_query = query
