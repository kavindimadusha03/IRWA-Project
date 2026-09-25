"""IR-14 only: normal logins and three declared role targets per isolated role database."""
from __future__ import annotations
import argparse,hashlib,inspect,json,os,re,socket,sqlite3,subprocess,sys,tempfile,threading,time
from pathlib import Path
from datetime import datetime,timezone
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[key]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'; os.environ['HF_HUB_OFFLINE']='1'; os.environ['TRANSFORMERS_OFFLINE']='1'
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT)); os.chdir(ROOT)
from collect_baseline import clean,digest,code_hashes
from run_ir13 import db_state
ROLES=['CUSTOMER','IT_SUPPORT','KNOWLEDGE_ANALYST','ADMIN','AUDIT_VIEWER']
DRAFT={'doc_id':'AUDIT-IR14-DRAFT-001','title':'IR14 role approval fixture','content':'Synthetic audit note for testing knowledge approval. No troubleshooting action is requested.','category':'Printers','status':'draft','source_type':'internal_kb','author':'IR-14 synthetic fixture','authoritative':False,'supported_os':'Any','security_class':'internal'}
CATEGORY={'name':'IR14 Audit Category','description':'Synthetic category for role authorization check.'}
def now(): return datetime.now(timezone.utc).isoformat()
def save(folder,name,value):
 text=value if isinstance(value,str) else json.dumps(value,indent=2,ensure_ascii=False)
 (folder/name).write_text(clean(text)+'\n',encoding='utf-8',newline='\n')
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def fixture_state(session,select,Article,Category,User):
 article=session.exec(select(Article).where(Article.doc_id==DRAFT['doc_id'])).one()
 return {'article':article.model_dump(mode='json'),'other_articles_sha256':hashlib.sha256(json.dumps([a.model_dump(mode='json') for a in session.exec(select(Article).where(Article.doc_id!=DRAFT['doc_id']).order_by(Article.id)).all()],sort_keys=True).encode()).hexdigest(),'categories':[c.model_dump(mode='json') for c in session.exec(select(Category).order_by(Category.id)).all()], 'users':[{'id':u.id,'role':u.role,'active':u.is_active} for u in session.exec(select(User).order_by(User.id)).all()]}
