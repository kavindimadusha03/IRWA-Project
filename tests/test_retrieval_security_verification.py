from types import SimpleNamespace

from starlette.requests import Request
from fastapi import HTTPException
from sqlmodel import Session, SQLModel, create_engine, select

from app.agents import coordinator
from app.agents import retrieval_agent
from app.agents.retrieval_agent import search_knowledge
from app.agents.solution_agent import recommend_solution
from app.main import (
    display_decision_explanation,
    maximum_retrieval_ranking_score,
    retrieval_decision,
    templates,
)
from app.agents.ticket_agent import analyze_ticket, build_clarified_issue
from app.models import KnowledgeArticle, Notification, Ticket, User
from app.routes import agents, tickets as ticket_routes
from app.schemas import AgentMessage
from app.services.auth import create_access_token


def _engine():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    return engine


def _request(token=None):
    headers = [] if not token else [(b"cookie", f"access_token={token}".encode())]
    return Request({"type": "http", "headers": headers})


def _message(payload):
    return AgentMessage(
        message_id="m-1",
        request_id="r-1",
        sender="caller",
        receiver="agent",
        task="request",
        payload=payload,
    )


def test_ir_06_ambiguous_multi_service_requires_clarification(monkeypatch):
    monkeypatch.setattr("app.agents.ticket_agent.llm.chat_json", lambda *args, **kwargs: {})
    analysis = analyze_ticket(
        "Connection problems: my Wi-Fi, VPN, Outlook, printer and remote desktop are not working. "
        "I cannot connect to anything."
    )
    assert analysis["ambiguity_required"] is True
    assert analysis["category"] == "Unknown"
    assert len(analysis["clarification_questions"]) == 3


def test_clarification_is_persisted_and_retrieval_runs_after_answers(monkeypatch):
    engine = _engine()
    monkeypatch.setattr("app.agents.ticket_agent.llm.chat_json", lambda *args, **kwargs: {})
    monkeypatch.setattr("app.agents.solution_agent.llm.chat", lambda *args, **kwargs: "1. Follow KB-VPN-1.")
    calls = []

    def fake_search(session, query, top_k=5, **kwargs):
        calls.append(query)
        return {
            "query": query,
            "items": [{
                "source_id": "KB-VPN-1",
                "title": "VPN disconnects after login",
                "content": "Reconnect the VPN profile after login.",
                "category": "VPN",
                "source_type": "internal_kb",
                "status": "approved",
                "hybrid_score": 0.91,
            }],
            "best_score": 0.91,
            "decision": "HIGH",
        }

    monkeypatch.setattr(coordinator, "search_knowledge", fake_search)
    with Session(engine) as session:
        user = User(username="clarify", full_name="Clarify", hashed_password="x", role="CUSTOMER")
        session.add(user)
        session.commit()
        session.refresh(user)
        ticket = Ticket(
            ticket_code="TCK-CLARIFY",
            user_id=user.id,
            title="Connection problems",
            description="My Wi-Fi, VPN, Outlook, printer and remote desktop are not working. I cannot connect to anything.",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)

        first = coordinator.process_new_ticket(session, ticket)
        assert first["ticket"].status == "CLARIFICATION_REQUIRED"
        assert "Which single service" in ticket.decision_explanation
        assert calls == []

        second = coordinator.process_new_ticket(
            session,
            ticket,
            additional_context="I checked again. My Wi-Fi and internet are working. Outlook, the printer and remote desktop are also working. Only my VPN disconnects after login. I am using Windows 11.",
        )
        assert second["ticket"].status == "SOLUTION_PROPOSED"
        assert len(calls) == 1
        assert calls[0] == "Only my VPN disconnects after login Windows 11"
        assert second["analysis"]["category"] == "VPN"
        assert second["analysis"]["category"] != "Wi-Fi / DNS"
        assert "Clarification answers supplied" in ticket.decision_explanation
        assert ticket.description.startswith("My Wi-Fi")
        assert ticket.retrieval_confidence == 0.91


