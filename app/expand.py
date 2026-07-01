from app.providers.crossref import CrossrefProvider
from app.providers.openalex import OpenAlexProvider
from app.models import ExpansionCandidate, Candidate

crossref = CrossrefProvider()
openalex = OpenAlexProvider()


def expand_from_candidate(candidate: Candidate, limit: int = 6):
    results = []

    # --- attempt citation-like using DOI first ---
    query = candidate.doi if candidate.doi else candidate.title
    try:
        citation_results = crossref.search(query, limit)
    except Exception:
        citation_results = []

    # --- author expansion ---
    author_results = []
    if candidate.authors:
        try:
            author_results = openalex.search(candidate.authors[0], max(2, limit//2))
        except Exception:
            author_results = []

    combined = citation_results + author_results

    seen = set()
    for r in combined:
        key = (r.doi or r.title.lower())
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
