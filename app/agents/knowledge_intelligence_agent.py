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
MAX_CLUSTER_TICKETS = 120


def analyze_knowledge_health(session: Session) -> Dict:
    global _health_cache, _health_cache_time

    now = time.time()

    if _health_cache is not None and (now - _health_cache_time) < HEALTH_CACHE_SECONDS:
        return _health_cache

    tickets = session.exec(select(Ticket)).all()
    category_counts = Counter(t.category for t in tickets)
    ranked_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:MAX_CATEGORY_ROWS]
    samples = defaultdict(list)
    for ticket in tickets:
        if ticket.category not in {category for category, _ in ranked_categories}:
            continue
        if len(samples[ticket.category]) < 2:
            samples[ticket.category].append(ticket.canonical_issue or ticket.title)

    approved_articles = session.exec(
        select(KnowledgeArticle).where(KnowledgeArticle.status == "approved")
    ).all()
    articles_by_category: Dict[str, List[KnowledgeArticle]] = defaultdict(list)
    for article in approved_articles:
        articles_by_category[article.category].append(article)

    rows: List[Dict] = []
    for category, count in ranked_categories:
        if len(tickets) > 60:
            known_articles = len(articles_by_category.get(category, []))
            coverage = min(0.95, max(0.2, (known_articles / max(1, count / 2)) * 0.7))
        else:
            query = " ".join(samples[category]) or category
            result = search_knowledge(session, query, top_k=3)
            coverage = float(result.get("best_score", 0.0))
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
    if len(tickets) < MAX_CLUSTER_TICKETS:
        texts = [t.canonical_issue or t.title for t in tickets]
        vectors = encode_texts(texts)
        n_clusters = min(5, len(tickets))
        if n_clusters >= 2:
            model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = model.fit_predict(vectors)
            for cluster_id in range(n_clusters):
                members = [tickets[i] for i, label in enumerate(labels) if label == cluster_id]
                if not members:
                    continue
                cat = Counter(t.category for t in members).most_common(1)[0][0]
                cluster_summary.append({
                    "cluster_id": cluster_id + 1,
                    "label": cat,
                    "count": len(members),
                    "example": members[0].canonical_issue or members[0].title,
                })

    _health_cache = {"health": rows, "clusters": cluster_summary}
    _health_cache_time = now
    return _health_cache