def test_clarification_state_handles_negation_contradiction_and_multi_service():
    original = "Wi-Fi, VPN and Remote Desktop are not working."
    contradicted = build_clarified_issue(original, "Wi-Fi and Remote Desktop are working. Only VPN disconnects after login on Windows 11.")
    assert contradicted["affected_service"] == "VPN"
    assert contradicted["resolved_or_negated_symptoms"] == ["Remote Desktop", "Wi-Fi / DNS"]
    assert contradicted["effective_query"] == "Only VPN disconnects after login on Windows 11"

    multiple = build_clarified_issue(original, "Wi-Fi and VPN both disconnect frequently on Windows 11.")
    assert multiple["affected_service"] == "Multiple services"
    assert len(multiple["confirmed_active_symptoms"]) == 1

    incomplete = build_clarified_issue(original, "VPN is the affected service.")
    assert incomplete["remaining_uncertainties"]


def test_ir_01_and_ir_02_specific_wifi_queries_keep_category(monkeypatch):
    monkeypatch.setattr("app.agents.ticket_agent.llm.chat_json", lambda *args, **kwargs: {})
    for text in (
        "Wi-Fi connected but no internet access",
        "Wireless is connected, but websites will not load",
    ):
        result = analyze_ticket(text)
        assert result["category"] == "Wi-Fi / DNS"
        assert result["ambiguity_required"] is False


def test_ir_11_swelling_battery_after_windows_updates_is_specific(monkeypatch):
    monkeypatch.setattr("app.agents.ticket_agent.llm.chat_json", lambda *args, **kwargs: {})
    result = analyze_ticket("My laptop battery is swelling after Windows updates on Windows 11")
    assert result["category"] == "Windows / Updates"
    assert result["ambiguity_required"] is False


def test_ir_09_draft_sources_are_not_authoritative():
    engine = _engine()
    with Session(engine) as session:
        session.add_all([
            KnowledgeArticle(
                doc_id="KB-APPROVED",
                title="Wi-Fi connection",
                content="Reconnect the wireless adapter.",
                category="Wi-Fi / DNS",
                status="approved",
                source_type="internal_kb",
            ),
            KnowledgeArticle(
                doc_id="KB-DRAFT",
                title="Wi-Fi draft",
                content="Unreviewed instructions.",
                category="Wi-Fi / DNS",
                status="draft",
                source_type="internal_kb",
            ),
        ])
        session.commit()
        result = search_knowledge.__globals__["hybrid_rank"]
        assert result is not None
        records = search_knowledge.__globals__["_records_from_db"](session)
        assert {record["source_id"] for record in records} == {"KB-APPROVED"}


def test_retrieval_rejects_ubuntu_rdp_for_windows_vpn_and_keeps_platform_independent_sources(monkeypatch):
    engine = _engine()
    with Session(engine) as session:
        session.add(KnowledgeArticle(
            doc_id="KB-VPN-WIN11",
            title="Windows 11 VPN disconnects after login",
            content="Reconnect the VPN profile after login on Windows 11.",
            category="VPN",
            status="approved",
            supported_os="Windows 11",
        ))
        session.add(Ticket(
            ticket_code="SYN-0070",
            user_id=1,
            title="Remote Desktop cannot connect to office PC",
            description="Remote Desktop cannot connect to office PC on Ubuntu.",
            canonical_issue="Remote Desktop cannot connect to office PC",
            category="Remote Desktop",
            status="RESOLVED",
            resolution_notes="Enabled the approved RDP rule.",
        ))
        session.commit()
        monkeypatch.setattr(retrieval_agent, "hybrid_rank", lambda query, records, top_k=5: [
            {**record, "hybrid_score": 0.9, "bm25_score": 0.8, "semantic_score": 0.9}
            for record in records
        ])
        result = retrieval_agent.search_knowledge(
            session,
            "Only my VPN disconnects after login Windows 11",
            category="VPN",
            operating_system="Windows 11",
        )
        assert [item["source_id"] for item in result["items"]] == ["KB-VPN-WIN11"]
        assert result["items"][0]["applicability"]["operating_system_applicable"] is True


