from datetime import datetime
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select
from app.database import get_session
from app.models import SolutionFeedback, Ticket
from app.notifications import create_resolution_notification
from app.routes.auth import current_user_from_request
from app.agents.coordinator import process_new_ticket

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _save_feedback(session: Session, ticket: Ticket, user_id: int, rating: str, comment: str = ""):
    feedback = session.exec(
        select(SolutionFeedback).where(
            SolutionFeedback.ticket_id == ticket.id,
            SolutionFeedback.user_id == user_id,
        )
    ).first()
    if not feedback:
        feedback = SolutionFeedback(ticket_id=ticket.id, user_id=user_id, rating=rating)
    feedback.rating = rating
    feedback.comment = comment.strip()[:1000]
    feedback.updated_at = datetime.utcnow()
    session.add(feedback)


@router.post("/create")
def create_ticket(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    session: Session = Depends(get_session),
):
    user = current_user_from_request(request, session)
    if not user:
        return RedirectResponse(url="/", status_code=303)
    if len(title.strip()) < 3 or len(description.strip()) < 10:
        raise HTTPException(status_code=422, detail="Title or description is too short")

    next_number = (session.exec(select(Ticket)).all().__len__()) + 1
    ticket = Ticket(
        ticket_code=f"TCK-{next_number:05d}",
        user_id=user.id,
        title=title.strip(),
        description=description.strip(),
    )
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    process_new_ticket(session, ticket)
    return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)


@router.post("/{ticket_id}/clarify")
def submit_clarification(
    ticket_id: int,
    request: Request,
    answers: str = Form(""),
    answer_1: str = Form(""),
    answer_2: str = Form(""),
    answer_3: str = Form(""),
    session: Session = Depends(get_session),
):
    user = current_user_from_request(request, session)
    if not user:
        return RedirectResponse(url="/", status_code=303)
    ticket = session.get(Ticket, ticket_id)
    if not ticket or ticket.user_id != user.id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    answers = "\n".join(value.strip() for value in (answers, answer_1, answer_2, answer_3) if value.strip()).strip()
    if ticket.status != "CLARIFICATION_REQUIRED":
        raise HTTPException(status_code=409, detail="This ticket is not waiting for clarification")
    if len(answers) < 10 or len(answers) > 3000:
        raise HTTPException(status_code=422, detail="Please provide enough detail to reanalyze the ticket")
    ticket.status = "REANALYZING"
    ticket.updated_at = datetime.utcnow()
    session.add(ticket)
    session.commit()
    try:
        process_new_ticket(session, ticket, additional_context=answers)
    except Exception:
        ticket.status = "ESCALATED"
        ticket.decision_explanation = "Reanalysis could not complete safely. The ticket has been escalated to IT Support."
        ticket.updated_at = datetime.utcnow()
        session.add(ticket)
        session.commit()
        return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)
    return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)


@router.post("/{ticket_id}/solved")
def mark_solved(ticket_id: int, request: Request, session: Session = Depends(get_session)):
    user = current_user_from_request(request, session)
    if not user:
        return RedirectResponse(url="/", status_code=303)
    ticket = session.get(Ticket, ticket_id)
    if not ticket or ticket.user_id != user.id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.status = "CLOSED"
    ticket.solved_by_user = True
    ticket.learning_summary = (
        ticket.learning_summary or f"Customer confirmed the recommended guidance resolved the issue for {ticket.category}."
    )
    ticket.updated_at = datetime.utcnow()
    session.add(ticket)
    _save_feedback(session, ticket, user.id, "HELPFUL")
    session.commit()
    create_resolution_notification(session, ticket)
    return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)


@router.post("/{ticket_id}/not-solved")
def mark_not_solved(ticket_id: int, request: Request, session: Session = Depends(get_session)):
    user = current_user_from_request(request, session)
    if not user:
        return RedirectResponse(url="/", status_code=303)
    ticket = session.get(Ticket, ticket_id)
    if not ticket or ticket.user_id != user.id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.status = "ESCALATED"
    ticket.solved_by_user = False
    ticket.learning_summary = (
        ticket.learning_summary or f"Customer reported the recommendation was not sufficient for {ticket.category}."
    )
    ticket.updated_at = datetime.utcnow()
    session.add(ticket)
    _save_feedback(session, ticket, user.id, "NOT_HELPFUL")
    session.commit()
    return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)


@router.post("/{ticket_id}/approve")
def approve_ai_response(
    ticket_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    user = current_user_from_request(request, session)
    if not user or user.role not in {"IT_SUPPORT", "ADMIN"}:
        return RedirectResponse(url="/", status_code=303)
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.approval_status = "APPROVED"
    ticket.approved_by = user.id
    ticket.approved_at = datetime.utcnow()
    if ticket.status == "SOLUTION_PROPOSED":
        ticket.status = "RESOLVED"
    ticket.updated_at = datetime.utcnow()
    session.add(ticket)
    session.commit()
    create_resolution_notification(session, ticket)
    return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)


@router.post("/{ticket_id}/reject")
def reject_ai_response(
    ticket_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    user = current_user_from_request(request, session)
    if not user or user.role not in {"IT_SUPPORT", "ADMIN"}:
        return RedirectResponse(url="/", status_code=303)
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.approval_status = "REJECTED"
    ticket.approved_by = user.id
    ticket.approved_at = datetime.utcnow()
    ticket.status = "ESCALATED"
    ticket.updated_at = datetime.utcnow()
    session.add(ticket)
    session.commit()
    return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)


@router.post("/{ticket_id}/feedback")
def submit_feedback(
    ticket_id: int,
    request: Request,
    rating: str = Form(...),
    comment: str = Form(""),
    session: Session = Depends(get_session),
):
    user = current_user_from_request(request, session)
    if not user:
        return RedirectResponse(url="/", status_code=303)
    ticket = session.get(Ticket, ticket_id)
    if not ticket or ticket.user_id != user.id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if rating not in {"HELPFUL", "NOT_HELPFUL"}:
        raise HTTPException(status_code=422, detail="Invalid feedback rating")
    _save_feedback(session, ticket, user.id, rating, comment)
    if rating == "HELPFUL":
        ticket.status = "CLOSED"
        ticket.solved_by_user = True
    else:
        ticket.status = "ESCALATED"
        ticket.solved_by_user = False
    ticket.updated_at = datetime.utcnow()
    session.add(ticket)
    session.commit()
    if rating == "HELPFUL":
        create_resolution_notification(session, ticket)
    return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)
