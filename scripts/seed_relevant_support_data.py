from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlmodel import Session, select

from app.database import create_db_and_tables, engine
from app.models import KnowledgeArticle, Ticket, User


KB_ARTICLES = [
    {
        "doc_id": "KB-VPN-WIN11-DISCONNECT",
        "title": "Windows 11 VPN disconnects after login",
        "content": (
            "Use this procedure when an approved VPN connects successfully and then disconnects after login on Windows 11. "
            "Confirm the VPN client is organization-supported, install the current approved client update, restart the client, "
            "and recreate the VPN profile using the approved organization settings. Escalate if the disconnect continues."
        ),
        "category": "VPN",
        "supported_os": "Windows 11",
    },
    {
        "doc_id": "KB-VPN-LOGIN-DISCONNECT-CHECKS",
        "title": "VPN disconnects immediately after authentication",
        "content": (
            "For a VPN that disconnects immediately after successful authentication, record the client version and connection time, "
            "verify the device date and time, and compare the configuration with the approved VPN profile. Do not change firewall "
            "or routing rules without IT Support approval. Escalate with the collected details if the approved profile still fails."
        ),
        "category": "VPN",
        "supported_os": "Any",
    },
]

RESOLVED_TICKETS = [
    {
        "ticket_code": "SUP-VPN-WIN11-001",
        "title": "Windows 11 VPN connects then disconnects",
        "description": (
            "The approved VPN connects after login but disconnects within one minute on a Windows 11 work laptop. "
            "Wi-Fi and internet access remain available."
        ),
        "category": "VPN",
        "root_cause": "The installed VPN client was outdated and its local connection profile was inconsistent with the current service configuration.",
        "resolution_notes": "Installed the current organization-approved VPN client and recreated the approved VPN connection profile. The user confirmed the tunnel remained connected.",
    },
    {
        "ticket_code": "SUP-VPN-WIN11-002",
        "title": "VPN drops after successful login on Windows 11",
        "description": (
            "Only the VPN is affected. It authenticates successfully and then disconnects after login on Windows 11; "
            "Outlook, printing, Remote Desktop, Wi-Fi and internet access work normally."
        ),
        "category": "VPN",
        "root_cause": "A stale VPN profile remained after a supported client update.",
        "resolution_notes": "Removed the stale profile, installed the approved client configuration, and verified a stable VPN connection with IT Support.",
    },
]


def seed_relevant_data(session: Session) -> tuple[int, int]:
    admin = session.exec(select(User).where(User.username == "admin")).first()
    if not admin:
        raise RuntimeError("The admin user is required. Run scripts/seed_db.py first.")

    added_articles = 0
    for item in KB_ARTICLES:
        if session.exec(select(KnowledgeArticle).where(KnowledgeArticle.doc_id == item["doc_id"])).first():
            continue
        session.add(KnowledgeArticle(
            doc_id=item["doc_id"],
            title=item["title"],
            content=item["content"],
            category=item["category"],
            status="approved",
            source_type="internal_kb",
            author="supplemental_seed",
            authoritative=True,
            supported_os=item["supported_os"],
            security_class="internal",
        ))
        added_articles += 1

    added_tickets = 0
    now = datetime.utcnow()
    for item in RESOLVED_TICKETS:
        if session.exec(select(Ticket).where(Ticket.ticket_code == item["ticket_code"])).first():
            continue
        session.add(Ticket(
            ticket_code=item["ticket_code"],
            user_id=admin.id,
            title=item["title"],
            description=item["description"],
            masked_description=item["description"],
            category=item["category"],
            priority="High",
            canonical_issue=item["title"],
            status="RESOLVED",
            approval_status="APPROVED",
            approved_by=admin.id,
            approved_at=now,
            root_cause=item["root_cause"],
            resolution_notes=item["resolution_notes"],
            source_used="supplemental_seed",
            created_at=now,
            updated_at=now,
        ))
        added_tickets += 1

    session.commit()
    return added_articles, added_tickets


if __name__ == "__main__":
    create_db_and_tables()
    with Session(engine) as session:
        articles, tickets = seed_relevant_data(session)
    print(f"Added {articles} approved KB article(s) and {tickets} resolved ticket(s).")
    print("Existing records were preserved; rerunning this script is idempotent.")
