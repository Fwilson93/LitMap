from typing import List
from app.providers.semantic_scholar import SemanticScholarProvider
from app.providers.openalex import OpenAlexProvider
from app.providers.crossref import CrossrefProvider
from app.models import Candidate

PROVIDERS = [
    CrossrefProvider(),
    SemanticScholarProvider(),
    OpenAlexProvider(),
]

STOPWORDS = {"the", "of", "and", "in", "for", "with", "on", "at"}

def normalize_query(q: str) -> str:
    q = q.replace("FeO", "iron oxide")
    q = q.replace("Fe", "iron")
    return q.strip()

def generate_query_variants(query: str) -> List[str]:
    q = normalize_query(query)

    variants = []

    variants.append(q)
    variants.append(f'"{q}"')

    tokens = [t for t in q.lower().split() if t not in STOPWORDS]
    if tokens:
        variants.append(" ".join(tokens))

    tokens_no_year = [t for t in tokens if not (t.isdigit() and len(t) == 4)]
    if tokens_no_year:
        variants.append(" ".join(tokens_no_year))

    seen = set()
    final = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            final.append(v)

    return final

def shape_query_for_provider(query: str, provider_name: str) -> str:
    tokens = query.split()

    words = [t for t in tokens if not (t.isdigit() and len(t) == 4)]

    if provider_name in ["OpenAlexProvider", "CrossrefProvider"] and len(words) > 1:
        return " ".join(words[::-1])

    return query

def safe_provider_search(provider, query: str, limit: int):
    try:
        return provider.search(query, limit)
    except Exception as e:
        print(f">>> {provider.__class__.__name__} failed: {e}")
        return []

def merge_results(results: List[Candidate]) -> List[Candidate]:
    by_key = {}
    for r in results:
        key = r.doi or r.title.lower().strip()
        if key not in by_key:
            by_key[key] = r
    return list(by_key.values())

def run_search(query: str, limit: int = 12):
    variants = generate_query_variants(query)

    all_results: List[Candidate] = []

    for provider in PROVIDERS:
        print(f">>> {provider.__class__.__name__}")

        for v in variants:
            shaped = shape_query_for_provider(v, provider.__class__.__name__)
            results = safe_provider_search(provider, shaped, limit)

            print(f">>>   variant: '{shaped}' → {len(results)} results")

            all_results.extend(results)

    merged = merge_results(all_results)

    print(f">>> total merged results: {len(merged)}")

    return merged[:limit]
