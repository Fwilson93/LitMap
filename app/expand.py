from app.providers.semantic_scholar import SemanticScholarProvider
from app.providers.openalex import OpenAlexProvider
from app.providers.crossref import CrossrefProvider
from app.models import ExpansionCandidate, Candidate

ss = SemanticScholarProvider()
openalex = OpenAlexProvider()
crossref = CrossrefProvider()


def expand_from_candidate(candidate: Candidate, limit: int = 8):
    results = []
    seen = set()

    graph = ss.fetch_graph(candidate.doi) if candidate.doi else {}
    if not isinstance(graph, dict):
        graph = {}

    for section, source_type in [("references", "citation"), ("citations", "citation")]:
        section_items = graph.get(section) or []
        if not isinstance(section_items, list):
            section_items = []
        for item in section_items[:limit]:
            c = ss.to_candidate(item)
            key = c.doi or c.title
            if not key or key in seen:
                continue
            seen.add(key)
            results.append(
                ExpansionCandidate(
                    candidate_id=f"exp-{c.candidate_id}",
                    title=c.title,
                    source=candidate.candidate_id,
                    source_type=source_type,
                )
            )

    if candidate.authors:
        for r in openalex.search(candidate.authors[0], max(limit // 2, 1)):
            key = r.doi or r.title
            if not key or key in seen:
                continue
            seen.add(key)
            results.append(
                ExpansionCandidate(
                    candidate_id=f"exp-{r.candidate_id}",
                    title=r.title,
                    source=candidate.candidate_id,
                    source_type="author",
                )
            )

    if not results:
        for r in crossref.search(candidate.title, limit):
            key = r.doi or r.title
            if not key or key in seen:
                continue
            seen.add(key)
            results.append(
                ExpansionCandidate(
                    candidate_id=f"exp-{r.candidate_id}",
                    title=r.title,
                    source=candidate.candidate_id,
                    source_type="fallback",
                )
            )

    return results[:limit]
