from app.providers.crossref import CrossrefProvider
from app.providers.openalex import OpenAlexProvider
from app.models import ExpansionCandidate, Candidate

crossref = CrossrefProvider()
openalex = OpenAlexProvider()


def expand_from_candidate(candidate: Candidate, limit: int = 5):
    results = []

    # --- citation-style (Crossref search by title / DOI) ---
    try:
        refs = crossref.search(candidate.doi or candidate.title, limit)
    except Exception:
        refs = []

    # --- author expansion ---
    author_results = []
    if candidate.authors:
        primary_author = candidate.authors[0]
        try:
            author_results = openalex.search(primary_author, limit // 2 or 1)
        except Exception:
            author_results = []

    combined = refs + author_results

    seen = set()

    for r in combined:
        key = r.doi or r.title.lower()
        if key in seen:
            continue
        seen.add(key)

        results.append(ExpansionCandidate(
            candidate_id=f"exp-{r.candidate_id}",
            title=r.title,
            source=candidate.candidate_id
        ))

        if len(results) >= limit:
            break

    return results
