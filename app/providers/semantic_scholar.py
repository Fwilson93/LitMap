import httpx
from app.models import Candidate

API = "https://api.semanticscholar.org/graph/v1/paper/"

class SemanticScholarProvider:

    def fetch_graph(self, doi: str):
        if not doi:
            return {}
        url = API + f"{doi}"
        params = {"fields": "title,authors,year,venue,externalIds,references,citations,openAccessPdf"}
        try:
            r = httpx.get(url, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception:
            return {}

    def to_candidate(self, item):
        title = item.get("title", "")
        authors = [a.get("name", "") for a in item.get("authors", [])]
        year = item.get("year")
        journal = item.get("venue", "")
        doi = (item.get("externalIds") or {}).get("DOI")
        return Candidate(
            candidate_id=(doi or title)[:12],
            title=title,
            authors=authors,
            journal=journal,
            year=year,
            doi=doi
        )
