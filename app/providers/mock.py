from hashlib import sha1
from dataclasses import dataclass
from typing import Optional
from app.models import Candidate

@dataclass(frozen=True)
class SearchRecord:
    title: str
    authors: tuple[str, ...]
    journal: str
    year: Optional[int]
    doi: Optional[str]
    abstract: str
    keywords: tuple[str, ...]
    reasons: tuple[str, ...] = ()

CATALOGUE: tuple[SearchRecord, ...] = (
    SearchRecord(
        title="Thermal and electrical conductivity of iron at Earth's core conditions",
        authors=("Matteo Pozzo", "Chris Davies", "David Gubbins", "Dario Alfè"),
        journal="Nature",
        year=2012,
        doi="10.1038/nature11031",
        abstract="Classic conductivity paper covering iron at core conditions.",
        keywords=("conductivity", "iron", "core"),
        reasons=("concept:core transport",),
    ),
    # (you can keep or extend this later)
)

class MockProvider:
    def search(self, query: str, limit: int):
        results = []

        for record in CATALOGUE[:limit]:
            identity = record.doi or record.title
            cid = sha1(identity.encode("utf-8")).hexdigest()[:12]

            results.append(
                Candidate(
                    candidate_id=cid,
                    title=record.title,
                    authors=list(record.authors),
                    journal=record.journal,
                    year=record.year,
                    doi=record.doi,
                    abstract=record.abstract,
                    reasons=list(record.reasons),
                    keywords=list(record.keywords),
                )
            )

        return results
