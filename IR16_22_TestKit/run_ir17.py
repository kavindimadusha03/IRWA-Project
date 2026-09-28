"""IR-17: Bounded, authenticated API rate-limiting assessment."""
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

for key in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[key] = "1"

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

MAX_REQUESTS = 6
INTERVAL_SECONDS = 1
ENDPOINT = "/agents/retrieval/search"
ISSUE = "My laptop is connected to Wi-Fi but there is no internet."


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    path = Path(path)
    return (
        hashlib.sha256(path.read_bytes()).hexdigest()
        if path.is_file()
        else None
    )


def source_hashes():
    names = (
        "app/main.py",
        "app/config.py",
        "app/models.py",
        "app/routes/agents.py",
        "app/agents/retrieval_agent.py",
    )
    return {name: sha256(ROOT / name) for name in names}


def working_database_hashes():
    return {
        name: sha256(ROOT / name)
        for name in (
            "knowgap.db",
            "knowgap.db-wal",
            "knowgap.db-shm",
        )
    }


def save(folder, filename, value):
    path = folder / filename
    if isinstance(value, str):
        path.write_text(value, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(
                value,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )


def available_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def inspect_rate_limit_code():
    """Record keyword evidence; absence is not proof of no limiter."""
    pattern = re.compile(
        r"rate[_-]?limit|slowapi|throttl|"
        r"retry[-_]after|429"
    )

    matches = []

    for path in sorted((ROOT / "app").rglob("*.py")):
        for number, line in enumerate(
            path.read_text(
                encoding="utf-8-sig",
                errors="replace",
            ).splitlines(),
            start=1,
        ):
            if pattern.search(line.lower()):
                matches.append({
                    "file": path.relative_to(ROOT).as_posix(),
                    "line": number,
                    "text": line.strip()[:180],
                })

    return {
        "scope": "app/**/*.py only",
        "matching_lines": matches,
        "external_proxy_or_gateway": "NOT ASSESSED",
        "interpretation": (
            "A keyword scan cannot establish the absence "
            "of all application or deployment rate limits."
        ),
    }


def run():
    import httpx
    import uvicorn
    from sqlmodel import Session, select

    stamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )
    folder = (
        ROOT / "audit" / "evidence" /
        "IR-17" / ("run-" + stamp)
    )
    folder.mkdir(parents=True, exist_ok=False)

    before_source = source_hashes()
    before_database = working_database_hashes()

    result = {
        "case": "IR-17",
        "started_at_utc": now(),
        "status": "NOT READY",
        "outcome": "UNASSESSED",
        "scope": (
            "Original FastAPI application, loopback only, "
            "temporary synthetic database"
        ),
        "maximum_requests": MAX_REQUESTS,
        "interval_seconds": INTERVAL_SECONDS,
        "requests": [],
        "checks": {},
    }

    prepared = (
        ROOT / "audit" / "evidence" / "IR-17" /
        "run-20260926T094704448586Z"
    )
    expected = prepared / "expected_result.md"

    if expected.is_file():
        save(
            folder,
            "expected_result.md",
            expected.read_text(encoding="utf-8-sig"),
        )

    save(folder, "preconditions.json", {
        "recorded_at_utc": now(),
        "source_sha256": before_source,
        "working_database_sha256": before_database,
        "planned_requests": MAX_REQUESTS,
        "concurrency": 1,
        "request_interval_seconds": INTERVAL_SECONDS,
        "target": ENDPOINT,
        "deployment": "isolated local loopback server",
    })

    save(
        folder,
        "static_rate_limit_inspection.json",
        inspect_rate_limit_code(),
    )

    server = None
    thread = None
    engine = None

    try:
        with tempfile.TemporaryDirectory(
            prefix="knowgap-ir17-"
        ) as tmp:
            database = Path(tmp) / "ir17.db"

            if database.resolve() == (
                ROOT / "knowgap.db"
            ).resolve():
                raise RuntimeError(
                    "Database isolation verification failed"
                )

            os.environ["DATABASE_URL"] = (
                "sqlite:///" + database.as_posix()
            )

            from app.database import create_db_and_tables
            from app.database import engine as app_engine
            from app.models import Ticket, User
            from scripts.seed_db import (
                USERS,
                seed_users,
                seed_kb,
                seed_historical_tickets,
            )

            engine = app_engine

            if Path(engine.url.database).resolve() != (
                database.resolve()
            ):
                raise RuntimeError(
                    "Application engine does not use "
                    "the temporary database"
                )

            create_db_and_tables()

            with Session(engine) as session:
                seed_users(session)
                seed_kb(session)
                seed_historical_tickets(session)

                account = next(
                    row for row in USERS
                    if row[2] == "CUSTOMER"
                )

                user = session.exec(
                    select(User).where(
                        User.username == account[0]
                    )
                ).one()

                initial_ticket_count = len(
                    session.exec(select(Ticket)).all()
                )

                result["synthetic_account"] = {
                    "role": user.role,
                    "is_active": user.is_active,
                    "credentials_recorded": False,
                }

            from app.services.llm import llm
            llm.enabled = False
            result["llm_scope"] = (
                "Disabled; no external LLM required"
            )

            from app.main import app

            port = available_port()
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

            ready = False

            for _ in range(100):
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
                raise RuntimeError(
                    "Isolated server failed its health check"
                )

            with httpx.Client(
                base_url=address,
                follow_redirects=False,
                timeout=90,
                trust_env=False,
            ) as client:

                login = client.post(
                    "/login",
                    data={
                        "username": account[0],
                        "password": account[3],
                    },
                )

                authenticated = (
                    login.status_code == 303
                    and login.headers.get("location") == "/home"
                    and bool(
                        client.cookies.get("access_token")
                    )
                )

                result["login"] = {
                    "status": login.status_code,
                    "redirect": login.headers.get("location"),
                    "authenticated": authenticated,
                }

                if not authenticated:
                    raise RuntimeError(
                        "Synthetic authentication failed"
                    )

                request_body = {
                    "message_id": "ir17-local-001",
                    "request_id": "ir17-bounded-test",
                    "sender": "coordinator",
                    "receiver": "retrieval_agent",
                    "task": "search_knowledge",
                    "payload": {
                        "issue": ISSUE,
                    },
                }

                save(
                    folder,
                    "request_template.json",
                    request_body,
                )

                for index in range(MAX_REQUESTS):
                    if index:
                        time.sleep(INTERVAL_SECONDS)

                    sent_at = now()
                    started = time.perf_counter()

                    response = client.post(
                        ENDPOINT,
                        json=request_body,
                    )

                    elapsed = round(
                        (time.perf_counter() - started) * 1000,
                        2,
                    )

                    headers = {
                        key: value
                        for key, value in response.headers.items()
                        if (
                            "ratelimit" in key.lower()
                            or "rate-limit" in key.lower()
                            or key.lower() == "retry-after"
                        )
                    }

                    observation = {
                        "request_number": index + 1,
                        "sent_at_utc": sent_at,
                        "http_status": response.status_code,
                        "elapsed_ms": elapsed,
                        "rate_limit_headers": headers,
                    }

                    if response.status_code == 200:
                        try:
                            data = response.json()
                        except ValueError as error:
                            raise RuntimeError(
                                "Retrieval returned invalid JSON"
                            ) from error

                        if not isinstance(data, dict):
                            raise RuntimeError(
                                "Unexpected retrieval response shape"
                            )

                        items = data.get("items")

                        if not isinstance(items, list):
                            raise RuntimeError(
                                "Retrieval response has no items list"
                            )

                        observation["retrieval"] = {
                            "item_count": len(items),
                            "decision": data.get("decision"),
                            "best_score": data.get("best_score"),
                            "source_ids": [
                                item.get("source_id")
                                for item in items[:5]
                                if isinstance(item, dict)
                            ],
                        }

                    result["requests"].append(observation)

                    save(
                        folder,
                        "request_observations.json",
                        result["requests"],
                    )

                    print(
                        f"IR-17 request {index + 1}/6: "
                        f"HTTP {response.status_code}, "
                        f"{elapsed:.0f} ms",
                        flush=True,
                    )

                    if (
                        index == 0
                        and response.status_code != 200
                    ):
                        raise RuntimeError(
                            "First valid retrieval control "
                            "did not return HTTP 200"
                        )

                    if response.status_code not in (200, 429):
                        raise RuntimeError(
                            "Unexpected HTTP status during "
                            "bounded request sequence: "
                            + str(response.status_code)
                        )

            with Session(engine) as session:
                final_ticket_count = len(
                    session.exec(select(Ticket)).all()
                )

            result["checks"] = {
                "authentication_succeeded": authenticated,
                "first_retrieval_succeeded": (
                    result["requests"][0]["http_status"] == 200
                ),
                "exactly_six_requests": (
                    len(result["requests"]) == MAX_REQUESTS
                ),
                "sequential_execution": True,
                "ticket_count_unchanged": (
                    initial_ticket_count == final_ticket_count
                ),
            }

            server.should_exit = True
            thread.join(timeout=15)

            if thread.is_alive():
                raise RuntimeError(
                    "Isolated server did not stop"
                )

            engine.dispose()
            engine = None

        statuses = [
            entry["http_status"]
            for entry in result["requests"]
        ]

        result["status"] = "EXECUTED"
        result["http_status_sequence"] = statuses
        result["rate_limit_observed"] = 429 in statuses

        if not all(result["checks"].values()):
            result["outcome"] = (
                "INCONCLUSIVE — prerequisite or integrity "
                "check did not pass"
            )
        elif 429 in statuses:
            result["outcome"] = (
                "RATE LIMIT OBSERVED within six "
                "sequential requests"
            )
        else:
            result["outcome"] = (
                "NO RATE LIMIT OBSERVED in six "
                "sequential requests; broader "
                "policy remains unverified"
            )

    except Exception:
        result["status"] = "NOT READY"
        result["outcome"] = (
            "INCONCLUSIVE — execution or "
            "request prerequisite failed"
        )
        save(
            folder,
            "execution_error.txt",
            traceback.format_exc(),
        )

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
            before_database == working_database_hashes()
        )

        if not (
            result["source_files_unchanged"]
            and result["working_database_files_unchanged"]
        ):
            result["outcome"] = (
                "INCONCLUSIVE — source or working "
                "database integrity needs investigation"
            )

        save(
            folder,
            "process_result.json",
            result,
        )

        print(
            json.dumps({
                "case": result["case"],
                "status": result["status"],
                "outcome": result["outcome"],
                "requests": result["requests"],
                "checks": result["checks"],
                "source_files_unchanged": (
                    result["source_files_unchanged"]
                ),
                "working_database_files_unchanged": (
                    result["working_database_files_unchanged"]
                ),
                "evidence_directory": str(
                    folder.relative_to(ROOT)
                ),
            }, indent=2),
            flush=True,
        )

    return 0 if result["status"] == "EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(run())
