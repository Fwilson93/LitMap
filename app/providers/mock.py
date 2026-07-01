
from app.search import CATALOGUE
from app.models import Candidate
from hashlib import sha1

class MockProvider:
    def search(self, query: str, limit: int):
        results = []
        for record in CATALOGUE[:limit]:
            identity = record.doi or record.title
            cid = sha1(identity.encode('utf-8')).hexdigest()[:12]
            results.append(Candidate(
                candidate_id=cid,
                title=record.title,
                authors=list(record.authors),
                journal=record.journal,
                year=record.year,
                doi=record.doi,
                abstract=record.abstract,
                reasons=list(record.reasons),
                keywords=list(record.keywords),
            ))
        return results
