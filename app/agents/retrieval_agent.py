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
    return 0.0


def _is_applicable(record: Dict, query: str) -> bool:
    supported_os = _normalize_text(record.get("supported_os", "any"))
    query_os = _normalize_text(query)
    if supported_os in {"", "any"}:
        return True
    if "windows" in query_os and "windows" in supported_os:
        return True
    return any(
        os_name in supported_os
        for os_name in ("windows 11", "windows 10", "ubuntu", "macos", "android", "ios")
        if os_name in query_os
    ) or not any(os_name in query_os for os_name in ("windows", "ubuntu", "macos", "android", "ios"))


def _symptom_applicable(record: Dict, query: str, category: str | None = None) -> bool:
    if not category or category in {"Unknown", "Multiple services"}:
        return True
    record_category = _normalize_text(record.get("category", ""))
    expected_category = _normalize_text(category)
    if expected_category == record_category or expected_category in record_category or record_category in expected_category:
        return True
    record_text = _normalize_text(f"{record.get('title', '')} {record.get('content', '')}")
    service_terms = {
        "Wi-Fi / DNS": ("wifi", "wireless", "dns", "internet"),
        "VPN": ("vpn", "tunnel", "remote access"),
        "Outlook / MFA": ("outlook", "mfa", "email", "authenticator"),
        "Accounts / Passwords": ("password", "account", "login", "signin"),
        "Printers": ("printer", "printing", "print queue"),
        "Windows / Updates": ("windows", "update", "driver", "blue screen"),
        "Software Installation": ("install", "software", "application"),
        "Remote Desktop": ("rdp", "remote desktop", "remote session"),
    }
    return any(term in record_text for term in service_terms.get(category, ()))


def _infer_supported_os(text: str) -> str:
    lowered = text.lower()
    for os_name in ("Windows 11", "Windows 10", "Ubuntu", "macOS", "Android", "iOS"):
        if os_name.lower() in lowered:
            return os_name
    return "Any"


def _records_from_db(session: Session, approved_only: bool = False) -> List[Dict]:
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

    if approved_only:
        return records

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
            "supported_os": _infer_supported_os(f"{ticket.description}\n{ticket.canonical_issue}\n{ticket.resolution_notes}"),
            "source_type": "resolved_ticket",
            "status": "resolved",
        })

    return records


def search_knowledge(
    session: Session,
    query: str,
    top_k: int = 5,
    approved_only: bool = False,
    category: str | None = None,
    operating_system: str | None = None,
) -> Dict:
    records = _records_from_db(session, approved_only=approved_only)
    query_for_os = f"{query} {operating_system or ''}".strip()
    candidate_records = [
        record for record in records
        if _symptom_applicable(record, query, category)
        and _is_applicable(record, query_for_os)
    ]
    items = hybrid_rank(query_for_os, candidate_records, top_k=max(top_k * 2, top_k))

    boosted_items = []
    for item in items:
        bonus = _metadata_boost(query, item)
        trust = _trust_weight(item)
        if trust <= 0 or not _is_applicable(item, query_for_os) or not _symptom_applicable(item, query, category):
            continue
        adjusted = dict(item)
        adjusted["hybrid_score"] = float(item.get("hybrid_score", 0.0)) * trust + bonus
        adjusted["score_breakdown"] = {
            "bm25_score": float(item.get("bm25_score", 0.0)),
            "semantic_score": float(item.get("semantic_score", 0.0)),
            "hybrid_score": float(adjusted["hybrid_score"]),
        }
        adjusted["source"] = item.get("source_id", "")
        adjusted["applicability"] = {
            "source_eligible": True,
            "symptom_applicable": True,
            "operating_system_applicable": True,
            "evidence_sufficient": bool(str(item.get("content", "")).strip()),
        }
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
