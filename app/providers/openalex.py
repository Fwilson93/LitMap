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

        for attempt in range(2):
            try:
                r = httpx.get(BASE_URL, params=params, timeout=4)
                if r.status_code == 429 or r.status_code == 503:
                    time.sleep(1.0)
                    continue
                r.raise_for_status()
                break
            except Exception as e:
                if attempt == 1:
                    print(f">>> OpenAlex failed: {e}")
                    return []
                time.sleep(0.5)

        data = r.json()
        results = []

        for item in data.get("results", []):
            doi = item.get("doi")
            title = item.get("title", "")
            authors = [a.get("author", {}).get("display_name", "") for a in item.get("authorships", [])]
            journal = item.get("host_venue", {}).get("display_name", "")
            year = item.get("publication_year")

            identity = doi or item.get("id") or title
            cid = sha1(identity.encode("utf-8")).hexdigest()[:12]

            results.append(Candidate(
                candidate_id=cid,
                title=title,
                authors=authors,
                journal=journal,
                year=year,
                doi=doi,
                abstract="",
                reasons=[],
                keywords=[]
            ))

        return results
