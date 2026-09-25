"""IR-13 only: four declared unauthenticated HTTP requests to an owned loopback server.
Uses a private synthetic database; no login, malformed tokens, role tests or application edits.
"""
from __future__ import annotations
import argparse,csv,hashlib,inspect,json,os,re,socket,sqlite3,subprocess,sys,tempfile,threading,time
from pathlib import Path
from datetime import datetime,timezone
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[key]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'; os.environ['HF_HUB_OFFLINE']='1'; os.environ['TRANSFORMERS_OFFLINE']='1'
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT)); os.chdir(ROOT)
from collect_baseline import clean,digest,code_hashes
ISSUE='My laptop is connected to Wi-Fi but there is no internet.'
MESSAGE={'message_id':'ir13-retrieval-001','request_id':'ir13-local-audit','sender':'audit_client','receiver':'retrieval_agent','task':'retrieve_knowledge','payload':{'issue':ISSUE}}
TARGETS=[{'id':'A01','method':'GET','path':'/home','encoding':'none','body':None},
 {'id':'A02','method':'POST','path':'/tickets/create','encoding':'form','body':{'title':'No-login ticket audit','description':ISSUE}},
 {'id':'A03','method':'POST','path':'/agents/retrieval/search','encoding':'json','body':MESSAGE},
 {'id':'A04','method':'POST','path':'/agents/knowledge/analyze','encoding':'none','body':None}]
def now(): return datetime.now(timezone.utc).isoformat()
def save(folder,name,obj):
 text=obj if isinstance(obj,str) else json.dumps(obj,indent=2,ensure_ascii=False)
 (folder/name).write_text(clean(text)+'\n',encoding='utf-8',newline='\n')
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def db_state(path):
 with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as con:
  con.execute('PRAGMA query_only=ON')
  tables=[x[0] for x in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
  result={}
  for table in tables:
   if not re.fullmatch(r'[a-zA-Z0-9_]+',table): raise RuntimeError('Unexpected table identifier')
   rows=con.execute('SELECT * FROM "'+table+'" ORDER BY rowid').fetchall()
   result[table]={'row_count':len(rows),'rows_sha256':hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':'),default=str).encode('utf-8')).hexdigest()}
 return result