def worker(folder,role,route_harness=False):
 state={'case':'IR-14','role':role,'started_at_utc':now(),'stage':'setup','status':'Not ready','outcome':'Unassessed','login_requests':0,'profile_requests':0,'target_requests':0,'redirect_followups':0}
 server=None; thread=None; bound=None; observations=[]; current_request={'id':'setup'}
 def progress(stage):
  state['stage']=stage; save(folder,'execution.json',state); print('IR-14 '+role+': '+stage,flush=True)
 try:
  directory=Path(tempfile.mkdtemp(prefix='knowgap-ir14-'+role.lower()+'-')); database=directory/'knowgap.db'; os.environ['DATABASE_URL']='sqlite:///'+database.as_posix(); state['isolated_database']=str(database)
  from app.config import get_settings
  cfg=get_settings(); state['configuration']={'high_threshold':cfg.high_confidence_threshold,'uncertain_threshold':cfg.uncertain_threshold,'bm25_weight':cfg.hybrid_bm25_weight,'semantic_weight':cfg.hybrid_semantic_weight,'llm_model':cfg.groq_model,'thread_limit':1,'cached_model_only':True}
  from app.database import create_db_and_tables,engine
  if Path(engine.url.database).resolve()!=database.resolve() or database.resolve()==(ROOT/'knowgap.db').resolve(): raise RuntimeError('Database isolation failed before setup writes')
  from sqlmodel import Session,select
  from scripts.seed_db import USERS,seed_users,seed_kb,seed_historical_tickets
  from app.models import KnowledgeArticle,Ticket,User,Category
  create_db_and_tables()
  with Session(engine) as session:
   seed_users(session); seed_kb(session); seed_historical_tickets(session)
   if role=='AUDIT_VIEWER':
    demo=next(row for row in USERS if row[2]=='CUSTOMER'); source_user=session.exec(select(User).where(User.username==demo[0])).one()
    session.add(User(username='audit_ir14_viewer',full_name='IR14 Unsupported Role Fixture',role=role,is_active=True,hashed_password=source_user.hashed_password)); session.commit()
    account_name='audit_ir14_viewer'; account_password=demo[3]
   else:
    account=next(row for row in USERS if row[2]==role); account_name=account[0]; account_password=account[3]
   current_user=session.exec(select(User).where(User.username==account_name)).one(); assert current_user.role==role and current_user.is_active
   user_id=current_user.id
   analyst_id=session.exec(select(User).where(User.role=='KNOWLEDGE_ANALYST')).one().id; admin_id=session.exec(select(User).where(User.role=='ADMIN')).one().id
   session.add(KnowledgeArticle(**DRAFT,created_at=datetime(2026,9,22),updated_at=datetime(2026,9,22))); session.commit()
   fixture=fixture_state(session,select,KnowledgeArticle,Category,User); article_id=fixture['article']['id']
   assert fixture['article']['status']=='draft' and not fixture['article']['authoritative'] and fixture['categories']==[]
   assert len(session.exec(select(Ticket)).all())==500 and len(session.exec(select(KnowledgeArticle)).all())==81
   state['test_identity']={'database_user_id':user_id,'stored_role':role,'active':True,'unsupported_fixture':role=='AUDIT_VIEWER','origin':'Four original seed accounts; extra active unsupported-role account only in its own private DB; login secrets omitted'}
  targets=[
   {'id':'R01','method':'POST','path':f'/knowledge/{article_id}/approve','query':{},'body':None if role=='KNOWLEDGE_ANALYST' else {'role':'KNOWLEDGE_ANALYST','user_id':str(analyst_id),'status':'approved','authoritative':'true'},'expected_allowed':role=='KNOWLEDGE_ANALYST','expected_status':303 if role=='KNOWLEDGE_ANALYST' else 403},
   {'id':'R02','method':'GET','path':'/admin','query':{} if role=='ADMIN' else {'role':'ADMIN','user_id':str(admin_id)},'body':None,'expected_allowed':role=='ADMIN','expected_status':200 if role=='ADMIN' else 403},
   {'id':'R03','method':'POST','path':'/admin/categories/create','query':{},'body':dict(CATEGORY) if role=='ADMIN' else {**CATEGORY,'role':'ADMIN','user_id':str(admin_id)},'expected_allowed':role=='ADMIN','expected_status':303 if role=='ADMIN' else 403},
  ]
  save(folder,'inputs.json',{'recorded_before_requests_at_utc':now(),'role':role,'identity':state['test_identity'],'targets':targets,'article_fixture':DRAFT,'category_fixture':CATEGORY,'field_claim_note':'Denied-role cases carry claimed privileged role/user_id in ordinary form/query fields; authentication cookie remains issued for original stored identity. Positive controls use normal fields only.','unsupported_role_note':'Active AUDIT_VIEWER fixture is provisioned directly in only its isolated DB; this does not demonstrate creation through an admin endpoint.'})
  from app.routes import auth,knowledge,admin
  from app.services.llm import llm
  state['llm']={'configured_enabled':bool(llm.enabled),'calls':0}
  if bool(llm.enabled)!=read(ROOT/'audit/evidence/IR-01/run-20260921T194038486465Z/execution.json')['llm']['configured_enabled']: raise RuntimeError('Provider mode changed from baseline')
  original_chat=llm.chat
  def observed_chat(*args,**kwargs): state['llm']['calls']+=1; return original_chat(*args,**kwargs)
  llm.chat=observed_chat
  original_auth=auth.current_user_from_request; original_knowledge=knowledge.current_user_from_request; original_admin=admin.current_user_from_request
  def observed_current(request,session):
   user=original_auth(request,session)
   observations.append({'request_id':current_request['id'],'path':request.url.path,'user_found':user is not None,'database_user_id':user.id if user else None,'stored_role':user.role if user else None,'active':user.is_active if user else None})
   return user
  auth.current_user_from_request=observed_current; knowledge.current_user_from_request=observed_current; admin.current_user_from_request=observed_current
  if route_harness:
   from fastapi import FastAPI
   from fastapi.staticfiles import StaticFiles
   app=FastAPI(title=cfg.app_name,version='1.0.0')
   app.mount('/static',StaticFiles(directory=str(ROOT/'app/static')),name='static')
   app.include_router(auth.router); app.include_router(knowledge.router); app.include_router(admin.router)
   app.add_event_handler('startup',create_db_and_tables)
   state['runtime_mode']='original auth/knowledge/admin routers in audit FastAPI HTTP harness'
   state['full_application_loaded']=False
  else:
   from app.main import app
   state['runtime_mode']='original full app.main FastAPI application'; state['full_application_loaded']=True
  save(folder,'runtime_mode.json',{'mode':state['runtime_mode'],'full_application_loaded':state['full_application_loaded'],'mounted_router_modules':['app.routes.auth','app.routes.knowledge','app.routes.admin'] if route_harness else 'all original application routers','user_middleware_count':len(app.user_middleware),'global_dependencies':len(app.router.dependencies),'startup':'Original create_db_and_tables registered directly in route harness; original main startup otherwise','static_mount':'Original app/static mounted under name static for original template URL generation','dependency_overrides_count':len(app.dependency_overrides),'original_identity_helpers_observed':True,'guards_return_values_and_templates_unchanged':True,'limit':'Route harness excludes main-page, ticket, agent, support and chat integration; redirect destinations are captured, not followed. No blocked DLL loaded and no OS policy changed.' if route_harness else None})
  routes=[]
  for endpoint in (knowledge.approve_article,admin.admin_page,admin.create_category):
   lines,line=inspect.getsourcelines(endpoint); routes.append({'handler':endpoint.__name__,'file':Path(inspect.getsourcefile(endpoint)).relative_to(ROOT).as_posix(),'line':line,'source':''.join(lines)})
  save(folder,'route_preflight.json',{'handlers':routes,'admin_default_categories':list(admin.DEFAULT_CATEGORIES),'GET_admin_side_effect':'Original _ensure_categories runs after ADMIN guard; with this seed it may add default/source categories. Record its actual mutation rather than treating GET as inherently read-only.','guards_unchanged':True})
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
   if not thread.is_alive(): raise RuntimeError('Server exited before startup')
   if server.started: break
   time.sleep(.25)
  if not server.started: raise RuntimeError('Server startup timeout')
  state['server_started']=True; before=db_state(database); snapshot=directory/'before_role_requests.sqlite'
  with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as src:
   src.execute('PRAGMA query_only=ON')
   with sqlite3.connect(str(snapshot)) as dst: src.backup(dst); integrity=dst.execute('PRAGMA integrity_check').fetchone()[0]
  assert integrity=='ok' and db_state(snapshot)==before
  snapshot_hash=digest(snapshot)
  save(folder,'isolated_database_backup.json',{'recorded_before_requests_at_utc':now(),'path':str(snapshot),'sha256':snapshot_hash,'integrity_check':integrity,'outside_repository':not snapshot.resolve().is_relative_to(ROOT.resolve()),'all_table_states_match_seeded_source':True,'method':'SQLite backup API after fixture/server setup, before login or target requests'})
  save(folder,'database_preflight.json',{'tables':before,'fixtures':fixture,'note':'Raw account rows/password hashes not exported; user metadata limited to ID, role and active state'})
  with httpx.Client(base_url=address,follow_redirects=False,timeout=90,trust_env=False) as client:
   current_request={'id':'LOGIN'}; progress('normal login for synthetic '+role); state['login_requests']+=1
   login=client.post('/login',data={'username':account_name,'password':account_password})
   state['login']={'status':login.status_code,'location':login.headers.get('location'),'cookie_present':bool(client.cookies.get('access_token')),'redirect_history_count':len(login.history),'credentials_recorded':False}
   save(folder,'login.json',{'role':role,**state['login']})
   if login.status_code!=303 or login.headers.get('location')!='/home' or not client.cookies.get('access_token'): raise RuntimeError('Normal role login failed; no privileged target will be submitted')
   current_request={'id':'PROFILE'}; state['profile_requests']+=1; profile=client.get('/profile')
   resolved=observations[-1] if observations else {}
   profile_control={'status':profile.status_code,'location':profile.headers.get('location'),'redirect_history_count':len(profile.history),'identity':resolved,'profile_form_present':'action="/profile"' in profile.text,'login_proven_by_original_helper':resolved.get('path')=='/profile' and resolved.get('database_user_id')==user_id and resolved.get('stored_role')==role,'database_unchanged':db_state(database)==before}
   save(folder,'profile_control.json',profile_control); save(folder,'profile_control.html',profile.text)
   if profile.status_code!=200 or not profile_control['profile_form_present'] or not profile_control['login_proven_by_original_helper'] or not profile_control['database_unchanged']: raise RuntimeError('Authenticated profile control failed; privileged targets not submitted')
   for target in targets:
    ident=target['id']; current_request={'id':ident}; request_folder=folder/ident; request_folder.mkdir(); progress(role+' '+ident+' '+target['method']+' '+target['path'])
    table_before=db_state(database)
    with Session(engine) as session: fixture_before=fixture_state(session,select,KnowledgeArticle,Category,User)
    save(request_folder,'before.json',{'tables':table_before,'fixtures':fixture_before})
    kwargs={'params':target['query']}
    if target['body'] is not None: kwargs['data']=target['body']
    request=client.build_request(target['method'],target['path'],**kwargs)
    request_capture={'recorded_before_send_at_utc':now(),'role':role,'id':ident,'method':request.method,'url':str(request.url),'path':target['path'],'query':target['query'],'declared_form':target['body'],'serialized_body':request.content.decode('utf-8'),'content_type':request.headers.get('content-type'),'cookie_present':'cookie' in request.headers,'authorization_header_present':'authorization' in request.headers,'cookie_value':'omitted','follow_redirects':False,'expected_allowed':target['expected_allowed'],'expected_status':target['expected_status']}
    assert request_capture['cookie_present'] and not request_capture['authorization_header_present']
    save(request_folder,'request.json',request_capture); observation_start=len(observations); state['target_requests']+=1; save(folder,'execution.json',state)
    started=time.perf_counter(); response=client.send(request,follow_redirects=False)
    try: parsed=response.json()
    except ValueError: parsed=None
    save(request_folder,'response.json',{'status':response.status_code,'location':response.headers.get('location'),'content_type':response.headers.get('content-type'),'response_bytes':len(response.content),'body_sha256':hashlib.sha256(response.content).hexdigest(),'body_json':parsed,'body_text':response.text,'redirect_history_count':len(response.history),'set_cookie_present':'set-cookie' in response.headers,'elapsed_seconds':round(time.perf_counter()-started,3)})
    save(request_folder,'response_body.html' if 'text/html' in response.headers.get('content-type','') else 'response_body.txt',response.text)
    resolved=observations[observation_start:]; save(request_folder,'resolved_identity.json',resolved)
    table_after=db_state(database)
    with Session(engine) as session: fixture_after=fixture_state(session,select,KnowledgeArticle,Category,User)
    changed=[name for name in table_before if table_before[name]!=table_after[name]]
    save(request_folder,'after.json',{'tables':table_after,'fixtures':fixture_after,'changed_tables':changed,'article_before_status':fixture_before['article']['status'],'article_after_status':fixture_after['article']['status'],'category_count_before':len(fixture_before['categories']),'category_count_after':len(fixture_after['categories']),'users_unchanged':fixture_before['users']==fixture_after['users'],'returned_identity_matches_login':bool(resolved) and all(x['database_user_id']==user_id and x['stored_role']==role for x in resolved),'expected_allowed':target['expected_allowed'],'status_matches_expected':response.status_code==target['expected_status'],'unauthorized_state_unchanged':not changed if not target['expected_allowed'] else None})
  after=db_state(database)
  with Session(engine) as session: final_fixtures=fixture_state(session,select,KnowledgeArticle,Category,User)
  save(folder,'postflight.json',{'tables':after,'fixtures':final_fixtures,'changed_tables_since_setup':[name for name in before if before[name]!=after[name]],'private_snapshot_unchanged':digest(snapshot)==snapshot_hash,'original_user_rows_unchanged':before['user']==after['user'],'ticket_rows_unchanged':before['ticket']==after['ticket'],'all_observed_identities':observations})
  state['status']='Executed; awaiting role and mutation review'; state['stage']='execution completed'
 except Exception as exc:
  import traceback
  state['status']='Execution error; review required'; state['error']={'type':type(exc).__name__,'message':str(exc)}; traceback.print_exc()
 finally:
  if server: server.should_exit=True
  if thread: thread.join(timeout=12)
  if bound: bound.close()
  if 'original_auth' in locals(): auth.current_user_from_request=original_auth; knowledge.current_user_from_request=original_knowledge; admin.current_user_from_request=original_admin
  if 'original_chat' in locals(): llm.chat=original_chat
  state['server_stopped']=thread is None or not thread.is_alive(); state['finished_at_utc']=now(); save(folder,'execution.json',state); print(clean(json.dumps(state)),flush=True)
 return 0 if state['status']=='Executed; awaiting role and mutation review' and state['server_stopped'] else 1

