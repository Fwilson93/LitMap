
import httpx
from hashlib import sha1
from app.models import Candidate

API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

class SemanticScholarProvider:
    def search(self, query: str, limit: int):
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,authors,year,venue,abstract,externalIds"
        }
        try:
            r = httpx.get(API_URL, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            raise RuntimeError(f"SemanticScholar request failed: {e}")

        results = []
        for item in data.get("data", []):
            title = item.get("title", "")
            authors = [a.get("name", "") for a in item.get("authors", [])]
            year = item.get("year")
            journal = item.get("venue", "")
            abstract = item.get("abstract", "")

            doi = None
            ext = item.get("externalIds") or {}
            if isinstance(ext, dict):
                doi = ext.get("DOI")

            identity = doi or title
            cid = sha1(identity.encode("utf-8")).hexdigest()[:12]

            results.append(Candidate(
                candidate_id=cid,
                title=title,
                authors=authors,
                journal=journal,
                year=year,
                doi=doi,
                abstract=abstract or "",
                reasons=[],
                keywords=[]
            ))

        return results