def worker(folder):
 state={'case':'IR-13','started_at_utc':now(),'stage':'setup','status':'Not ready','outcome':'Unassessed','target_requests':0,'login_requests':0,'redirect_followups':0,'endpoint_calls':{'retrieval':0,'knowledge':0}}
 server=None; thread=None; bound=None
 def progress(stage):
  state['stage']=stage; save(folder,'execution.json',state); print('IR-13 stage: '+stage,flush=True)
 try:
  temp=Path(tempfile.mkdtemp(prefix='knowgap-ir13-')); database=temp/'knowgap.db'; os.environ['DATABASE_URL']='sqlite:///'+database.as_posix(); state['isolated_database']=str(database)
  from app.config import get_settings
  cfg=get_settings(); state['configuration']={'bm25_weight':cfg.hybrid_bm25_weight,'semantic_weight':cfg.hybrid_semantic_weight,'high_threshold':cfg.high_confidence_threshold,'uncertain_threshold':cfg.uncertain_threshold,'embedding_model':'all-MiniLM-L6-v2','llm_model':cfg.groq_model,'thread_limit':1,'cached_model_only':True}
  from app.services.llm import llm
  state['llm']={'configured_enabled':bool(llm.enabled),'chat_attempts':0,'successful_returns':0}
  previous=read(ROOT/'audit/evidence/IR-01/run-20260921T194038486465Z/execution.json')
  if bool(llm.enabled)!=previous['llm']['configured_enabled']: raise RuntimeError('Provider mode differs from baseline; review before HTTP requests')
  progress('load original cached model')
  from app.services.embeddings import get_model
  start=time.perf_counter(); get_model(); state['model_load_call_seconds']=round(time.perf_counter()-start,3)
  from app.database import create_db_and_tables,engine
  if Path(engine.url.database).resolve()!=database.resolve() or database.resolve()==(ROOT/'knowgap.db').resolve(): raise RuntimeError('Database isolation failed before setup writes')
  from sqlmodel import Session,select
  from scripts.seed_db import seed_users,seed_kb,seed_historical_tickets
  from app.models import KnowledgeArticle,Ticket,User
  create_db_and_tables()
  with Session(engine) as session:
   seed_users(session); seed_kb(session); seed_historical_tickets(session)
   roles=sorted(u.role for u in session.exec(select(User)).all())
   articles=session.exec(select(KnowledgeArticle)).all(); historical=session.exec(select(Ticket)).all()
   state['seed_counts']={'articles':len(articles),'historical_tickets':len(historical),'users':len(roles)}; state['roles_present']=roles
  from app.agents import retrieval_agent,knowledge_intelligence_agent as kia
  from app.routes import agents as routes
  from app.schemas import AgentMessage
  assert AgentMessage.model_validate(MESSAGE).model_dump()==MESSAGE
  assert len(TARGETS[1]['body']['title'].strip())>=3 and len(TARGETS[1]['body']['description'].strip())>=10
  with Session(engine) as session: records=retrieval_agent._records_from_db(session)
  with (ROOT/'data/knowledge_base.csv').open(encoding='utf-8-sig',newline='') as f: kb=list(csv.DictReader(f))
  with (ROOT/'data/tickets.csv').open(encoding='utf-8-sig',newline='') as f: tickets=list(csv.DictReader(f))
  expected=[{'source_id':r['doc_id'],'title':r['title'],'content':r['body'],'category':r['category'],'supported_os':r['supported_os'],'source_type':r['source_type'],'status':r['status']} for r in kb if r['status']=='approved']
  expected += [{'source_id':r['ticket_id'],'title':r['title'],'content':f"Problem: {r['description']}\nRoot cause: \nResolution: {r['resolution_notes']}",'category':r['ground_truth_category'],'supported_os':'Any','source_type':'resolved_ticket','status':'resolved'} for r in tickets if r['status']=='Resolved' and r['resolution_notes'].strip()]
  assert sorted(records,key=lambda x:x['source_id'])==sorted(expected,key=lambda x:x['source_id']) and len(records)==427
  save(folder,'eligible_records.json',records)
  save(folder,'corpus_preflight.json',{'recorded_before_requests_at_utc':now(),'eligible_count':len(records),'matches_original_CSV_in_all_retrieval_fields':True,'knowledge_article_security_classes':sorted({a.security_class for a in articles}),'seed_counts':state['seed_counts'],'retrieval_issue':ISSUE,'schema_valid':True,'ticket_form_meets_length_rules':True,'knowledge_analyze_body':'No body parameter declared; send none','working_database_rows_copied':False})
  # Observation wrappers call originals once and return unchanged; no authentication or scoring substitute.
  original_search=routes.search_knowledge; original_health=routes.analyze_knowledge_health; original_chat=llm.chat
  def observed_search(*args,**kwargs):
   state['endpoint_calls']['retrieval']+=1; start=time.perf_counter(); result=original_search(*args,**kwargs); save(folder,'retrieval_function_result.json',{'elapsed_seconds':round(time.perf_counter()-start,3),'result':result}); return result
  def observed_health(*args,**kwargs):
   state['endpoint_calls']['knowledge']+=1; before={'cache_present':kia._health_cache is not None,'cache_time':kia._health_cache_time}; start=time.perf_counter(); result=original_health(*args,**kwargs)
   save(folder,'knowledge_function_result.json',{'elapsed_seconds':round(time.perf_counter()-start,3),'cache_before':before,'cache_present_after':kia._health_cache is not None,'result':result}); return result
  def observed_chat(*args,**kwargs):
   state['llm']['chat_attempts']+=1; result=original_chat(*args,**kwargs); state['llm']['successful_returns']+=1; return result
  routes.search_knowledge=observed_search; routes.analyze_knowledge_health=observed_health; llm.chat=observed_chat
  from app.main import app
  metadata=[]
  for target in TARGETS:
   route=next(r for r in app.routes if getattr(r,'path',None)==target['path'] and target['method'] in getattr(r,'methods',set()))
   lines,line_no=inspect.getsourcelines(route.endpoint)
   metadata.append({'id':target['id'],'method':target['method'],'path':target['path'],'handler':route.endpoint.__name__,'source_file':Path(inspect.getsourcefile(route.endpoint)).relative_to(ROOT).as_posix(),'line':line_no,'handler_source':''.join(lines),'direct_dependencies':[{'name':d.name,'call':getattr(d.call,'__name__',str(type(d.call))),'nested_dependency_count':len(d.dependencies)} for d in route.dependant.dependencies],'body_parameters':[{'name':f.name,'required':f.required} for f in route.dependant.body_params]})
  save(folder,'route_preflight.json',{'recorded_before_requests_at_utc':now(),'global_dependencies':len(app.router.dependencies),'user_middleware_count':len(app.user_middleware),'targets':metadata,'source_note':'Dependency absence supplements explicit handler inspection; it alone is not a runtime denial/exposure result'})
  import httpx,uvicorn
  progress('start owned loopback server')
  for port in (8001,8002,0):
   candidate=socket.socket()
   try: candidate.bind(('127.0.0.1',port))
   except OSError: candidate.close(); continue
   bound=candidate; break
  if bound is None: raise RuntimeError('No loopback socket available')
  port=bound.getsockname()[1]; address=f'http://127.0.0.1:{port}'; state['base_url']=address
  server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='info',access_log=False)); thread=threading.Thread(target=lambda:server.run(sockets=[bound]),daemon=True); thread.start()
  for _ in range(120):
   if not thread.is_alive(): raise RuntimeError('Audit server exited before startup')
   if server.started: break
   time.sleep(.25)
  if not server.started: raise RuntimeError('Audit server startup timeout')
  state['server_started']=True; state['health_probe']='No extra HTTP health request; verified owned server.started before the four targets'
  before=db_state(database); db_before=digest(database); snapshot=temp/'before_unauthenticated_requests.sqlite'
  with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as src:
   src.execute('PRAGMA query_only=ON')
   with sqlite3.connect(str(snapshot)) as dst: src.backup(dst); integrity=dst.execute('PRAGMA integrity_check').fetchone()[0]
  assert integrity=='ok' and db_state(snapshot)==before
  snapshot_hash=digest(snapshot)
  save(folder,'isolated_database_backup.json',{'recorded_before_requests_at_utc':now(),'path':str(snapshot),'sha256':snapshot_hash,'integrity_check':integrity,'outside_repository':not snapshot.resolve().is_relative_to(ROOT.resolve()),'method':'SQLite backup API from read-only source after owned server startup and before target requests','all_table_states_match_seeded_source':True})
  save(folder,'database_preflight.json',{'recorded_before_requests_at_utc':now(),'tables':before,'seeded_database_main_file_sha256':db_before,'note':'Only row counts and hashes saved; row values including credential hashes are not exported'})
  responses=[]
  for target in TARGETS:
   progress('anonymous request '+target['id']+' '+target['method']+' '+target['path'])
   request_folder=folder/target['id']; request_folder.mkdir()
   # One fresh client per target, no prior login, no ambient proxy or netrc auth.
   with httpx.Client(base_url=address,follow_redirects=False,timeout=150,trust_env=False) as client:
    kwargs={}
    if target['encoding']=='form': kwargs['data']=target['body']
    if target['encoding']=='json': kwargs['json']=target['body']
    request=client.build_request(target['method'],target['path'],**kwargs)
    capture={'id':target['id'],'recorded_before_send_at_utc':now(),'method':request.method,'url':str(request.url),'path':target['path'],'encoding':target['encoding'],'declared_body':target['body'],'serialized_body':request.content.decode('utf-8'),'content_type':request.headers.get('content-type'),'cookie_header_present':'cookie' in request.headers,'authorization_header_present':'authorization' in request.headers,'proxy_authorization_header_present':'proxy-authorization' in request.headers,'client_cookie_count_before':len(client.cookies),'fresh_client':True,'follow_redirects':False,'trust_env':False}
    assert not capture['cookie_header_present'] and not capture['authorization_header_present'] and not capture['proxy_authorization_header_present'] and capture['client_cookie_count_before']==0
    save(request_folder,'request.json',capture)
    state['target_requests']+=1; save(folder,'execution.json',state)
    started=time.perf_counter(); response=client.send(request,follow_redirects=False)
    try: body=response.json()
    except ValueError: body=None
    result={'id':target['id'],'received_at_utc':now(),'method':target['method'],'path':target['path'],'status_code':response.status_code,'location':response.headers.get('location'),'content_type':response.headers.get('content-type'),'elapsed_seconds':round(time.perf_counter()-started,3),'response_bytes':len(response.content),'response_text_sha256':hashlib.sha256(response.content).hexdigest(),'redirect_history_count':len(response.history),'set_cookie_header_present':'set-cookie' in response.headers,'client_cookie_count_after':len(client.cookies),'body_json':body,'body_text':response.text,'no_authentication_sent':True}
    save(request_folder,'response.json',result); save(request_folder,'response_body.txt',response.text)
   after=db_state(database)
   save(request_folder,'database_after.json',{'recorded_after_request_at_utc':now(),'tables':after,'all_tables_equal_pre_request_snapshot':after==before,'ticket_count_before':before['ticket']['row_count'],'ticket_count_after':after['ticket']['row_count'],'ticket_rows_hash_unchanged':after['ticket']==before['ticket']})
   responses.append({'id':target['id'],'method':target['method'],'path':target['path'],'status_code':response.status_code,'location':response.headers.get('location'),'response_bytes':len(response.content),'no_authentication_sent':True,'database_unchanged':after==before})
  save(folder,'response_summary.json',responses)
  after=db_state(database)
  post={'tables':after,'all_tables_unchanged':after==before,'seeded_database_main_file_unchanged':digest(database)==db_before,'private_snapshot_unchanged':digest(snapshot)==snapshot_hash,'ticket_count_unchanged':before['ticket']==after['ticket'],'target_requests':state['target_requests'],'knowledge_cache_populated':kia._health_cache is not None,'cache_side_effect':'Process-local knowledge-health cache; no persistent write attributed unless table hashes change'}
  save(folder,'database_postflight.json',post)
  state['status']='Executed; awaiting authentication and disclosure review'; state['stage']='execution completed'
 except Exception as exc:
  import traceback
  state['status']='Execution error; review required'; state['error']={'type':type(exc).__name__,'message':str(exc)}; traceback.print_exc()
 finally:
  if server: server.should_exit=True
  if thread: thread.join(timeout=12)
  if bound: bound.close()
  if 'original_search' in locals(): routes.search_knowledge=original_search
  if 'original_health' in locals(): routes.analyze_knowledge_health=original_health
  if 'original_chat' in locals(): llm.chat=original_chat
  state['server_stopped']=thread is None or not thread.is_alive(); state['finished_at_utc']=now(); save(folder,'execution.json',state); print(clean(json.dumps(state)),flush=True)
 return 0 if state['status']=='Executed; awaiting authentication and disclosure review' and state['server_stopped'] else 1

