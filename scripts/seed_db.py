from pathlib import Path
import csv
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlmodel import Session, select
from app.database import create_db_and_tables, engine
from app.models import KnowledgeArticle, Ticket, User
from app.services.auth import hash_password

DATA_DIR = ROOT / "data"

USERS = [
    ("customer", "Demo Customer", "CUSTOMER", "Customer123!"),
    ("support", "IT Support Demo", "IT_SUPPORT", "Support123!"),
    ("analyst", "Knowledge Analyst Demo", "KNOWLEDGE_ANALYST", "Analyst123!"),
    ("admin", "System Admin Demo", "ADMIN", "Admin123!"),
]


def seed_users(session: Session):
    for username, full_name, role, password in USERS:
        existing = session.exec(select(User).where(User.username == username)).first()
        if not existing:
            session.add(User(
                username=username,
                full_name=full_name,
                role=role,
                hashed_password=hash_password(password),
            ))
    session.commit()


def seed_kb(session: Session):
    kb_path = DATA_DIR / "knowledge_base.csv"
    if not kb_path.exists():
        raise FileNotFoundError("Run: python scripts/generate_dataset.py first")
    with kb_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            existing = session.exec(select(KnowledgeArticle).where(KnowledgeArticle.doc_id == row["doc_id"])).first()
            if existing:
                continue
            session.add(KnowledgeArticle(
                doc_id=row["doc_id"],
                title=row["title"],
                content=row["body"],
                category=row["category"],
                status=row["status"],
                source_type=row["source_type"],
                author="dataset_generator",
                authoritative=row["authoritative"].lower() == "true",
                supported_os=row["supported_os"],
                security_class=row["security_class"],
            ))
    session.commit()


def seed_historical_tickets(session: Session):
    tickets_path = DATA_DIR / "tickets.csv"
    if not tickets_path.exists():
        raise FileNotFoundError("Run: python scripts/generate_dataset.py first")
    admin = session.exec(select(User).where(User.username == "admin")).first()
    if not admin:
        raise RuntimeError("Admin user missing")
    with tickets_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = row["ticket_id"]
            existing = session.exec(select(Ticket).where(Ticket.ticket_code == code)).first()
            if existing:
                continue
            status = "RESOLVED" if row["status"] == "Resolved" else "OPEN"
            session.add(Ticket(
                ticket_code=code,
                user_id=admin.id,
                title=row["title"],
                description=row["description"],
                masked_description=row["description"],
                category=row["ground_truth_category"],
                canonical_issue=row["title"],
                status=status,
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["created_at"]),
                resolution_notes=row["resolution_notes"],
                retrieval_confidence=0.0,
                source_used="historical_dataset",
            ))
    session.commit()


if __name__ == "__main__":
    create_db_and_tables()
    with Session(engine) as session:
        seed_users(session)
        seed_kb(session)
        seed_historical_tickets(session)
    print("Database seeded successfully.")
    print("Demo accounts:")
    for username, _, role, password in USERS:
        print(f"  {role:18s} username={username:8s} password={password}")
