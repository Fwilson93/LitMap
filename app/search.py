import re
from typing import List

from app.models import Candidate
from app.providers.crossref import CrossrefProvider
from app.providers.openalex import OpenAlexProvider
from app.providers.semantic_scholar import SemanticScholarProvider

PROVIDERS = [
    CrossrefProvider(),
    SemanticScholarProvider(),
    OpenAlexProvider(),
]

STOPWORDS = {"the", "of", "and", "in", "for", "with", "on", "at"}
MAX_VARIANTS = {
    "CrossrefProvider": 2,
    "SemanticScholarProvider": 1,
    "OpenAlexProvider": 1,
}


def normalize_query(q: str) -> str:
    q = q.replace("FeO", "iron oxide")
    q = q.replace("Fe", "iron")
    return q.strip()


def generate_query_variants(query: str) -> List[str]:
    q = normalize_query(query)
    variants = [q, f'"{q}"']
    tokens = [t for t in q.lower().split() if t not in STOPWORDS]
    if tokens:
        variants.append(" ".join(tokens))
    tokens_no_year = [t for t in tokens if not (t.isdigit() and len(t) == 4)]
    if tokens_no_year:
        variants.append(" ".join(tokens_no_year))
    seen = set()
    final = []
    for variant in variants:
        variant = variant.strip()
        if variant and variant not in seen:
            seen.add(variant)
            final.append(variant)
    return final


def shape_query_for_provider(query: str, provider_name: str) -> str:
    tokens = query.replace('"', '').split()
    words = [t for t in tokens if not (t.isdigit() and len(t) == 4)]
    if provider_name in ["OpenAlexProvider", "CrossrefProvider"] and len(words) > 1:
        return " ".join(words[::-1])
    return query


def safe_provider_search(provider, query: str, limit: int):
    search_fn = getattr(provider, "search", None)
    if not callable(search_fn):
        print(f">>> {provider.__class__.__name__} has no search() method; skipping")
        return []
    try:
        return search_fn(query, limit)
    except Exception as exc:
        print(f">>> {provider.__class__.__name__} failed: {exc}")
        return []


def merge_results(results: List[Candidate]) -> List[Candidate]:
    by_key = {}
    for result in results:
        key = result.doi or result.title.lower().strip()
        if key not in by_key:
            by_key[key] = result
    return list(by_key.values())


def score_result(query: str, result: Candidate) -> float:
    score = 0.0
    q = query.lower()
    if result.title:
        title = result.title.lower()
        if q in title:
            score += 5.0
        overlap = sum(1 for token in q.split() if token in title)
        score += overlap * 0.5
    if result.authors:
        for author in result.authors:
            if any(token in author.lower() for token in q.split()):
                score += 1.0
                break
    match = re.search(r"(19|20)\d{2}", q)
    if match and result.year:
        try:
            year_query = int(match.group())
            if abs(result.year - year_query) <= 1:
                score += 2.0
        except Exception:
            pass
    return score


def rank_results(query: str, results: List[Candidate]) -> List[Candidate]:
    scored = [(score_result(query, result), result) for result in results]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [result for _, result in scored]


def run_search(query: str, limit: int = 12):
    variants = generate_query_variants(query)
    all_results: List[Candidate] = []
    for provider in PROVIDERS:
        provider_name = provider.__class__.__name__
        print(f">>> {provider_name}")
        max_variants = MAX_VARIANTS.get(provider_name, 1)
        provider_success = False
        for variant in variants[:max_variants]:
            shaped = shape_query_for_provider(variant, provider_name)
            results = safe_provider_search(provider, shaped, limit)
            print(f">>>   variant: '{shaped}' → {len(results)} results")
            if results:
                provider_success = True
            all_results.extend(results)
            merged_now = merge_results(all_results)
            if len(merged_now) >= limit:
                ranked = rank_results(query, merged_now)
                print(f">>> total merged results: {len(ranked)} (early stop)")
                return ranked[:limit]
        if not provider_success and provider_name != "CrossrefProvider":
            print(f">>> skipping further effort on {provider_name} (no results)")
    merged = merge_results(all_results)
    ranked = rank_results(query, merged)
    print(f">>> total merged results: {len(ranked)}")
    return ranked[:limit]