def parent():
 folder=ROOT/'audit/evidence/IR-13'/('run-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')); folder.mkdir(parents=True,exist_ok=False)
 before=code_hashes(); db_hash=digest(ROOT/'knowgap.db'); baseline=read(ROOT/'audit/evidence/baseline/environment.json'); backup=read(ROOT/'audit/evidence/baseline/database_backup.json'); backup_path=Path(backup['path']); backup_ok=backup_path.is_file() and digest(backup_path)==backup['backup_sha256']
 prior={p.relative_to(ROOT).as_posix():digest(p) for name in ['baseline']+[f'IR-{i:02d}' for i in range(1,13)] for p in (ROOT/'audit/evidence'/name).rglob('*') if p.is_file()}
 save(folder,'inputs.json',{'case':'IR-13','recorded_before_execution_at_utc':now(),'targets':TARGETS,'requests_per_target':1,'target_request_limit':4,'authentication':'Fresh cookie-free client per target; no Authorization header, no login or crafted token','follow_redirects':False,'body_policy':'Valid normal form/AgentMessage; knowledge analyze declares no body','no_other_targets':True})
 save(folder,'expected_result.md','\n'.join([
  '# IR-13 criteria fixed before execution','',
  '- Objective: access without login. Four targets only: GET /home, POST /tickets/create, POST /agents/retrieval/search, POST /agents/knowledge/analyze. One request each; no automatic redirect following.',
  '- Expected policy: protected UI/ticket operations reject anonymous access or redirect to login; sensitive retrieval/knowledge-analysis operations reject anonymous callers. Current missing agent dependencies are a suspected weakness, not a public-access PASS rule.',
  '- Use valid benign form and AgentMessage bodies; knowledge analyze takes no body. Request validation (422) is not authentication evidence. Fresh client per target, Cookie and Authorization absent on built requests, ambient auth/proxies disabled.',
  '- Per-target PASS: login redirect or explicit 401/403 without protected data or mutation. Verify redirect is the actual login target (/ under this app); do not follow it.',
  '- Per-target FAIL: valid anonymous request executes protected operation or returns internal source/analytics data. 200 alone is insufficient: inspect actual response and original function invocation. 422/5xx/environment failures are inconclusive unless separately sufficient evidence proves access.',
  '- Overall PASS requires all four targets to satisfy intended policy. Any valid demonstrated exposure makes IR-13 FAIL, while other target outcomes remain separate.',
  '- Verify original private backup; seed only synthetic original CSVs/users into fresh isolated SQLite DB, snapshot it before requests, own the loopback socket and verify all table counts/hashes after each request. No login or production-data use.',
  '- Capture serialized nonsecret requests, absent-auth booleans, initial status/Location/body, actual function result and redacted logs. Never save credentials, cookies, tokens or raw account rows.',
  '- Retrieval evidence should identify returned source IDs/text/type/status and match against actual eligible records. Knowledge-health evidence should distinguish aggregates from individual ticket text; do not claim clusters/examples unless actually returned.',
  '- Record configured Groq and any original chat calls; authentication observations do not depend on successful LLM generation. Observe original functions without replacing scores or security checks.',
  '- One common missing-authentication root cause may support one formal finding across agent routes. Explain impact/likelihood/severity under tested loopback/synthetic scope; do not infer internet reachability, real-user disclosure, privilege escalation or DoS.',
  '- No role-switching, invalid-token, alternate endpoint, schema-abuse, credential-guessing, stress tests, repairs or authentication fixes. IR-14/IR-15 remain unexecuted.',
 ]))
 save(folder,'preconditions.json',{'recorded_before_execution_at_utc':now(),'production_source_sha256':before,'original_database_main_file_sha256':db_hash,'sources_match_baseline':before==baseline['source_sha256'],'database_matches_baseline':db_hash==baseline['original_database_sha256'],'private_phase1_backup_verified':backup_ok,'prior_evidence_file_count':len(prior),'scope':'Owned loopback server, original synthetic CSVs in private temporary DB; no real data or public targets'})
 if not backup_ok or before!=baseline['source_sha256'] or db_hash!=baseline['original_database_sha256']:
  save(folder,'execution.json',{'status':'Not ready','outcome':'Unassessed','reason':'Baseline source/database/backup precondition failed; no requests sent'}); print(str(folder)); return 1
 print('IR-13 evidence: '+str(folder),flush=True)
 command=[sys.executable,'-B',str(Path(__file__).resolve()),'--worker',str(folder)]; started=time.perf_counter(); timed_out=False
 try:
  run=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding='utf-8',errors='replace',timeout=300,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)); output=run.stdout+'\n'+run.stderr; exit_code=run.returncode
 except subprocess.TimeoutExpired as exc:
  timed_out=True; exit_code=None
  def decode(x): return x.decode('utf-8',errors='replace') if isinstance(x,bytes) else x or ''
  output=decode(exc.stdout)+'\n'+decode(exc.stderr)
 save(folder,'terminal_log.txt',output)
 result={'case':'IR-13','finished_at_utc':now(),'process_exit_code':exit_code,'timed_out':timed_out,'elapsed_seconds':round(time.perf_counter()-started,3),'source_files_unchanged':before==code_hashes(),'original_database_main_file_unchanged':db_hash==digest(ROOT/'knowgap.db'),'prior_evidence_unchanged':all(digest(ROOT/name)==value for name,value in prior.items()),'evidence_directory':folder.relative_to(ROOT).as_posix(),'integrity_limit':'Main-file hash does not cover unrelated concurrent SQLite WAL writes','outcome':'Unassessed; awaiting review'}
 save(folder,'process_result.json',result); print(clean(json.dumps(result)),flush=True)
 return 0 if exit_code==0 and not timed_out and all(result[k] for k in ('source_files_unchanged','original_database_main_file_unchanged','prior_evidence_unchanged')) else 1
if __name__=='__main__':
 parser=argparse.ArgumentParser(); parser.add_argument('--worker',type=Path); args=parser.parse_args()
 if args.worker:
  folder=args.worker.resolve()
  if not folder.is_relative_to((ROOT/'audit/evidence/IR-13').resolve()): raise SystemExit('Invalid evidence path')
  raise SystemExit(worker(folder))
 raise SystemExit(parent())
