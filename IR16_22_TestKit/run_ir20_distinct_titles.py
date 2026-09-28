"""IR-20: Contradictory approved knowledge, baseline versus conflict."""
from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

for name in (
    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"
):
    os.environ[name] = "1"

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

KEEP_ID = "AUDIT-IR20-KEEP-001"
RESET_ID = "AUDIT-IR20-RESET-002"

QUERY = (
    "My printer queue is stuck and print jobs "
    "will not clear."
)

TITLE = "Printer queue stuck and print jobs will not clear"
KEEP_TITLE = "Printer queue recovery: preserve existing settings"
RESET_TITLE = "Printer queue recovery: restore factory settings"

KEEP_BODY = (
    "For a printer queue that is stuck and print jobs "
    "that will not clear, KEEP all existing printer "
    "settings unchanged. Stop the print spooler, clear "
    "the stuck print jobs, restart the print spooler, "
    "and retry printing. Do NOT reset printer settings."
)

RESET_BODY = (
    "For a printer queue that is stuck and print jobs "
    "that will not clear, RESET the printer settings "
    "to factory defaults before attempting to print "
    "again. Do NOT retain the existing printer settings."
)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    p = Path(path)
    return (
        hashlib.sha256(p.read_bytes()).hexdigest()
        if p.is_file() else None
    )


def original_hashes():
    paths = list((ROOT / "app").rglob("*.py"))
    paths += [
        ROOT / "scripts" / "seed_db.py",
        ROOT / "data" / "tickets.csv",
        ROOT / "data" / "knowledge_base.csv",
        ROOT / "knowgap.db",
        ROOT / "knowgap.db-wal",
        ROOT / "knowgap.db-shm",
    ]
    return {
        str(p.relative_to(ROOT)): sha(p)
        for p in sorted(paths)
    }


def save(folder, filename, content):
    path = Path(folder) / filename
    if isinstance(content, str):
        path.write_text(content, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(
                content, indent=2,
                ensure_ascii=False, default=str
            ),
            encoding="utf-8",
        )


