from typing import Dict, List
from sqlmodel import Session, select
from app.config import get_settings
from app.models import KnowledgeArticle, Ticket
from app.services.hybrid_search import hybrid_rank

settings = get_settings()


def _records_from_db(session: Session) -> List[Dict]:
    records: List[Dict] = []

    articles = session.exec(
        select(KnowledgeArticle).where(KnowledgeArticle.status == "approved")
    ).all()
    for article in articles:
        records.append({
            "source_id": article.doc_id,
            "title": article.title,
            "content": article.content,
            "category": article.category,
            "source_type": article.source_type,
            "status": article.status,
        })

    resolved_tickets = session.exec(
        select(Ticket).where(Ticket.status == "RESOLVED")
    ).all()
    for ticket in resolved_tickets:
        if not ticket.resolution_notes.strip():
            continue
        records.append({
            "source_id": ticket.ticket_code,
            "title": ticket.canonical_issue or ticket.title,
            "content": f"Problem: {ticket.description}\nRoot cause: {ticket.root_cause}\nResolution: {ticket.resolution_notes}",
            "category": ticket.category,
            "source_type": "resolved_ticket",
            "status": "resolved",
        })

    return records


def search_knowledge(session: Session, query: str, top_k: int = 5) -> Dict:
    records = _records_from_db(session)
    items = hybrid_rank(query, records, top_k=top_k)
    best_score = items[0]["hybrid_score"] if items else 0.0

    if best_score >= settings.high_confidence_threshold:
        decision = "HIGH"
    elif best_score >= settings.uncertain_threshold:
        decision = "UNCERTAIN"
    else:
        decision = "LOW"

    return {
        "query": query,
        "items": items,
        "best_score": float(best_score),
        "decision": decision,
    }