def test_solution_citations_are_unique_and_escalate_without_applicable_evidence(monkeypatch):
    monkeypatch.setattr("app.agents.solution_agent.llm.chat", lambda *args, **kwargs: "Use the documented VPN procedure.")
    duplicate = {
        "source_id": "KB-VPN",
        "title": "VPN procedure",
        "content": "Reconnect VPN.",
        "category": "VPN",
        "source_type": "internal_kb",
        "status": "approved",
        "hybrid_score": 0.9,
    }
    result = recommend_solution("VPN disconnects after login Windows 11", {
        "decision": "HIGH", "items": [duplicate, dict(duplicate)],
    })
    assert result["can_recommend"] is True
    assert [citation["source_id"] for citation in result["citations"]] == ["KB-VPN"]

    unrelated = dict(duplicate, source_id="SYN-0070", title="Ubuntu RDP", category="Remote Desktop", content="Enable RDP on Ubuntu.")
    result = recommend_solution("VPN disconnects after login Windows 11", {
        "decision": "HIGH", "items": [unrelated],
    })
    assert result["can_recommend"] is False
    assert result["citations"] == []


def test_ir_12_threshold_and_grounding_use_one_eligible_citation(monkeypatch):
    low = recommend_solution("wifi issue", {"decision": "UNCERTAIN", "items": []})
    assert low["can_recommend"] is False

    monkeypatch.setattr("app.agents.solution_agent.llm.chat", lambda *args, **kwargs: "1. Reconnect the adapter. [KB-1]")
    result = recommend_solution("wifi issue", {
        "decision": "HIGH",
        "best_score": 0.91,
        "items": [{
            "source_id": "KB-1",
            "title": "Wi-Fi article",
            "content": "Reconnect the adapter.",
            "category": "Wi-Fi / DNS",
            "source_type": "internal_kb",
            "status": "approved",
            "hybrid_score": 0.91,
            "bm25_score": 0.61,
            "semantic_score": 0.91,
        }, {
            "source_id": "T-OLD",
            "title": "Resolved ticket",
            "content": "A different fix.",
            "category": "Printers",
            "source_type": "resolved_ticket",
            "status": "resolved",
            "hybrid_score": 0.90,
        }],
    })
    assert result["can_recommend"] is True
    assert [citation["source_id"] for citation in result["citations"]] == ["KB-1"]
    assert "BM25 0.61, semantic 0.91" in result["explanation"]
    assert "final adjusted retrieval ranking score is 0.91" in result["explanation"]
    assert "is a probability" in result["explanation"]


def test_ranking_score_display_boundaries_and_legacy_explanation():
    assert [retrieval_decision(score, 0.68, 0.55) for score in (0.54, 0.55, 0.68, 1.00, 1.14)] == [
        "LOW", "UNCERTAIN", "HIGH", "HIGH", "HIGH",
    ]
    legacy = "Selected SYN-1 with 100% relevance. Relevance is a ranking signal, not a probability of correctness."
    displayed = display_decision_explanation(legacy)
    assert "100% relevance" not in displayed
    assert "based on the selected source" in displayed
    assert maximum_retrieval_ranking_score() == 1.79


def test_ticket_template_shows_adjusted_score_and_unmeasured_clarification():
    settings = __import__("app.config", fromlist=["get_settings"]).get_settings()
    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/tickets/1",
        "headers": [],
        "query_string": b"",
        "server": ("testserver", 80),
        "scheme": "http",
        "client": ("127.0.0.1", 1234),
        "root_path": "",
    })
    context = {
        "request": request,
        "user": SimpleNamespace(role="CUSTOMER", full_name="Test User", notifications=[]),
        "logs": [],
        "trace_request_id": None,
        "feedback": None,
        "citations": [],
        "clarification": {},
        "high_confidence_threshold": settings.high_confidence_threshold,
        "uncertain_threshold": settings.uncertain_threshold,
        "maximum_ranking_score": maximum_retrieval_ranking_score(),
        "display_decision_explanation": "A ranking score is not a probability.",
    }
    ticket = SimpleNamespace(
        id=1,
        ticket_code="TCK-1",
        status="SOLUTION_PROPOSED",
        title="Test issue",
        description="Test description",
        category="Wi-Fi / DNS",
        canonical_issue="wifi issue",
        retrieval_confidence=1.14,
        source_used="KB-1",
        recommended_solution="See source.",
        decision_explanation="A ranking score is not a probability.",
        suggested_reply="",
        root_cause="",
        resolution_notes="",
    )
    template = templates.get_template("ticket_result.html")
    rendered = template.render(**context, ticket=ticket)
    assert "<strong>1.14</strong>" in rendered
    assert "score-high\">HIGH</span>" in rendered
    assert "not a probability that the solution is correct" in rendered
    assert "Theoretical maximum under current scoring: 1.79" in rendered
    assert "114%" not in rendered

    ticket.status = "CLARIFICATION_REQUIRED"
    ticket.retrieval_confidence = 0.0
    rendered = template.render(**context, ticket=ticket)
    score_block = rendered.split('class="analysis-item analysis-confidence"', 1)[1].split(
        '<div class="analysis-item">', 1
    )[0]
    assert "<strong>Not evaluated</strong>" in score_block
    assert "0%" not in score_block


def test_ir_13_anonymous_sensitive_agent_access_is_rejected():
    engine = _engine()
    with Session(engine) as session:
        try:
            agents.retrieval_search(_message({"issue": "wifi"}), _request(), session)
        except HTTPException as error:
            assert error.status_code == 401
        else:
            raise AssertionError("anonymous agent access was accepted")


def test_submitted_clarification_escalates_and_notifies_it_support(monkeypatch):
    engine = _engine()
    with Session(engine) as session:
        customer = User(username="clarification-customer", full_name="Customer", hashed_password="x", role="CUSTOMER")
        support = User(username="clarification-support", full_name="Support", hashed_password="x", role="IT_SUPPORT")
        session.add_all([customer, support])
        session.commit()
        session.refresh(customer)
        ticket = Ticket(
            ticket_code="TCK-ESCALATE-CLARIFICATION",
            user_id=customer.id,
            title="Windows blue screen error 0x00000124",
            description="Windows blue screen error 0x00000124",
            status="CLARIFICATION_REQUIRED",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        monkeypatch.setattr(
            ticket_routes,
            "process_new_ticket",
            lambda session, ticket, additional_context: None,
        )
        token = create_access_token(customer.id, customer.username, customer.role)
        response = ticket_routes.submit_clarification(
            ticket.id,
            _request(token),
            answers="",
            answer_1="It happens during startup after a Windows update.",
            answer_2="Windows 11 laptop.",
            answer_3="No other services are affected.",
            session=session,
        )
        session.refresh(ticket)
        assert response.status_code == 303
        assert ticket.status == "ESCALATED"
        notification = session.exec(
            select(Notification).where(Notification.ticket_id == ticket.id)
        ).first()
        assert notification is not None
        assert notification.notification_type == "ticket_escalated"


def test_ir_14_and_ir_15_roles_and_fabricated_evidence_are_rejected(monkeypatch):
    engine = _engine()
    with Session(engine) as session:
        customer = User(username="customer", full_name="Customer", hashed_password="x", role="CUSTOMER")
        session.add(customer)
        session.commit()
        session.refresh(customer)
        token = create_access_token(customer.id, customer.username, customer.role)
        try:
            agents.knowledge_analyze(_request(token), session)
        except HTTPException as error:
            assert error.status_code == 403
        else:
            raise AssertionError("customer reached knowledge analysis")

        server_result = {"decision": "LOW", "items": [], "best_score": 0.1, "query": "wifi"}
        monkeypatch.setattr(agents, "search_knowledge", lambda *args, **kwargs: server_result)
        result = agents.solution_recommend(
            _message({
                "query": "wifi",
                "retrieval": {
                    "decision": "HIGH",
                    "items": [{"source_id": "FAKE", "status": "approved"}],
                },
            }),
            _request(token),
            session,
        )
        assert result["can_recommend"] is False
        assert result["citations"] == []
