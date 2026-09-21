from datetime import datetime
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select
from app.database import get_session
from app.models import KnowledgeArticle, Ticket
from app.notifications import create_resolution_notification
from app.routes.auth import current_user_from_request

router = APIRouter(prefix="/support", tags=["support"])


def _require_support(request: Request, session: Session):
    user = current_user_from_request(request, session)
    if not user or user.role not in {"IT_SUPPORT", "ADMIN"}:
        raise HTTPException(status_code=403, detail="IT Support role required")
    return user


@router.post("/tickets/{ticket_id}/resolve")
def resolve_ticket(
    ticket_id: int,
    request: Request,
    root_cause: str = Form(...),
    resolution_notes: str = Form(...),
    create_kb_draft: str = Form(default="yes"),
    session: Session = Depends(get_session),
):
    user = _require_support(request, session)
    if user.role != "IT_SUPPORT":
        raise HTTPException(status_code=403, detail="Only IT Support users can resolve tickets")
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.root_cause = root_cause.strip()
    ticket.resolution_notes = resolution_notes.strip()
    ticket.status = "RESOLVED"
    ticket.approval_status = "APPROVED"
    ticket.approved_by = user.id
    ticket.approved_at = datetime.utcnow()
    ticket.assigned_to = user.id
    ticket.learning_summary = (
        ticket.learning_summary
        or f"Resolved in {ticket.category} with root cause '{ticket.root_cause[:80]}'. The support record was approved and stored for future retrieval."
    )
    ticket.updated_at = datetime.utcnow()
    session.add(ticket)
    session.commit()
    create_resolution_notification(session, ticket)

    if create_kb_draft == "yes":
        doc_id = f"KB-DRAFT-{ticket.ticket_code}"
        existing = session.exec(
            select(KnowledgeArticle).where(KnowledgeArticle.doc_id == doc_id)
        ).first()
        if not existing:
            article = KnowledgeArticle(
                doc_id=doc_id,
                title=f"Resolution for {ticket.canonical_issue or ticket.title}",
                content=(
                    f"Problem: {ticket.canonical_issue or ticket.title}\n"
                    f"Root cause: {ticket.root_cause}\n"
                    f"Resolution: {ticket.resolution_notes}"
                ),
                category=ticket.category,
                status="draft",
                source_type="resolved_ticket_draft",
                author=user.username,
                authoritative=False,
            )
            session.add(article)
            session.commit()

    return RedirectResponse(url="/support", status_code=303)
