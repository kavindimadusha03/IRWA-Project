"""IR-16: Cross-user ticket access using the original app and synthetic data."""
from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import sys
import tempfile
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Set isolation before importing any application modules.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

for key in (
    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"
):
    os.environ[key] = "1"

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

MARKER = "IR16-PRIVATE-CUSTOMER-A"
SECOND_CUSTOMER = "audit_ir16_customer_b"


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    path = Path(path)
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    names = [
        "app/main.py",
        "app/config.py",
        "app/models.py",
        "app/agents/retrieval_agent.py",
        "app/agents/solution_agent.py",
    ]
    return {name: digest(ROOT / name) for name in names}


def working_database_hashes():
    return {
        name: digest(ROOT / name)
        for name in ("knowgap.db", "knowgap.db-wal", "knowgap.db-shm")
    }


def save(folder, name, value):
    path = folder / name
    if isinstance(value, str):
        path.write_text(value, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(value, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )


def ticket_snapshot(ticket):
    return {
        column.name: getattr(ticket, column.name)
        for column in ticket.__table__.columns
    }


def choose_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def run():
    import httpx
    import uvicorn
    from sqlmodel import Session, select

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder = ROOT / "audit" / "evidence" / "IR-16" / ("run-" + stamp)
    folder.mkdir(parents=True, exist_ok=False)

    result = {
        "case": "IR-16",
        "started_at_utc": now(),
        "status": "NOT READY",
        "outcome": "UNASSESSED",
        "scope": "Original FastAPI application, isolated synthetic database",
        "http": {},
        "checks": {},
    }

    before_source = source_hashes()
    before_working_db = working_database_hashes()

    prepared = (
        ROOT / "audit" / "evidence" / "IR-16"
        / "run-20260926T085916546998Z"
    )

    expected_file = prepared / "expected_result.md"
    if expected_file.is_file():
        save(folder, "expected_result.md", expected_file.read_text(
            encoding="utf-8-sig"
        ))

    save(folder, "preconditions.json", {
        "recorded_at_utc": now(),
        "source_sha256": before_source,
        "working_database_sha256": before_working_db,
        "data_csv_sha256": {
            name: digest(ROOT / "data" / name)
            for name in ("knowledge_base.csv", "tickets.csv")
        },
        "prepared_evidence": str(prepared.relative_to(ROOT)),
        "expected_users": "Two distinct synthetic CUSTOMER accounts",
        "original_application_modified": False,
    })

    server = None
    thread = None
    engine = None

    try:
        with tempfile.TemporaryDirectory(prefix="knowgap-ir16-") as tmp:
            database = Path(tmp) / "ir16.db"

            if database.resolve() == (ROOT / "knowgap.db").resolve():
                raise RuntimeError("Database isolation check failed")

            os.environ["DATABASE_URL"] = (
                "sqlite:///" + database.as_posix()
            )

            from app.database import create_db_and_tables
            from app.database import engine as app_engine
            from app.models import User, Ticket
            from scripts.seed_db import (
                USERS, seed_users, seed_kb, seed_historical_tickets
            )

            engine = app_engine

            if Path(engine.url.database).resolve() != database.resolve():
                raise RuntimeError(
                    "Application engine is not using the isolated database"
                )

            create_db_and_tables()

            with Session(engine) as session:
                seed_users(session)
                seed_kb(session)
                seed_historical_tickets(session)

                customer_account = next(
                    user for user in USERS if user[2] == "CUSTOMER"
                )

                customer_a = session.exec(
                    select(User).where(
                        User.username == customer_account[0]
                    )
                ).one()

                customer_b = User(
                    username=SECOND_CUSTOMER,
                    full_name="IR16 Synthetic Customer B",
                    role="CUSTOMER",
                    is_active=True,
                    hashed_password=customer_a.hashed_password,
                )

                session.add(customer_b)
                session.commit()
                session.refresh(customer_b)

                if customer_a.id == customer_b.id:
                    raise RuntimeError("Synthetic user isolation failed")

                result["synthetic_users"] = {
                    "customer_a_id": customer_a.id,
                    "customer_b_id": customer_b.id,
                    "roles": ["CUSTOMER", "CUSTOMER"],
                    "credentials_recorded": False,
                }

            # Disable external LLM calls for this controlled audit.
            from app.services.llm import llm
            llm.enabled = False
            result["llm_scope"] = "Disabled; local fallback only"

            from app.main import app

            port = choose_port()
            address = f"http://127.0.0.1:{port}"

            config = uvicorn.Config(
                app,
                host="127.0.0.1",
                port=port,
                log_level="warning",
                access_log=False,
            )
            server = uvicorn.Server(config)
            thread = threading.Thread(
                target=server.run,
                daemon=True,
            )
            thread.start()

            # Wait for the isolated server to become ready.
            ready = False
            for attempt in range(100):
                if not thread.is_alive():
                    break
                try:
                    with httpx.Client(
                        base_url=address,
                        timeout=3,
                        trust_env=False,
                    ) as probe:
                        if probe.get("/health").status_code == 200:
                            ready = True
                            break
                except httpx.RequestError:
                    pass
                time.sleep(0.3)

            if not ready:
                raise RuntimeError("Isolated application server not ready")

            result["server"] = {
                "interface": "127.0.0.1",
                "health": 200,
                "temporary_database": True,
            }

            with (
                httpx.Client(
                    base_url=address,
                    follow_redirects=False,
                    timeout=90,
                    trust_env=False,
                ) as owner,
                httpx.Client(
                    base_url=address,
                    follow_redirects=False,
                    timeout=30,
                    trust_env=False,
                ) as other,
                httpx.Client(
                    base_url=address,
                    follow_redirects=False,
                    timeout=30,
                    trust_env=False,
                ) as anonymous,
            ):
                password = customer_account[3]

                login_a = owner.post("/login", data={
                    "username": customer_account[0],
                    "password": password,
                })

                login_b = other.post("/login", data={
                    "username": SECOND_CUSTOMER,
                    "password": password,
                })

                result["http"]["customer_a_login"] = {
                    "status": login_a.status_code,
                    "cookie_present": bool(
                        owner.cookies.get("access_token")
                    ),
                }
                result["http"]["customer_b_login"] = {
                    "status": login_b.status_code,
                    "cookie_present": bool(
                        other.cookies.get("access_token")
                    ),
                }

                if (
                    login_a.status_code != 303
                    or login_b.status_code != 303
                    or not owner.cookies.get("access_token")
                    or not other.cookies.get("access_token")
                ):
                    raise RuntimeError(
                        "Synthetic login prerequisite failed"
                    )

                description = (
                    "My printer queue is stuck and print jobs will "
                    "not clear. " + MARKER
                )

                save(folder, "input.json", {
                    "title": "IR16 synthetic private ticket",
                    "description": description,
                    "creator_role": "CUSTOMER",
                    "test_requests": [
                        "Owner GET /tickets/{id}",
                        "Other customer GET /tickets/{id}",
                        "Anonymous GET /tickets/{id}",
                    ],
                })

                created = owner.post("/tickets/create", data={
                    "title": "IR16 synthetic private ticket",
                    "description": description,
                })

                result["http"]["create_ticket"] = {
                    "status": created.status_code,
                    "location": created.headers.get("location"),
                }

                location = created.headers.get("location", "")
                match = re.fullmatch(r"/tickets/(\d+)", location)

                if created.status_code != 303 or not match:
                    raise RuntimeError(
                        "Ticket creation prerequisite failed"
                    )

                ticket_id = int(match.group(1))

                with Session(engine) as session:
                    stored = session.get(Ticket, ticket_id)
                    if not stored:
                        raise RuntimeError("Created ticket not stored")

                    if (
                        stored.user_id != result["synthetic_users"][
                            "customer_a_id"
                        ]
                        or MARKER not in stored.description
                    ):
                        raise RuntimeError(
                            "Ticket ownership or marker mismatch"
                        )

                    before_ticket = ticket_snapshot(stored)

                save(folder, "ticket_before_access.json", before_ticket)

                owner_response = owner.get(location)
                other_response = other.get(location)
                anonymous_response = anonymous.get(location)

                for name, response in (
                    ("owner", owner_response),
                    ("other_customer", other_response),
                    ("anonymous", anonymous_response),
                ):
                    save(
                        folder,
                        name + "_response.html",
                        response.text,
                    )
                    result["http"][name] = {
                        "status": response.status_code,
                        "location": response.headers.get("location"),
                        "private_marker_present": (
                            MARKER in response.text
                        ),
                    }

                with Session(engine) as session:
                    stored_after = session.get(Ticket, ticket_id)
                    after_ticket = ticket_snapshot(stored_after)

                save(folder, "ticket_after_access.json", after_ticket)

                result["ticket_id"] = ticket_id
                result["checks"] = {
                    "owner_can_view": owner_response.status_code == 200,
                    "owner_marker_visible": (
                        MARKER in owner_response.text
                    ),
                    "other_customer_denied": (
                        other_response.status_code in (403, 404)
                    ),
                    "other_customer_marker_absent": (
                        MARKER not in other_response.text
                    ),
                    "anonymous_denied": (
                        anonymous_response.status_code in (302, 303, 401, 403)
                    ),
                    "anonymous_marker_absent": (
                        MARKER not in anonymous_response.text
                    ),
                    "ticket_unchanged_by_get_requests": (
                        before_ticket == after_ticket
                    ),
                }

            server.should_exit = True
            thread.join(timeout=15)
            if thread.is_alive():
                raise RuntimeError("Isolated server did not stop")

            engine.dispose()
            engine = None

        result["status"] = "EXECUTED"

        if all(result["checks"].values()):
            result["outcome"] = "PASS"
        elif (
            result["checks"]["owner_can_view"]
            and not result["checks"]["other_customer_denied"]
            and not result["checks"]["other_customer_marker_absent"]
        ):
            result["outcome"] = "FAIL — cross-user ticket disclosure"
        else:
            result["outcome"] = "MIXED — review HTTP evidence"

    except Exception as error:
        result["status"] = "NOT READY"
        result["outcome"] = "INCONCLUSIVE — execution prerequisite failed"
        save(folder, "execution_error.txt", traceback.format_exc())

    finally:
        if server is not None:
            server.should_exit = True
        if thread is not None:
            thread.join(timeout=15)
        if engine is not None:
            engine.dispose()

        result["finished_at_utc"] = now()
        result["source_files_unchanged"] = (
            before_source == source_hashes()
        )
        result["working_database_files_unchanged"] = (
            before_working_db == working_database_hashes()
        )

        if not (
            result["source_files_unchanged"]
            and result["working_database_files_unchanged"]
        ):
            result["outcome"] = (
                "INCONCLUSIVE — original source/database integrity "
                "needs investigation"
            )

        save(folder, "process_result.json", result)
        print(json.dumps({
            "case": result["case"],
            "status": result["status"],
            "outcome": result["outcome"],
            "http": result["http"],
            "checks": result["checks"],
            "source_files_unchanged": (
                result["source_files_unchanged"]
            ),
            "working_database_files_unchanged": (
                result["working_database_files_unchanged"]
            ),
            "evidence_directory": str(folder.relative_to(ROOT)),
        }, indent=2))

    return 0 if result["status"] == "EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(run())
