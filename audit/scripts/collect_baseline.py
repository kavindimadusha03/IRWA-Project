"""Collect Phase 1 evidence without changing production application files or data.
Run from project root with .venv/Scripts/python.exe -B audit/scripts/collect_baseline.py ACTION.
ACTION: inspect, backup, tests, evaluation, smoke. Normal synthetic inputs only.
"""
from __future__ import annotations
import argparse
import ast
import contextlib
import csv
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import re
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
BASELINE = ROOT / "audit" / "evidence" / "baseline"
LOW_MEMORY = "--low-memory" in sys.argv
EVIDENCE = BASELINE / "low_memory" if LOW_MEMORY else BASELINE
if LOW_MEMORY:
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
EVIDENCE.mkdir(parents=True, exist_ok=True)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
# Use the cached model; never silently substitute a different embedding model.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

def stamp():
    return datetime.now(timezone.utc).isoformat()

def secret_values():
    from dotenv import dotenv_values
    values = dotenv_values(ROOT / ".env")
    sensitive = []
    for key, value in {**values, **os.environ}.items():
        if value and any(word in key.upper() for word in ("SECRET", "PASSWORD", "API_KEY", "ACCESS_TOKEN")):
            sensitive.append(str(value))
    # Redact seeded demo credentials if a library happens to include them in an exception.
    module = ast.parse((ROOT / "scripts" / "seed_db.py").read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "USERS" for t in node.targets):
            sensitive.extend(str(row[3]) for row in ast.literal_eval(node.value))
    return sorted(set(sensitive), key=len, reverse=True)

SECRETS = secret_values()

