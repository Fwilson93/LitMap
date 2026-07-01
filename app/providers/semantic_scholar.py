import httpx
import time
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

        for attempt in range(3):
            try:
                r = httpx.get(API_URL, params=params, timeout=10)
                if r.status_code == 429:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                r.raise_for_status()
                break
            except Exception:
                if attempt == 2:
                    return []
                time.sleep(1.0 * (attempt + 1))

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

        return results
