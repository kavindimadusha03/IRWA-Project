import uuid

from sqlmodel import Session

from app.agents.solution_agent import recommend_solution
from app.agents.ticket_agent import analyze_ticket
from app.database import create_db_and_tables, engine
from app.models import Ticket, User
from app.notifications import create_resolution_notification, get_user_notifications
from app.services.bm25 import tokenize
from app.services.embeddings import clear_document_embedding_cache, get_document_embeddings
from app.services.hybrid_search import normalize_query_for_search
from app.agents.retrieval_agent import _trust_weight, search_knowledge


def test_resolution_notification_created_for_customer():
    create_db_and_tables()
    with Session(engine) as session:
        user = User(username=f"notify_user_{uuid.uuid4().hex}", full_name="Notify User", hashed_password="x", role="CUSTOMER")
        session.add(user)
        session.commit()
        session.refresh(user)

        ticket = Ticket(
            ticket_code=f"TCK-NOTIFY-{uuid.uuid4().hex[:8].upper()}",
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


def test_normalize_query_for_search_handles_common_typo_query():
    corpus = [
        "Wi-Fi connected but no internet access",
        "VPN disconnects every few minutes",
    ]
    normalized = normalize_query_for_search("wifi connectef, bur no interner", corpus)
    assert "wifi" in normalized.lower()
    assert "connected" in normalized.lower()
    assert "but" in normalized.lower()
    assert "internet" in normalized.lower()


def test_tokenize_preserves_technical_terms_and_error_codes():
    tokens = tokenize("VPN DNS Windows-11 0x00000124 ipconfig /flushdns MFA RDP ping 8.8.8.8 nslookup winver svc restart")
    assert "vpn" in tokens
    assert "dns" in tokens
    assert "windows-11" in tokens
    assert "0x00000124" in tokens
    assert "ipconfig" in tokens
    assert "flushdns" in tokens
    assert "mfa" in tokens
    assert "rdp" in tokens
    assert "ping" in tokens
    assert "8.8.8.8" in tokens
    assert "nslookup" in tokens
    assert "winver" in tokens
    assert "svc" in tokens
    assert "restart" in tokens


def test_normalize_query_for_search_keeps_meaningful_terms_and_drops_filler_words():
    normalized = normalize_query_for_search("My laptop suddenly cannot connect to wireless internet", [
        "laptop wifi internet connection",
        "wireless internet connectivity issues",
    ])
    assert "laptop" in normalized.lower()
    assert "wifi" in normalized.lower()
    assert "internet" in normalized.lower()
    assert "connect" in normalized.lower()
    assert "cannot" in normalized.lower()


def test_normalize_query_for_search_handles_synonyms_abbreviations_and_typos():
    normalized = normalize_query_for_search(
        "wlan cant connect to the internt and mfa auth keeps failin",
        [
            "wifi connection internet access",
            "vpn login authentication failed",
            "mfa authentication issue",
        ],
    )
    text = normalized.lower()
    assert "wifi" in text
    assert "cannot" in text
    assert "connect" in text
    assert "internet" in text
    assert "mfa" in text
    assert "authentication" in text or "auth" in text
    assert "failed" in text


def test_document_embeddings_are_cached_for_repeated_queries():
    clear_document_embedding_cache()
    corpus = [
        "Wi-Fi connected but no internet access",
        "VPN disconnects every few minutes",
    ]

    first = get_document_embeddings(tuple(corpus))
    second = get_document_embeddings(tuple(corpus))

    assert first is second
    assert first.shape[0] == len(corpus)


def test_metadata_reranking_prefers_windows_11_vpn_article():
    records = [
        {
            "source_id": "KB-WIN11-VPN",
            "title": "Windows 11 VPN disconnects after login",
            "content": "VPN disconnects on Windows 11 after login.",
            "category": "VPN",
            "supported_os": "Windows 11",
            "source_type": "internal_kb",
            "status": "approved",
        },
        {
            "source_id": "KB-GENERIC-NETWORK",
            "title": "General network troubleshooting",
            "content": "Check router and internet connectivity.",
            "category": "Networking",
            "supported_os": "Any",
            "source_type": "internal_kb",
            "status": "approved",
        },
    ]

    result = search_knowledge.__globals__["hybrid_rank"]("VPN disconnects on Windows 11", records, top_k=2)
    first_id = result[0]["source_id"]
    second_id = result[1]["source_id"]

    assert first_id == "KB-WIN11-VPN"
    assert second_id == "KB-GENERIC-NETWORK"


def test_source_trust_weighting_prefers_approved_kb_and_excludes_drafts():
    approved = {"status": "approved", "source_type": "internal_kb"}
    resolved = {"status": "resolved", "source_type": "resolved_ticket"}
    draft = {"status": "draft", "source_type": "resolved_ticket_draft"}

    assert _trust_weight(approved) == 1.0
    assert _trust_weight(resolved) == 0.85
    assert _trust_weight(draft) == 0.0


def test_search_knowledge_exposes_score_breakdown_and_source_metadata():
    records = [
        {
            "source_id": "KB-ERR-0X124",
            "title": "Windows error code 0x00000124",
            "content": "0x00000124 indicates a driver timeout or delayed network stack recovery issue.",
            "category": "Windows",
            "supported_os": "Windows 11",
            "source_type": "internal_kb",
            "status": "approved",
            "bm25_score": 0.61,
            "semantic_score": 0.91,
            "hybrid_score": 0.76,
        },
    ]

    retrieval = search_knowledge.__globals__["hybrid_rank"]("error 0x00000124", records, top_k=1)
    item = retrieval[0]

    assert item["source_id"] == "KB-ERR-0X124"
    assert item["source_type"] == "internal_kb"
    assert "bm25_score" in item
    assert "semantic_score" in item
    assert "hybrid_score" in item
    assert item["exact_error_match"] is True


def test_hybrid_rank_gives_exact_error_code_bonus():
    records = [
        {
            "source_id": "KB-GENERIC-NETWORK",
            "title": "General Wi-Fi connection troubleshooting",
            "content": "Check router configuration and internet connectivity.",
            "category": "Networking",
            "supported_os": "Any",
            "source_type": "internal_kb",
            "status": "approved",
        },
        {
            "source_id": "KB-ERR-0X124",
            "title": "Windows error code 0x00000124",
            "content": "0x00000124 indicates a driver timeout or a delayed network stack recovery issue.",
            "category": "Windows",
            "supported_os": "Windows 11",
            "source_type": "internal_kb",
            "status": "approved",
        },
    ]

    result = search_knowledge.__globals__["hybrid_rank"]("error 0x00000124", records, top_k=2)

    assert result[0]["source_id"] == "KB-ERR-0X124"
    assert result[0]["exact_error_match"] is True
    assert result[0]["hybrid_score"] >= result[1]["hybrid_score"]


def test_hybrid_rank_deduplicates_near_duplicate_articles():
    records = [
        {
            "source_id": "KB-021",
            "title": "Clear Print Queue - Guide 3",
            "content": "Stop the print spooler, clear stuck print jobs, restart the print spooler, and try printing again.",
            "category": "Printers",
            "supported_os": "Any",
            "source_type": "internal_kb",
            "status": "approved",
        },
        {
            "source_id": "KB-044",
            "title": "Clear Print Queue - Guide 6",
            "content": "Stop the print spooler, clear stuck print jobs, restart the print spooler, and try printing again.",
            "category": "Printers",
            "supported_os": "Any",
            "source_type": "internal_kb",
            "status": "approved",
        },
        {
            "source_id": "KB-061",
            "title": "Clear Print Queue - Guide 8",
            "content": "Stop the print spooler, clear stuck print jobs, restart the print spooler, and try printing again.",
            "category": "Printers",
            "supported_os": "Any",
            "source_type": "internal_kb",
            "status": "approved",
        },
        {
            "source_id": "KB-999",
            "title": "Printer driver installation issue",
            "content": "If the printer driver is missing, reinstall the approved driver for the device.",
            "category": "Printers",
            "supported_os": "Any",
            "source_type": "internal_kb",
            "status": "approved",
        },
    ]

    result = search_knowledge.__globals__["hybrid_rank"]("stuck print queue", records, top_k=3)
    ids = [item["source_id"] for item in result]

    assert "KB-021" in ids or "KB-044" in ids or "KB-061" in ids
    assert ids.count("KB-021") + ids.count("KB-044") + ids.count("KB-061") <= 1
    assert "KB-999" in ids
