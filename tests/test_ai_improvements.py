from sqlmodel import Session

from app.agents.solution_agent import recommend_solution
from app.agents.ticket_agent import analyze_ticket
from app.database import create_db_and_tables, engine
from app.models import Ticket, User
from app.notifications import create_resolution_notification, get_user_notifications


def test_resolution_notification_created_for_customer():
    create_db_and_tables()
    with Session(engine) as session:
        user = User(username="notify_user", full_name="Notify User", hashed_password="x", role="CUSTOMER")
        session.add(user)
        session.commit()
        session.refresh(user)

        ticket = Ticket(
            ticket_code="TCK-NOTIFY-001",
            user_id=user.id,
            title="Wi-Fi keeps dropping",
            description="The Wi-Fi randomly disconnects every few minutes.",
            category="Wi-Fi / DNS",
            status="RESOLVED",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)

        notification = create_resolution_notification(session, ticket)
        assert notification is not None
        assert notification.user_id == user.id
        assert notification.ticket_id == ticket.id
        assert "resolved" in notification.title.lower()
        assert get_user_notifications(session, user.id)[0].ticket_id == ticket.id


def test_analyze_ticket_sets_priority_and_category():
    analysis = analyze_ticket("VPN login failed and my MFA approval never arrived")
    assert analysis["category"] == "VPN"
    assert analysis["priority"] in {"Critical", "High", "Medium", "Low"}


def test_recommend_solution_includes_explanation_and_reply():
    retrieval = {
        "decision": "HIGH",
        "best_score": 0.93,
        "items": [
            {
                "source_id": "KB-101",
                "title": "Reset VPN MFA registration",
                "content": "Remove the old MFA registration and complete the VPN MFA setup again.",
                "category": "VPN",
                "source_type": "internal_kb",
                "hybrid_score": 0.93,
            }
        ],
    }
    result = recommend_solution("VPN login failed after MFA change", retrieval)
    assert "explanation" in result and result["explanation"]
    assert "suggested_reply" in result and result["suggested_reply"]
