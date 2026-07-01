from app.providers.crossref import CrossrefProvider
from app.models import ExpansionCandidate, Candidate

provider = CrossrefProvider()

def expand_from_candidate(candidate: Candidate, limit: int = 5):
    results = []

    if candidate.doi:
        try:
            # simple heuristic: reuse search on title for related work
            refs = provider.search(candidate.title, limit)
        except Exception:
            refs = []
    else:
        refs = provider.search(candidate.title, limit)

    for r in refs:
        results.append(ExpansionCandidate(
            candidate_id=f"exp-{r.candidate_id}",
            title=r.title,
            source=candidate.candidate_id
        ))

    return results
