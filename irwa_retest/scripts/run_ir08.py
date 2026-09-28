
"""IR-08 only: five formatting variants, each with the same labelled isolated exact-code fixture.

Each run has a new evidence directory. Original app/test/data files are not edited.
"""

from __future__ import annotations

from retest_paths import latest_run

import argparse
import csv
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone


# ---------------------------------------------------------------------
# Environment and project configuration
# ---------------------------------------------------------------------

for key in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[key] = "1"

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from collect_baseline import clean, digest, code_hashes, SECRETS


# ---------------------------------------------------------------------
# Fixed test inputs
# ---------------------------------------------------------------------

TITLE = "Windows blue screen report"

ERROR_CODE = "0x00000124"

VARIANTS = {
    "lowercase": "0x00000124",
    "uppercase": "0X00000124",
    "prefix": "error: 0x00000124",
    "punctuation": "0x00000124!!!",
    "quoted": '"0x00000124"',
}

SUBCASES = {
    name: "Windows blue screen error " + variant
    for name, variant in VARIANTS.items()
}


# ---------------------------------------------------------------------
# Isolated synthetic fixture
# ---------------------------------------------------------------------

FIXTURE = {
    "doc_id": "AUDIT-IR08-EXACT-001",
    "title": "Synthetic lookup: Windows blue screen 0x00000124",
    "content": (
        "Synthetic IR-08 lookup fixture for error 0x00000124. "
        "This fixture does not establish a diagnosis or a verified repair. "
        "Record the displayed code and symptoms and ask IT Support "
        "to review them before applying changes."
    ),
    "category": "Windows / Updates",
    "status": "approved",
    "source_type": "internal_kb",
    "author": "IR-08 synthetic audit fixture",
    "authoritative": False,
    "supported_os": "Any",
    "security_class": "internal",
}

FIXTURE_RECORD = {
    "source_id": FIXTURE["doc_id"],
    **{
        key: FIXTURE[key]
        for key in (
            "title",
            "content",
            "category",
            "status",
            "source_type",
            "supported_os",
        )
    },
}


# ---------------------------------------------------------------------
# Reference runs
# ---------------------------------------------------------------------

IR03_RUN = latest_run(ROOT, "IR-03")
IR01_RUN = latest_run(ROOT, "IR-01")


# ---------------------------------------------------------------------
# Evidence helpers
# ---------------------------------------------------------------------

def now():
    return datetime.now(timezone.utc).isoformat()


def save(folder, name, data):
    if isinstance(data, str):
        content = data
    else:
        content = json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )

    (folder / name).write_text(
        clean(content) + "\n",
        encoding="utf-8",
    )