def worker(variant, folder):
    import httpx
    import uvicorn
    from sqlmodel import Session, select

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)

    state = {
        "variant": variant,
        "status": "INCONCLUSIVE",
        "ticket_requests": 0,
        "started_at_utc": now(),
    }

    server = None
    thread = None
    bound_socket = None
    engine = None

    try:
        with tempfile.TemporaryDirectory(
            prefix="knowgap-ir20-" + variant + "-"
        ) as temporary:

            database = Path(temporary) / "ir20.db"

            os.environ["DATABASE_URL"] = (
                "sqlite:///" + database.as_posix()
            )

            from app.database import (
                create_db_and_tables,
                engine as app_engine,
            )
            from app.models import (
                KnowledgeArticle, Ticket,
                TicketCitation, User,
            )
            from scripts.seed_db import (
                USERS, seed_users, seed_kb,
                seed_historical_tickets,
            )

            engine = app_engine

            if (
                Path(engine.url.database).resolve()
                != database.resolve()
                or database.resolve()
                == (ROOT / "knowgap.db").resolve()
            ):
                raise RuntimeError(
                    "Temporary database isolation failed"
                )

            create_db_and_tables()

            fixed_date = datetime(2026, 9, 20)

            def article(doc_id, body):
                return KnowledgeArticle(
                    doc_id=doc_id,
                    title=(
                        KEEP_TITLE if doc_id == KEEP_ID
                        else RESET_TITLE
                    ),
                    content=body,
                    category="Printers",
                    status="approved",
                    source_type="internal_kb",
                    author="IR20 synthetic audit",
                    authoritative=True,
                    supported_os="Any",
                    security_class="internal",
                    created_at=fixed_date,
                    updated_at=fixed_date,
                )

            with Session(engine) as session:
                seed_users(session)
                seed_kb(session)
                seed_historical_tickets(session)

                session.add(article(KEEP_ID, KEEP_BODY))

                if variant == "conflict":
                    session.add(
                        article(RESET_ID, RESET_BODY)
                    )

                session.commit()

                original_printer = session.exec(
                    select(KnowledgeArticle).where(
                        KnowledgeArticle.doc_id == "KB-005"
                    )
                ).one()

                keep = session.exec(
                    select(KnowledgeArticle).where(
                        KnowledgeArticle.doc_id == KEEP_ID
                    )
                ).one()

                reset = session.exec(
                    select(KnowledgeArticle).where(
                        KnowledgeArticle.doc_id == RESET_ID
                    )
                ).first()

                if (
                    original_printer.status != "approved"
                    or keep.status != "approved"
                    or (
                        variant == "conflict"
                        and (
                            reset is None
                            or reset.status != "approved"
                        )
                    )
                    or (
                        variant == "baseline"
                        and reset is not None
                    )
                ):
                    raise RuntimeError(
                        "Approved article fixture check failed"
                    )

                initial_ticket_count = len(
                    session.exec(select(Ticket)).all()
                )

                account = next(
                    row for row in USERS
                    if row[2] == "CUSTOMER"
                )

            fixtures = {
                "existing_approved_printer": {
                    "id": original_printer.doc_id,
                    "title": original_printer.title,
                    "content": original_printer.content,
                    "status": original_printer.status,
                },
                "retain_article": {
                    "id": KEEP_ID,
                    "title": keep.title,
                    "content": keep.content,
                    "status": keep.status,
                    "created_at": keep.created_at,
                    "updated_at": keep.updated_at,
                },
                "reset_article": (
                    {
                        "id": RESET_ID,
                        "title": reset.title,
                        "content": reset.content,
                        "status": reset.status,
                        "created_at": reset.created_at,
                        "updated_at": reset.updated_at,
                    }
                    if reset else None
                ),
            }

            save(folder, "verified_fixtures.json", fixtures)

            snapshot = folder / "pre_request.sqlite"

            with closing(
                sqlite3.connect(str(database))
            ) as source:
                with closing(
                    sqlite3.connect(str(snapshot))
                ) as destination:
                    source.backup(destination)
                    integrity = destination.execute(
                        "PRAGMA integrity_check"
                    ).fetchone()[0]

            if integrity != "ok":
                raise RuntimeError(
                    "Synthetic database snapshot invalid"
                )

            snapshot_sha = sha(snapshot)

            # All LLM calls are blocked; only local fallback
            # behavior is assessed.
            from app.services.llm import llm

            llm_calls = {"blocked": 0}

            def offline_chat(*args, **kwargs):
                llm_calls["blocked"] += 1
                raise RuntimeError(
                    "IR-20: external LLM disabled"
                )

            llm.chat = offline_chat

            from app.agents import (
                coordinator, retrieval_agent
            )

            observed = {
                "eligible_corpus": None,
                "retrieval": None,
                "solution": None,
            }

            original_rank = retrieval_agent.hybrid_rank

            def capture_rank(*args, **kwargs):
                records = (
                    args[1] if len(args) > 1
                    else kwargs.get("records", [])
                )

                observed["eligible_corpus"] = records
                save(folder, "eligible_corpus.json", records)

                result = original_rank(*args, **kwargs)
                save(folder, "raw_hybrid_ranking.json", result)
                return result

            retrieval_agent.hybrid_rank = capture_rank

            original_search = coordinator.search_knowledge

            def capture_search(*args, **kwargs):
                result = original_search(*args, **kwargs)
                observed["retrieval"] = result
                save(folder, "retrieval.json", result)
                return result

            coordinator.search_knowledge = capture_search

            original_solution = coordinator.recommend_solution

            def capture_solution(*args, **kwargs):
                result = original_solution(*args, **kwargs)
                observed["solution"] = result
                save(folder, "solution.json", result)
                return result

            coordinator.recommend_solution = capture_solution

            from app.main import app

            bound_socket = socket.socket()
            bound_socket.bind(("127.0.0.1", 0))
            port = bound_socket.getsockname()[1]

            server = uvicorn.Server(
                uvicorn.Config(
                    app,
                    host="127.0.0.1",
                    port=port,
                    log_level="warning",
                    access_log=False,
                )
            )

            thread = threading.Thread(
                target=lambda: server.run(
                    sockets=[bound_socket]
                ),
                daemon=True,
            )
            thread.start()

            for _ in range(120):
                if not thread.is_alive():
                    raise RuntimeError(
                        "Local test server terminated"
                    )
                if server.started:
                    break
                time.sleep(0.25)

            if not server.started:
                raise RuntimeError(
                    "Local test server startup timeout"
                )

            address = f"http://127.0.0.1:{port}"

            with httpx.Client(
                base_url=address,
                follow_redirects=False,
                timeout=150,
                trust_env=False,
            ) as client:

                if client.get("/health").status_code != 200:
                    raise RuntimeError(
                        "Local health check failed"
                    )

                login = client.post(
                    "/login",
                    data={
                        "username": account[0],
                        "password": account[3],
                    },
                )

                if (
                    login.status_code != 303
                    or not client.cookies.get(
                        "access_token"
                    )
                ):
                    raise RuntimeError(
                        "Synthetic login failed"
                    )

                state["ticket_requests"] = 1

                created = client.post(
                    "/tickets/create",
                    data={
                        "title": TITLE,
                        "description": QUERY,
                    },
                )

                location = created.headers.get(
                    "location", ""
                )

                if (
                    created.status_code != 303
                    or not re.fullmatch(
                        r"/tickets/\d+", location
                    )
                ):
                    raise RuntimeError(
                        "Ticket creation failed: "
                        + str(created.status_code)
                    )

                ticket_id = int(
                    location.rsplit("/", 1)[-1]
                )

                page = client.get(location)

                if page.status_code != 200:
                    raise RuntimeError(
                        "Customer ticket page failed"
                    )

                save(
                    folder,
                    "customer_result.html",
                    page.text
                )

            with Session(engine) as session:
                ticket = session.get(
                    Ticket, ticket_id
                )

                if ticket is None:
                    raise RuntimeError(
                        "Created ticket missing"
                    )

                fields = (
                    "id", "ticket_code",
                    "canonical_issue", "category",
                    "status", "source_used",
                    "retrieval_confidence",
                    "recommended_solution",
                    "decision_explanation",
                    "suggested_reply",
                )

                stored = {
                    name: getattr(ticket, name)
                    for name in fields
                }

                citations = session.exec(
                    select(TicketCitation).where(
                        TicketCitation.ticket_id
                        == ticket_id
                    ).order_by(TicketCitation.rank)
                ).all()

                stored["citations"] = [
                    {
                        "source_id": c.source_id,
                        "title": c.title,
                        "rank": c.rank,
                    }
                    for c in citations
                ]

                final_ticket_count = len(
                    session.exec(select(Ticket)).all()
                )

            save(folder, "stored_ticket.json", stored)

            corpus = (
                observed["eligible_corpus"] or []
            )
            retrieval = observed["retrieval"] or {}
            solution = observed["solution"] or {}

            eligible_ids = [
                item.get("source_id")
                for item in corpus
            ]
            ranked_ids = [
                item.get("source_id")
                for item in retrieval.get(
                    "items", []
                )
            ]
            citation_ids = [
                item["source_id"]
                for item in stored["citations"]
            ]

            answer = "\n".join(
                str(value or "")
                for value in (
                    stored["recommended_solution"],
                    stored["decision_explanation"],
                    stored["suggested_reply"],
                    solution.get("message"),
                    solution.get("explanation"),
                )
            )

            answer_lower = answer.lower()

            conflict_indicators = [
                term
                for term in (
                    "conflict",
                    "contradict",
                    "disagree",
                    "inconsistent",
                    "different advice",
                    "two approaches",
                    "two procedures",
                    "human review",
                    "escalat",
                    "clarif",
                )
                if term in answer_lower
            ]

            state["observation"] = {
                "ticket_id": ticket_id,
                "canonical_issue": stored[
                    "canonical_issue"
                ],
                "ticket_status": stored["status"],
                "eligible_count": len(corpus),
                "keep_eligible": (
                    KEEP_ID in eligible_ids
                ),
                "reset_eligible": (
                    RESET_ID in eligible_ids
                ),
                "keep_top_k": (
                    KEEP_ID in ranked_ids
                ),
                "reset_top_k": (
                    RESET_ID in ranked_ids
                ),
                "both_conflicting_sources_top_k": (
                    KEEP_ID in ranked_ids
                    and RESET_ID in ranked_ids
                ),
                "ranked_source_ids": ranked_ids,
                "retrieval_decision": retrieval.get(
                    "decision"
                ),
                "best_score": retrieval.get(
                    "best_score"
                ),
                "source_used": stored[
                    "source_used"
                ],
                "citation_ids": citation_ids,
                "conflict_indicators_in_answer": (
                    conflict_indicators
                ),
                "keep_instruction_in_answer": (
                    "keep" in answer_lower
                    and "settings" in answer_lower
                ),
                "reset_instruction_in_answer": (
                    "reset" in answer_lower
                    and "settings" in answer_lower
                ),
                "answer_excerpt": answer[:700],
                "one_ticket_created": (
                    final_ticket_count
                    == initial_ticket_count + 1
                ),
                "snapshot_unchanged": (
                    sha(snapshot) == snapshot_sha
                ),
                "llm_calls_blocked": (
                    llm_calls["blocked"]
                ),
            }

            save(
                folder, "observation.json",
                state["observation"]
            )

            if any(
                observed[key] is None
                for key in (
                    "eligible_corpus",
                    "retrieval",
                    "solution",
                )
            ):
                raise RuntimeError(
                    "Ticket did not reach all "
                    "required workflow stages"
                )

            if not state["observation"][
                "snapshot_unchanged"
            ]:
                raise RuntimeError(
                    "Synthetic snapshot changed"
                )

            server.should_exit = True
            thread.join(timeout=20)

            if thread.is_alive():
                raise RuntimeError(
                    "Local test server did not stop"
                )

            engine.dispose()
            engine = None

            state["status"] = "EXECUTED"

    except Exception:
        save(
            folder,
            "execution_error.txt",
            traceback.format_exc()
        )

    finally:
        if server is not None:
            server.should_exit = True
        if thread is not None:
            thread.join(timeout=20)
        if bound_socket is not None:
            bound_socket.close()
        if engine is not None:
            engine.dispose()

        state["finished_at_utc"] = now()
        save(
            folder,
            "worker_result.json",
            state
        )

    return 0 if state["status"] == "EXECUTED" else 1


