
import httpx
from hashlib import sha1
from app.models import Candidate

BASE_URL = "https://api.openalex.org/works"

class OpenAlexProvider:
    def search(self, query: str, limit: int):
        try:
            params = {
                "search": query,
                "per_page": limit
            }
            r = httpx.get(BASE_URL, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
        except Exception:
            raise RuntimeError("OpenAlex request failed")

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