def parent(route_harness=False):
 folder=ROOT/'audit/evidence/IR-14'/('run-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')); folder.mkdir(parents=True,exist_ok=False)
 before=code_hashes(); db_hash=digest(ROOT/'knowgap.db'); baseline=read(ROOT/'audit/evidence/baseline/environment.json'); backup=read(ROOT/'audit/evidence/baseline/database_backup.json'); backup_path=Path(backup['path']); backup_ok=backup_path.is_file() and digest(backup_path)==backup['backup_sha256']
 prior={p.relative_to(ROOT).as_posix():digest(p) for name in ['baseline']+[f'IR-{i:02d}' for i in range(1,14)] for p in (ROOT/'audit/evidence'/name).rglob('*') if p.is_file()}
 matrix={role:{'approve_article':role=='KNOWLEDGE_ANALYST','admin_page':role=='ADMIN','create_category':role=='ADMIN'} for role in ROLES}
 save(folder,'inputs.json',{'case':'IR-14','recorded_before_execution_at_utc':now(),'runtime_mode':'original-router HTTP harness' if route_harness else 'full application','roles':ROLES,'article_fixture':DRAFT,'category_fixture':CATEGORY,'expected_matrix':matrix,'per_role_requests':{'login':1,'profile':1,'targets':3},'total_HTTP_request_limit':25,'target_request_limit':15,'fixture_policy':'Separate private database/process/server per role; original seed corpus and four users plus one draft article. Only AUDIT_VIEWER worker adds one active unsupported-role account directly. Fixture timestamps fixed to 2026-09-22T00:00:00.','field_claim_policy':'Denied roles claim privileged role and user_id in form/query; actual issued cookie retains logged-in identity. No cookie/header token manipulation.','follow_redirects':False})
 save(folder,'expected_result.md','\n'.join([
  '# IR-14 criteria fixed before execution','',
  '- Runtime scope: '+('Original auth, knowledge and admin routers mounted in an audit FastAPI app, with original static mount, dependencies, templates, login and guards; direct original create_db_and_tables startup. Full app startup remains blocked by Windows Application Control/PyTorch. This is router-level HTTP integration only.' if route_harness else 'Original full app.main FastAPI application.'),
  '- Objective: confirm that a successful login grants only the stored role permissions. Five independent private databases, one per CUSTOMER, IT_SUPPORT, KNOWLEDGE_ANALYST, ADMIN and directly provisioned active AUDIT_VIEWER fixture.',
  '- Three targets per role, in order: POST /knowledge/{draft_id}/approve, GET /admin, POST /admin/categories/create. Use a real existing draft fixture and valid unique category form. Log in normally once and require GET /profile 200 with original helper resolving the expected stored identity before testing any privileged target.',
  '- Only KNOWLEDGE_ANALYST may approve: expected 303 /knowledge and only fixture status=approved, authoritative=true, updated_at changed. ADMIN has no universal override. Every other role must receive 403 with all table fingerprints unchanged.',
  '- Only ADMIN may view /admin: expected 200 with administration content. Original _ensure_categories may add missing default/source categories after the guard; record exactly these expected changes. Every other role must receive 403 with no administration data or database mutation.',
  '- Only ADMIN may create the benign category: expected 303 to /admin with success message and exactly one new active category with submitted name/description. Every other role must receive 403 and no category or other table changes.',
  '- Denied cases include privileged role/user_id claims in ordinary request fields. These must not replace the role resolved from the issued cookie subject/database. Save nonsecret identity observations and exact built fields. Positive controls use ordinary fields only.',
  '- Per-target PASS requires expected access decision, correct authenticated identity and only expected persistent effects. A 403 without authenticated control/identity is insufficient. 422, 5xx, startup/login failure or missing fixture makes the affected check inconclusive, not an authorization PASS.',
  '- Overall PASS requires all fifteen valid target checks, including positive controls, to pass. Any demonstrated unauthorized action/disclosure makes FAIL. A failed test alone is not automatically a confirmed vulnerability; classify cause and scope from evidence.',
  '- Preserve the original application, original database and baseline evidence. Verify the original private backup, snapshot each seeded private database before requests, compare all ten tables after each target, and also fingerprint all other KB articles and account rows.',
  '- No passwords, password hashes, cookies, JWTs or API keys in saved artifacts. Capture only cookie presence and resolved ID/stored role/active flag. Observe original identity helpers once per invocation without replacing guards or return values.',
  '- Unsupported fixture creation is direct isolated setup; login acceptance is a precondition, not proof of an administrative account-creation bypass. No malformed tokens, other privileged endpoints, ownership/CSRF, stress testing, real data, external systems, application fixes or IR-15 execution.',
  '- Existing VULN-IR13-01 remains open regardless of this separate role-guard result. Groq calls are observed and not required by these role targets.',
 ]))
 save(folder,'preconditions.json',{'recorded_before_execution_at_utc':now(),'production_source_sha256':before,'original_database_main_file_sha256':db_hash,'sources_match_baseline':before==baseline['source_sha256'],'database_matches_baseline':db_hash==baseline['original_database_sha256'],'private_phase1_backup_verified':backup_ok,'prior_evidence_file_count':len(prior),'prior_evidence_sha256':prior,'scope':'Owned loopback servers, original synthetic CSVs plus declared fixtures, isolated SQLite databases'})
 if route_harness:
  failed=ROOT/'audit/evidence/IR-14/run-20260923T020808917231Z'
  save(folder,'scope_adjustment.json',{'recorded_before_execution_at_utc':now(),'reason':'Full app import blocked by Windows Application Control (WinError 4551) at torch_python.dll before any HTTP; preserve failed attempt, test only original role routers without loading this unrelated dependency.','failed_full_application_attempt':failed.relative_to(ROOT).as_posix(),'preserved_failed_attempt_sha256':{p.relative_to(ROOT).as_posix():digest(p) for p in failed.rglob('*') if p.is_file()},'basis':'app/main.py mounts auth, knowledge and admin without added router dependencies or custom middleware. Harness retains their original APIRoutes and SQLModel/session/auth/template behavior.','scope_limit':'Does not establish current full application startup or all-route integration; no OS policy, DLL, dependency package or app source changes.'})
 if not backup_ok or before!=baseline['source_sha256'] or db_hash!=baseline['original_database_sha256']:
  save(folder,'execution.json',{'status':'Not ready','outcome':'Unassessed','reason':'Baseline source/database/backup precondition failed; no requests sent'}); print(str(folder)); return 1
 print('IR-14 evidence: '+str(folder),flush=True); results=[]; started=time.perf_counter()
 for role in ROLES:
  role_folder=folder/role; role_folder.mkdir(); command=[sys.executable,'-B',str(Path(__file__).resolve()),'--worker',str(role_folder),'--role',role]; role_start=time.perf_counter(); timed_out=False
  if route_harness: command.append('--route-harness')
  try:
   run=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding='utf-8',errors='replace',timeout=240,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)); output=run.stdout+'\n'+run.stderr; exit_code=run.returncode
  except subprocess.TimeoutExpired as exc:
   timed_out=True; exit_code=None
   def decode(x): return x.decode('utf-8',errors='replace') if isinstance(x,bytes) else x or ''
   output=decode(exc.stdout)+'\n'+decode(exc.stderr)
  save(role_folder,'terminal_log.txt',output)
  execution=read(role_folder/'execution.json') if (role_folder/'execution.json').exists() else {}
  result={'role':role,'process_exit_code':exit_code,'timed_out':timed_out,'elapsed_seconds':round(time.perf_counter()-role_start,3),'status':execution.get('status'),'login_requests':execution.get('login_requests',0),'profile_requests':execution.get('profile_requests',0),'target_requests':execution.get('target_requests',0),'server_stopped':execution.get('server_stopped',False)}
  save(role_folder,'process_result.json',result); results.append(result); print(clean(json.dumps(result)),flush=True)
  if exit_code!=0 or timed_out: break
 result={'case':'IR-14','finished_at_utc':now(),'workers':results,'completed_worker_count':len(results),'total_HTTP_requests':sum(x[k] for x in results for k in ('login_requests','profile_requests','target_requests')),'target_requests':sum(x['target_requests'] for x in results),'elapsed_seconds':round(time.perf_counter()-started,3),'source_files_unchanged':before==code_hashes(),'original_database_main_file_unchanged':db_hash==digest(ROOT/'knowgap.db'),'prior_evidence_unchanged':all(digest(ROOT/name)==value for name,value in prior.items()),'evidence_directory':folder.relative_to(ROOT).as_posix(),'integrity_limit':'Main-file hash does not cover unrelated concurrent SQLite WAL writes','outcome':'Unassessed; awaiting review'}
 save(folder,'process_result.json',result); print(clean(json.dumps(result)),flush=True)
 return 0 if len(results)==len(ROLES) and all(x['process_exit_code']==0 and not x['timed_out'] for x in results) and all(result[k] for k in ('source_files_unchanged','original_database_main_file_unchanged','prior_evidence_unchanged')) else 1
if __name__=='__main__':
 parser=argparse.ArgumentParser(); parser.add_argument('--worker',type=Path); parser.add_argument('--role',choices=ROLES); parser.add_argument('--route-harness',action='store_true'); args=parser.parse_args()
 if args.worker:
  folder=args.worker.resolve()
  if not folder.is_relative_to((ROOT/'audit/evidence/IR-14').resolve()) or args.role is None or folder.name!=args.role: raise SystemExit('Invalid evidence path or role')
  raise SystemExit(worker(folder,args.role,args.route_harness))
 if args.role: raise SystemExit('--role requires --worker')
 raise SystemExit(parent(args.route_harness))
