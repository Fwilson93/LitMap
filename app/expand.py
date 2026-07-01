from app.providers.semantic_scholar import SemanticScholarProvider
from app.providers.openalex import OpenAlexProvider
from app.providers.crossref import CrossrefProvider
from app.models import ExpansionCandidate, Candidate

ss = SemanticScholarProvider()
openalex = OpenAlexProvider()
crossref = CrossrefProvider()

def expand_from_candidate(candidate: Candidate, limit:int=8):
    results=[]
    seen=set()

    # --- REAL citations ---
    graph = ss.fetch_graph(candidate.doi) if candidate.doi else {}

    for section, stype in [("references","citation"),("citations","citation")]:
        for item in graph.get(section,[])[:limit]:
            c = ss.to_candidate(item)
            key = c.doi or c.title
            if key in seen: continue
            seen.add(key)
            results.append(ExpansionCandidate(
                candidate_id=f"exp-{c.candidate_id}",
                title=c.title,
                source=candidate.candidate_id,
                source_type="citation"
            ))

    # --- AUTHOR expansion ---
    if candidate.authors:
        for r in openalex.search(candidate.authors[0], limit//2):
            key = r.doi or r.title
            if key in seen: continue
            seen.add(key)
            results.append(ExpansionCandidate(
                candidate_id=f"exp-{r.candidate_id}",
                title=r.title,
                source=candidate.candidate_id,
                source_type="author"
            ))

    # --- fallback ---
    if not results:
        for r in crossref.search(candidate.title, limit):
            key = r.doi or r.title
            if key in seen: continue
            seen.add(key)
            results.append(ExpansionCandidate(
                candidate_id=f"exp-{r.candidate_id}",
                title=r.title,
                source=candidate.candidate_id,
                source_type="fallback"
            ))

    return results[:limit]
