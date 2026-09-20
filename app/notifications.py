from __future__ import annotations

from typing import List

from sqlmodel import Session, select

from app.models import Notification, Ticket


def get_user_notifications(session: Session, user_id: int, limit: int = 8) -> List[Notification]:
    return session.exec(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.id.desc())
        .limit(limit)
    ).all()


def create_resolution_notification(session: Session, ticket: Ticket) -> Notification | None:
    if ticket.status not in {"RESOLVED", "CLOSED"}:
        return None

    existing = session.exec(
        select(Notification).where(
            Notification.ticket_id == ticket.id,
            Notification.notification_type == "ticket_resolved",
        )
    ).first()
    if existing:
        return existing

    message = (
        f"Your ticket '{ticket.title}' has been marked as resolved. "
        "Please confirm the fix worked for you."
        if ticket.status == "RESOLVED"
        else f"Your ticket '{ticket.title}' has been closed successfully."
    )

    notification = Notification(
        user_id=ticket.user_id,
        ticket_id=ticket.id,
        title="Ticket resolved",
        message=message,
        notification_type="ticket_resolved",
    )
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification
