from sqlmodel import Session, SQLModel, create_engine

from app.agents import knowledge_intelligence_agent as agent
from app.models import Ticket


def test_analyze_knowledge_health_caps_large_cluster_work(monkeypatch):
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    tickets = [
        Ticket(
            ticket_code=f"T-{idx}",
            user_id=1,
            title=f"Issue {idx}",
            description=f"Description {idx}",
            category="Hardware",
            canonical_issue=f"Hardware issue {idx}",
        )
        for idx in range(200)
    ]

    with Session(engine) as session:
        session.add_all(tickets)
        session.commit()

        monkeypatch.setattr(agent, "encode_texts", lambda texts: [[0.0] * 384 for _ in texts])
        monkeypatch.setattr(
            agent,
            "search_knowledge",
            lambda session, query, top_k=3, approved_only=False: {"best_score": 0.75},
        )

        with Session(engine) as session:
            result = agent.analyze_knowledge_health(session)

    assert result["health"]
    assert result["clusters"]
    assert all(cluster["sampled"] for cluster in result["clusters"])
