"""IR-07 only: one normal ticket on an isolated synthetic database.
Each run has a new evidence directory. Original app/test/data files are not edited.
"""
from __future__ import annotations
import argparse
import hashlib
import html
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

TITLE="Printer queue problem"
BASE_DESCRIPTION="My printer's queue is stuck and print jobs will not clear."
NOISE_SENTENCE="The notebook is blue and the meeting is on Tuesday. "
NOISE_REPETITIONS=20
DESCRIPTION=BASE_DESCRIPTION+" "+NOISE_SENTENCE*NOISE_REPETITIONS
IR05_RUN=ROOT/"audit"/"evidence"/"IR-05"/"run-20260922T035809651634Z"
BASELINE_RUN=IR05_RUN/"baseline"
IR01_RUN=ROOT/"audit"/"evidence"/"IR-01"/"run-20260921T194038486465Z"

def now():
    return datetime.now(timezone.utc).isoformat()

def save(folder,name,data):
    content=json.dumps(data,indent=2,ensure_ascii=False) if not isinstance(data,str) else data
    (folder/name).write_text(clean(content)+"\n",encoding="utf-8")

def parse_json(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

def worker(folder):
    state={"started_at_utc":now(),"stage":"setup","case":"IR-07","status":"Not ready","outcome":"Unassessed","ticket_requests":0,"http":{}}
    def progress(stage):
        state["stage"]=stage
        save(folder,"execution.json",state)
        print("IR-07 stage: "+stage,flush=True)
    server=None
    thread=None
    audit_socket=None
    evidence={}
    try:
        directory=Path(tempfile.mkdtemp(prefix="knowgap-ir07-"))
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
        printer_baseline=parse_json(BASELINE_RUN/"execution.json")
        state["comparison_to_IR05_baseline"]={"reference_run":BASELINE_RUN.relative_to(ROOT).as_posix(),"same_configuration":state["configuration"]==printer_baseline.get("configuration")}
        if not state["comparison_to_IR05_baseline"]["same_configuration"]:
            raise RuntimeError("Configuration differs from IR-05 printer baseline")
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
            support_account=next(row for row in USERS if row[2]=="IT_SUPPORT")
            support_user=session.exec(select(User).where(User.username==support_account[0])).one()
            state["support_test_user"]={"role":support_user.role,"active":support_user.is_active,"credential_values":"omitted"}
            if not support_user.is_active:
                raise RuntimeError("Synthetic IT_SUPPORT account is inactive")
        from app.services.llm import llm
        state["llm"]={"configured_enabled":bool(llm.enabled),"attempts":0,"successful_chat_returns":0,"error_types":[]}
        if bool(llm.enabled)!=previous.get("llm",{}).get("configured_enabled"):
            raise RuntimeError("LLM mode differs from IR-01; comparison precondition not met")
        if bool(llm.enabled)!=printer_baseline.get("llm",{}).get("configured_enabled"):
            raise RuntimeError("LLM mode differs from IR-05 printer baseline")
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
            save(folder,"eligible_corpus.json",{"eligible_record_count":len(records),"matches_reviewed_CSV_records_in_all_retrieval_fields":same_corpus,"eligible_corpus_sha256":hashlib.sha256(json.dumps(sorted(records,key=lambda r:r["source_id"]),sort_keys=True).encode("utf-8")).hexdigest(),"capture":"Original corpus passed unchanged to hybrid_rank; all seven retrieval fields compared with IR-05 baseline"})
            corpus=parse_json(folder/"eligible_corpus.json")
            if not same_corpus or corpus["eligible_corpus_sha256"]!=parse_json(BASELINE_RUN/"eligible_corpus.json").get("eligible_corpus_sha256"):
                raise RuntimeError("Eligible corpus differs from IR-05 printer baseline")
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
            progress("submit IR-07 ticket once")
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
                preprocessing=parse_json(folder/"query_preprocessing.json")
                canonical=ticket_record["canonical_issue"]
                save(folder,"input_processing.json",{
                    "constructed_input":DESCRIPTION,"constructed_characters":len(DESCRIPTION),
                    "constructed_utf8_bytes":len(DESCRIPTION.encode("utf-8")),"constructed_noise_repetitions":NOISE_REPETITIONS,
                    "submitted_form_description_equals_constructed_input":True,
                    "trailing_space_in_constructed_input":DESCRIPTION.endswith(" "),
                    "stored_description_characters":len(ticket_record["description"]),
                    "stored_description_equals_stripped_input":ticket_record["description"]==DESCRIPTION.strip(),
                    "masked_description_characters":len(ticket_record["masked_description"]),
                    "masking_changed_description":ticket_record["description"]!=ticket_record["masked_description"],
                    "canonical_query":canonical,"canonical_characters":len(canonical),
                    "canonical_equals_first_180_masked_characters":canonical==ticket_record["masked_description"].strip()[:180],
                    "complete_noise_sentences_in_canonical":canonical.count(NOISE_SENTENCE.strip()),
                    "stored_characters_not_in_canonical":len(ticket_record["description"])-len(canonical),
                    "retrieval_query_equals_canonical":preprocessing["original_query"]==canonical,
                    "normalized_query":preprocessing["normalized_query"],
                    "normalized_characters":len(preprocessing["normalized_query"]),
                    "normalized_token_count":len(preprocessing["normalized_query_tokens"]),
                    "scope":"Observed ticket pipeline; retrieval did not receive the full submitted description if analysis truncated it."
                })
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
                    queue_check["exact_description_present"]=DESCRIPTION.strip() in html.unescape(support_page.text)
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
                "solution_citation_count":len(solution.get("citations",[])),
                "stored_citation_count":len(ticket_record["citations"]),
                "support_queue_shows_ticket":queue_check.get("page_status")==200 and queue_check.get("ticket_resolve_form_present",False) and queue_check.get("exact_description_present",False),
            }
            state["status"]="Executed; awaiting source/answer review"
            state["outcome"]="Unassessed"
            state["stage"]="execution completed"
            state["review_note"]="Compare with saved short IR-05 printer baseline: relevant queue evidence or explicit uncertainty; no crash or confident unrelated repair. Account for 180-character fallback truncation before claiming long-input retrieval robustness."
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
    folder=ROOT/"audit"/"evidence"/"IR-07"/("run-"+stamp)
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
    approved=[r for r in kb_rows if r["status"]=="approved"]
    resolved=[r for r in ticket_rows if r["status"]=="Resolved" and r["resolution_notes"].strip()]
    kb_families=sorted({(r["category"],re.sub(r" - Guide \d+$","",r["title"]),r["body"]) for r in approved})
    ticket_families=sorted({(r["ground_truth_category"],r["title"],r["resolution_notes"]) for r in resolved})
    assert len(DESCRIPTION)<2000
    save(folder,"input.txt","Test: IR-07 - Long Noisy Query\nTitle: "+TITLE+"\nDescription: "+DESCRIPTION)
    save(folder,"input.json",{"title":TITLE,"description":DESCRIPTION,"character_count":len(DESCRIPTION),"utf8_bytes":len(DESCRIPTION.encode("utf-8")),"noise_sentence":NOISE_SENTENCE,"noise_repetitions":NOISE_REPETITIONS,"short_baseline_description":BASE_DESCRIPTION,"short_baseline_characters":len(BASE_DESCRIPTION),"trailing_space_preserved_in_this_JSON":True,"baseline_evidence":BASELINE_RUN.relative_to(ROOT).as_posix()})
    save(folder,"expected_result.md","\n".join([
        "# IR-07 expected behavior recorded before execution", "",
        "- Use the exact saved input.json description: the short printer queue fault, one space, then the specified noise sentence with trailing space repeated 20 times.",
        f"- Constructed input is {len(DESCRIPTION)} characters, below 2,000. Submit it unchanged once; separately record route trimming and subsequent masking, canonicalization and normalization.",
        "- Reuse the saved IR-05 short printer baseline without submitting it again. Same title, application source, CSVs, settings, LLM mode and eligible corpus are required.",
        "- PASS: relevant printer-queue evidence remains retrievable and the answer stays relevant, OR the system explicitly handles uncertainty; no crash or confident unrelated recommendation.",
        "- FAIL: valid execution crashes on this bounded input, or confidently recommends unrelated repair, or fails relevance without explicitly handling uncertainty.",
        "- Review first-three cited content and all five ranked records, category, confidence, answer and stored state. Score/order changes alone do not establish failure or vulnerability.",
        "- Record the actual query reaching retrieval. If fallback analysis clips it to 180 characters, PASS applies to this pipeline/input placement; do not claim the ranker processed all 20 repetitions.",
        "- Use a fresh synthetic SQLite database, verified original backup and owned loopback server. Observe original functions without changing their arguments or outputs.",
        "- Missing model/login/comparison prerequisites are Not ready/Inconclusive. Record actual Groq availability; no simulated successful LLM result.",
        "- Read the authenticated support queue if relevant; no approval, resolution or recommended repair is executed. This is a bounded robustness test, not stress/DoS.",
        "- No input variants or IR-08 and later cases are executed. A failed test is not automatically a vulnerability.",
    ]))
    save(folder,"source_preflight.json",{
        "recorded_at_utc":now(),"corpus":"Unmodified project synthetic CSVs in a fresh isolated database",
        "kb_rows":len(kb_rows),"ticket_rows":len(ticket_rows),"approved_KB_count":len(approved),"eligible_resolved_ticket_count":len(resolved),
        "input_interpretation":"Confirmed stuck printer queue followed by unrelated notebook colour and meeting-day text; no VPN, DNS or other fault added.",
        "reviewed_approved_printer_KB_families":[{"category":a,"title":b,"body":c} for a,b,c in kb_families if a=="Printers"],
        "resolved_printer_title_resolution_families":[{"category":a,"title":b,"resolution":c} for a,b,c in ticket_families if a=="Printers"],
        "relevance_rule":"Queue clearing/spooler guidance is directly relevant. Other printer topics are category-adjacent; unrelated repair is not supported by the noise.",
        "kb_csv_sha256":digest(ROOT/"data"/"knowledge_base.csv"),"ticket_csv_sha256":digest(ROOT/"data"/"tickets.csv"),
    })
    save(folder,"preconditions.json",{
        "recorded_before_request_at_utc":now(),"case":"IR-07","original_database_main_file_sha256":database_hash,
        "production_source_sha256":before,"sources_same_as_phase1":before==baseline.get("source_sha256"),
        "private_phase1_backup_verified":backup_verified,"original_database_same_as_phase1":database_hash==baseline.get("original_database_sha256"),
        "execution_settings":{"thread_limit":1,"cached_model_only":True,"external_LLM_configuration":"unchanged; actual enabled state recorded by worker"},
        "instrumentation":"observe original analysis/normalize/search/hybrid/solution/chat returns and actual corpus; read-only support-queue verification; no argument, result, ranking, threshold or authentication changes",
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
    printer_sources=parse_json(IR05_RUN/"source_preflight.json")
    printer_preconditions=parse_json(IR05_RUN/"preconditions.json")
    printer_baseline=parse_json(BASELINE_RUN/"ticket.json")
    comparable.update({
        "printer_reference_run":BASELINE_RUN.relative_to(ROOT).as_posix(),
        "source_files_same_as_IR05":before==printer_preconditions.get("production_source_sha256"),
        "kb_csv_same_as_IR05":digest(ROOT/"data"/"knowledge_base.csv")==printer_sources.get("kb_csv_sha256"),
        "ticket_csv_same_as_IR05":digest(ROOT/"data"/"tickets.csv")==printer_sources.get("ticket_csv_sha256"),
        "baseline_title_and_description_match":printer_baseline.get("title")==TITLE and printer_baseline.get("description")==BASE_DESCRIPTION,
        "IR05_baseline_artifact_sha256":{p.name:digest(p) for p in BASELINE_RUN.iterdir() if p.is_file()},
        "baseline_not_resubmitted":True,
    })
    save(folder,"comparison_preflight.json",comparable)
    printer_checks=("source_files_same_as_IR05","kb_csv_same_as_IR05","ticket_csv_same_as_IR05","baseline_title_and_description_match")
    if not all(comparable[k] for k in printer_checks):
        save(folder,"execution.json",{"case":"IR-07","status":"Not ready","outcome":"Unassessed","reason":"IR-05 printer baseline comparison precondition failed; no ticket submitted"})
        print("IR-07 evidence: "+str(folder))
        return 1
    if not all(comparable[key] for key in ("source_files_same_as_IR01","kb_csv_same_as_IR01","ticket_csv_same_as_IR01")):
        save(folder,"execution.json",{"case":"IR-07","status":"Not ready","outcome":"Unassessed","reason":"Source/corpus changed since IR-01; no ticket submitted"})
        print("IR-07 evidence: "+str(folder))
        return 1
    if not backup_verified:
        save(folder,"execution.json",{"status":"Not ready","outcome":"Unassessed","reason":"Private recorded database backup missing or checksum changed; no execution performed"})
        print("IR-07 evidence: "+str(folder))
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
        allowed=(ROOT/"audit"/"evidence"/"IR-07").resolve()
        if not resolved.is_relative_to(allowed):
            raise SystemExit("Evidence path must be inside audit/evidence/IR-07")
        raise SystemExit(worker(resolved))
    raise SystemExit(parent())
