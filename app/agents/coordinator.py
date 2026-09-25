from datetime import datetime
from uuid import uuid4
from sqlmodel import Session, select
from app.models import AgentLog, SecurityEvent, Ticket, TicketCitation
from app.agents.security_agent import check_input
from app.agents.ticket_agent import (
    analyze_ticket,
    build_clarified_issue,
    serialize_clarification_state,
    summarize_ticket_history,
)
from app.agents.retrieval_agent import search_knowledge
from app.agents.solution_agent import clarification_response, recommend_solution


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


def process_new_ticket(session: Session, ticket: Ticket, additional_context: str = "") -> dict:
    request_id = f"KG-{datetime.utcnow().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"

    analysis_text = ticket.description
    if additional_context.strip():
        analysis_text += f"\nClarification answers:\n{additional_context.strip()}"
    _log(session, request_id, "coordinator_agent", "security_agent", "check_input", analysis_text)
    security = check_input(analysis_text)

    if security["flags"]:
        session.add(SecurityEvent(
            request_id=request_id,
            event_type="PROMPT_INJECTION",
            severity="MEDIUM",
            details=", ".join(security["flags"]),
        ))
        session.commit()

    ticket.masked_description = security["masked_text"]
    structured_issue = None
    effective_text = security["masked_text"]
    if additional_context.strip():
        original_masked, _, answers_masked = security["masked_text"].partition("\nClarification answers:")
        structured_issue = build_clarified_issue(original_masked, answers_masked.strip())
        effective_text = structured_issue.get("effective_query", "")

    _log(session, request_id, "coordinator_agent", "ticket_agent", "analyze_ticket", effective_text)
    analysis = analyze_ticket(effective_text, structured_issue=structured_issue)
    ticket.category = analysis["category"]
    ticket.priority = analysis.get("priority", "Medium")
    ticket.canonical_issue = analysis["canonical_issue"]
    ticket.history_summary = summarize_ticket_history(
        security["masked_text"],
        ticket.category,
        ticket.priority,
        ticket.canonical_issue,
    )

    if analysis.get("ambiguity_required"):
        solution = clarification_response(analysis)
        if structured_issue is None:
            structured_issue = {
                "confirmed_active_symptoms": [],
                "resolved_or_negated_symptoms": [],
                "operating_system": None,
                "affected_service": "",
                "original_context": ticket.description,
                "remaining_uncertainties": analysis.get("ambiguity_reasons", []),
                "effective_query": "",
            }
        structured_issue["clarification_questions"] = solution.get("clarification_questions", [])
        ticket.retrieval_confidence = 0.0
        ticket.recommended_solution = solution["message"]
        state_line = serialize_clarification_state(structured_issue)
        ticket.decision_explanation = state_line + "\nClarification required before retrieval:\n" + "\n".join(
            f"{index}. {question}"
            for index, question in enumerate(solution.get("clarification_questions", []), start=1)
        )
        if additional_context.strip():
            ticket.decision_explanation += f"\nClarification answers supplied:\n{additional_context.strip()}"
        ticket.suggested_reply = solution.get("suggested_reply", "")
        ticket.approval_status = "PENDING"
        ticket.source_used = ""
        ticket.status = "CLARIFICATION_REQUIRED"
        ticket.updated_at = datetime.utcnow()
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        _log(session, request_id, "coordinator_agent", "user", "clarification_required", ticket.decision_explanation)
        return {
            "request_id": request_id,
            "security": security,
            "analysis": analysis,
            "retrieval": {"query": ticket.canonical_issue, "items": [], "best_score": 0.0, "decision": "CLARIFICATION_REQUIRED"},
            "solution": solution,
            "ticket": ticket,
        }

    _log(session, request_id, "coordinator_agent", "retrieval_agent", "retrieve_knowledge", ticket.canonical_issue)
    retrieval = search_knowledge(
        session,
        ticket.canonical_issue,
        top_k=5,
        category=analysis.get("category"),
        operating_system=(structured_issue or {}).get("operating_system"),
    )
    ticket.retrieval_confidence = retrieval["best_score"]

    solution = recommend_solution(ticket.canonical_issue, retrieval)

    solution_succeeded = solution["can_recommend"]
    _log(
        session,
        request_id,
        "retrieval_agent",
        "solution_agent",
        "recommend_solution" if solution_succeeded else "evaluate_evidence",
        str(retrieval["items"][:2]),
        status="OK" if solution_succeeded else "ESCALATED",
    )

    ticket.recommended_solution = solution["message"]
    ticket.decision_explanation = solution.get("explanation") or solution.get("confidence_explanation") or ""
    if structured_issue:
        ticket.decision_explanation = f"{serialize_clarification_state(structured_issue)}\n{ticket.decision_explanation}"
    if additional_context.strip():
        ticket.decision_explanation = f"Clarification answers supplied:\n{additional_context.strip()}\n\n{ticket.decision_explanation}"
    ticket.suggested_reply = solution.get("suggested_reply") or ""
    ticket.approval_status = "PENDING"
    for old_citation in session.exec(select(TicketCitation).where(TicketCitation.ticket_id == ticket.id)).all():
        session.delete(old_citation)
    session.flush()
    seen_sources = set()
    for rank, citation in enumerate(solution.get("citations", []), start=1):
        if citation["source_id"] in seen_sources:
            continue
        seen_sources.add(citation["source_id"])
        session.add(TicketCitation(
            ticket_id=ticket.id,
            source_id=citation["source_id"],
            title=citation["title"],
            category=citation.get("category", "Unknown"),
            source_type=citation.get("source_type", "internal_kb"),
            relevance_score=float(citation.get("relevance_score", 0.0)),
            rank=len(seen_sources),
        ))
    if solution_succeeded:
        ticket.status = "SOLUTION_PROPOSED"
        ticket.source_used = solution["source_id"]
    else:
        ticket.status = "ESCALATED"
        ticket.source_used = ""

    ticket.updated_at = datetime.utcnow()
    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    _log(
        session,
        request_id,
        "coordinator_agent",
        "user",
        "final_response" if solution_succeeded else "escalation_response",
        solution["message"],
    )

    return {
        "request_id": request_id,
        "security": security,
        "analysis": analysis,
        "retrieval": retrieval,
        "solution": solution,
        "ticket": ticket,
    }
