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
    cleaned=[]; last=False
    for c in value.lower().strip():
        if c.isalnum(): cleaned.append(c); last=False
        elif not last: cleaned.append("-"); last=True
    return "".join(cleaned).strip("-") or "project"

class Decision(str, Enum):
    UNREVIEWED="unreviewed"; YES="yes"; NO="no"; DEFER="defer"

class NodeType(str, Enum):
    PAPER="paper"; AUTHOR="author"; TOPIC="topic"

class EdgeType(str, Enum):
    PAPER_AUTHOR="paper_author"; PAPER_TOPIC="paper_topic"

class TimelineEvent(BaseModel):
    event_id:str=Field(default_factory=lambda:make_id("evt"))
    event_type:str; timestamp:datetime=Field(default_factory=utc_now)
    message:str; payload:dict[str,Any]=Field(default_factory=dict)

class Candidate(BaseModel):
    candidate_id:str; title:str
    authors:list[str]=Field(default_factory=list)
    journal:str=""; year:Optional[int]=None
    doi:Optional[str]=None; abstract:str=""
    reasons:list[str]=Field(default_factory=list)
    keywords:list[str]=Field(default_factory=list)
    decision:Decision=Decision.UNREVIEWED
    notes:str=""; local_pdf_present:bool=False
    local_pdf_path:Optional[str]=None
    local_supplement_present:bool=False
    local_supplement_path:Optional[str]=None

class GraphNode(BaseModel):
    node_id:str; node_type:NodeType; label:str

class GraphEdge(BaseModel):
    edge_id:str; edge_type:EdgeType
    source:str; target:str; label:str=""

class Graph(BaseModel):
    nodes:list[GraphNode]=Field(default_factory=list)
    edges:list[GraphEdge]=Field(default_factory=list)

class RetrievalItem(BaseModel):
    candidate_id:str; title:str
    pdf_missing:bool; supplement_missing:bool; lookup_hint:str

class ExpansionCandidate(BaseModel):
    candidate_id:str; title:str; source:str

class Project(BaseModel):
    project_id:str; title:str; description:str=""; search_query:str=""
    created_at:datetime=Field(default_factory=utc_now)
    updated_at:datetime=Field(default_factory=utc_now)
    candidates:list[Candidate]=Field(default_factory=list)
    graph:Graph=Field(default_factory=Graph)
    timeline:list[TimelineEvent]=Field(default_factory=list)
    expansion_candidates:list[ExpansionCandidate]=Field(default_factory=list)
    blacklist:Set[str]=Field(default_factory=set)

    @classmethod
    def create(cls,title:str,description:str=""):
        p=cls(project_id=slugify(title),title=title,description=description)
        p.timeline.append(TimelineEvent(event_type="project_created",message=f"Created project '{title}'."))
        return p

    def candidate_map(self): return {c.candidate_id:c for c in self.candidates}

    def replace_candidates(self,incoming:list[Candidate],query:str):
        existing=self.candidate_map(); new=[]
        for i in incoming:
            if i.candidate_id in existing:
                cur=existing[i.candidate_id]; i.decision=cur.decision; i.notes=cur.notes
            new.append(i)
        self.candidates=new; self.search_query=query

    def upsert_candidates(self,incoming:list[Candidate],query:str=""):
        m=self.candidate_map()
        for i in incoming: m[i.candidate_id]=i
        self.candidates=list(m.values())
        if query: self.search_query=query

    def add_event(self,et, msg, **pl):
        self.timeline.insert(0,TimelineEvent(event_type=et,message=msg,payload=pl))

    def get_candidate(self,cid:str):
        for c in self.candidates:
            if c.candidate_id==cid: return c
        raise KeyError(cid)

    def set_decision(self,cid:str,d:Decision,notes:str=""):
        c=self.get_candidate(cid); c.decision=d; c.notes=notes
        self.add_event("candidate_decision",f"Marked '{c.title}' as {d.value}.",candidate_id=cid,decision=d.value)
        return c

    def add_expansion(self,items):
        for i in items:
            if i.candidate_id in self.blacklist: continue
            if i.candidate_id not in [c.candidate_id for c in self.expansion_candidates]:
                self.expansion_candidates.append(i)

    def blacklist_item(self,cid):
        self.blacklist.add(cid)
        self.expansion_candidates=[c for c in self.expansion_candidates if c.candidate_id!=cid]
