from datetime import datetime
from uuid import uuid4
from sqlmodel import Session
from app.models import AgentLog, SecurityEvent, Ticket, TicketCitation
from app.agents.security_agent import check_input
from app.agents.ticket_agent import analyze_ticket, summarize_ticket_history
from app.agents.retrieval_agent import search_knowledge
from app.agents.solution_agent import recommend_solution


def _log(session: Session, request_id: str, sender: str, receiver: str, task: str, payload_summary: str, status: str = "OK"):
    session.add(AgentLog(
        request_id=request_id,
        message_id=f"msg-{uuid4().hex[:10]}",
        sender=sender,
        receiver=receiver,
        task=task,
        payload_summary=payload_summary[:1000],
        status=status,
    ))
    session.commit()


def process_new_ticket(session: Session, ticket: Ticket) -> dict:
    request_id = f"KG-{datetime.utcnow().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"

    _log(session, request_id, "coordinator_agent", "security_agent", "check_input", ticket.description)
    security = check_input(ticket.description)

    if security["flags"]:
        session.add(SecurityEvent(
            request_id=request_id,
            event_type="PROMPT_INJECTION",
            severity="MEDIUM",
            details=", ".join(security["flags"]),
        ))
        session.commit()

    ticket.masked_description = security["masked_text"]

    _log(session, request_id, "coordinator_agent", "ticket_agent", "analyze_ticket", security["masked_text"])
    analysis = analyze_ticket(security["masked_text"])
    ticket.category = analysis["category"]
    ticket.priority = analysis.get("priority", "Medium")
    ticket.canonical_issue = analysis["canonical_issue"]
    ticket.history_summary = summarize_ticket_history(
        security["masked_text"],
        ticket.category,
        ticket.priority,
        ticket.canonical_issue,
    )

    _log(session, request_id, "coordinator_agent", "retrieval_agent", "retrieve_knowledge", ticket.canonical_issue)
    retrieval = search_knowledge(session, ticket.canonical_issue, top_k=5)
    ticket.retrieval_confidence = retrieval["best_score"]

    _log(session, request_id, "retrieval_agent", "solution_agent", "recommend_solution", str(retrieval["items"][:2]))
    solution = recommend_solution(ticket.canonical_issue, retrieval)

    ticket.recommended_solution = solution["message"]
    ticket.decision_explanation = solution.get("explanation") or solution.get("confidence_explanation") or ""
    ticket.suggested_reply = solution.get("suggested_reply") or ""
    ticket.approval_status = "PENDING"
    for rank, citation in enumerate(solution.get("citations", []), start=1):
        session.add(TicketCitation(
            ticket_id=ticket.id,
            source_id=citation["source_id"],
            title=citation["title"],
            category=citation.get("category", "Unknown"),
            source_type=citation.get("source_type", "internal_kb"),
            relevance_score=float(citation.get("relevance_score", 0.0)),
            rank=rank,
        ))
    if solution["can_recommend"]:
        ticket.status = "SOLUTION_PROPOSED"
        ticket.source_used = solution["source_id"]
    else:
        ticket.status = "ESCALATED"
        ticket.source_used = ""

    ticket.updated_at = datetime.utcnow()
    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    _log(session, request_id, "coordinator_agent", "user", "final_response", solution["message"])

    return {
        "request_id": request_id,
        "security": security,
        "analysis": analysis,
        "retrieval": retrieval,
        "solution": solution,
        "ticket": ticket,
    }
