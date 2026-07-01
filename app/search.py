
from app.providers.semantic_scholar import SemanticScholarProvider
from app.providers.openalex import OpenAlexProvider
from app.providers.mock import MockProvider


def run_search(query: str, limit: int = 12):
    try:
        print(">>> SemanticScholar")
        return SemanticScholarProvider().search(query, limit)
    except Exception as e:
        print(">>> SemanticScholar failed:", e)
        try:
            print(">>> OpenAlex")
            return OpenAlexProvider().search(query, limit)
        except Exception as e2:
            print(">>> OpenAlex failed:", e2)
            print(">>> Falling back to mock")
            return MockProvider().search(query, limit)
