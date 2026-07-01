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
    for v in variants:
        v = v.strip()
        if v and v not in seen:
            seen.add(v)
            final.append(v)

    return final

def shape_query_for_provider(query: str, provider_name: str) -> str:
    tokens = query.replace('"', '').split()
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
        key = (r.doi or r.title.lower().strip())
        if key not in by_key:
            by_key[key] = r
    return list(by_key.values())

def score_result(query: str, r: Candidate) -> float:
    score = 0.0
    q = query.lower()

    # title match boost
    if r.title:
        title = r.title.lower()
        if q in title:
            score += 5.0
        overlap = sum(1 for t in q.split() if t in title)
        score += overlap * 0.5

    # author hint (very light)
    if r.authors:
        for a in r.authors:
            if any(tok in a.lower() for tok in q.split()):
                score += 1.0
                break

    # year proximity
    import re
    m = re.search(r"(19|20)\d{2}", q)
    if m and r.year:
        try:
            yq = int(m.group())
            if abs(r.year - yq) <= 1:
                score += 2.0
        except:
            pass

    return score

def rank_results(query: str, results: List[Candidate]) -> List[Candidate]:
    scored = [(score_result(query, r), r) for r in results]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored]

def run_search(query: str, limit: int = 12):
    variants = generate_query_variants(query)

    all_results: List[Candidate] = []

    for provider in PROVIDERS:
        pname = provider.__class__.__name__
        print(f">>> {pname}")

        max_v = MAX_VARIANTS.get(pname, 1)
        provider_success = False

        for v in variants[:max_v]:
            shaped = shape_query_for_provider(v, pname)
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

        if not provider_success and pname != "CrossrefProvider":
            print(f">>> skipping further effort on {pname} (no results)")

    merged = merge_results(all_results)
    ranked = rank_results(query, merged)

    print(f">>> total merged results: {len(ranked)}")

    return ranked[:limit]
