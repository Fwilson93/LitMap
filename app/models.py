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

class Decision(str, Enum):
    UNREVIEWED="unreviewed"; YES="yes"; NO="no"; DEFER="defer"

class RetrievalStatus(str, Enum):
    MISSING="missing"
    AUTO="auto"
    MANUAL="manual"
    FAILED="failed"

class Candidate(BaseModel):
    candidate_id:str
    title:str
    authors:list[str]=Field(default_factory=list)
    journal:str=""
    year:Optional[int]=None
    doi:Optional[str]=None
    decision:Decision=Decision.UNREVIEWED

    # retrieval
    pdf_status: RetrievalStatus = RetrievalStatus.MISSING
    local_pdf_path: Optional[str] = None

    si_status: RetrievalStatus = RetrievalStatus.MISSING
    local_si_path: Optional[str] = None

def slugify_filename(candidate: Candidate) -> str:
    author = candidate.authors[0].split()[-1] if candidate.authors else "Unknown"
    year = str(candidate.year) if candidate.year else "noyear"
    title = ''.join(c for c in candidate.title if c.isalnum() or c==' ')[:40].strip().replace(' ','_')
    return f"{author}{year}_{title}.pdf"
