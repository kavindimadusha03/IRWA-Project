"""IR-18: Local communication and session-cookie security assessment."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    path = Path(path)
    return (
        hashlib.sha256(path.read_bytes()).hexdigest()
        if path.is_file()
        else None
    )


def original_hashes():
    paths = [
        "app/main.py",
        "app/config.py",
        "app/routes/auth.py",
        "app/database.py",
        "knowgap.db",
        "knowgap.db-wal",
        "knowgap.db-shm",
        "data/knowledge_base.csv",
        "data/tickets.csv",
    ]
    return {name: sha256(ROOT / name) for name in paths}


def save(folder, name, value):
    path = folder / name
    if isinstance(value, str):
        path.write_text(value, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(value, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )


def inspect_source():
    terms = (
        "set_cookie(",
        "HTTPSRedirectMiddleware",
        "TrustedHostMiddleware",
        "Strict-Transport-Security",
        "CORSMiddleware",
        "secure=True",
        "proxy_headers",
    )
    matches = []

    for path in sorted((ROOT / "app").rglob("*.py")):
        for number, line in enumerate(
            path.read_text(
                encoding="utf-8-sig",
                errors="replace",
            ).splitlines(),
            1,
        ):
            if any(term.lower() in line.lower() for term in terms):
                matches.append({
                    "file": path.relative_to(ROOT).as_posix(),
                    "line": number,
                    "text": line.strip()[:200],
                })

    deployment_names = (
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "nginx.conf",
        "Caddyfile",
        "Procfile",
    )

    return {
        "application_python_matches": matches,
        "root_deployment_files_found": [
            name for name in deployment_names
            if (ROOT / name).is_file()
        ],
        "inspection_limit": (
            "Only application Python files and selected "
            "root deployment filenames were inspected. "
            "External hosting configuration was not assessed."
        ),
    }


async def test_responses(app, account):
    import httpx

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        follow_redirects=False,
        timeout=30,
    ) as client:

        login = await client.post(
            "/login",
            data={
                "username": account[0],
                "password": account[3],
            },
        )

        raw_cookie = login.headers.get("set-cookie", "")
        attributes = {}

        # Preserve cookie attributes, never its secret token.
        for part in raw_cookie.split(";")[1:]:
            part = part.strip()
            if not part:
                continue

            if "=" in part:
                name, value = part.split("=", 1)
                attributes[name.lower()] = value
            else:
                attributes[part.lower()] = True

        if (
            login.status_code != 303
            or login.headers.get("location") != "/home"
            or not raw_cookie.lower().startswith("access_token=")
            or not client.cookies.get("access_token")
        ):
            raise RuntimeError(
                "Synthetic login failed; cookie assessment is invalid."
            )

        home = await client.get("/home")
        health = await client.get("/health")

        security_headers = (
            "strict-transport-security",
            "content-security-policy",
            "x-content-type-options",
            "referrer-policy",
            "x-frame-options",
        )

        def headers_for(response):
            return {
                key: response.headers.get(key)
                for key in security_headers
            }

        return {
            "login": {
                "http_status": login.status_code,
                "redirect": login.headers.get("location"),
                "session_cookie_present": True,
                "cookie_attributes": attributes,
                "httponly": bool(attributes.get("httponly")),
                "secure": bool(attributes.get("secure")),
                "samesite": attributes.get("samesite"),
                "security_headers": headers_for(login),
            },
            "authenticated_home": {
                "http_status": home.status_code,
                "security_headers": headers_for(home),
            },
            "health": {
                "http_status": health.status_code,
                "security_headers": headers_for(health),
            },
        }


def run():
    from sqlmodel import Session

    stamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )
    folder = (
        ROOT / "audit" / "evidence" /
        "IR-18" / ("run-" + stamp)
    )
    folder.mkdir(parents=True, exist_ok=False)

    before = original_hashes()
    engine = None

    result = {
        "case": "IR-18",
        "started_at_utc": now(),
        "status": "NOT EXECUTED",
        "outcome": "UNASSESSED",
        "scope": (
            "Original FastAPI ASGI application, temporary "
            "synthetic database; no actual TLS connection"
        ),
    }

    save(folder, "preconditions.json", {
        "original_file_hashes": before,
        "synthetic_accounts_only": True,
        "external_network_requests": False,
        "production_deployment_assessed": False,
    })

    save(
        folder,
        "source_inspection.json",
        inspect_source(),
    )

    try:
        with tempfile.TemporaryDirectory(
            prefix="knowgap-ir18-"
        ) as temporary:
            database = Path(temporary) / "ir18.db"

            if database.resolve() == (
                ROOT / "knowgap.db"
            ).resolve():
                raise RuntimeError(
                    "Database isolation verification failed."
                )

            os.environ["DATABASE_URL"] = (
                "sqlite:///" + database.as_posix()
            )

            from app.database import (
                create_db_and_tables,
                engine as app_engine,
            )
            from scripts.seed_db import USERS, seed_users

            engine = app_engine

            if Path(engine.url.database).resolve() != (
                database.resolve()
            ):
                raise RuntimeError(
                    "Application is not using the temporary database."
                )

            create_db_and_tables()

            with Session(engine) as session:
                seed_users(session)

            account = next(
                row for row in USERS
                if row[2] == "CUSTOMER"
            )

            from app.main import app

            observations = asyncio.run(
                test_responses(app, account)
            )

            save(
                folder,
                "http_observations.json",
                observations,
            )

            login = observations["login"]

            result["checks"] = {
                "login_succeeded": (
                    login["http_status"] == 303
                ),
                "cookie_httponly": login["httponly"],
                "cookie_secure": login["secure"],
                "cookie_samesite": login["samesite"],
                "home_http_status": observations[
                    "authenticated_home"
                ]["http_status"],
                "hsts_on_login": bool(
                    login["security_headers"][
                        "strict-transport-security"
                    ]
                ),
            }

            engine.dispose()
            engine = None

        result["status"] = "EXECUTED"
        result["outcome"] = (
            "PARTIAL — local cookie and header behavior assessed; "
            "actual deployment HTTPS/TLS remains unverified"
        )

    except Exception:
        result["status"] = "NOT READY"
        result["outcome"] = (
            "INCONCLUSIVE — execution prerequisite failed"
        )
        save(
            folder,
            "execution_error.txt",
            traceback.format_exc(),
        )

    finally:
        if engine is not None:
            engine.dispose()

        result["finished_at_utc"] = now()
        result["original_files_unchanged"] = (
            before == original_hashes()
        )

        if not result["original_files_unchanged"]:
            result["outcome"] = (
                "INCONCLUSIVE — original-file integrity "
                "requires investigation"
            )

        result["deployment_limitations"] = (
            "ASGITransport tests application responses "
            "without a real network connection. It does "
            "not verify a deployment certificate, HTTPS "
            "redirection, TLS version or reverse proxy."
        )

        save(
            folder,
            "process_result.json",
            result,
        )

        print(json.dumps({
            **result,
            "evidence_directory": str(
                folder.relative_to(ROOT)
            ),
        }, indent=2))

    return 0 if result["status"] == "EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(run())
