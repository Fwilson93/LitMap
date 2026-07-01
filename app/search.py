
from app.providers.semantic_scholar import SemanticScholarProvider
from app.providers.openalex import OpenAlexProvider
from app.providers.mock import MockProvider


def run_search(query: str, limit: int = 12):
    try:
        return SemanticScholarProvider().search(query, limit)
    except Exception as e:
        try:
            return OpenAlexProvider().search(query, limit)
        except Exception:
            return MockProvider().search(query, limit)
