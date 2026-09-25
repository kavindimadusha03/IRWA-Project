"""IR-03 only: one normal ticket on an isolated synthetic database.
Each run has a new evidence directory. Original app/test/data files are not edited.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):
    os.environ[key]="1"
os.environ["PYTHONDONTWRITEBYTECODE"]="1"
os.environ["HF_HUB_OFFLINE"]="1"
os.environ["TRANSFORMERS_OFFLINE"]="1"
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
from collect_baseline import clean, digest, code_hashes, SECRETS

TITLE="Windows blue screen error 0x00000124"
DESCRIPTION="Windows blue screen error 0x00000124"
ERROR_CODE="0x00000124"
IR01_RUN=ROOT/"audit"/"evidence"/"IR-01"/"run-20260921T194038486465Z"
RELEVANT_IDS={f"KB-{i:03d}" for i in range(6,79,8)}

def now():
    return datetime.now(timezone.utc).isoformat()

def save(folder,name,data):
    content=json.dumps(data,indent=2,ensure_ascii=False) if not isinstance(data,str) else data
    (folder/name).write_text(clean(content)+"\n",encoding="utf-8")

def parse_json(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

def worker(folder):
    state={"started_at_utc":now(),"stage":"setup","case":"IR-03","status":"Not ready","outcome":"Unassessed","ticket_requests":0,"http":{}}
    def progress(stage):
        state["stage"]=stage
        save(folder,"execution.json",state)
        print("IR-03 stage: "+stage,flush=True)
    server=None
    thread=None
    audit_socket=None
    evidence={}
    try:
        directory=Path(tempfile.mkdtemp(prefix="knowgap-ir03-"))
        database=directory/"knowgap.db"
        os.environ["DATABASE_URL"]="sqlite:///"+database.as_posix()
        state["isolated_database"]=str(database)
        state["dataset"]="Unmodified project synthetic CSVs; no existing working-database rows copied"
        from app.config import get_settings
        settings=get_settings()
        state["configuration"]={
            "bm25_weight":settings.hybrid_bm25_weight,"semantic_weight":settings.hybrid_semantic_weight,
            "high_threshold":settings.high_confidence_threshold,"uncertain_threshold":settings.uncertain_threshold,
            "embedding_model":"all-MiniLM-L6-v2","llm_model":settings.groq_model,"ticket_top_k":5,
            "thread_limit":1,"cached_model_only":True,
        }
        previous=parse_json(IR01_RUN/"execution.json")
        state["comparison_to_IR01"]={
            "reference_run":IR01_RUN.relative_to(ROOT).as_posix(),
            "same_configuration":state["configuration"]==previous.get("configuration"),
        }
        if not state["comparison_to_IR01"]["same_configuration"]:
            raise RuntimeError("Configuration differs from IR-01; comparison precondition not met")
        progress("embedding model preflight")
        started=time.perf_counter()
        from app.services.embeddings import get_model
        get_model()
        state["model_preflight"]={"loaded":True,"elapsed_seconds":round(time.perf_counter()-started,3)}
        progress("seed isolated synthetic database")
        from app.database import create_db_and_tables,engine
        from sqlmodel import Session,select
        from scripts.seed_db import USERS,seed_users,seed_kb,seed_historical_tickets
        from app.models import KnowledgeArticle,Ticket,TicketCitation,User
        create_db_and_tables()
        with Session(engine) as session:
            seed_users(session)
            seed_kb(session)
            seed_historical_tickets(session)
            account=next(row for row in USERS if row[2]=="CUSTOMER")
            synthetic_user=session.exec(select(User).where(User.username==account[0])).one()
            state["test_user"]={"role":synthetic_user.role,"active":synthetic_user.is_active,"origin":"synthetic CSV seed account; credential values omitted"}
            articles=session.exec(select(KnowledgeArticle)).all()
            historical=session.exec(select(Ticket)).all()
            state["fixture_counts"]={"articles":len(articles),"historical_tickets":len(historical)}
            actual_relevant=[a.doc_id for a in articles if a.doc_id in RELEVANT_IDS and a.status=="approved"]
            state["approved_related_generic_sources"]=actual_relevant
            state["approved_exact_code_sources"]=[a.doc_id for a in articles if a.status=="approved" and ERROR_CODE in " ".join((a.title,a.content,a.category,a.supported_os)).lower()]
            state["matching_quality_subcase"]="Not ready: no approved exact-code source" if not state["approved_exact_code_sources"] else "Ready"
            if not actual_relevant:
                raise RuntimeError("Required generic Windows update fixture source is absent")
        from app.services.llm import llm
        state["llm"]={"configured_enabled":bool(llm.enabled),"attempts":0,"successful_chat_returns":0,"error_types":[]}
        if bool(llm.enabled)!=previous.get("llm",{}).get("configured_enabled"):
            raise RuntimeError("LLM mode differs from IR-01; comparison precondition not met")
        original_chat=llm.chat
        def observed_chat(*args,**kwargs):
            state["llm"]["attempts"]+=1
            try:
                response=original_chat(*args,**kwargs)
            except Exception as exc:
                state["llm"]["error_types"].append(type(exc).__name__)
                raise
            state["llm"]["successful_chat_returns"]+=1
            return response
        llm.chat=observed_chat

        # Capture original return values from this single ticket's workflow.
        # Wrappers call the original once, do not change its arguments/results,
        # and re-raise its exceptions. No scoring/authentication rule is replaced.
        from app.agents import coordinator,retrieval_agent
        from app.services import hybrid_search
        from app.services.bm25 import tokenize
        save(folder,"token_code_preflight.json",{
            "input":DESCRIPTION,"tokens":tokenize(DESCRIPTION),
            "extracted_error_codes":sorted(hybrid_search._extract_error_codes(DESCRIPTION)),
            "capture":"Pure function diagnostics on the exact saved input before ticket submission; no search or substitute ranking",
        })
        original_normalize=hybrid_search.normalize_query_for_search
        def observed_normalize(*args,**kwargs):
            result=original_normalize(*args,**kwargs)
            save(folder,"query_preprocessing.json",{
                "original_query":args[0] if args else kwargs.get("query"),
                "normalized_query":result,
                "normalized_query_tokens":tokenize(result),
                "original_query_error_codes":sorted(hybrid_search._extract_error_codes(args[0] if args else kwargs.get("query", ""))),
                "normalized_query_error_codes":sorted(hybrid_search._extract_error_codes(result)),
                "capture":"original function return observed; no result or input changed",
            })
            return result
        hybrid_search.normalize_query_for_search=observed_normalize
        original_hybrid=retrieval_agent.hybrid_rank
        def observed_hybrid(*args,**kwargs):
            records=args[1] if len(args)>1 else kwargs.get("records",[])
            exact=[record for record in records if ERROR_CODE in hybrid_search._extract_error_codes(" ".join(str(record.get(field,"")) for field in ("title","content","category","supported_os")))]
            save(folder,"eligible_corpus.json",{"eligible_record_count":len(records),"eligible_exact_code_records":exact,"capture":"Actual records passed unchanged to hybrid_rank by this ticket workflow"})
            result=original_hybrid(*args,**kwargs)
            save(folder,"hybrid_before_trust.json",result)
            return result
        retrieval_agent.hybrid_rank=observed_hybrid
        original_search=coordinator.search_knowledge
        def observed_search(*args,**kwargs):
            start=time.perf_counter()
            result=original_search(*args,**kwargs)
            evidence["retrieval"]=result
            save(folder,"retrieval.json",result)
            state["retrieval_elapsed_seconds"]=round(time.perf_counter()-start,3)
            return result
        coordinator.search_knowledge=observed_search
        original_solution=coordinator.recommend_solution
        def observed_solution(*args,**kwargs):
            result=original_solution(*args,**kwargs)
            evidence["solution"]=result
            save(folder,"solution.json",result)
            return result
        coordinator.recommend_solution=observed_solution

        from app.main import app
        import socket
        import threading
        import uvicorn
        import httpx
        progress("start local audit server")
        # Keep the socket bound: no request can accidentally hit a different server.
        for port in (8001,8002,0):
            candidate=socket.socket()
            try:
                candidate.bind(("127.0.0.1",port))
            except OSError:
                candidate.close()
                continue
            audit_socket=candidate
            break
        if audit_socket is None:
            raise RuntimeError("No loopback socket could be reserved")
        actual_port=audit_socket.getsockname()[1]
        address=f"http://127.0.0.1:{actual_port}"
        state["base_url"]=address
        state["page"]=address+"/home"
        state["endpoint"]="POST "+address+"/tickets/create"
        server=uvicorn.Server(uvicorn.Config(app,host="127.0.0.1",port=actual_port,log_level="info",access_log=False))
        thread=threading.Thread(target=lambda:server.run(sockets=[audit_socket]),daemon=True)
        thread.start()
        for _ in range(120):
            if not thread.is_alive():
                raise RuntimeError("Audit server terminated before startup")
            if server.started:
                break
            time.sleep(0.25)
        if not server.started:
            raise RuntimeError("Audit server startup timeout")
        with httpx.Client(base_url=address,follow_redirects=False,timeout=150,trust_env=False) as client:
            health=client.get("/health")
            state["http"]["health"]=health.status_code
            if health.status_code!=200:
                raise RuntimeError("Audit server health check failed")
            progress("login with seeded synthetic CUSTOMER account")
            login=client.post("/login",data={"username":account[0],"password":account[3]})
            state["http"]["login"]={"status":login.status_code,"location":login.headers.get("location"),"cookie_present":bool(client.cookies.get("access_token"))}
            if login.status_code!=303 or login.headers.get("location")!="/home" or not client.cookies.get("access_token"):
                raise RuntimeError("Normal synthetic login did not succeed; ticket was not submitted")
            home=client.get("/home")
            state["http"]["home"]=home.status_code
            if home.status_code!=200:
                raise RuntimeError("Authenticated customer page not available")
            progress("submit IR-03 ticket once")
            state["ticket_requests"]=1
            save(folder,"execution.json",state)
            created=client.post("/tickets/create",data={"title":TITLE,"description":DESCRIPTION})
            state["http"]["ticket_create"]={"status":created.status_code,"location":created.headers.get("location")}
            progress("capture actual ticket response")
            location=created.headers.get("location","")
            if created.status_code!=303 or not re.fullmatch(r"/tickets/\d+",location):
                save(folder,"ticket_error_response.txt",created.text)
                state["status"]="Execution error"
                raise RuntimeError("Normal ticket request did not return a ticket redirect")
            ticket_id=int(location.rsplit("/",1)[-1])
            page=client.get(location)
            state["http"]["ticket_page"]=page.status_code
            state["ticket_url"]=address+location
            save(folder,"customer_result.html",page.text)
            with Session(engine) as session:
                ticket=session.get(Ticket,ticket_id)
                fields=("id","title","description","masked_description","category","canonical_issue","priority","status","approval_status","retrieval_confidence","source_used","recommended_solution","decision_explanation","suggested_reply")
                ticket_record={key:getattr(ticket,key) for key in fields}
                citations=session.exec(select(TicketCitation).where(TicketCitation.ticket_id==ticket_id).order_by(TicketCitation.rank)).all()
                ticket_record["citations"]=[{"source_id":r.source_id,"title":r.title,"source_type":r.source_type,"category":r.category,"relevance_score":r.relevance_score,"rank":r.rank} for r in citations]
                save(folder,"ticket.json",ticket_record)
                state["ticket"]={key:ticket_record[key] for key in ("id","category","canonical_issue","status","approval_status","retrieval_confidence","source_used")}
            items=evidence.get("retrieval",{}).get("items",[])
            state["mechanical_checks"]={
                "single_ticket_request":state["ticket_requests"]==1,
                "ticket_page_200":page.status_code==200,
                "retrieved_any_sources":bool(items),
                "top_in_related_generic_KB_set":bool(items) and items[0].get("source_id") in RELEVANT_IDS,
                "any_exact_error_match":any(item.get("exact_error_match") for item in items),
                "code_survives_canonical_issue":ERROR_CODE in state["ticket"]["canonical_issue"].lower(),
                "all_sources_approved_or_resolved":bool(items) and all(i.get("status") in ("approved","resolved") for i in items),
            }
            state["status"]="Executed; awaiting source/answer review"
            state["outcome"]="Unassessed"
            state["stage"]="execution completed"
            state["review_note"]="A matching source ID/category and HIGH score alone do not establish answer grounding. Assess each recommended action against retrieved evidence."
    except Exception as exc:
        state["error"]={"type":type(exc).__name__,"message":str(exc)}
        if state["ticket_requests"]==0:
            state["status"]="Not ready"
        else:
            state["status"]="Execution error; review required"
        import traceback
        traceback.print_exc()
        state["outcome"]="Unassessed"
    finally:
        if server:
            server.should_exit=True
        if thread:
            thread.join(timeout=12)
        if audit_socket:
            audit_socket.close()
        state["server_stopped"]=thread is None or not thread.is_alive()
        state["finished_at_utc"]=now()
        save(folder,"execution.json",state)
        print(clean(json.dumps(state)),flush=True)
    return 0 if state["status"]=="Executed; awaiting source/answer review" else 1

def parent():
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder=ROOT/"audit"/"evidence"/"IR-03"/("run-"+stamp)
    folder.mkdir(parents=True,exist_ok=False)
    before=code_hashes()
    database_hash=digest(ROOT/"knowgap.db")
    baseline=parse_json(ROOT/"audit"/"evidence"/"baseline"/"environment.json")
    backup=parse_json(ROOT/"audit"/"evidence"/"baseline"/"database_backup.json")
    backup_path=Path(backup.get("path",""))
    backup_verified=backup_path.is_file() and digest(backup_path)==backup.get("backup_sha256")
    with (ROOT/"data"/"knowledge_base.csv").open(encoding="utf-8-sig",newline="") as handle:
        kb_rows=list(csv.DictReader(handle))
    with (ROOT/"data"/"tickets.csv").open(encoding="utf-8-sig",newline="") as handle:
        ticket_rows=list(csv.DictReader(handle))
    exact_kb=[r for r in kb_rows if ERROR_CODE in " ".join(r.values()).lower()]
    exact_tickets=[r for r in ticket_rows if ERROR_CODE in " ".join(r.values()).lower()]
    approved_exact=[r for r in exact_kb if r["status"]=="approved"]
    resolved_exact=[r for r in exact_tickets if r["status"]=="Resolved" and r["resolution_notes"].strip()]
    generic_sources=[r for r in kb_rows if r["doc_id"] in RELEVANT_IDS]
    save(folder,"input.txt","Test: IR-03 - Exact Technical Error Code\nTitle: "+TITLE+"\nDescription: "+DESCRIPTION)
    save(folder,"expected_result.md","\n".join([
        "# Expected result recorded before execution", "",
        "- Use one normal ticket through the unchanged workflow on a fresh synthetic database.",
        "- Exact description: Windows blue screen error 0x00000124",
        "- Preserve 0x00000124 in canonical issue, normalized query, BM25 tokens and extracted code identity.",
        "- If relevant approved exact-code evidence exists, retrieve and identify it accurately.",
        "- Preflight found zero exact-code KB articles and four exact-code tickets, all Open with no resolution. Generic driver-update articles do not establish code-specific support.",
        "- Therefore the approved exact-source matching subcase is Not ready; do not count absence of the source as a retrieval failure.",
        "- No controlled exact-code fixture is added. Do not claim that the +0.35 positive boost branch was exercised without an eligible exact match.",
        "- Without relevant code-specific evidence, the application must not invent a code-specific diagnosis or resolution. Inspect the actual message, explanation and source applicability, not merely its HIGH label.",
        "- Generic troubleshooting text can be traceable while its applicability to this exact error remains unsupported; distinguish these outcomes.",
        "- Eligible sources must be approved articles or resolved historical tickets. Record exact_error_match flags and confidence honestly.",
        "- Model/login/environment failures make execution Not ready or Inconclusive, not a fabricated retrieval verdict.",
        "- Groq correctness is assessed only if provider output was actually used; otherwise label observed fallback mode.",
        "- This case does not execute IR-04 or the formatting variants reserved for IR-08.",
    ]))
    save(folder,"source_preflight.json",{
        "recorded_at_utc":now(),"corpus":"Unmodified synthetic CSVs in an isolated database; no injected article",
        "error_code":ERROR_CODE,"kb_rows":len(kb_rows),"ticket_rows":len(ticket_rows),
        "exact_code_KB_rows":exact_kb,"approved_exact_code_count":len(approved_exact),
        "exact_code_ticket_rows":exact_tickets,"eligible_resolved_exact_code_count":len(resolved_exact),
        "related_generic_approved_articles":generic_sources,
        "matching_quality_subcase":"Not ready: no approved exact-code evidence" if not approved_exact else "Ready",
        "kb_csv_sha256":digest(ROOT/"data"/"knowledge_base.csv"),"ticket_csv_sha256":digest(ROOT/"data"/"tickets.csv"),
    })
    save(folder,"preconditions.json",{
        "recorded_before_request_at_utc":now(),"case":"IR-03","original_database_main_file_sha256":database_hash,
        "production_source_sha256":before,"sources_same_as_phase1":before==baseline.get("source_sha256"),
        "private_phase1_backup_verified":backup_verified,"original_database_same_as_phase1":database_hash==baseline.get("original_database_sha256"),
        "execution_settings":{"thread_limit":1,"cached_model_only":True,"external_LLM_configuration":"unchanged; actual enabled state recorded by worker"},
        "instrumentation":"observe original normalize/search/hybrid/solution/chat returns and actual eligible corpus; pure token/code diagnostics; no argument, result, ranking, threshold or authentication changes",
    })
    previous_preconditions=parse_json(IR01_RUN/"preconditions.json")
    previous_sources=parse_json(IR01_RUN/"source_preflight.json")
    comparable={
        "reference_run":IR01_RUN.relative_to(ROOT).as_posix(),
        "source_files_same_as_IR01":before==previous_preconditions.get("production_source_sha256"),
        "kb_csv_same_as_IR01":digest(ROOT/"data"/"knowledge_base.csv")==previous_sources.get("kb_csv_sha256"),
        "ticket_csv_same_as_IR01":digest(ROOT/"data"/"tickets.csv")==previous_sources.get("ticket_csv_sha256"),
        "IR01_outcome":parse_json(IR01_RUN/"review.json").get("outcome"),
    }
    save(folder,"comparison_preflight.json",comparable)
    if not all(comparable[key] for key in ("source_files_same_as_IR01","kb_csv_same_as_IR01","ticket_csv_same_as_IR01")):
        save(folder,"execution.json",{"case":"IR-03","status":"Not ready","outcome":"Unassessed","reason":"Source/corpus changed since IR-01; no ticket submitted"})
        print("IR-03 evidence: "+str(folder))
        return 1
    if not backup_verified:
        save(folder,"execution.json",{"status":"Not ready","outcome":"Unassessed","reason":"Private recorded database backup missing or checksum changed; no execution performed"})
        print("IR-03 evidence: "+str(folder))
        return 1
    command=[sys.executable,"-B",str(Path(__file__).resolve()),"--worker",str(folder)]
    started=time.perf_counter()
    timed_out=False
    try:
        run=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding="utf-8",errors="replace",timeout=300,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        output=run.stdout+"\n"+run.stderr
        exit_code=run.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out=True
        exit_code=None
        def decode(value):
            return value.decode("utf-8",errors="replace") if isinstance(value,bytes) else value or ""
        output=decode(exc.stdout)+"\n"+decode(exc.stderr)
    save(folder,"terminal_log.txt",output)
    state=parse_json(folder/"execution.json")
    result={
        "finished_at_utc":now(),"process_exit_code":exit_code,"timed_out":timed_out,"elapsed_seconds":round(time.perf_counter()-started,3),
        "source_files_unchanged":before==code_hashes(),"original_database_main_file_unchanged":database_hash==digest(ROOT/"knowgap.db"),
        "integrity_limit":"Main-file checksum does not cover concurrent writes to separate SQLite WAL by another process. No original DB write is performed by this helper.",
        "evidence_directory":folder.relative_to(ROOT).as_posix(),"worker_status":state.get("status"),"worker_stage":state.get("stage"),
        "ticket_requests":state.get("ticket_requests",0),
    }
    save(folder,"process_result.json",result)
    print(clean(json.dumps(result)))
    return 0 if exit_code==0 and not timed_out else 1

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--worker",type=Path)
    args=parser.parse_args()
    if args.worker:
        resolved=args.worker.resolve()
        allowed=(ROOT/"audit"/"evidence"/"IR-03").resolve()
        if not resolved.is_relative_to(allowed):
            raise SystemExit("Evidence path must be inside audit/evidence/IR-03")
        raise SystemExit(worker(resolved))
    raise SystemExit(parent())
