from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1

from app.models import Candidate


@dataclass(frozen=True)
class SearchRecord:
    title: str
    authors: tuple[str, ...]
    journal: str
    year: int | None
    doi: str | None
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
        abstract="Classic conductivity paper covering iron at core conditions and useful as a seed item for core transport maps.",
        keywords=("conductivity", "iron", "core", "thermal", "electrical"),
        reasons=("concept:core transport", "concept:conductivity"),
    ),
    SearchRecord(
        title="Thermal and electrical conductivity of solid iron and iron-silicon mixtures at Earth's core conditions",
        authors=("Matteo Pozzo", "Chris Davies", "David Gubbins", "Dario Alfè"),
        journal="Earth and Planetary Science Letters",
        year=2013,
        doi="10.1016/j.epsl.2013.09.040",
        abstract="Extension of conductivity work into solid iron and iron-silicon mixtures at core conditions.",
        keywords=("conductivity", "iron", "silicon", "core"),
        reasons=("concept:core transport", "concept:alloys"),
    ),
    SearchRecord(
        title="Large low shear velocity provinces and the structure of the lowermost mantle",
        authors=("B. Romanowicz", "J. Hernlund"),
        journal="Annual Review of Earth and Planetary Sciences",
        year=2008,
        doi="10.1146/annurev.earth.36.031207.124139",
        abstract="Review of lowermost mantle structure and LLSVP interpretations.",
        keywords=("mantle", "llsvp", "tomography", "deep earth"),
        reasons=("concept:mantle structure",),
    ),
    SearchRecord(
        title="OpenAlex: A fully open index of scholarly works, authors, venues, institutions, and concepts",
        authors=("Jason Priem", "Heather Piwowar", "Richard Orr"),
        journal="Quantitative Science Studies",
        year=2022,
        doi="10.1162/qss_a_00198",
        abstract="A paper describing the OpenAlex literature index and concept graph.",
        keywords=("openalex", "metadata", "scholarly graph"),
        reasons=("concept:metadata infrastructure",),
    ),
)


def _score(query: str, record: SearchRecord) -> int:
    lowered = query.lower().strip()
    if not lowered:
        return 0
    terms = {term for term in lowered.replace('-', ' ').split() if term}
    haystack = ' '.join((record.title, record.journal, ' '.join(record.authors), ' '.join(record.keywords))).lower()
    score = 0
    for term in terms:
        if term in haystack:
            score += 2
    if lowered in haystack:
        score += 3
    return score


def run_search(query: str, limit: int = 12) -> list[Candidate]:
    ranked = sorted(
        ((record, _score(query, record)) for record in CATALOGUE),
        key=lambda item: (item[1], item[0].year or 0),
        reverse=True,
    )
    chosen = [record for record, score in ranked if score > 0][:limit]
    if not chosen and query.strip():
        chosen = list(CATALOGUE[: min(limit, 3)])
    results: list[Candidate] = []
    for record in chosen:
        identity = record.doi or record.title
        candidate_id = sha1(identity.encode('utf-8')).hexdigest()[:12]
        results.append(
            Candidate(
                candidate_id=candidate_id,
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
