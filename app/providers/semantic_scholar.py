
import httpx
from hashlib import sha1
from typing import List
from app.models import Candidate

API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

class SemanticScholarProvider:
    def search(self, query: str, limit: int) -> List[Candidate]:
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,authors,year,venue,abstract,externalIds"
        }

        r = httpx.get(API_URL, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        results = []
        for item in data.get("data", []):
            title = item.get("title", "")
            authors = [a.get("name", "") for a in item.get("authors", [])]
            year = item.get("year")
            journal = item.get("venue", "")
            abstract = item.get("abstract", "") or ""

            ext = item.get("externalIds") or {}
            doi = ext.get("DOI") if isinstance(ext, dict) else None

            identity = doi or title
            cid = sha1(identity.encode("utf-8")).hexdigest()[:12]

            results.append(Candidate(
                candidate_id=cid,
                title=title,
                authors=authors,
                journal=journal,
                year=year,
                doi=doi,
                abstract=abstract,
                reasons=[],
                keywords=[]
            ))

        if len(results) < 3:
            raise RuntimeError("SemanticScholar weak results")

        return results
