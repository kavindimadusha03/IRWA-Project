"""IR-10 only: one trust comparison on a backed-up fixture-only database.
Each run has a new evidence directory. Original app/test/data files are not edited.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
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

TITLE="Printer queue trust comparison"
DESCRIPTION="My printer queue is stuck and print jobs will not clear."
SUBCASES={"trust_pair":DESCRIPTION}
KB_ID="AUDIT-IR10-KB-001"
RESOLVED_ID="AUDIT-IR10-RESOLVED-001"
DRAFT_ID="AUDIT-IR10-DRAFT-001"
OPEN_ID="AUDIT-IR10-OPEN-001"
DRAFT_WITNESS="draftmarble612"
OPEN_WITNESS="openwillow824"
KB_COMMON={"category":"Printers","source_type":"internal_kb","author":"IR-10 synthetic audit fixture","authoritative":True,"supported_os":"Any","security_class":"internal"}
KB_FIXTURES=[
 {**KB_COMMON,"doc_id":KB_ID,"title":"Printer queue review procedure","content":"For a stuck printer queue, record the waiting print jobs and ask IT Support to review the queue before making changes. Synthetic approved reference for this audit.","status":"approved"},
 {**KB_COMMON,"doc_id":DRAFT_ID,"title":"Unreviewed printer backlog proposal","content":"Draft-only witness draftmarble612. An unreviewed note about a printer queue; no validated procedure is supplied.","status":"draft"},
]
TICKET_FIXTURES=[
 {"ticket_code":RESOLVED_ID,"title":"Stalled print jobs reviewed by support","description":"Printer queue was stuck and print jobs would not clear.","category":"Printers","canonical_issue":"","status":"RESOLVED","approval_status":"APPROVED","root_cause":"Synthetic support case; no verified device diagnosis.","resolution_notes":"Recorded waiting jobs and referred the printer queue to IT Support for review. No device settings were changed."},
 {"ticket_code":OPEN_ID,"title":"Printer queue still waiting for investigation","description":"Printer queue is stuck and print jobs will not clear; case remains unresolved.","category":"Printers","canonical_issue":"","status":"OPEN","approval_status":"PENDING","root_cause":"","resolution_notes":"Provisional unverified note only. Open-ticket witness openwillow824; no completed resolution."},
]
KB_RECORDS=[{"source_id":f["doc_id"],**{k:f[k] for k in ("title","content","category","status","source_type","supported_os")}} for f in KB_FIXTURES]
RESOLVED_RECORD={"source_id":RESOLVED_ID,"title":TICKET_FIXTURES[0]["title"],"content":"Problem: "+TICKET_FIXTURES[0]["description"]+"\nRoot cause: "+TICKET_FIXTURES[0]["root_cause"]+"\nResolution: "+TICKET_FIXTURES[0]["resolution_notes"],"category":"Printers","supported_os":"Any","source_type":"resolved_ticket","status":"resolved"}
EXPECTED_ELIGIBLE=[KB_RECORDS[0],RESOLVED_RECORD]
FIXTURE_DIAGNOSTICS=[KB_RECORDS[0],RESOLVED_RECORD,KB_RECORDS[1]]
def capture_fixtures(session,select,KnowledgeArticle,Ticket):
    result={"articles":[],"tickets":[]}
    for fields in KB_FIXTURES:
        row=session.exec(select(KnowledgeArticle).where(KnowledgeArticle.doc_id==fields["doc_id"])).one()
        result["articles"].append({key:getattr(row,key) for key in fields})
    for fields in TICKET_FIXTURES:
        row=session.exec(select(Ticket).where(Ticket.ticket_code==fields["ticket_code"])).one()
        result["tickets"].append({key:getattr(row,key) for key in fields})
    return result
IR01_RUN=ROOT/"audit"/"evidence"/"IR-01"/"run-20260921T194038486465Z"

def now():
    return datetime.now(timezone.utc).isoformat()

def save(folder,name,data):
    content=json.dumps(data,indent=2,ensure_ascii=False) if not isinstance(data,str) else data
    (folder/name).write_text(clean(content)+"\n",encoding="utf-8")

def parse_json(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

def worker(folder,subcase):
    DESCRIPTION=SUBCASES[subcase]
    state={"started_at_utc":now(),"stage":"setup","case":"IR-10","subcase":subcase,"status":"Not ready","outcome":"Unassessed","ticket_requests":0,"http":{}}
    def progress(stage):
        state["stage"]=stage
        save(folder,"execution.json",state)
        print("IR-10 stage: "+stage,flush=True)
    server=None
    thread=None
    audit_socket=None
    evidence={}
    try:
        directory=Path(tempfile.mkdtemp(prefix="knowgap-ir10-"+subcase+"-"))
        database=directory/"knowgap.db"
        os.environ["DATABASE_URL"]="sqlite:///"+database.as_posix()
        state["isolated_database"]=str(database)
        state["dataset"]="Fixture-only: two KB articles and two historical tickets, plus seeded synthetic users; no CSV KB/ticket corpus or working-database rows copied"
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
        from scripts.seed_db import USERS,seed_users
        from app.models import KnowledgeArticle,Ticket,TicketCitation,User
        if Path(engine.url.database).resolve()!=database.resolve() or database.resolve()==(ROOT/"knowgap.db").resolve():
            raise RuntimeError("Database isolation check failed before any creation or seed write")
        create_db_and_tables()
        with Session(engine) as session:
            seed_users(session)
            account=next(row for row in USERS if row[2]=="CUSTOMER")
            synthetic_user=session.exec(select(User).where(User.username==account[0])).one()
            state["test_user"]={"role":synthetic_user.role,"active":synthetic_user.is_active,"origin":"synthetic seed account; credentials omitted"}
            for fields in KB_FIXTURES:
                session.add(KnowledgeArticle(**fields,created_at=datetime(2026,9,22),updated_at=datetime(2026,9,22)))
            for fields in TICKET_FIXTURES:
                session.add(Ticket(**fields,user_id=synthetic_user.id,created_at=datetime(2026,9,22),updated_at=datetime(2026,9,22)))
            session.commit()
            actual_fixtures=capture_fixtures(session,select,KnowledgeArticle,Ticket)
            if actual_fixtures!={"articles":KB_FIXTURES,"tickets":TICKET_FIXTURES}:
                raise RuntimeError("Stored trust fixtures differ from declared fields")
            save(folder,"fixture_preflight.json",{"recorded_before_request_at_utc":now(),"fixtures":actual_fixtures,"isolation_verified":True,"statuses_are_synthetic_setup_not_approval_workflow":True})
            articles=session.exec(select(KnowledgeArticle)).all()
            historical=session.exec(select(Ticket)).all()
            state["fixture_counts"]={"articles":len(articles),"historical_tickets":len(historical)}
            support_account=next(row for row in USERS if row[2]=="IT_SUPPORT")
            support_user=session.exec(select(User).where(User.username==support_account[0])).one()
            state["support_test_user"]={"role":support_user.role,"active":support_user.is_active,"credential_values":"omitted"}
            if not support_user.is_active:
                raise RuntimeError("Synthetic IT_SUPPORT account is inactive")
        snapshot=directory/"before_requests.sqlite"
        with sqlite3.connect(database.as_uri()+"?mode=ro",uri=True) as source:
            source.execute("PRAGMA query_only=ON")
            with sqlite3.connect(str(snapshot)) as target:
                source.backup(target)
                integrity=target.execute("PRAGMA integrity_check").fetchone()[0]
                statuses=target.execute("SELECT doc_id,status FROM knowledgearticle UNION ALL SELECT ticket_code,status FROM ticket ORDER BY 1").fetchall()
        if integrity!="ok" or dict(statuses)!={KB_ID:"approved",DRAFT_ID:"draft",RESOLVED_ID:"RESOLVED",OPEN_ID:"OPEN"}:
            raise RuntimeError("Isolated pre-request snapshot verification failed")
        save(folder,"isolated_database_backup.json",{"recorded_before_request_at_utc":now(),"method":"SQLite backup API from mode=ro source after fixture setup","path":str(snapshot),"sha256":digest(snapshot),"integrity_check":integrity,"fixture_statuses":dict(statuses),"outside_repository":not snapshot.resolve().is_relative_to(ROOT.resolve())})
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
        with Session(engine) as session:
            preflight_records=retrieval_agent._records_from_db(session)
        kept=hybrid_search._deduplicate_records(preflight_records)
        save(folder,"deduplication_preflight.json",{"recorded_before_request_at_utc":now(),"scope":"Pure original deduplication on actual seeded records; no search/scores generated","eligible_source_ids":[r["source_id"] for r in preflight_records],"retained_source_ids":[r["source_id"] for r in kept],"both_positive_controls_survive":{KB_ID,RESOLVED_ID}.issubset({r["source_id"] for r in kept})})
        if not {KB_ID,RESOLVED_ID}.issubset({r["source_id"] for r in kept}):
            raise RuntimeError("Required pair removed by eligibility/deduplication; redesign before trust interpretation")
        original_dedup=hybrid_search._deduplicate_records
        def observed_dedup(*args,**kwargs):
            result=original_dedup(*args,**kwargs)
            records=args[0] if args else kwargs.get("records",[])
            save(folder,"deduplication_runtime.json",{"input_source_ids":[r["source_id"] for r in records],"retained_source_ids":[r["source_id"] for r in result],"retained_records":result,"capture":"Actual original hybrid_rank deduplication result; unchanged"})
            return result
        hybrid_search._deduplicate_records=observed_dedup
        from rank_bm25 import BM25Okapi
        original_native_scores=BM25Okapi.get_scores
        def observed_native_scores(model,query):
            result=original_native_scores(model,query)
            save(folder,"native_bm25.json",{"query_tokens":query,"native_scores":result.tolist(),"document_order":"Same as deduplication_runtime.retained_source_ids","capture":"Original BM25Okapi.get_scores called once by BM25Search.scores before min-max normalization; return unchanged"})
            return result
        BM25Okapi.get_scores=observed_native_scores
        metadata_calls=[]
        original_metadata=retrieval_agent._metadata_boost
        def observed_metadata(query,record):
            result=original_metadata(query,record)
            metadata_calls.append({"query":query,"source_id":record["source_id"],"category":record.get("category"),"status":record.get("status"),"supported_os":record.get("supported_os"),"metadata_bonus":result})
            save(folder,"actual_metadata_calls.json",metadata_calls)
            return result
        retrieval_agent._metadata_boost=observed_metadata
        original_trust=retrieval_agent._trust_weight
        save(folder,"trust_preflight.json",{"scope":"Pure original helper calls on declared fixture records; separate from actual ranking and not proof of exclusion","values":[{"source_id":r["source_id"],"status":r["status"],"source_type":r["source_type"],"trust_weight":original_trust(r)} for r in FIXTURE_DIAGNOSTICS]})
        trust_calls=[]
        def observed_trust(record):
            result=original_trust(record)
            trust_calls.append({"source_id":record["source_id"],"status":record.get("status"),"source_type":record.get("source_type"),"trust_weight":result})
            save(folder,"actual_trust_calls.json",trust_calls)
            return result
        retrieval_agent._trust_weight=observed_trust
        original_normalize=hybrid_search.normalize_query_for_search
        def observed_normalize(*args,**kwargs):
            result=original_normalize(*args,**kwargs)
            save(folder,"query_preprocessing.json",{
                "original_query":args[0] if args else kwargs.get("query"),
                "normalized_query":result,
                "normalized_query_tokens":tokenize(result),
                "submitted_issue":DESCRIPTION,
                "capture":"original function return observed; no result or input changed",
            })
            return result
        hybrid_search.normalize_query_for_search=observed_normalize
        original_hybrid=retrieval_agent.hybrid_rank
        def observed_hybrid(*args,**kwargs):
            records=args[1] if len(args)>1 else kwargs.get("records",[])
            same_corpus=sorted(records,key=lambda r:r["source_id"])==sorted(EXPECTED_ELIGIBLE,key=lambda r:r["source_id"])
            corpus_sha256=hashlib.sha256(json.dumps(sorted(records,key=lambda r:r["source_id"]),sort_keys=True).encode("utf-8")).hexdigest()
            save(folder,"eligible_records.json",records)
            save(folder,"eligible_corpus.json",{"eligible_record_count":len(records),"matches_declared_approved_and_resolved_records":same_corpus,"eligible_corpus_sha256":corpus_sha256,"eligible_source_ids":[r["source_id"] for r in records],"draft_id_present":any(r["source_id"]==DRAFT_ID for r in records),"open_id_present":any(r["source_id"]==OPEN_ID for r in records),"capture":"Full actual records passed unchanged from fixture-only DB; no pre-trust scores replaced"})
            result=original_hybrid(*args,**kwargs)
            save(folder,"hybrid_before_trust.json",result)
            return result
        retrieval_agent.hybrid_rank=observed_hybrid
        original_analysis=coordinator.analyze_ticket
        def observed_analysis(*args,**kwargs):
            result=original_analysis(*args,**kwargs)
            save(folder,"analysis.json",result)
            return result
        coordinator.analyze_ticket=observed_analysis
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
            progress("submit IR-10 ticket once")
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
                fields=("id","ticket_code","assigned_to","history_summary","title","description","masked_description","category","canonical_issue","priority","status","approval_status","retrieval_confidence","source_used","recommended_solution","decision_explanation","suggested_reply")
                ticket_record={key:getattr(ticket,key) for key in fields}
                citations=session.exec(select(TicketCitation).where(TicketCitation.ticket_id==ticket_id).order_by(TicketCitation.rank)).all()
                ticket_record["citations"]=[{"source_id":r.source_id,"title":r.title,"source_type":r.source_type,"category":r.category,"relevance_score":r.relevance_score,"rank":r.rank} for r in citations]
                save(folder,"ticket.json",ticket_record)
                state["ticket"]={key:ticket_record[key] for key in ("id","category","canonical_issue","status","approval_status","retrieval_confidence","source_used")}
            progress("verify visibility in human support queue without changing ticket")
            queue_check={"verification":"Read-only GET /support after normal synthetic IT_SUPPORT login; no resolve/approve/reject request", "role":"IT_SUPPORT", "ticket_id":ticket_id, "stored_status":ticket_record["status"], "assigned_to":ticket_record["assigned_to"]}
            with httpx.Client(base_url=address,follow_redirects=False,timeout=30,trust_env=False) as support_client:
                support_login=support_client.post("/login",data={"username":support_account[0],"password":support_account[3]})
                queue_check["login_status"]=support_login.status_code
                queue_check["login_location"]=support_login.headers.get("location")
                queue_check["cookie_present"]=bool(support_client.cookies.get("access_token"))
                if support_login.status_code==303 and queue_check["cookie_present"]:
                    support_page=support_client.get("/support")
                    queue_check["page_status"]=support_page.status_code
                    queue_check["ticket_resolve_form_present"]=f'action="/support/tickets/{ticket_id}/resolve"' in support_page.text
                    queue_check["ticket_code_present"]=ticket_record["ticket_code"] in support_page.text
                    queue_check["exact_description_present"]=DESCRIPTION in html.unescape(support_page.text)
                    save(folder,"support_queue.html",support_page.text)
                else:
                    queue_check["page_status"]=None
                    queue_check["verification_error"]="Normal support login failed; no queue request sent"
            save(folder,"support_queue_check.json",queue_check)
            state["support_queue_check"]=queue_check
            items=evidence.get("retrieval",{}).get("items",[])
            solution=evidence.get("solution",{})
            state["mechanical_checks"]={
                "single_ticket_request":state["ticket_requests"]==1,
                "ticket_page_200":page.status_code==200,
                "retrieved_any_sources":bool(items),
                "all_returned_sources_approved_or_resolved":all(i.get("status") in ("approved","resolved") for i in items),
                "solution_can_recommend":solution.get("can_recommend"),
                "stored_ticket_escalated":ticket_record["status"]=="ESCALATED",
                "top_category":items[0].get("category") if items else None,
                "approved_pair_source_in_top_k":any(i.get("source_id")==KB_ID for i in items),
                "resolved_pair_source_in_top_k":any(i.get("source_id")==RESOLVED_ID for i in items),
                "negative_control_in_top_k":any(i.get("source_id") in (DRAFT_ID,OPEN_ID) for i in items),
                "exact_match_source_ids":[i["source_id"] for i in items if i.get("exact_error_match")],
                "solution_citation_count":len(solution.get("citations",[])),
                "stored_citation_count":len(ticket_record["citations"]),
                "support_queue_shows_ticket":queue_check.get("page_status")==200 and queue_check.get("ticket_resolve_form_present",False) and queue_check.get("exact_description_present",False),
            }
            with Session(engine) as session:
                after=capture_fixtures(session,select,KnowledgeArticle,Ticket)
            save(folder,"fixture_postflight.json",{"recorded_at_utc":now(),"fixtures":after,"fields_and_statuses_unchanged":after==actual_fixtures,"private_snapshot_unchanged":digest(snapshot)==parse_json(folder/"isolated_database_backup.json")["sha256"]})
            output_text=json.dumps(solution).lower()
            save(folder,"negative_control_checks.json",{"draft_in_rankings_or_citations":any(i.get("source_id")==DRAFT_ID for i in items+solution.get("citations",[])+ticket_record["citations"]),"open_in_rankings_or_citations":any(i.get("source_id")==OPEN_ID for i in items+solution.get("citations",[])+ticket_record["citations"]),"draft_witness_in_solution_or_HTML":DRAFT_WITNESS in output_text or DRAFT_WITNESS in page.text.lower(),"open_witness_in_solution_or_HTML":OPEN_WITNESS in output_text or OPEN_WITNESS in page.text.lower()})
            state["status"]="Executed; awaiting source/answer review"
            state["outcome"]="Unassessed"
            state["stage"]="execution completed"
            state["review_note"]="Compare final scores with actual raw hybrid * trust + metadata. Approved=1.0, resolved=0.85; negative controls excluded. Comparable subject matter does not imply equal numeric relevance. Equal-score arithmetic belongs in separate derived evidence, not an invented retrieval result."

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
    folder=ROOT/"audit"/"evidence"/"IR-10"/("run-"+stamp)
    folder.mkdir(parents=True,exist_ok=False)
    before=code_hashes()
    database_hash=digest(ROOT/"knowgap.db")
    baseline=parse_json(ROOT/"audit"/"evidence"/"baseline"/"environment.json")
    backup=parse_json(ROOT/"audit"/"evidence"/"baseline"/"database_backup.json")
    backup_path=Path(backup.get("path",""))
    backup_verified=backup_path.is_file() and digest(backup_path)==backup.get("backup_sha256")
    save(folder,"inputs.json",{"recorded_before_requests_at_utc":now(),"case":"IR-10","title":TITLE,"description":DESCRIPTION,"characters":len(DESCRIPTION),"ticket_requests_planned":1})
    save(folder,"fixtures.json",{"recorded_before_requests_at_utc":now(),"articles":KB_FIXTURES,"historical_tickets":TICKET_FIXTURES,"expected_eligible_records":EXPECTED_ELIGIBLE,"scope":"Fixture-only temporary DB; no project CSV knowledge/tickets seeded. Both positive sources cover a stuck printer queue and recording waiting jobs for support review without setting changes. Statuses are synthetic setup metadata."})
    child=folder/"trust_pair"
    child.mkdir()
    save(child,"input.json",{"case":"IR-10","title":TITLE,"description":DESCRIPTION,"characters":len(DESCRIPTION)})
    save(folder,"expected_result.md","\n".join([
        "# IR-10 criteria fixed before request", "",
        "- One printer-queue issue through normal ticket workflow on fixture-only approved KB/resolved ticket/draft KB/open ticket corpus. No score substitution or application change.",
        "- Positive sources cover the same issue with distinct bodies/titles, same Printers category and Any OS. Verify both survive original deduplication before trust interpretation. Top-k remains 5 with two expected eligible sources.",
        "- PASS: both positives remain eligible/shortlisted; actual trust=1.0 approved and 0.85 resolved; final scores equal original pre-trust hybrid * actual trust + actual metadata bonus; draft/open controls excluded from trusted retrieval/citations.",
        "- FAIL: valid execution applies wrong trust/arithmetic or treats negative controls as trusted. A more relevant historical source ranking above KB is not itself a failure.",
        "- Capture native BM25 before normalization, normalized BM25, semantic, pre-trust hybrid, trust, metadata and final ranks. Comparable issue content is qualitative, not equal numeric relevance.",
        "- Equal-score condition: separately calculate both adjustments using a common positive raw score taken from the run and equal observed metadata. This is formula verification, not actual equal-score retrieval; no scores injected. Zero raw score ties.",
        "- Draft uses internal_kb/authoritative=true; open ticket has nonempty provisional notes. Neither may enter actual corpus. A standalone helper weight is not proof of eligibility.",
        "- Verify original private backup, create a private seeded-DB snapshot before request, verify unchanged fixture fields/statuses afterward.",
        "- Capture normal login, original pipeline/HTML/citations and read-only support queue. Review answer/provenance separately from numerical trust treatment.",
        "- Missing environment/eligibility/dedup prerequisites are Not ready/Inconclusive; redesign before interpretation if necessary. Disabled Groq means fallback-only answers.",
        "- One bounded local query; no real data, source approval/status changes, repairs, alternate-route probes, fixes, full-corpus comparison, forced scores or IR-11/later cases.",
    ]))
    save(folder,"source_preflight.json",{"recorded_at_utc":now(),"corpus":"Four fixture records only; two eligible expected","expected_article_count":2,"expected_historical_ticket_count":2,"expected_eligible_source_ids":[KB_ID,RESOLVED_ID],"negative_controls":[DRAFT_ID,OPEN_ID],"qualitative_relevance":"Both positives cover stuck print queue and recording waiting jobs for support review without device-setting changes.","kb_csv_sha256":digest(ROOT/"data"/"knowledge_base.csv"),"ticket_csv_sha256":digest(ROOT/"data"/"tickets.csv"),"csv_note":"Hashes for preservation only; CSV corpora not loaded"})
    save(folder,"preconditions.json",{
        "recorded_before_requests_at_utc":now(),"case":"IR-10","original_database_main_file_sha256":database_hash,
        "production_source_sha256":before,"sources_same_as_phase1":before==baseline.get("source_sha256"),
        "private_phase1_backup_verified":backup_verified,"original_database_same_as_phase1":database_hash==baseline.get("original_database_sha256"),
        "execution_settings":{"thread_limit":1,"cached_model_only":True,"external_LLM_configuration":"unchanged; actual enabled state recorded per worker"},
        "instrumentation":"Observe original analysis/normalization/hybrid/search/solution/chat returns and corpus; original functions called once without argument/result changes; read-only queue verification.",
    })
    previous_preconditions=parse_json(IR01_RUN/"preconditions.json")
    previous_sources=parse_json(IR01_RUN/"source_preflight.json")
    comparable={
        "reference_run":IR01_RUN.relative_to(ROOT).as_posix(),
        "source_files_same_as_IR01":before==previous_preconditions.get("production_source_sha256"),
        "kb_csv_same_as_IR01":digest(ROOT/"data"/"knowledge_base.csv")==previous_sources.get("kb_csv_sha256"),
        "ticket_csv_same_as_IR01":digest(ROOT/"data"/"tickets.csv")==previous_sources.get("ticket_csv_sha256"),
    }
    comparable["corpus_scope"]="Fixture-only corpus; code/config preserved but scores not directly comparable with earlier full-CSV cases"
    save(folder,"comparison_preflight.json",comparable)
    if not backup_verified or not all(comparable[key] for key in ("source_files_same_as_IR01","kb_csv_same_as_IR01","ticket_csv_same_as_IR01")):
        save(folder,"process_result.json",{"case":"IR-10","status":"Not ready","outcome":"Unassessed","reason":"Backup or unchanged source/CSV precondition failed; no ticket submitted"})
        print("IR-10 evidence: "+str(folder))
        return 1
    results=[]
    for name in SUBCASES:
        child=folder/name
        command=[sys.executable,"-B",str(Path(__file__).resolve()),"--worker",str(child),"--subcase",name]
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
        save(child,"terminal_log.txt",output)
        state=parse_json(child/"execution.json")
        result={
            "finished_at_utc":now(),"subcase":name,"process_exit_code":exit_code,"timed_out":timed_out,"elapsed_seconds":round(time.perf_counter()-started,3),
            "source_files_unchanged":before==code_hashes(),"original_database_main_file_unchanged":database_hash==digest(ROOT/"knowgap.db"),
            "evidence_directory":child.relative_to(ROOT).as_posix(),"worker_status":state.get("status"),"worker_stage":state.get("stage"),"ticket_requests":state.get("ticket_requests",0),
        }
        save(child,"process_result.json",result)
        results.append(result)
        print(clean(json.dumps(result)),flush=True)
        if exit_code!=0 or timed_out or not result["source_files_unchanged"] or not result["original_database_main_file_unchanged"]:
            break
    result={"case":"IR-10","finished_at_utc":now(),"outcome":"Unassessed; await reviewed comparison","subcases":results,"ticket_requests":sum(x["ticket_requests"] for x in results),"source_files_unchanged":before==code_hashes(),"original_database_main_file_unchanged":database_hash==digest(ROOT/"knowgap.db"),"integrity_limit":"Original main-file checksum does not cover concurrent WAL writes by another process; helper never writes working database.","evidence_directory":folder.relative_to(ROOT).as_posix()}
    save(folder,"process_result.json",result)
    print(clean(json.dumps(result)),flush=True)
    return 0 if len(results)==len(SUBCASES) and all(x["process_exit_code"]==0 and not x["timed_out"] for x in results) else 1

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--worker",type=Path)
    parser.add_argument("--subcase",choices=tuple(SUBCASES))
    args=parser.parse_args()
    if args.worker:
        resolved=args.worker.resolve()
        allowed=(ROOT/"audit"/"evidence"/"IR-10").resolve()
        if not resolved.is_relative_to(allowed):
            raise SystemExit("Evidence path must be inside audit/evidence/IR-10")
        if not args.subcase or resolved.name!=args.subcase:
            raise SystemExit("Worker requires matching subcase folder")
        raise SystemExit(worker(resolved,args.subcase))
    raise SystemExit(parent())
