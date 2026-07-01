import httpx
import time
from hashlib import sha1
from app.models import Candidate

BASE_URL = "https://api.openalex.org/works"

class OpenAlexProvider:
    def search(self, query: str, limit: int):
        params = {
            "search": query,
            "per_page": limit
        }

        for attempt in range(3):
            try:
                r = httpx.get(BASE_URL, params=params, timeout=10)
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

        for item in data.get("results", []):
            doi = item.get("doi")
            title = item.get("title", "")
            authors = [a.get("author", {}).get("display_name", "") for a in item.get("authorships", [])]
            journal = item.get("host_venue", {}).get("display_name", "")
            year = item.get("publication_year")

            abstract = item.get("abstract_inverted_index")
            abstract_text = ""
            if isinstance(abstract, dict):
                words = sorted(((pos, word) for word, positions in abstract.items() for pos in positions))
                abstract_text = " ".join(word for _, word in words)

            identity = doi or item.get("id") or title
            cid = sha1(identity.encode("utf-8")).hexdigest()[:12]

            results.append(Candidate(
                candidate_id=cid,
                title=title,
                authors=authors,
                journal=journal,
                year=year,
                doi=doi,
                abstract=abstract_text,
                reasons=[],
                keywords=[]
            ))

        return results
