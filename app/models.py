from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Set
from pydantic import BaseModel, Field

class Decision(str, Enum):
    UNREVIEWED="unreviewed"; YES="yes"; NO="no"; DEFER="defer"

class RetrievalStatus(str, Enum):
    MISSING="missing"; AUTO="auto"; MANUAL="manual"; FAILED="failed"

class Candidate(BaseModel):
    candidate_id:str
    title:str
    authors:list[str]=Field(default_factory=list)
    journal:str=""; year:Optional[int]=None
    doi:Optional[str]=None
    decision:Decision=Decision.UNREVIEWED

    pdf_status: RetrievalStatus = RetrievalStatus.MISSING
    local_pdf_path: Optional[str] = None

    si_status: RetrievalStatus = RetrievalStatus.MISSING
    local_si_path: Optional[str] = None

class ExpansionCandidate(BaseModel):
    candidate_id:str
    title:str
    source:str
    source_type:str

class Project(BaseModel):
    project_id:str
    title:str
    description:str=""
    candidates:list[Candidate]=Field(default_factory=list)
    expansion_candidates:list[ExpansionCandidate]=Field(default_factory=list)
    blacklist:Set[str]=Field(default_factory=set)

    @classmethod
    def create(cls,title:str,description:str=""):
        return cls(project_id=title.lower().replace(" ","-"), title=title, description=description)

    def upsert_candidates(self,incoming,query:str=""):
        existing={c.candidate_id:c for c in self.candidates}
        for i in incoming:
            existing[i.candidate_id]=i
        self.candidates=list(existing.values())

    def get_candidate(self,cid):
        for c in self.candidates:
            if c.candidate_id==cid: return c
        raise KeyError(cid)

    def set_decision(self,cid,d:Decision):
        c=self.get_candidate(cid); c.decision=d; return c

    def blacklist_item(self,cid):
        self.blacklist.add(cid)
        self.expansion_candidates=[c for c in self.expansion_candidates if c.candidate_id!=cid]