def clean(text):
    for value in SECRETS:
        if len(value) >= 4:
            text = text.replace(value, "[REDACTED]")
    text = re.sub(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[REDACTED_JWT]", text)
    return text

def save(name, value):
    text = json.dumps(value, indent=2, ensure_ascii=False) if not isinstance(value, str) else value
    (EVIDENCE / name).write_text(clean(text) + "\n", encoding="utf-8")

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def code_hashes():
    output = {}
    for folder in ("app", "evaluation", "tests", "data"):
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                output[path.relative_to(ROOT).as_posix()] = digest(path)
    return output

def inspect_baseline():
    from dotenv import dotenv_values
    from app.config import get_settings
    settings = get_settings()
    env = dotenv_values(ROOT / ".env")
    packages = {}
    for name in ("fastapi", "sqlmodel", "sentence-transformers", "rank-bm25", "pytest", "httpx", "uvicorn"):
        packages[name] = importlib.metadata.version(name)
    config = {
        "database_type": "SQLite" if settings.database_url.startswith("sqlite") else "other",
        "database_is_workspace_knowgap": settings.database_url in ("sqlite:///./knowgap.db", "sqlite:///knowgap.db"),
        "embedding_model": "all-MiniLM-L6-v2",
        "llm_model": settings.groq_model,
        "hybrid_bm25_weight": settings.hybrid_bm25_weight,
        "hybrid_semantic_weight": settings.hybrid_semantic_weight,
        "high_threshold": settings.high_confidence_threshold,
        "uncertain_threshold": settings.uncertain_threshold,
        "ticket_top_k": 5, "direct_retrieval_top_k": 5, "chat_top_k": 3,
    }
    database = {"exists": (ROOT / "knowgap.db").is_file(), "inspection": "read-only URI, PRAGMA query_only=ON"}
    with sqlite3.connect("file:knowgap.db?mode=ro", uri=True) as connection:
        connection.execute("PRAGMA query_only=ON")
        database["tables"] = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        database["role_counts"] = [{"role": r[0], "active": bool(r[1]), "count": r[2]} for r in connection.execute("SELECT role,is_active,COUNT(*) FROM user GROUP BY role,is_active ORDER BY role")]
        database["counts"] = {name: connection.execute("SELECT COUNT(*) FROM " + name).fetchone()[0] for name in ("user", "ticket", "knowledgearticle")}
        database["article_status_counts"] = dict(connection.execute("SELECT status,COUNT(*) FROM knowledgearticle GROUP BY status").fetchall())
    csv_files = {}
    for name in ("data/knowledge_base.csv", "data/tickets.csv", "evaluation/gold_queries.csv"):
        with (ROOT / name).open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        csv_files[name] = {"rows": len(rows), "columns": reader.fieldnames}
    inventory = []
    for path in sorted(ROOT.rglob("*")):
        if any(part in (".git", ".venv", "__pycache__", ".pytest_cache", "audit") for part in path.relative_to(ROOT).parts):
            continue
        if path.is_file():
            inventory.append(path.relative_to(ROOT).as_posix())
    data = {
        "recorded_at_utc": stamp(), "python": platform.python_version(), "python_executable": sys.executable,
        "operating_system": platform.platform(), "packages": packages, "configuration": config,
        "localhost_url": "http://127.0.0.1:8000",
        "required_env_entries_exist": {key: key in env for key in ("SECRET_KEY", "GROQ_API_KEY")},
        "database": database, "csv_files": csv_files, "source_sha256": code_hashes(),
        "original_database_sha256": digest(ROOT / "knowgap.db"),
    }
    save("environment.json", data)
    save("workspace_files.txt", "\n".join(inventory))
    print(json.dumps({"saved": "environment.json", "roles": database["role_counts"], "counts": database["counts"]}))

def backup_database():
    destination_dir = Path(tempfile.mkdtemp(prefix="knowgap-audit-backup-"))
    destination = destination_dir / "knowgap.db"
    with sqlite3.connect("file:knowgap.db?mode=ro", uri=True) as source:
        source.execute("PRAGMA query_only=ON")
        with sqlite3.connect(destination) as target:
            source.backup(target)
            integrity = target.execute("PRAGMA integrity_check").fetchone()[0]
    save("database_backup.json", {
        "recorded_at_utc": stamp(), "method": "sqlite3.Connection.backup from mode=ro source",
        "path": str(destination), "outside_repository": True, "integrity_check": integrity,
        "backup_sha256": digest(destination), "original_database_sha256": digest(ROOT / "knowgap.db"),
        "note": "Private backup only. Do not commit or submit this database as evidence."
    })
    print(json.dumps({"backup_created": True, "integrity_check": integrity, "location_recorded_in": "database_backup.json"}))

def isolate_database(prefix):
    directory = Path(tempfile.mkdtemp(prefix=prefix))
    database_path = directory / "knowgap.db"
    os.environ["DATABASE_URL"] = "sqlite:///" + database_path.as_posix()
    return directory, database_path

def observe_llm():
    from app.services.llm import llm
    state = {"configured_enabled": bool(llm.enabled), "attempts": 0, "successes": 0, "error_types": []}
    original = llm.chat
    def recorded_chat(*args, **kwargs):
        state["attempts"] += 1
        try:
            result = original(*args, **kwargs)
        except Exception as exc:
            state["error_types"].append(type(exc).__name__)
            raise
        state["successes"] += 1
        return result
    llm.chat = recorded_chat
    return state

def run_tests():
    directory, database_path = isolate_database("knowgap-audit-tests-")
    started = time.perf_counter()
    out = io.StringIO()
    state = {}
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        state = observe_llm()
        import pytest
        exit_code = int(pytest.main(["-q", "-p", "no:cacheprovider", "tests"]))
    captured = out.getvalue()
    save("pytest_output.txt", captured)
    result = {
        "recorded_at_utc": stamp(), "exit_code": exit_code, "elapsed_seconds": round(time.perf_counter()-started,3),
        "command": "pytest -q -p no:cacheprovider tests (through audit helper)",
        "database": "isolated temporary SQLite file; original knowgap.db not used",
        "database_path": str(database_path), "llm": state,
        "embedding_mode": "existing local cache; HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1",
        "tests_modified": False,
        "summary_lines": [line.strip() for line in captured.splitlines() if re.search(r"\b\d+ (passed|failed|error|errors|skipped)\b", line)],
    }
    save("pytest_result.json", result)
    print(json.dumps(result))
    return exit_code

def run_evaluation():
    import runpy
    out = io.StringIO()
    started = time.perf_counter()
    failure = None
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        try:
            runpy.run_path(str(ROOT / "evaluation" / "evaluate_ir.py"), run_name="__main__")
        except Exception as exc:
            failure = type(exc).__name__
            import traceback
            traceback.print_exc()
    captured = out.getvalue()
    save("ir_evaluation_output.txt", captured)
    metrics = []
    for line in captured.splitlines():
        parts = line.split()
        if len(parts) == 5 and parts[0] in ("BM25", "Semantic", "Hybrid"):
            try:
                metrics.append(dict(zip(("method","P@1","P@5","Recall@5","MRR"), [parts[0]] + [float(x) for x in parts[1:]])))
            except ValueError:
                pass
    result = {
        "recorded_at_utc": stamp(), "elapsed_seconds": round(time.perf_counter()-started,3),
        "exit_code": 1 if failure else 0, "error_type": failure, "metrics_as_printed": metrics,
        "command": "python evaluation/evaluate_ir.py (via runpy; original script unchanged)",
        "corpus": "approved data/knowledge_base.csv articles; no database ticket sources",
        "weights": {"bm25":0.45,"semantic":0.55}, "weight_sweep_implemented": False,
        "embedding_mode": "existing local cache; HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1",
        "limitations": ["simpler ranking path than live retrieval","duplicate relevant labels may be incomplete","no-answer row scores zero without evaluating abstention"]
    }
    save("ir_evaluation_result.json", result)
    print(json.dumps(result))
    return result["exit_code"]

def smoke_baseline():
    directory, database_path = isolate_database("knowgap-audit-smoke-")
    started = time.perf_counter()
    out = io.StringIO()
    result = {
        "recorded_at_utc": stamp(),
        "scope": "Normal positive checks on isolated database seeded solely from project synthetic CSVs. No original user/ticket data copied.",
        "database_path": str(database_path),
        "expected_before_execution": {
            "startup": "GET /health returns 200 and status ok",
            "login": "synthetic user registration succeeds; valid login returns 303 /home; cookie authenticates profile",
            "retrieval": "known Wi-Fi issue returns relevant approved source; save scores and resulting ticket decision without assuming HIGH",
        },
        "checks": {},
    }
    server = None
    thread = None
    selected_socket = None
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            from scripts.seed_db import seed_users, seed_kb, seed_historical_tickets
            from app.database import create_db_and_tables, engine
            from sqlmodel import Session, select
            from app.models import Ticket, TicketCitation
            create_db_and_tables()
            with Session(engine) as session:
                seed_users(session)
                seed_kb(session)
                seed_historical_tickets(session)
            state = observe_llm()
            from app.main import app
            import threading
            import uvicorn
            import httpx
            selected_port = None
            for candidate in (8000,8001,8002):
                sock = socket.socket()
                try:
                    sock.bind(("127.0.0.1",candidate))
                except OSError:
                    sock.close()
                    continue
                selected_port = candidate
                selected_socket = sock
                break
            if selected_port is None:
                raise RuntimeError("No audit localhost port available")
            address = "http://127.0.0.1:" + str(selected_port)
            result["localhost_url"] = address
            server = uvicorn.Server(uvicorn.Config(app,host="127.0.0.1",port=selected_port,log_level="info",access_log=False))
            thread = threading.Thread(target=lambda: server.run(sockets=[selected_socket]),daemon=True)
            thread.start()
            with httpx.Client(base_url=address,follow_redirects=False,timeout=180,trust_env=False) as client:
                health = None
                for _ in range(120):
                    if not thread.is_alive():
                        raise RuntimeError("Audit server stopped before startup")
                    if not server.started:
                        time.sleep(0.25)
                        continue
                    try:
                        response = client.get("/health")
                        if response.status_code == 200:
                            health = response
                            break
                    except httpx.RequestError:
                        pass
                    time.sleep(0.25)
                result["checks"]["startup"] = {"passed": health is not None and health.json().get("status") == "ok", "http_status": health.status_code if health is not None else None}
                if health is None:
                    raise RuntimeError("Local application did not start")
                docs = client.get("/docs")
                result["checks"]["swagger"] = {"http_status":docs.status_code,"passed":docs.status_code == 200}
                username = "audit_" + secrets.token_hex(6)
                password = secrets.token_urlsafe(32)
                SECRETS.append(password)
                registration = client.post("/register",data={"username":username,"full_name":"Synthetic Audit User","password":password,"confirm_password":password})
                result["checks"]["registration"] = {"http_status":registration.status_code,"passed":registration.status_code == 303}
                login = client.post("/login",data={"username":username,"password":password})
                profile = client.get("/profile")
                result["checks"]["login"] = {"http_status":login.status_code,"redirect":login.headers.get("location"),"cookie_present":bool(client.cookies.get("access_token")),"authenticated_profile_status":profile.status_code,"passed":login.status_code == 303 and login.headers.get("location") == "/home" and profile.status_code == 200}
                query = "My laptop is connected to Wi-Fi, but websites do not load and there is no internet access."
                result["known_query"] = query
                retrieval = client.post("/agents/retrieval/search",json={"message_id":"baseline-normal-1","request_id":"baseline-normal-1","sender":"audit_baseline","receiver":"retrieval_agent","task":"retrieve_knowledge","payload":{"issue":query}})
                retrieved = retrieval.json() if retrieval.status_code == 200 else {}
                items = retrieved.get("items",[])
                safe_fields = ("source_id","title","category","source_type","status","bm25_score","semantic_score","hybrid_score","exact_error_match")
                result["checks"]["known_retrieval"] = {
                    "http_status":retrieval.status_code,"decision":retrieved.get("decision"),"best_score":retrieved.get("best_score"),
                    "items":[{k:item.get(k) for k in safe_fields} for item in items],
                    "passed":retrieval.status_code == 200 and bool(items) and items[0].get("status") == "approved" and items[0].get("source_type") == "internal_kb" and items[0].get("source_id") in {f"KB-{i:03d}" for i in range(1,74,8)},
                    "criterion":"top source is one of the reviewed approved Wi-Fi CSV guides KB-001/009/017/025/033/041/049/057/065/073; answer factual safety is not assessed here"
                }
                created = client.post("/tickets/create",data={"title":"Wi-Fi connected but no internet","description":query})
                location = created.headers.get("location","")
                ticket_id = int(location.rstrip("/").split("/")[-1]) if re.fullmatch(r"/tickets/\d+",location) else None
                detail_status = client.get(location).status_code if ticket_id else None
                with Session(engine) as session:
                    ticket = session.get(Ticket,ticket_id) if ticket_id else None
                    if ticket:
                        citations=session.exec(select(TicketCitation).where(TicketCitation.ticket_id==ticket.id).order_by(TicketCitation.rank)).all()
                        result["ticket"]={"id":ticket.id,"status":ticket.status,"category":ticket.category,"canonical_issue":ticket.canonical_issue,"confidence":ticket.retrieval_confidence,"source_used":ticket.source_used,"approval_status":ticket.approval_status,"explanation":ticket.decision_explanation,"recommendation":ticket.recommended_solution,"citations":[{"source_id":c.source_id,"source_type":c.source_type,"relevance_score":c.relevance_score} for c in citations]}
                result["checks"]["ticket_workflow"]={"http_status":created.status_code,"detail_status":detail_status,"passed":created.status_code == 303 and detail_status == 200 and bool(result.get("ticket"))}
                result["llm"] = state
                result["runtime_routes"]=[{"path":route.path,"methods":sorted(route.methods or []),"name":route.name} for route in app.routes if hasattr(route,"methods")]
                # No full HTML, cookies, headers, credentials, or existing user data are saved.
    except Exception as exc:
        result["error_type"]=type(exc).__name__
        result["error_message"]=str(exc)
    finally:
        if server:
            server.should_exit=True
        if thread:
            thread.join(timeout=10)
        if selected_socket:
            selected_socket.close()
        result["elapsed_seconds"]=round(time.perf_counter()-started,3)
        result["server_stopped"]=not thread or not thread.is_alive()
        save("application_output.txt",out.getvalue())
        save("application_baseline.json",result)
        print(clean(json.dumps({k:v for k,v in result.items() if k not in ("runtime_routes","ticket")})))
    return 0 if all(result["checks"].get(k,{}).get("passed") for k in ("startup","swagger","registration","login","known_retrieval","ticket_workflow")) else 1

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("action",choices=["inspect","backup","tests","evaluation","smoke"])
    parser.add_argument("--low-memory",action="store_true",help="Limit numerical-library threads to one and save separately.")
    args=parser.parse_args()
    for number in range(1,16):
        folder=ROOT / "audit" / "evidence" / f"IR-{number:02d}"
        folder.mkdir(parents=True,exist_ok=True)
        (folder / ".gitkeep").touch(exist_ok=True)
    before=digest(ROOT/"knowgap.db")
    try:
        result={"inspect":inspect_baseline,"backup":backup_database,"tests":run_tests,"evaluation":run_evaluation,"smoke":smoke_baseline}[args.action]()
        return result or 0
    except Exception as exc:
        save(args.action+"_error.json",{"recorded_at_utc":stamp(),"error_type":type(exc).__name__,"message":str(exc)})
        print(json.dumps({"action":args.action,"error_type":type(exc).__name__,"details":"saved redacted error record"}))
        return 1
    finally:
        original=json.loads((BASELINE/"environment.json").read_text(encoding="utf-8")) if (BASELINE/"environment.json").exists() else {}
        save(args.action+"_integrity.json",{"original_db_sha256_before":before,"original_db_sha256_after":digest(ROOT/"knowgap.db"),"original_db_unchanged_during_action":before==digest(ROOT/"knowgap.db"),"production_sources_unchanged_since_snapshot":not original or code_hashes()==original.get("source_sha256")})
if __name__ == "__main__":
    raise SystemExit(main())
