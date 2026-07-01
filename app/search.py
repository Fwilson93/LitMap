
from app.providers.openalex import OpenAlexProvider
from app.providers.mock import MockProvider


def run_search(query: str, limit: int = 12):
    provider = OpenAlexProvider()
    try:
        return provider.search(query, limit)
    except Exception:
        return MockProvider().search(query, limit)
