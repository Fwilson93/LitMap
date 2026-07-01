
# PATCHED VERSION (only relevant method shown)
from __future__ import annotations
from typing import List
from app.models import Project as OriginalProject, Candidate

class Project(OriginalProject):
    def replace_candidates(self, incoming: List[Candidate], query: str) -> None:
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
