"""IR-09 only: draft exclusion and approved control on backed-up isolated synthetic databases.
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

TITLE="Audit reference lookup"
DRAFT_MARKER="quartzmeadow729"
CONTROL_MARKER="cobaltlantern463"
DRAFT_WITNESS="violetcompassstamp"
CONTROL_WITNESS="amberharborreceipt"
SUBCASES={"draft_probe":DRAFT_MARKER,"approved_control":CONTROL_MARKER}
COMMON={"category":"Audit / Lookup","source_type":"internal_kb","author":"IR-09 synthetic audit fixture","authoritative":True,"supported_os":"Any","security_class":"internal"}
FIXTURES=[
    {**COMMON,"doc_id":"AUDIT-IR09-DRAFT-001","title":"Draft lookup quartzmeadow729","content":"Unreviewed reference for quartzmeadow729. Response-only witness: violetcompassstamp. This synthetic record is not approved for recommendations.","status":"draft"},
    {**COMMON,"doc_id":"AUDIT-IR09-CONTROL-001","title":"Approved lookup cobaltlantern463","content":"Reviewed test reference for cobaltlantern463. Response-only witness: amberharborreceipt. This is harmless synthetic lookup text, not a device repair.","status":"approved"},
]
FIXTURE_RECORDS=[{"source_id":f["doc_id"],**{k:f[k] for k in ("title","content","category","status","source_type","supported_os")}} for f in FIXTURES]
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
    state={"started_at_utc":now(),"stage":"setup","case":"IR-09","subcase":subcase,"status":"Not ready","outcome":"Unassessed","ticket_requests":0,"http":{}}
    def progress(stage):
        state["stage"]=stage
        save(folder,"execution.json",state)
        print("IR-09 stage: "+stage,flush=True)
    server=None
    thread=None
    audit_socket=None
    evidence={}
    try:
        directory=Path(tempfile.mkdtemp(prefix="knowgap-ir09-"+subcase+"-"))
        database=directory/"knowgap.db"
        os.environ["DATABASE_URL"]="sqlite:///"+database.as_posix()
        state["isolated_database"]=str(database)
        state["dataset"]="Project synthetic CSVs plus identical draft/approved fixtures in a fresh backed-up temporary database; no working-database rows copied"
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
        if Path(engine.url.database).resolve()!=database.resolve() or database.resolve()==(ROOT/"knowgap.db").resolve():
            raise RuntimeError("Database isolation check failed before any creation or seed write")
        create_db_and_tables()
        with Session(engine) as session:
            seed_users(session)
            seed_kb(session)
            seed_historical_tickets(session)
            for fields in FIXTURES:
                session.add(KnowledgeArticle(**fields,created_at=datetime(2026,9,22),updated_at=datetime(2026,9,22)))
            session.commit()
            actual_fixtures=[]
            for fields in FIXTURES:
                record=session.exec(select(KnowledgeArticle).where(KnowledgeArticle.doc_id==fields["doc_id"])).one()
                actual_fixtures.append({key:getattr(record,key) for key in fields})
            if actual_fixtures!=FIXTURES:
                raise RuntimeError("Stored draft/control fixtures differ from declared fields")
            fixture_metadata={"recorded_before_request_at_utc":now(),"fixtures":actual_fixtures,"isolation_verified":True,"statuses_are_test_setup_not_approval_workflow":True}
            save(folder,"fixture_preflight.json",fixture_metadata)
            account=next(row for row in USERS if row[2]=="CUSTOMER")
            synthetic_user=session.exec(select(User).where(User.username==account[0])).one()
            state["test_user"]={"role":synthetic_user.role,"active":synthetic_user.is_active,"origin":"synthetic CSV seed account; credential values omitted"}
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
                statuses=target.execute("SELECT doc_id,status FROM knowledgearticle WHERE doc_id IN (?,?) ORDER BY doc_id",tuple(f["doc_id"] for f in FIXTURES)).fetchall()
        if integrity!="ok" or dict(statuses)!={f["doc_id"]:f["status"] for f in FIXTURES}:
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
        original_trust=retrieval_agent._trust_weight
        save(folder,"trust_preflight.json",{"scope":"Pure original helper calls on declared fixture records; separate from actual ranking and not proof of exclusion","values":[{"source_id":r["source_id"],"status":r["status"],"source_type":r["source_type"],"trust_weight":original_trust(r)} for r in FIXTURE_RECORDS]})
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
                "submitted_marker":DESCRIPTION,
                "marker_preserved_in_normalized_query":DESCRIPTION in tokenize(result),
                "capture":"original function return observed; no result or input changed",
            })
            return result
        hybrid_search.normalize_query_for_search=observed_normalize
        original_hybrid=retrieval_agent.hybrid_rank
        def observed_hybrid(*args,**kwargs):
            records=args[1] if len(args)>1 else kwargs.get("records",[])
            with (ROOT/"data"/"knowledge_base.csv").open(encoding="utf-8-sig",newline="") as handle:
                expected_articles=[r for r in csv.DictReader(handle) if r["status"]=="approved"]
            with (ROOT/"data"/"tickets.csv").open(encoding="utf-8-sig",newline="") as handle:
                expected_tickets=[r for r in csv.DictReader(handle) if r["status"]=="Resolved" and r["resolution_notes"].strip()]
            expected_records=[{"source_id":r["doc_id"],"title":r["title"],"content":r["body"],"category":r["category"],"supported_os":r["supported_os"],"source_type":r["source_type"],"status":r["status"]} for r in expected_articles]
            expected_records += [{"source_id":r["ticket_id"],"title":r["title"],"content":f"Problem: {r['description']}\nRoot cause: \nResolution: {r['resolution_notes']}","category":r["ground_truth_category"],"supported_os":"Any","source_type":"resolved_ticket","status":"resolved"} for r in expected_tickets]
            expected_records.append(FIXTURE_RECORDS[1])
            same_corpus=sorted(records,key=lambda r:r["source_id"])==sorted(expected_records,key=lambda r:r["source_id"])
            corpus_sha256=hashlib.sha256(json.dumps(sorted(records,key=lambda r:r["source_id"]),sort_keys=True).encode("utf-8")).hexdigest()
            serialized=json.dumps(records).lower()
            save(folder,"eligible_records.json",records)
            save(folder,"eligible_corpus.json",{"eligible_record_count":len(records),"matches_original_approved_resolved_plus_approved_control":same_corpus,"eligible_corpus_sha256":corpus_sha256,"eligible_source_ids":[r["source_id"] for r in records],"draft_id_present":any(r["source_id"]==FIXTURES[0]["doc_id"] for r in records),"approved_control_present":any(r==FIXTURE_RECORDS[1] for r in records),"draft_marker_present":DRAFT_MARKER in serialized,"draft_witness_present":DRAFT_WITNESS in serialized,"capture":"Full actual records passed unchanged to hybrid_rank; exclusion is assessed here before deduplication/top-k. A failed exclusion check does not stop collection of the real answer."})
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
            progress("submit IR-09 ticket once")
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
                "draft_in_top_k":any(i.get("source_id")==FIXTURES[0]["doc_id"] for i in items),
                "approved_control_in_top_k":any(i.get("source_id")==FIXTURES[1]["doc_id"] for i in items),
                "exact_match_source_ids":[i["source_id"] for i in items if i.get("exact_error_match")],
                "solution_citation_count":len(solution.get("citations",[])),
                "stored_citation_count":len(ticket_record["citations"]),
                "support_queue_shows_ticket":queue_check.get("page_status")==200 and queue_check.get("ticket_resolve_form_present",False) and queue_check.get("exact_description_present",False),
            }
            with Session(engine) as session:
                after=[]
                for fields in FIXTURES:
                    record=session.exec(select(KnowledgeArticle).where(KnowledgeArticle.doc_id==fields["doc_id"])).one()
                    after.append({key:getattr(record,key) for key in fields})
            save(folder,"fixture_postflight.json",{"recorded_at_utc":now(),"fixtures":after,"fields_and_statuses_unchanged":after==actual_fixtures,"private_snapshot_unchanged":digest(snapshot)==parse_json(folder/"isolated_database_backup.json")["sha256"]})
            generated_text="\n".join(str(solution.get(k,"")) for k in ("message","explanation","suggested_reply"))
            save(folder,"leakage_checks.json",{"scope":"Source identity and response-only witness distinguish leakage from legitimate user-input echo","draft_id_in_raw_shortlist":any(i["source_id"]==FIXTURES[0]["doc_id"] for i in parse_json(folder/"hybrid_before_trust.json")),"draft_id_in_final_ranking":any(i["source_id"]==FIXTURES[0]["doc_id"] for i in items),"draft_id_in_solution_citations":any(i["source_id"]==FIXTURES[0]["doc_id"] for i in solution.get("citations",[])),"draft_id_in_stored_citations":any(i["source_id"]==FIXTURES[0]["doc_id"] for i in ticket_record["citations"]),"draft_witness_in_recommendation":DRAFT_WITNESS in generated_text.lower(),"draft_witness_in_customer_HTML":DRAFT_WITNESS in html.unescape(page.text).lower(),"draft_source_id_in_customer_HTML":FIXTURES[0]["doc_id"] in html.unescape(page.text),"query_marker_in_customer_HTML":DESCRIPTION in html.unescape(page.text),"draft_marker_in_recommendation":DRAFT_MARKER in generated_text.lower(),"approved_control_cited":any(i["source_id"]==FIXTURES[1]["doc_id"] for i in solution.get("citations",[])),"approved_control_witness_in_recommendation":CONTROL_WITNESS in generated_text.lower()})
            state["status"]="Executed; awaiting source/answer review"
            state["outcome"]="Unassessed"
            state["stage"]="execution completed"
            state["review_note"]="Review draft exclusion across the entire actual corpus, both ranking stages, answer/citations/HTML and unchanged statuses. Approved control must remain eligible and be retrievable on its own query. User-marker echo alone is not source leakage. Pure zero-trust diagnostic is not proof of runtime filtering."

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
    folder=ROOT/"audit"/"evidence"/"IR-09"/("run-"+stamp)
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
    markers=(DRAFT_MARKER,CONTROL_MARKER,DRAFT_WITNESS,CONTROL_WITNESS)
    original_text=json.dumps(kb_rows+ticket_rows).lower()
    collisions={marker:marker in original_text for marker in markers}
    save(folder,"inputs.json",{"recorded_before_requests_at_utc":now(),"case":"IR-09","title":TITLE,"cases":[{"name":name,"description":description,"characters":len(description)} for name,description in SUBCASES.items()],"draft_response_only_witness":DRAFT_WITNESS,"approved_response_only_witness":CONTROL_WITNESS})
    save(folder,"fixtures.json",{"recorded_before_requests_at_utc":now(),"fixtures":FIXTURES,"retrieval_records":FIXTURE_RECORDS,"scope":"Identical draft and approved-control fixtures in each of two temporary synthetic DBs. No draft approval, production edit or repair. Both source_type=internal_kb and authoritative=true; draft status should govern exclusion."})
    for name,description in SUBCASES.items():
        child=folder/name
        child.mkdir()
        save(child,"input.json",{"case":"IR-09","subcase":name,"title":TITLE,"description":description,"characters":len(description)})
        save(child,"input.txt","IR-09 / "+name+"\nTitle: "+TITLE+"\nDescription: "+description)
    save(folder,"expected_result.md","\n".join([
        "# IR-09 criteria fixed before requests", "",
        "- Submit the draft-only marker once, then the distinct approved-control marker once, with identical seeded corpus/fixtures/config in separate temporary databases. No approval or source-status change during testing.",
        "- Verify markers and response-only witnesses absent from original CSVs; save exact queries/fixture metadata before requests. Both markers must survive the actual canonical/normalized query for the intended probe.",
        "- Verify existing private working-DB backup. Create and integrity-check a separate SQLite snapshot of each seeded isolated database before the request; save draft/approved statuses before and after.",
        "- PASS: draft is absent from the full actual eligible corpus passed to hybrid_rank, raw shortlist, final ranking, persisted source/citations and recommendation content; the approved control is present in the corpus and retrieved by its own marker query.",
        "- FAIL: valid run includes the draft in authoritative retrieval or uses/cites its witness/source as a recommendation, or excludes the approved control. If control is eligible but retrieval misses it, report that positive-control limitation without inventing draft leakage.",
        "- Record the full corpus before deduplication/top-k. A low rank or trust=0 does not establish exclusion. Observe real ranking trust calls separately from pure _trust_weight calls on stored fixtures (draft expected 0; approved expected 1).",
        "- Draft query text may legitimately appear in submitted description/history/UI. Use draft source ID, response-only witness and actual content/attribution to distinguish source leakage; do not call query echo a vulnerability.",
        "- Capture normal login, original pipeline returns, scores, decision, stored ticket/citations, customer HTML and read-only support queue. Keep any relevance/answer weakness separate from the exclusion criterion.",
        "- Missing login/model/backup/fixture/query prerequisites are Not ready/Inconclusive; do not fabricate outcomes. Record configured Groq mode and scope fallback-only results appropriately.",
        "- Do not approve the draft, mutate production sources, run alternative routes/variants, fix code or execute IR-10 and later cases. No stress/DoS or real user data.",
    ]))
    save(folder,"source_preflight.json",{"recorded_at_utc":now(),"kb_rows":len(kb_rows),"ticket_rows":len(ticket_rows),"original_marker_collisions":collisions,"draft_id":FIXTURES[0]["doc_id"],"approved_control_id":FIXTURES[1]["doc_id"],"expected_eligible_count":428,"expected_database_article_count":82,"kb_csv_sha256":digest(ROOT/"data"/"knowledge_base.csv"),"ticket_csv_sha256":digest(ROOT/"data"/"tickets.csv")})
    save(folder,"preconditions.json",{
        "recorded_before_requests_at_utc":now(),"case":"IR-09","original_database_main_file_sha256":database_hash,
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
    comparable["corpus_scope"]="Original 427 eligible CSV records plus approved control; draft stored but expected excluded. Same fixtures across two queries; no relative trust experiment against resolved history."
    save(folder,"comparison_preflight.json",comparable)
    if not backup_verified or any(collisions.values()) or not all(comparable[key] for key in ("source_files_same_as_IR01","kb_csv_same_as_IR01","ticket_csv_same_as_IR01")):
        save(folder,"process_result.json",{"case":"IR-09","status":"Not ready","outcome":"Unassessed","reason":"Backup, marker uniqueness or unchanged source/CSV precondition failed; no ticket submitted"})
        print("IR-09 evidence: "+str(folder))
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
    result={"case":"IR-09","finished_at_utc":now(),"outcome":"Unassessed; await reviewed comparison","subcases":results,"ticket_requests":sum(x["ticket_requests"] for x in results),"source_files_unchanged":before==code_hashes(),"original_database_main_file_unchanged":database_hash==digest(ROOT/"knowgap.db"),"integrity_limit":"Original main-file checksum does not cover concurrent WAL writes by another process; helper never writes working database.","evidence_directory":folder.relative_to(ROOT).as_posix()}
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
        allowed=(ROOT/"audit"/"evidence"/"IR-09").resolve()
        if not resolved.is_relative_to(allowed):
            raise SystemExit("Evidence path must be inside audit/evidence/IR-09")
        if not args.subcase or resolved.name!=args.subcase:
            raise SystemExit("Worker requires matching subcase folder")
        raise SystemExit(worker(resolved,args.subcase))
    raise SystemExit(parent())
