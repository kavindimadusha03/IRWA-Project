"""IR-05 only: baseline, fixed variant and exploratory input on an isolated synthetic database.
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

TITLE="Printer queue problem"
SUBCASES={
    "baseline":"My printer's queue is stuck and print jobs will not clear.",
    "stuffed":"My printer's queue is stuck and print jobs will not clear. VPN VPN VPN VPN VPN",
    "exploratory":"VPN VPN VPN VPN VPN printer problem",
}
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
    state={"started_at_utc":now(),"stage":"setup","case":"IR-05","subcase":subcase,"status":"Not ready","outcome":"Unassessed","ticket_requests":0,"http":{}}
    def progress(stage):
        state["stage"]=stage
        save(folder,"execution.json",state)
        print("IR-05 stage: "+stage,flush=True)
    server=None
    thread=None
    audit_socket=None
    evidence={}
    try:
        directory=Path(tempfile.mkdtemp(prefix="knowgap-ir05-"+subcase+"-"))
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
            state["approved_printer_sources"]=[a.doc_id for a in articles if a.status=="approved" and a.category=="Printers"]
            if not state["approved_printer_sources"]:
                raise RuntimeError("Required approved printer sources absent")
            support_account=next(row for row in USERS if row[2]=="IT_SUPPORT")
            support_user=session.exec(select(User).where(User.username==support_account[0])).one()
            state["support_test_user"]={"role":support_user.role,"active":support_user.is_active,"credential_values":"omitted"}
            if not support_user.is_active:
                raise RuntimeError("Synthetic IT_SUPPORT account is inactive")
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
        original_normalize=hybrid_search.normalize_query_for_search
        def observed_normalize(*args,**kwargs):
            result=original_normalize(*args,**kwargs)
            save(folder,"query_preprocessing.json",{
                "original_query":args[0] if args else kwargs.get("query"),
                "normalized_query":result,
                "normalized_query_tokens":tokenize(result),
                "raw_VPN_occurrences":len(re.findall(r"\bvpn\b",args[0] if args else kwargs.get("query",""),flags=re.I)),
                "normalized_VPN_token_count":tokenize(result).count("vpn"),
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
            same_corpus=sorted(records,key=lambda r:r["source_id"])==sorted(expected_records,key=lambda r:r["source_id"])
            corpus_sha256=hashlib.sha256(json.dumps(sorted(records,key=lambda r:r["source_id"]),sort_keys=True).encode("utf-8")).hexdigest()
            save(folder,"eligible_corpus.json",{"eligible_record_count":len(records),"matches_reviewed_CSV_records_in_all_retrieval_fields":same_corpus,"eligible_corpus_sha256":corpus_sha256,"approved_printer_sources":[r["source_id"] for r in records if r["category"]=="Printers" and r["status"]=="approved"],"capture":"Original records passed unchanged to hybrid_rank; corpus parity includes all seven retrieval fields"})
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
            progress("submit IR-05 ticket once")
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
                "printer_results":sum(i.get("category")=="Printers" for i in items),
                "VPN_results":sum(i.get("category")=="VPN" for i in items),
                "solution_citation_count":len(solution.get("citations",[])),
                "stored_citation_count":len(ticket_record["citations"]),
                "support_queue_shows_ticket":queue_check.get("page_status")==200 and queue_check.get("ticket_resolve_form_present",False) and queue_check.get("exact_description_present",False),
            }
            state["status"]="Executed; awaiting source/answer review"
            state["outcome"]="Unassessed"
            state["stage"]="execution completed"
            state["review_note"]="Compare baseline and fixed variant for printer relevance and unsupported VPN advice. Exploratory intent is ambiguous and is not the paired-case verdict. Score/category changes alone do not assign PASS/FAIL."
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
    folder=ROOT/"audit"/"evidence"/"IR-05"/("run-"+stamp)
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
    printers=[r for r in kb_rows if r["status"]=="approved" and r["category"]=="Printers"]
    resolved_printers=[r for r in ticket_rows if r["status"]=="Resolved" and r["resolution_notes"].strip() and r["ground_truth_category"]=="Printers"]
    vpns=[r for r in kb_rows if r["status"]=="approved" and r["category"]=="VPN"]
    input_text=["Test: IR-05 - Keyword Stuffing","Same title for every subcase: "+TITLE]
    for name,description in SUBCASES.items():
        input_text.extend(["",name+": "+description])
        child=folder/name
        child.mkdir()
        save(child,"input.txt","IR-05 / "+name+"\nTitle: "+TITLE+"\nDescription: "+description)
    save(folder,"input.txt","\n".join(input_text))
    save(folder,"expected_result.md","\n".join([
        "# IR-05 expectations recorded before any request", "",
        "- Execute baseline and fixed appended-VPN variant once each; execute the listed short exploratory input once, separately labelled.",
        "- Use a fresh independently seeded synthetic database per input, the same source/corpus/configuration, and the same title. No source or score injection.",
        "- The baseline must establish relevant printer evidence and supported advice, or any baseline limitation must be disclosed before interpreting manipulation.",
        "- For the clear printer variant, PASS requires supported printer handling or explicit cautious handling of ambiguity; unrelated repeated words must not cause confident VPN repair advice.",
        "- FAIL when valid paired execution shows loss of the stated printer problem leading to confident unsupported VPN advice. Ranking/score/category differences alone do not establish failure or vulnerability.",
        "- Review all returned sources and substantive answer actions, not only the highest score or category. Preserve original function returns and ticket HTML.",
        "- Capture raw VPN count, observed normalized query and token count, raw hybrid scores, trust-adjusted scores, decision, category, priority, answer and citations.",
        "- The exploratory phrase lacks a specific confirmed fault; describe observed response without treating a VPN choice alone as wrong printer intent. It does not override the controlled paired-case verdict.",
        "- Log in normally as CUSTOMER. Read support queue as synthetic IT_SUPPORT to verify routing if a subcase escalates; never submit resolution, approval, rejection or manual-escalation requests.",
        "- Groq configuration remains unchanged and is recorded. Disabled/fallback results do not establish live LLM robustness or prompt-injection resistance.",
        "- An added VPN token can change lexical/semantic content even after repetition is collapsed. No single-VPN control or disabled-normalizer counterfactual is run, so avoid measuring a repetition-only causal effect.",
        "- Models/login/environment failures are Not ready/Inconclusive, not invented ranking results. This is a bounded local probe, not load testing.",
        "- Stop after IR-05; no IR-06 or later input is executed.",
    ]))
    save(folder,"source_preflight.json",{
        "recorded_at_utc":now(),"corpus":"Unmodified synthetic CSVs, separate temporary database per subcase",
        "kb_rows":len(kb_rows),"ticket_rows":len(ticket_rows),"approved_printer_articles":printers,
        "resolved_printer_title_resolution_families":[{"title":a,"resolution":b} for a,b in sorted({(r["title"],r["resolution_notes"]) for r in resolved_printers})],
        "related_resolved_printer_rows":resolved_printers,
        "approved_VPN_article_families":[{"title":a,"body":b} for a,b in sorted({(re.sub(r" - Guide \d+$","",r["title"]),r["body"]) for r in vpns})],
        "review":"Approved Clear Print Queue articles directly support the baseline queue symptom. Resolved stuck-queue and queued-job tickets also support it. VPN profile advice does not address that stated printer fault absent further evidence.",
        "kb_csv_sha256":digest(ROOT/"data"/"knowledge_base.csv"),"ticket_csv_sha256":digest(ROOT/"data"/"tickets.csv"),
    })
    save(folder,"preconditions.json",{
        "recorded_before_requests_at_utc":now(),"case":"IR-05","original_database_main_file_sha256":database_hash,
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
    save(folder,"comparison_preflight.json",comparable)
    if not backup_verified or not printers or not all(comparable[key] for key in ("source_files_same_as_IR01","kb_csv_same_as_IR01","ticket_csv_same_as_IR01")):
        save(folder,"process_result.json",{"case":"IR-05","status":"Not ready","outcome":"Unassessed","reason":"Backup, approved printer evidence or unchanged source/corpus precondition failed; no ticket submitted"})
        print("IR-05 evidence: "+str(folder))
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
    result={"case":"IR-05","finished_at_utc":now(),"outcome":"Unassessed; await reviewed comparison","subcases":results,"ticket_requests":sum(x["ticket_requests"] for x in results),"source_files_unchanged":before==code_hashes(),"original_database_main_file_unchanged":database_hash==digest(ROOT/"knowgap.db"),"integrity_limit":"Original main-file checksum does not cover concurrent WAL writes by another process; helper never writes working database.","evidence_directory":folder.relative_to(ROOT).as_posix()}
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
        allowed=(ROOT/"audit"/"evidence"/"IR-05").resolve()
        if not resolved.is_relative_to(allowed):
            raise SystemExit("Evidence path must be inside audit/evidence/IR-05")
        if not args.subcase or resolved.name!=args.subcase:
            raise SystemExit("Worker requires matching subcase folder")
        raise SystemExit(worker(resolved,args.subcase))
    raise SystemExit(parent())
