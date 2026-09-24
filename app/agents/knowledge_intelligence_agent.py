import time
from collections import Counter, defaultdict
from typing import Dict, List
from sqlmodel import Session, select
from sklearn.cluster import KMeans
from app.models import KnowledgeArticle, Ticket
from app.services.embeddings import encode_texts
from app.agents.retrieval_agent import search_knowledge

_health_cache = None
_health_cache_time = 0
HEALTH_CACHE_SECONDS = 300
MAX_CATEGORY_ROWS = 5
MIN_CLUSTER_TICKETS = 8
MAX_CLUSTER_TICKETS = 160
HEALTH_SAMPLE_SIZE = 3


def _representative_queries(tickets: List[Ticket], limit: int) -> List[str]:
    candidates = []
    seen = set()
    for ticket in sorted(tickets, key=lambda item: item.id or 0):
        query = (ticket.canonical_issue or ticket.title or "").strip()
        if query and query not in seen:
            candidates.append(query)
            seen.add(query)

    if len(candidates) <= limit:
        return candidates

    indexes = [round(index * (len(candidates) - 1) / (limit - 1)) for index in range(limit)]
    return [candidates[index] for index in indexes]


def _deterministic_sample(tickets: List[Ticket], limit: int) -> List[Ticket]:
    ordered = sorted(tickets, key=lambda item: item.id or 0)
    if len(ordered) <= limit:
        return ordered
    indexes = [round(index * (len(ordered) - 1) / (limit - 1)) for index in range(limit)]
    return [ordered[index] for index in indexes]


def analyze_knowledge_health(session: Session) -> Dict:
    global _health_cache, _health_cache_time

    now = time.time()

    if _health_cache is not None and (now - _health_cache_time) < HEALTH_CACHE_SECONDS:
        return _health_cache

    tickets = session.exec(select(Ticket)).all()
    category_counts = Counter(t.category for t in tickets)
    ranked_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:MAX_CATEGORY_ROWS]
    approved_articles = session.exec(
        select(KnowledgeArticle).where(KnowledgeArticle.status == "approved")
    ).all()
    articles_by_category: Dict[str, List[KnowledgeArticle]] = defaultdict(list)
    for article in approved_articles:
        articles_by_category[article.category].append(article)

    rows: List[Dict] = []
    for category, count in ranked_categories:
        category_tickets = [ticket for ticket in tickets if ticket.category == category]
        category_articles = articles_by_category.get(category, [])
        if not category_articles:
            coverage = 0.0
        else:
            queries = _representative_queries(category_tickets, HEALTH_SAMPLE_SIZE) or [category]
            scores = []
            for query in queries:
                result = search_knowledge(session, query, top_k=3, approved_only=True)
                scores.append(min(1.0, max(0.0, float(result.get("best_score", 0.0)))))
            # This is evidence coverage: the mean strength of a few representative
            # ticket-to-approved-article matches, not retrieval accuracy.
            coverage = sum(scores) / len(scores) if scores else 0.0
        if coverage >= 0.68:
            gap = "Adequate"
        elif coverage >= 0.55:
            gap = "Moderate"
        elif coverage >= 0.35:
            gap = "Partial"
        else:
            gap = "GAP"
        rows.append({
            "category": category,
            "tickets": count,
            "coverage": round(coverage, 3),
            "gap": gap,
        })

    cluster_summary = []
    cluster_tickets = _deterministic_sample(tickets, MAX_CLUSTER_TICKETS)
    if MIN_CLUSTER_TICKETS <= len(cluster_tickets):
        texts = [t.canonical_issue or t.title for t in cluster_tickets]
        vectors = encode_texts(texts)
        n_clusters = min(5, len(cluster_tickets))
        if n_clusters >= 2:
            model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = model.fit_predict(vectors)
            for cluster_id in range(n_clusters):
                members = [cluster_tickets[i] for i, label in enumerate(labels) if label == cluster_id]
                if not members:
                    continue
                cat = Counter(t.category for t in members).most_common(1)[0][0]
                cluster_summary.append({
                    "cluster_id": cluster_id + 1,
                    "label": cat,
                    "count": len(members),
                    "example": members[0].canonical_issue or members[0].title,
                    "sampled": len(tickets) > MAX_CLUSTER_TICKETS,
                })

    _health_cache = {"health": rows, "clusters": cluster_summary}
    _health_cache_time = now
    return _health_cache
