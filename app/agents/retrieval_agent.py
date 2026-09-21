import re
from typing import Dict, List

from sqlmodel import Session, select

from app.config import get_settings
from app.models import KnowledgeArticle, Ticket
from app.services.hybrid_search import hybrid_rank

settings = get_settings()


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _metadata_boost(query: str, record: Dict) -> float:
    q = _normalize_text(query)
    q_tokens = set(q.split())
    bonus = 0.0

    category = _normalize_text(record.get("category", ""))
    if category and any(token in category for token in q_tokens):
        bonus += 0.18

    supported_os = _normalize_text(record.get("supported_os", ""))
    if supported_os and supported_os != "any":
        if "windows 11" in q and ("windows 11" in supported_os or "windows" in supported_os):
            bonus += 0.18
        elif "windows 10" in q and ("windows 10" in supported_os or "windows" in supported_os):
            bonus += 0.15
        elif "ubuntu" in q and "ubuntu" in supported_os:
            bonus += 0.14
        elif "mac" in q and ("mac" in supported_os or "macos" in supported_os):
            bonus += 0.14

    if record.get("status") in {"approved", "resolved"}:
        bonus += 0.08

    return bonus


def _trust_weight(record: Dict) -> float:
    status = str(record.get("status", "")).lower()
    source_type = str(record.get("source_type", "")).lower()

    if status == "draft" or "draft" in source_type:
        return 0.0
    if status == "approved" or source_type == "internal_kb":
        return 1.0
    if status == "resolved" or source_type == "resolved_ticket":
        return 0.85
    return 0.7


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
            "supported_os": article.supported_os,
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
            "supported_os": "Any",
            "source_type": "resolved_ticket",
            "status": "resolved",
        })

    return records


def search_knowledge(session: Session, query: str, top_k: int = 5) -> Dict:
    records = _records_from_db(session)
    items = hybrid_rank(query, records, top_k=top_k)

    boosted_items = []
    for item in items:
        bonus = _metadata_boost(query, item)
        trust = _trust_weight(item)
        adjusted = dict(item)
        adjusted["hybrid_score"] = float(item.get("hybrid_score", 0.0)) * trust + bonus
        adjusted["score_breakdown"] = {
            "bm25_score": float(item.get("bm25_score", 0.0)),
            "semantic_score": float(item.get("semantic_score", 0.0)),
            "hybrid_score": float(adjusted["hybrid_score"]),
        }
        adjusted["source"] = item.get("source_id", "")
        boosted_items.append(adjusted)

    items = sorted(boosted_items, key=lambda x: x["hybrid_score"], reverse=True)[:top_k]
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