def main():
    if (
        len(sys.argv) == 4
        and sys.argv[1] == "--worker"
    ):
        return worker(
            sys.argv[2],
            sys.argv[3]
        )

    stamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )
    folder = (
        ROOT / "audit" / "evidence" /
        "IR-20" / ("run-" + stamp)
    )
    folder.mkdir(parents=True, exist_ok=False)

    before = original_hashes()

    original_corpus = "\n".join(
        (ROOT / "data" / filename).read_text(
            encoding="utf-8-sig"
        )
        for filename in (
            "knowledge_base.csv", "tickets.csv"
        )
    )

    if (
        KEEP_ID in original_corpus
        or RESET_ID in original_corpus
    ):
        raise SystemExit(
            "Synthetic ID collision in original corpus; "
            "no test requests sent"
        )

    save(folder, "preconditions.json", {
        "original_file_sha256": before,
        "separate_temporary_databases": True,
        "normal_ticket_requests_per_variant": 1,
        "artificial_ranking_scores": False,
        "external_llm_calls": "blocked",
        "created_at_utc": now(),
    })

    results = {}
    complete = True

    for variant in (
        "baseline",
        "conflict",
    ):
        child = folder / variant

        try:
            process = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(Path(__file__).resolve()),
                    "--worker",
                    variant,
                    str(child),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=240,
            )

            save(
                folder,
                variant + "_stdout.txt",
                process.stdout
            )
            save(
                folder,
                variant + "_stderr.txt",
                process.stderr
            )

            result = json.loads(
                (child / "worker_result.json").read_text(
                    encoding="utf-8"
                )
            )

            results[variant] = result

            print(
                variant + ": " + result["status"],
                flush=True
            )

            if (
                process.returncode != 0
                or result["status"] != "EXECUTED"
            ):
                complete = False

        except Exception:
            complete = False
            save(
                folder,
                variant + "_parent_error.txt",
                traceback.format_exc()
            )
            break

    baseline = results.get(
        "baseline", {}
    ).get("observation", {})

    conflict = results.get(
        "conflict", {}
    ).get("observation", {})

    unchanged = before == original_hashes()

    comparable = (
        complete
        and unchanged
        and baseline.get(
            "keep_eligible"
        ) is True
        and baseline.get(
            "reset_eligible"
        ) is False
        and conflict.get(
            "keep_eligible"
        ) is True
        and conflict.get(
            "reset_eligible"
        ) is True
        and baseline.get(
            "canonical_issue"
        ) == conflict.get(
            "canonical_issue"
        )
        and baseline.get(
            "one_ticket_created"
        ) is True
        and conflict.get(
            "one_ticket_created"
        ) is True
        and baseline.get(
            "snapshot_unchanged"
        ) is True
        and conflict.get(
            "snapshot_unchanged"
        ) is True
    )

    if not comparable:
        assessment = (
            "INCONCLUSIVE — inspect worker errors "
            "and database comparability"
        )
    elif not conflict.get(
        "both_conflicting_sources_top_k"
    ):
        assessment = (
            "PARTIAL — both approved documents eligible, "
            "but both did not reach top-k; conflict-handling "
            "behavior not fully exercised"
        )
    else:
        assessment = (
            "BOTH CONTRADICTORY DOCUMENTS RETRIEVED — "
            "manual assessment of final answer and "
            "citations required"
        )

    summary = {
        "case": "IR-20",
        "status": (
            "EXECUTED" if comparable
            else "INCONCLUSIVE"
        ),
        "assessment": assessment,
        "comparable": comparable,
        "original_files_unchanged": unchanged,
        "baseline": baseline,
        "conflict": conflict,
        "limitations": (
            "Original retrieval and local fallback "
            "workflow; synthetic approved articles; "
            "external LLM disabled. One normal ticket "
            "request per variant."
        ),
        "evidence_directory": str(
            folder.relative_to(ROOT)
        ),
    }

    save(
        folder,
        "process_result.json",
        summary
    )

    print(json.dumps(
        summary,
        indent=2,
        ensure_ascii=False
    ))

    return 0 if comparable else 1


if __name__ == "__main__":
    raise SystemExit(main())
