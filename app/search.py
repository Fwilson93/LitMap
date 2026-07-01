
from app.providers.semantic_scholar import SemanticScholarProvider
from app.providers.openalex import OpenAlexProvider
from app.providers.mock import MockProvider


def _clean_query(q: str) -> str:
    q = q.replace("FeO", "iron oxide")
    q = q.replace("Fe", "iron")
    return q


def run_search(query: str, limit: int = 12):
    clean = _clean_query(query)

    try:
        print(">>> SemanticScholar")
        return SemanticScholarProvider().search(clean, limit)
    except Exception as e:
        print(">>> SemanticScholar failed:", e)
        try:
            print(">>> OpenAlex")
            return OpenAlexProvider().search(clean, limit)
        except Exception as e2:
            print(">>> OpenAlex failed:", e2)
            print(">>> Falling back to mock")
            return MockProvider().search(clean, limit)
