import httpx
from hashlib import sha1
from app.models import Candidate

API_URL = "https://api.crossref.org/works"

class CrossrefProvider:
    def search(self, query: str, limit: int):
        try:
            r = httpx.get(API_URL, params={"query": query, "rows": limit}, timeout=10)
            r.raise_for_status()
        except Exception as e:
            print(f">>> Crossref failed: {e}")
            return []

        data = r.json()
        results = []

        for item in data.get("message", {}).get("items", []):
            title = "".join(item.get("title", [])[:1])
            authors = []
            for a in item.get("author", []):
                name = " ".join(filter(None, [a.get("given"), a.get("family")]))
                if name:
                    authors.append(name)

            year = None
            if "published-print" in item:
                year = item["published-print"].get("date-parts", [[None]])[0][0]
            elif "published-online" in item:
                year = item["published-online"].get("date-parts", [[None]])[0][0]

            doi = item.get("DOI")
            journal = "".join(item.get("container-title", [])[:1])

            identity = doi or title
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