def parse_json(path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    return {}


# ---------------------------------------------------------------------
# Individual subcase worker
# ---------------------------------------------------------------------

def worker(folder, subcase):

    DESCRIPTION = SUBCASES[subcase]

    state = {
        "started_at_utc": now(),
        "stage": "setup",
        "case": "IR-08",
        "subcase": subcase,
        "status": "Not ready",
        "outcome": "Unassessed",
        "ticket_requests": 0,
        "http": {},
    }

    def progress(stage):
        state["stage"] = stage
        save(folder, "execution.json", state)
        print("IR-08 stage: " + stage, flush=True)

    server = None
    thread = None
    audit_socket = None
    evidence = {}

    try:

        # -------------------------------------------------------------
        # Create a fresh isolated database
        # -------------------------------------------------------------

        directory = Path(
            tempfile.mkdtemp(
                prefix="knowgap-ir08-" + subcase + "-"
            )
        )

        database = directory / "knowgap.db"

        os.environ["DATABASE_URL"] = (
            "sqlite:///" + database.as_posix()
        )

        state["isolated_database"] = str(database)

        state["dataset"] = (
            "Project synthetic CSVs plus one labelled approved-status "
            "IR-08 fixture in a fresh temporary database; "
            "no working-database rows copied"
        )

        from app.config import get_settings

        settings = get_settings()

        state["configuration"] = {
            "bm25_weight": settings.hybrid_bm25_weight,
            "semantic_weight": settings.hybrid_semantic_weight,
            "high_threshold": settings.high_confidence_threshold,
            "uncertain_threshold": settings.uncertain_threshold,
            "embedding_model": "all-MiniLM-L6-v2",
            "llm_model": settings.groq_model,
            "ticket_top_k": 5,
            "thread_limit": 1,
            "cached_model_only": True,
        }

        previous = parse_json(
            IR01_RUN / "execution.json"
        )

        state["comparison_to_IR01"] = {
            "reference_run": IR01_RUN.relative_to(ROOT).as_posix(),
            "same_configuration": (
                state["configuration"]
                == previous.get("configuration")
            ),
        }

        if not state["comparison_to_IR01"]["same_configuration"]:
            raise RuntimeError(
                "Configuration differs from IR-01; "
                "comparison precondition not met"
            )

        # -------------------------------------------------------------
        # Embedding model preflight
        # -------------------------------------------------------------

        progress("embedding model preflight")

        started = time.perf_counter()

        from app.services.embeddings import get_model

        get_model()

        state["model_preflight"] = {
            "loaded": True,
            "elapsed_seconds": round(
                time.perf_counter() - started,
                3,
            ),
        }

        # -------------------------------------------------------------
        # Seed isolated database and insert fixture
        # -------------------------------------------------------------

        progress("seed isolated synthetic database")

        from app.database import create_db_and_tables, engine

        from sqlmodel import Session, select

        from scripts.seed_db import (
            USERS,
            seed_users,
            seed_kb,
            seed_historical_tickets,
        )

        from app.models import (
            KnowledgeArticle,
            Ticket,
            TicketCitation,
            User,
        )

        if (
            Path(engine.url.database).resolve()
            != database.resolve()
            or database.resolve()
            == (ROOT / "knowgap.db").resolve()
        ):
            raise RuntimeError(
                "Database isolation check failed "
                "before any creation or seed write"
            )

        create_db_and_tables()

        with Session(engine) as session:

            seed_users(session)
            seed_kb(session)
            seed_historical_tickets(session)

            fixture = KnowledgeArticle(
                **FIXTURE,
                created_at=datetime(2026, 9, 22),
                updated_at=datetime(2026, 9, 22),
            )

            session.add(fixture)
            session.commit()
            session.refresh(fixture)

            actual_fixture = {
                key: getattr(fixture, key)
                for key in FIXTURE
            }

            if actual_fixture != FIXTURE:
                raise RuntimeError(
                    "Stored synthetic fixture differs "
                    "from predeclared fields"
                )

            save(
                folder,
                "fixture_preflight.json",
                {
                    "recorded_before_request_at_utc": now(),
                    "fixture": actual_fixture,
                    "database_record_id": fixture.id,
                    "approved_is_synthetic_test_metadata": True,
                    "no_independent_diagnosis_or_repair_validation": True,
                    "isolation_verified": True,
                },
            )

            account = next(
                row
                for row in USERS
                if row[2] == "CUSTOMER"
            )

            synthetic_user = session.exec(
                select(User).where(
                    User.username == account[0]
                )
            ).one()

            state["test_user"] = {
                "role": synthetic_user.role,
                "active": synthetic_user.is_active,
                "origin": (
                    "synthetic CSV seed account; "
                    "credential values omitted"
                ),
            }

            articles = session.exec(
                select(KnowledgeArticle)
            ).all()

            historical = session.exec(
                select(Ticket)
            ).all()

            state["fixture_counts"] = {
                "articles": len(articles),
                "historical_tickets": len(historical),
            }

            state["approved_exact_code_sources"] = [
                article.doc_id
                for article in articles
                if (
                    article.status == "approved"
                    and ERROR_CODE
                    in " ".join(
                        (
                            article.title,
                            article.content,
                            article.category,
                            article.supported_os,
                        )
                    ).lower()
                )
            ]

            if state["approved_exact_code_sources"] != [
                FIXTURE["doc_id"]
            ]:
                raise RuntimeError(
                    "Expected exactly the isolated fixture "
                    "as approved exact-code evidence"
                )

            support_account = next(
                row
                for row in USERS
                if row[2] == "IT_SUPPORT"
            )

            support_user = session.exec(
                select(User).where(
                    User.username == support_account[0]
                )
            ).one()

            state["support_test_user"] = {
                "role": support_user.role,
                "active": support_user.is_active,
                "credential_values": "omitted",
            }

            if not support_user.is_active:
                raise RuntimeError(
                    "Synthetic IT_SUPPORT account is inactive"
                )

        # -------------------------------------------------------------
        # Observe actual LLM availability without simulating success
        # -------------------------------------------------------------

        from app.services.llm import llm

        state["llm"] = {
            "configured_enabled": bool(llm.enabled),
            "attempts": 0,
            "successful_chat_returns": 0,
            "error_types": [],
        }

        if (
            bool(llm.enabled)
            != previous.get("llm", {}).get("configured_enabled")
        ):
            raise RuntimeError(
                "LLM mode differs from IR-01; "
                "comparison precondition not met"
            )

        original_chat = llm.chat

        def observed_chat(*args, **kwargs):

            state["llm"]["attempts"] += 1

            try:
                response = original_chat(
                    *args,
                    **kwargs,
                )

            except Exception as exc:
                state["llm"]["error_types"].append(
                    type(exc).__name__
                )
                raise

            state["llm"]["successful_chat_returns"] += 1

            return response

        llm.chat = observed_chat

        # -------------------------------------------------------------
        # Observe original application functions
        # -------------------------------------------------------------

        from app.agents import (
            coordinator,
            retrieval_agent,
        )

        from app.services import hybrid_search
        from app.services.bm25 import tokenize

        save(
            folder,
            "token_code_preflight.json",
            {
                "input": DESCRIPTION,
                "variant": VARIANTS[subcase],
                "tokens": tokenize(DESCRIPTION),
                "extracted_error_codes": sorted(
                    hybrid_search._extract_error_codes(
                        DESCRIPTION
                    )
                ),
                "capture": (
                    "Pure original token/code functions "
                    "before submission; not a separate "
                    "retrieval request"
                ),
            },
        )

        # -------------------------------------------------------------
        # Observe query normalization
        # -------------------------------------------------------------

        original_normalize = (
            hybrid_search.normalize_query_for_search
        )

        def observed_normalize(*args, **kwargs):

            result = original_normalize(
                *args,
                **kwargs,
            )

            original_query = (
                args[0]
                if args
                else kwargs.get("query", "")
            )

            save(
                folder,
                "query_preprocessing.json",
                {
                    "original_query": original_query,
                    "normalized_query": result,
                    "normalized_query_tokens": tokenize(
                        result
                    ),
                    "original_query_error_codes": sorted(
                        hybrid_search._extract_error_codes(
                            original_query
                        )
                    ),
                    "normalized_query_error_codes": sorted(
                        hybrid_search._extract_error_codes(
                            result
                        )
                    ),
                    "capture": (
                        "Original function return observed; "
                        "no result or input changed"
                    ),
                },
            )

            return result

        hybrid_search.normalize_query_for_search = (
            observed_normalize
        )

        # -------------------------------------------------------------
        # Observe hybrid ranking and validate its actual candidates
        #
        # IMPORTANT CORRECTION:
        #
        # search_knowledge() can filter records before hybrid_rank().
        # Consequently, hybrid_rank() is not required to receive all
        # 428 reference records.
        #
        # The actual candidate subset must:
        #   1. Contain only records from the isolated reference DB.
        #   2. Have no duplicate source IDs.
        #   3. Retain the declared fixture exactly once.
        #   4. Match the DB reference records in all retrieval fields.
        #
        # Independently check reference source IDs against the CSVs.
        # This reference-field comparison uses the application's own
        # record-construction function; it is not an independent
        # verification of every field transformation.
        # -------------------------------------------------------------

        original_hybrid = retrieval_agent.hybrid_rank

        def observed_hybrid(*args, **kwargs):

            records = (
                args[1]
                if len(args) > 1
                else kwargs.get("records", [])
            )

            # Read original approved KB records.

            with (
                ROOT / "data" / "knowledge_base.csv"
            ).open(
                encoding="utf-8-sig",
                newline="",
            ) as handle:

                expected_articles = [
                    row
                    for row in csv.DictReader(handle)
                    if row["status"] == "approved"
                ]

            # Read original eligible resolved tickets.

            with (
                ROOT / "data" / "tickets.csv"
            ).open(
                encoding="utf-8-sig",
                newline="",
            ) as handle:

                expected_tickets = [
                    row
                    for row in csv.DictReader(handle)
                    if (
                        row["status"] == "Resolved"
                        and row["resolution_notes"].strip()
                    )
                ]

            # Independently construct the allowed source-ID set
            # from the unchanged CSV files and declared fixture.

            expected_source_ids = (
                {
                    row["doc_id"]
                    for row in expected_articles
                }
                | {
                    row["ticket_id"]
                    for row in expected_tickets
                }
                | {
                    FIXTURE_RECORD["source_id"]
                }
            )

            # Obtain the canonical retrieval records from the
            # fresh isolated database. This preserves the actual
            # application's canonical title, root cause and
            # operating-system inference for historical tickets.

            with Session(engine) as verification_session:

                expected_records = (
                    retrieval_agent._records_from_db(
                        verification_session,
                        approved_only=False,
                    )
                )

            expected_by_id = {
                record["source_id"]: record
                for record in expected_records
            }

            # The database reference must have exactly the
            # declared CSV source IDs plus the single fixture.

            reference_ids_match_csv = (
                len(expected_records)
                == len(expected_by_id)
                and set(expected_by_id)
                == expected_source_ids
            )

            # The independently declared fixture fields must
            # match its canonical reference representation.

            reference_fixture_matches = (
                expected_by_id.get(
                    FIXTURE_RECORD["source_id"]
                )
                == FIXTURE_RECORD
            )

            # Inspect the actual candidate subset passed to
            # the original hybrid ranking function.

            actual_ids = [
                record["source_id"]
                for record in records
            ]

            actual_id_counts = Counter(
                actual_ids
            )

            duplicate_ids = sorted(
                source_id
                for source_id, count
                in actual_id_counts.items()
                if count > 1
            )

            unexpected_ids = sorted(
                source_id
                for source_id in actual_ids
                if source_id not in expected_by_id
            )

            mismatched_ids = sorted(
                record["source_id"]
                for record in records
                if (
                    record["source_id"]
                    in expected_by_id
                    and record
                    != expected_by_id[
                        record["source_id"]
                    ]
                )
            )

            # Identify records containing the exact error code
            # according to the application's original extractor.

            exact = [
                record
                for record in records
                if ERROR_CODE
                in hybrid_search._extract_error_codes(
                    " ".join(
                        str(record.get(field, ""))
                        for field in (
                            "title",
                            "content",
                            "category",
                            "supported_os",
                        )
                    )
                )
            ]

            fixture_present = (
                actual_id_counts[
                    FIXTURE_RECORD["source_id"]
                ]
                == 1
            )

            # Preserve the actual candidate-set fingerprint.

            corpus_sha256 = hashlib.sha256(
                json.dumps(
                    sorted(
                        records,
                        key=lambda record: (
                            record["source_id"]
                        ),
                    ),
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()

            # Save enough detail to diagnose another mismatch
            # without discarding the original execution.

            save(
                folder,
                "eligible_corpus.json",
                {
                    "eligible_record_count": len(
                        records
                    ),
                    "reference_record_count": len(
                        expected_records
                    ),
                    "expected_source_id_count": len(
                        expected_source_ids
                    ),
                    "reference_ids_match_csv": (
                        reference_ids_match_csv
                    ),
                    "reference_fixture_matches": (
                        reference_fixture_matches
                    ),
                    "candidate_subset_matches_reference": (
                        not duplicate_ids
                        and not unexpected_ids
                        and not mismatched_ids
                    ),
                    "duplicate_ids": duplicate_ids,
                    "unexpected_ids": unexpected_ids,
                    "mismatched_ids": mismatched_ids,
                    "fixture_present_once": fixture_present,
                    "eligible_corpus_sha256": (
                        corpus_sha256
                    ),
                    "eligible_exact_code_records": exact,
                    "capture": (
                        "Original candidate subset passed "
                        "unchanged to hybrid_rank. "
                        "Reference source IDs checked "
                        "independently against the CSVs "
                        "and declared fixture. Reference "
                        "record fields obtained from the "
                        "original application function "
                        "using the isolated test database."
                    ),
                },
            )

            # Preserve all important integrity checks while
            # allowing query-dependent candidate filtering.

            if (
                len(expected_records) != 428
                or len(expected_source_ids) != 428
                or not reference_ids_match_csv
                or not reference_fixture_matches
                or not records
                or duplicate_ids
                or unexpected_ids
                or mismatched_ids
                or not fixture_present
                or exact != [FIXTURE_RECORD]
            ):
                raise RuntimeError(
                    "IR-08 candidate validation failed; "
                    "inspect eligible_corpus.json"
                )

            # CRITICAL: Call the original ranking function
            # exactly once with the original arguments.

            result = original_hybrid(
                *args,
                **kwargs,
            )

            # Save the result without changing it.

            save(
                folder,
                "hybrid_before_trust.json",
                result,
            )

            return result

        retrieval_agent.hybrid_rank = observed_hybrid

        # -------------------------------------------------------------
        # Observe original ticket analysis
        # -------------------------------------------------------------

        original_analysis = coordinator.analyze_ticket

        def observed_analysis(*args, **kwargs):

            result = original_analysis(
                *args,
                **kwargs,
            )

            save(
                folder,
                "analysis.json",
                result,
            )

            return result

        coordinator.analyze_ticket = observed_analysis

        # -------------------------------------------------------------
        # Observe original retrieval response
        # -------------------------------------------------------------

        original_search = coordinator.search_knowledge

        def observed_search(*args, **kwargs):

            started = time.perf_counter()

            result = original_search(
                *args,
                **kwargs,
            )

            evidence["retrieval"] = result

            save(
                folder,
                "retrieval.json",
                result,
            )

            state["retrieval_elapsed_seconds"] = round(
                time.perf_counter() - started,
                3,
            )

            return result

        coordinator.search_knowledge = observed_search

        # -------------------------------------------------------------
        # Observe original solution recommendation
        # -------------------------------------------------------------

        original_solution = coordinator.recommend_solution

        def observed_solution(*args, **kwargs):

            result = original_solution(
                *args,
                **kwargs,
            )

            evidence["solution"] = result

            save(
                folder,
                "solution.json",
                result,
            )

            return result

        coordinator.recommend_solution = observed_solution

        # -------------------------------------------------------------
        # Start isolated local audit server
        # -------------------------------------------------------------

        from app.main import app

        import socket
        import threading
        import uvicorn
        import httpx

        progress("start local audit server")

        # Keep the socket bound to prevent accidentally
        # contacting another server.

        for port in (8001, 8002, 0):

            candidate = socket.socket()

            try:
                candidate.bind(
                    ("127.0.0.1", port)
                )

            except OSError:
                candidate.close()
                continue

            audit_socket = candidate
            break

        if audit_socket is None:
            raise RuntimeError(
                "No loopback socket could be reserved"
            )

        actual_port = (
            audit_socket.getsockname()[1]
        )

        address = (
            f"http://127.0.0.1:{actual_port}"
        )

        state["base_url"] = address
        state["page"] = address + "/home"

        state["endpoint"] = (
            "POST "
            + address
            + "/tickets/create"
        )

        server = uvicorn.Server(
            uvicorn.Config(
                app,
                host="127.0.0.1",
                port=actual_port,
                log_level="info",
                access_log=False,
            )
        )

        thread = threading.Thread(
            target=lambda: server.run(
                sockets=[audit_socket]
            ),
            daemon=True,
        )

        thread.start()

        for _ in range(120):

            if not thread.is_alive():
                raise RuntimeError(
                    "Audit server terminated "
                    "before startup"
                )

            if server.started:
                break

            time.sleep(0.25)

        if not server.started:
            raise RuntimeError(
                "Audit server startup timeout"
            )

        # -------------------------------------------------------------
        # Authenticate and submit exactly one ticket
        # -------------------------------------------------------------

        with httpx.Client(
            base_url=address,
            follow_redirects=False,
            timeout=150,
            trust_env=False,
        ) as client:

            health = client.get(
                "/health"
            )

            state["http"]["health"] = (
                health.status_code
            )

            if health.status_code != 200:
                raise RuntimeError(
                    "Audit server health check failed"
                )

            progress(
                "login with seeded synthetic CUSTOMER account"
            )

            login = client.post(
                "/login",
                data={
                    "username": account[0],
                    "password": account[3],
                },
            )

            state["http"]["login"] = {
                "status": login.status_code,
                "location": login.headers.get(
                    "location"
                ),
                "cookie_present": bool(
                    client.cookies.get(
                        "access_token"
                    )
                ),
            }

            if (
                login.status_code != 303
                or login.headers.get("location")
                != "/home"
                or not client.cookies.get(
                    "access_token"
                )
            ):
                raise RuntimeError(
                    "Normal synthetic login did not succeed; "
                    "ticket was not submitted"
                )

            home = client.get(
                "/home"
            )

            state["http"]["home"] = (
                home.status_code
            )

            if home.status_code != 200:
                raise RuntimeError(
                    "Authenticated customer page "
                    "not available"
                )

            progress(
                "submit IR-08 ticket once"
            )

            state["ticket_requests"] = 1

            save(
                folder,
                "execution.json",
                state,
            )

            created = client.post(
                "/tickets/create",
                data={
                    "title": TITLE,
                    "description": DESCRIPTION,
                },
            )

            state["http"]["ticket_create"] = {
                "status": created.status_code,
                "location": created.headers.get(
                    "location"
                ),
            }

            progress(
                "capture actual ticket response"
            )

            location = created.headers.get(
                "location",
                "",
            )

            if (
                created.status_code != 303
                or not re.fullmatch(
                    r"/tickets/\d+",
                    location,
                )
            ):
                save(
                    folder,
                    "ticket_error_response.txt",
                    created.text,
                )

                state["status"] = (
                    "Execution error"
                )

                raise RuntimeError(
                    "Normal ticket request did not "
                    "return a ticket redirect"
                )

            ticket_id = int(
                location.rsplit("/", 1)[-1]
            )

            page = client.get(
                location
            )

            state["http"]["ticket_page"] = (
                page.status_code
            )

            state["ticket_url"] = (
                address + location
            )

            save(
                folder,
                "customer_result.html",
                page.text,
            )

            # ---------------------------------------------------------
            # Capture persisted ticket and citations
            # ---------------------------------------------------------

            with Session(engine) as session:

                ticket = session.get(
                    Ticket,
                    ticket_id,
                )

                fields = (
                    "id",
                    "ticket_code",
                    "assigned_to",
                    "history_summary",
                    "title",
                    "description",
                    "masked_description",
                    "category",
                    "canonical_issue",
                    "priority",
                    "status",
                    "approval_status",
                    "retrieval_confidence",
                    "source_used",
                    "recommended_solution",
                    "decision_explanation",
                    "suggested_reply",
                )

                ticket_record = {
                    key: getattr(ticket, key)
                    for key in fields
                }

                citations = session.exec(
                    select(TicketCitation)
                    .where(
                        TicketCitation.ticket_id
                        == ticket_id
                    )
                    .order_by(
                        TicketCitation.rank
                    )
                ).all()

                ticket_record["citations"] = [
                    {
                        "source_id": citation.source_id,
                        "title": citation.title,
                        "source_type": citation.source_type,
                        "category": citation.category,
                        "relevance_score": (
                            citation.relevance_score
                        ),
                        "rank": citation.rank,
                    }
                    for citation in citations
                ]

                save(
                    folder,
                    "ticket.json",
                    ticket_record,
                )

                state["ticket"] = {
                    key: ticket_record[key]
                    for key in (
                        "id",
                        "category",
                        "canonical_issue",
                        "status",
                        "approval_status",
                        "retrieval_confidence",
                        "source_used",
                    )
                }

            # ---------------------------------------------------------
            # Read-only verification in IT Support queue
            # ---------------------------------------------------------

            progress(
                "verify visibility in human support queue "
                "without changing ticket"
            )

            queue_check = {
                "verification": (
                    "Read-only GET /support after normal "
                    "synthetic IT_SUPPORT login; "
                    "no resolve/approve/reject request"
                ),
                "role": "IT_SUPPORT",
                "ticket_id": ticket_id,
                "stored_status": ticket_record["status"],
                "assigned_to": ticket_record["assigned_to"],
            }

            with httpx.Client(
                base_url=address,
                follow_redirects=False,
                timeout=30,
                trust_env=False,
            ) as support_client:

                support_login = support_client.post(
                    "/login",
                    data={
                        "username": support_account[0],
                        "password": support_account[3],
                    },
                )

                queue_check["login_status"] = (
                    support_login.status_code
                )

                queue_check["login_location"] = (
                    support_login.headers.get(
                        "location"
                    )
                )

                queue_check["cookie_present"] = bool(
                    support_client.cookies.get(
                        "access_token"
                    )
                )

                if (
                    support_login.status_code == 303
                    and queue_check["cookie_present"]
                ):

                    support_page = (
                        support_client.get(
                            "/support"
                        )
                    )

                    queue_check["page_status"] = (
                        support_page.status_code
                    )

                    queue_check[
                        "ticket_resolve_form_present"
                    ] = (
                        f'action="/support/tickets/{ticket_id}/resolve"'
                        in support_page.text
                    )

                    queue_check[
                        "ticket_code_present"
                    ] = (
                        ticket_record["ticket_code"]
                        in support_page.text
                    )

                    queue_check[
                        "exact_description_present"
                    ] = (
                        DESCRIPTION
                        in html.unescape(
                            support_page.text
                        )
                    )

                    save(
                        folder,
                        "support_queue.html",
                        support_page.text,
                    )

                else:

                    queue_check["page_status"] = None

                    queue_check[
                        "verification_error"
                    ] = (
                        "Normal support login failed; "
                        "no queue request sent"
                    )

            save(
                folder,
                "support_queue_check.json",
                queue_check,
            )

            state["support_queue_check"] = (
                queue_check
            )

            # ---------------------------------------------------------
            # Record mechanical checks
            # ---------------------------------------------------------

            items = evidence.get(
                "retrieval",
                {},
            ).get(
                "items",
                [],
            )

            solution = evidence.get(
                "solution",
                {},
            )

            state["mechanical_checks"] = {
                "single_ticket_request": (
                    state["ticket_requests"] == 1
                ),
                "ticket_page_200": (
                    page.status_code == 200
                ),
                "retrieved_any_sources": bool(
                    items
                ),
                "all_returned_sources_approved_or_resolved": all(
                    item.get("status")
                    in ("approved", "resolved")
                    for item in items
                ),
                "solution_can_recommend": (
                    solution.get(
                        "can_recommend"
                    )
                ),
                "stored_ticket_escalated": (
                    ticket_record["status"]
                    == "ESCALATED"
                ),
                "top_category": (
                    items[0].get("category")
                    if items
                    else None
                ),
                "fixture_in_top_k": any(
                    item.get("source_id")
                    == FIXTURE["doc_id"]
                    for item in items
                ),
                "exact_match_source_ids": [
                    item["source_id"]
                    for item in items
                    if item.get(
                        "exact_error_match"
                    )
                ],
                "solution_citation_count": len(
                    solution.get(
                        "citations",
                        [],
                    )
                ),
                "stored_citation_count": len(
                    ticket_record[
                        "citations"
                    ]
                ),
                "support_queue_shows_ticket": (
                    queue_check.get(
                        "page_status"
                    )
                    == 200
                    and queue_check.get(
                        "ticket_resolve_form_present",
                        False,
                    )
                    and queue_check.get(
                        "exact_description_present",
                        False,
                    )
                ),
            }

            state["status"] = (
                "Executed; awaiting source/answer review"
            )

            state["outcome"] = (
                "Unassessed"
            )

            state["stage"] = (
                "execution completed"
            )

            state["review_note"] = (
                "Review five-variant code identity, exact fixture "
                "retention/flags/bonus and formatting-driven answer "
                "changes. Record auxiliary entity extraction separately. "
                "Synthetic approved metadata does not validate a real "
                "diagnosis or repair; review any generic fallback advice "
                "separately."
            )

    except Exception as exc:

        state["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

        if state["ticket_requests"] == 0:
            state["status"] = "Not ready"

        else:
            state["status"] = (
                "Execution error; review required"
            )

        import traceback

        traceback.print_exc()

        state["outcome"] = (
            "Unassessed"
        )

    finally:

        if server:
            server.should_exit = True

        if thread:
            thread.join(timeout=12)

        if audit_socket:
            audit_socket.close()

        state["server_stopped"] = (
            thread is None
            or not thread.is_alive()
        )

        state["finished_at_utc"] = now()

        save(
            folder,
            "execution.json",
            state,
        )

        print(
            clean(
                json.dumps(state)
            ),
            flush=True,
        )

    return (
        0
        if state["status"]
        == "Executed; awaiting source/answer review"
        else 1
    )


# ---------------------------------------------------------------------
# Parent runner: all five variants
# ---------------------------------------------------------------------

def parent():

    stamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )

    folder = (
        ROOT
        / "audit"
        / "evidence"
        / "IR-08"
        / ("run-" + stamp)
    )

    folder.mkdir(
        parents=True,
        exist_ok=False,
    )

    before = code_hashes()

    database_hash = digest(
        ROOT / "knowgap.db"
    )

    baseline = parse_json(
        ROOT
        / "audit"
        / "evidence"
        / "baseline"
        / "environment.json"
    )

    backup = parse_json(
        ROOT
        / "audit"
        / "evidence"
        / "baseline"
        / "database_backup.json"
    )

    backup_path = Path(
        backup.get(
            "path",
            "",
        )
    )

    backup_verified = (
        backup_path.is_file()
        and digest(backup_path)
        == backup.get("backup_sha256")
    )

    # -------------------------------------------------------------
    # Read original dataset metadata
    # -------------------------------------------------------------

    with (
        ROOT / "data" / "knowledge_base.csv"
    ).open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:

        kb_rows = list(
            csv.DictReader(handle)
        )

    with (
        ROOT / "data" / "tickets.csv"
    ).open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:

        ticket_rows = list(
            csv.DictReader(handle)
        )

    approved_exact = [
        row
        for row in kb_rows
        if (
            row["status"] == "approved"
            and ERROR_CODE
            in " ".join(
                str(value)
                for value in row.values()
            ).lower()
        )
    ]

    exact_tickets = [
        row
        for row in ticket_rows
        if ERROR_CODE
        in " ".join(
            str(value)
            for value in row.values()
        ).lower()
    ]

    resolved_exact = [
        row
        for row in exact_tickets
        if (
            row["status"] == "Resolved"
            and row["resolution_notes"].strip()
        )
    ]

    # -------------------------------------------------------------
    # Save declared inputs before executing any subcase
    # -------------------------------------------------------------

    save(
        folder,
        "inputs.json",
        {
            "recorded_before_requests_at_utc": now(),
            "case": "IR-08",
            "title": TITLE,
            "sentence_template": (
                "Windows blue screen error {variant}"
            ),
            "cases": [
                {
                    "name": name,
                    "variant": VARIANTS[name],
                    "description": description,
                    "characters": len(
                        description
                    ),
                }
                for name, description
                in SUBCASES.items()
            ],
        },
    )

    save(
        folder,
        "fixture.json",
        {
            "recorded_before_requests_at_utc": now(),
            "fixture": FIXTURE,
            "retrieval_record": FIXTURE_RECORD,
            "scope": (
                "Same synthetic approved-status fixture "
                "separately inserted in five fresh temporary "
                "databases; original DB and CSVs unchanged. "
                "Approval status is controlled test metadata, "
                "not independent validation."
            ),
            "why": (
                "IR-03 had zero eligible exact-code sources; "
                "test_plan.md IR-08 permits a labelled isolated "
                "fixture. IR-03 result remains unchanged."
            ),
        },
    )

    for name, description in SUBCASES.items():

        child = folder / name

        child.mkdir()

        save(
            child,
            "input.json",
            {
                "case": "IR-08",
                "subcase": name,
                "title": TITLE,
                "variant": VARIANTS[name],
                "description": description,
                "characters": len(
                    description
                ),
            },
        )

        save(
            child,
            "input.txt",
            (
                "IR-08 / "
                + name
                + "\nTitle: "
                + TITLE
                + "\nDescription: "
                + description
            ),
        )

    # -------------------------------------------------------------
    # Record expected behavior before execution
    # -------------------------------------------------------------

    save(
        folder,
        "expected_result.md",
        "\n".join(
            [
                "# IR-08 criteria fixed before any request",
                "",
                (
                    "- Submit each of the five planned variants "
                    "exactly once in the same full sentence and "
                    "same title, with fresh independently seeded "
                    "databases and the same labelled fixture."
                ),
                (
                    "- The original corpus has no eligible "
                    "exact-code source. The added article is an "
                    "isolated synthetic lookup control, not proof "
                    "of a real code diagnosis or repair. Do not "
                    "change IR-03's missing-prerequisite result."
                ),
                (
                    "- Primary retrieval PASS: all five valid "
                    "executions preserve the code identity "
                    "0x00000124 in canonical-query extraction, "
                    "normalized extraction and BM25 tokens, "
                    "retain the same exact-code fixture in top-k "
                    "with correct exact_error_match flags, and "
                    "exhibit no formatting-driven transition "
                    "to unsupported confident advice."
                ),
                (
                    "- Primary FAIL: valid formatting variation "
                    "loses code identity or exact fixture "
                    "relevance/flags, crashes, or causes an "
                    "unsupported confident-answer transition. "
                    "Numerical/rank changes alone do not fail "
                    "if relevance and behavior remain appropriate."
                ),
                (
                    "- Verify actual exact-match bonus using "
                    "raw hybrid score minus weighted BM25/"
                    "semantic components; +0.35 should apply "
                    "only to the code-matching fixture. "
                    "This arithmetic check is not an ablation "
                    "or independent search."
                ),
                (
                    "- Auxiliary entity check: all five "
                    "equivalent codes should populate "
                    "analysis.entities.error_code consistently "
                    "after case normalization. Record any "
                    "mismatch as its own PASS/FAIL because "
                    "the entity field is not the query "
                    "passed into retrieval."
                ),
                (
                    "- Review complete rankings, original "
                    "fallback message/explanation/reply/"
                    "citations and persisted state for each "
                    "case. Fixture retrieval does not certify "
                    "source approval security, real "
                    "troubleshooting applicability or "
                    "calibrated confidence."
                ),
                (
                    "- Record generic repair overstatement "
                    "if present across all forms separately "
                    "from a formatting-induced failure; do "
                    "not hide it behind a primary retrieval PASS."
                ),
                (
                    "- Same source/configuration/LLM mode, "
                    "eligible corpus and fixture across all "
                    "variants; original functions observed "
                    "without changed arguments/results. "
                    "A missing prerequisite yields "
                    "Not ready/Inconclusive."
                ),
                (
                    "- Normal CUSTOMER login and one ticket "
                    "per variant; read-only IT_SUPPORT queue "
                    "observation. No approval, repair, "
                    "resolution or other mutation beyond "
                    "declared isolated setup/ticket creation."
                ),
                (
                    "- Verify private backup; preserve "
                    "original database and CSV/source files. "
                    "Run cached model only. Disabled Groq "
                    "yields fallback-only conclusions."
                ),
                (
                    "- No other formats, no corpus-only "
                    "replay of IR-03, no load testing, "
                    "no fixes and no IR-09 or later cases. "
                    "A failed subcheck is not automatically "
                    "a security vulnerability."
                ),
            ]
        ),
    )

    # -------------------------------------------------------------
    # Dataset and source preflight evidence
    # -------------------------------------------------------------

    save(
        folder,
        "source_preflight.json",
        {
            "recorded_at_utc": now(),
            "original_corpus": (
                "Unmodified project CSVs"
            ),
            "test_corpus": (
                "Original eligible CSV records plus "
                "one declared isolated fixture per variant"
            ),
            "kb_rows": len(
                kb_rows
            ),
            "ticket_rows": len(
                ticket_rows
            ),
            "approved_exact_code_count_in_original": (
                len(approved_exact)
            ),
            "eligible_resolved_exact_code_count_in_original": (
                len(resolved_exact)
            ),
            "original_exact_code_tickets": [
                {
                    "source_id": row["ticket_id"],
                    "status": row["status"],
                    "has_resolution": bool(
                        row["resolution_notes"].strip()
                    ),
                }
                for row in exact_tickets
            ],
            "synthetic_fixture_source_id": (
                FIXTURE["doc_id"]
            ),
            "fixture_has_verified_real_repair": False,
            "kb_csv_sha256": digest(
                ROOT
                / "data"
                / "knowledge_base.csv"
            ),
            "ticket_csv_sha256": digest(
                ROOT
                / "data"
                / "tickets.csv"
            ),
        },
    )

    save(
        folder,
        "preconditions.json",
        {
            "recorded_before_requests_at_utc": now(),
            "case": "IR-08",
            "original_database_main_file_sha256": (
                database_hash
            ),
            "production_source_sha256": before,
            "sources_same_as_phase1": (
                before
                == baseline.get(
                    "source_sha256"
                )
            ),
            "private_phase1_backup_verified": (
                backup_verified
            ),
            "original_database_same_as_phase1": (
                database_hash
                == baseline.get(
                    "original_database_sha256"
                )
            ),
            "execution_settings": {
                "thread_limit": 1,
                "cached_model_only": True,
                "external_LLM_configuration": (
                    "unchanged; actual enabled state "
                    "recorded per worker"
                ),
            },
            "instrumentation": (
                "Observe original analysis/normalization/"
                "hybrid/search/solution/chat returns and "
                "corpus; original functions called once "
                "without argument/result changes; "
                "read-only queue verification."
            ),
        },
    )

    # -------------------------------------------------------------
    # Check unchanged sources against previous runs
    # -------------------------------------------------------------

    previous_preconditions = parse_json(
        IR01_RUN
        / "preconditions.json"
    )

    previous_sources = parse_json(
        IR01_RUN
        / "source_preflight.json"
    )

    comparable = {
        "reference_run": (
            IR01_RUN.relative_to(
                ROOT
            ).as_posix()
        ),
        "source_files_same_as_IR01": (
            before
            == previous_preconditions.get(
                "production_source_sha256"
            )
        ),
        "kb_csv_same_as_IR01": (
            digest(
                ROOT
                / "data"
                / "knowledge_base.csv"
            )
            == previous_sources.get(
                "kb_csv_sha256"
            )
        ),
        "ticket_csv_same_as_IR01": (
            digest(
                ROOT
                / "data"
                / "tickets.csv"
            )
            == previous_sources.get(
                "ticket_csv_sha256"
            )
        ),
    }

    previous_ir03 = parse_json(
        IR03_RUN
        / "preconditions.json"
    )

    comparable[
        "source_files_same_as_IR03"
    ] = (
        before
        == previous_ir03.get(
            "production_source_sha256"
        )
    )

    comparable[
        "IR03_original_missing_source_outcome_preserved"
    ] = parse_json(
        IR03_RUN
        / "review.json"
    ).get(
        "outcome"
    )

    comparable[
        "corpus_comparison_limit"
    ] = (
        "IR-08 deliberately adds one isolated synthetic "
        "exact-code fixture; its scores are not a "
        "like-for-like comparison with original-corpus IR-03"
    )

    save(
        folder,
        "comparison_preflight.json",
        comparable,
    )

    if (
        not backup_verified
        or approved_exact
        or resolved_exact
        or not all(
            comparable[key]
            for key in (
                "source_files_same_as_IR01",
                "kb_csv_same_as_IR01",
                "ticket_csv_same_as_IR01",
                "source_files_same_as_IR03",
            )
        )
    ):

        save(
            folder,
            "process_result.json",
            {
                "case": "IR-08",
                "status": "Not ready",
                "outcome": "Unassessed",
                "reason": (
                    "Backup, original missing-source "
                    "assumption or unchanged source/CSV "
                    "precondition failed; "
                    "no ticket submitted"
                ),
            },
        )

        print(
            "IR-08 evidence: "
            + str(folder)
        )

        return 1

    # -------------------------------------------------------------
    # Execute the five variants independently
    # -------------------------------------------------------------

    results = []

    for name in SUBCASES:

        child = folder / name

        command = [
            sys.executable,
            "-B",
            str(
                Path(__file__).resolve()
            ),
            "--worker",
            str(child),
            "--subcase",
            name,
        ]

        started = (
            time.perf_counter()
        )

        timed_out = False

        try:

            run = subprocess.run(
                command,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                errors="replace",
                timeout=300,
                creationflags=getattr(
                    subprocess,
                    "CREATE_NO_WINDOW",
                    0,
                ),
            )

            output = (
                run.stdout
                + "\n"
                + run.stderr
            )

            exit_code = (
                run.returncode
            )

        except subprocess.TimeoutExpired as exc:

            timed_out = True

            exit_code = None

            def decode(value):
                if isinstance(
                    value,
                    bytes,
                ):
                    return value.decode(
                        "utf-8",
                        errors="replace",
                    )

                return value or ""

            output = (
                decode(exc.stdout)
                + "\n"
                + decode(exc.stderr)
            )

        save(
            child,
            "terminal_log.txt",
            output,
        )

        child_state = parse_json(
            child
            / "execution.json"
        )

        result = {
            "finished_at_utc": now(),
            "subcase": name,
            "process_exit_code": exit_code,
            "timed_out": timed_out,
            "elapsed_seconds": round(
                time.perf_counter()
                - started,
                3,
            ),
            "source_files_unchanged": (
                before == code_hashes()
            ),
            "original_database_main_file_unchanged": (
                database_hash
                == digest(
                    ROOT / "knowgap.db"
                )
            ),
            "evidence_directory": (
                child.relative_to(
                    ROOT
                ).as_posix()
            ),
            "worker_status": (
                child_state.get(
                    "status"
                )
            ),
            "worker_stage": (
                child_state.get(
                    "stage"
                )
            ),
            "ticket_requests": (
                child_state.get(
                    "ticket_requests",
                    0,
                )
            ),
        }

        save(
            child,
            "process_result.json",
            result,
        )

        results.append(
            result
        )

        print(
            clean(
                json.dumps(
                    result
                )
            ),
            flush=True,
        )

        if (
            exit_code != 0
            or timed_out
            or not result[
                "source_files_unchanged"
            ]
            or not result[
                "original_database_main_file_unchanged"
            ]
        ):
            break

    # -------------------------------------------------------------
    # Save parent summary
    # -------------------------------------------------------------

    result = {
        "case": "IR-08",
        "finished_at_utc": now(),
        "outcome": (
            "Unassessed; await reviewed comparison"
        ),
        "subcases": results,
        "ticket_requests": sum(
            entry["ticket_requests"]
            for entry in results
        ),
        "source_files_unchanged": (
            before == code_hashes()
        ),
        "original_database_main_file_unchanged": (
            database_hash
            == digest(
                ROOT / "knowgap.db"
            )
        ),
        "integrity_limit": (
            "Original main-file checksum does not cover "
            "concurrent WAL writes by another process; "
            "helper never writes working database."
        ),
        "evidence_directory": (
            folder.relative_to(
                ROOT
            ).as_posix()
        ),
    }

    save(
        folder,
        "process_result.json",
        result,
    )

    print(
        clean(
            json.dumps(
                result
            )
        ),
        flush=True,
    )

    all_completed = (
        len(results)
        == len(SUBCASES)
        and all(
            entry["process_exit_code"] == 0
            and not entry["timed_out"]
            for entry in results
        )
    )

    return (
        0
        if all_completed
        else 1
    )


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--worker",
        type=Path,
    )

    parser.add_argument(
        "--subcase",
        choices=tuple(
            SUBCASES
        ),
    )

    args = parser.parse_args()

    if args.worker:

        resolved = (
            args.worker.resolve()
        )

        allowed = (
            ROOT
            / "audit"
            / "evidence"
            / "IR-08"
        ).resolve()

        if not resolved.is_relative_to(
            allowed
        ):
            raise SystemExit(
                "Evidence path must be inside "
                "audit/evidence/IR-08"
            )

        if (
            not args.subcase
            or resolved.name
            != args.subcase
        ):
            raise SystemExit(
                "Worker requires matching "
                "subcase folder"
            )

        raise SystemExit(
            worker(
                resolved,
                args.subcase,
            )
        )

    raise SystemExit(
        parent()
    )
