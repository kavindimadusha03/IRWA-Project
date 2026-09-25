"""IR-12 only: bounded natural-query diagnostics and separately labelled branch fixtures.
Calls original retrieval/solution components locally; no HTTP requests or ticket submission.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,os,sqlite3,subprocess,sys,tempfile,time
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[key]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'; os.environ['HF_HUB_OFFLINE']='1'; os.environ['TRANSFORMERS_OFFLINE']='1'
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT)); os.chdir(ROOT)
from collect_baseline import clean,digest,code_hashes
QUERIES=[
 ('N01','My laptop battery is swelling after charging.'),
 ('N02','The laptop casing is cracked.'),
 ('N03','My laptop screen has a dark patch.'),
 ('N04','My laptop hinge is broken.'),
 ('N05','My laptop keyboard has a loose key.'),
 ('N06','The laptop battery no longer holds charge.'),
 ('N07','My laptop is hot after charging.'),
 ('N08','The computer makes a rattling sound.'),
 ('N09','My laptop battery is swollen after an update.'),
 ('N10','After an update my laptop case is bulging.'),
 ('N11','The screen flickers when the laptop starts.'),
 ('N12','My computer restarts unexpectedly.'),
 ('N13','My laptop is slow.'),
 ('N14','My printer queue is stuck.'),
 ('N15','What colour is the notebook?'),
 ('N16','The device makes a clicking noise.'),
]
CONTROL_QUERY='Boundary diagnostic note.'
CONTROL_RECORD={'source_id':'AUDIT-IR12-CONTROL','title':'Boundary diagnostic note','content':'Synthetic boundary diagnostic reference. This record supplies no troubleshooting action.','category':'','supported_os':'Any','source_type':'internal_kb','status':'approved'}
def now(): return datetime.now(timezone.utc).isoformat()
def save(folder,name,obj):
 text=obj if isinstance(obj,str) else json.dumps(obj,indent=2,ensure_ascii=False)
 (folder/name).write_text(clean(text)+'\n',encoding='utf-8',newline='\n')
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def worker(folder):
 state={'case':'IR-12','started_at_utc':now(),'stage':'setup','status':'Not ready','outcome':'Unassessed','natural_searches':0,'selected_solution_calls':0,'controlled_searches':0,'controlled_solution_calls':0,'http_requests':0,'ticket_requests':0}
 def progress(stage):
  state['stage']=stage; save(folder,'execution.json',state); print('IR-12 stage: '+stage,flush=True)
 try:
  temp=Path(tempfile.mkdtemp(prefix='knowgap-ir12-')); db=temp/'knowgap.db'; os.environ['DATABASE_URL']='sqlite:///'+db.as_posix(); state['isolated_database']=str(db)
  from app.config import get_settings
  cfg=get_settings(); low=cfg.uncertain_threshold; high=cfg.high_confidence_threshold
  if not 0<low<high: raise RuntimeError('Threshold ordering invalid; branch fixture precondition fails')
  state['configuration']={'uncertain_threshold':low,'high_threshold':high,'bm25_weight':cfg.hybrid_bm25_weight,'semantic_weight':cfg.hybrid_semantic_weight,'embedding_model':'all-MiniLM-L6-v2','llm_model':cfg.groq_model,'top_k':5,'thread_limit':1,'cached_model_only':True}
  baseline=read(ROOT/'audit/evidence/baseline/environment.json')
  state['effective_thresholds_match_baseline']=low==baseline['configuration']['uncertain_threshold'] and high==baseline['configuration']['high_threshold']
  save(folder,'effective_configuration.json',{'recorded_before_search_at_utc':now(),**state['configuration'],'source':'Actual get_settings() used by original agents; no settings overrides'})
  from app.services.llm import llm
  state['llm']={'configured_enabled':bool(llm.enabled),'attempts':0,'successful_returns':0,'error_types':[]}
  previous=read(ROOT/'audit/evidence/IR-01/run-20260921T194038486465Z/execution.json')
  if bool(llm.enabled)!=previous['llm']['configured_enabled']: raise RuntimeError('Provider mode changed from baseline; review before calls')
  progress('load original cached embedding model')
  from app.services.embeddings import get_model
  started=time.perf_counter(); get_model(); state['model_load_seconds']=round(time.perf_counter()-started,3)
  from app.database import create_db_and_tables,engine
  if Path(engine.url.database).resolve()!=db.resolve() or db.resolve()==(ROOT/'knowgap.db').resolve(): raise RuntimeError('Isolation check failed before any database write')
  from sqlmodel import Session
  from scripts.seed_db import seed_users,seed_kb,seed_historical_tickets
  create_db_and_tables()
  with Session(engine) as session: seed_users(session); seed_kb(session); seed_historical_tickets(session)
  snapshot=temp/'before_component_calls.sqlite'
  with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as src:
   src.execute('PRAGMA query_only=ON')
   with sqlite3.connect(str(snapshot)) as dst:
    src.backup(dst); integrity=dst.execute('PRAGMA integrity_check').fetchone()[0]
    counts={table:dst.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('knowledgearticle','ticket','user')}
  assert integrity=='ok' and counts=={'knowledgearticle':80,'ticket':500,'user':4}
  snapshot_hash=digest(snapshot); db_before=digest(db)
  save(folder,'isolated_database_backup.json',{'recorded_before_calls_at_utc':now(),'path':str(snapshot),'sha256':snapshot_hash,'integrity_check':integrity,'counts':counts,'outside_repository':not snapshot.resolve().is_relative_to(ROOT.resolve()),'method':'SQLite backup API from mode=ro seeded source'})
  from app.agents import retrieval_agent as ra,solution_agent as sa
  from app.services import hybrid_search as hs
  from app.services.bm25 import tokenize
  from rank_bm25 import BM25Okapi
  with Session(engine) as session: records=ra._records_from_db(session)
  with (ROOT/'data/knowledge_base.csv').open(encoding='utf-8-sig',newline='') as f: kb=list(csv.DictReader(f))
  with (ROOT/'data/tickets.csv').open(encoding='utf-8-sig',newline='') as f: tickets=list(csv.DictReader(f))
  expected=[{'source_id':r['doc_id'],'title':r['title'],'content':r['body'],'category':r['category'],'supported_os':r['supported_os'],'source_type':r['source_type'],'status':r['status']} for r in kb if r['status']=='approved']
  expected += [{'source_id':r['ticket_id'],'title':r['title'],'content':f"Problem: {r['description']}\nRoot cause: \nResolution: {r['resolution_notes']}",'category':r['ground_truth_category'],'supported_os':'Any','source_type':'resolved_ticket','status':'resolved'} for r in tickets if r['status']=='Resolved' and r['resolution_notes'].strip()]
  assert sorted(records,key=lambda r:r['source_id'])==sorted(expected,key=lambda r:r['source_id'])
  save(folder,'eligible_records.json',records)
  save(folder,'corpus_preflight.json',{'eligible_records':len(records),'matches_original_CSV_in_all_retrieval_fields':True,'approved_KB_rows':len(kb),'resolved_histories':len(expected)-len(kb),'source_files_unchanged':True,'scope':'Original synthetic corpus; no working-database rows or inserted source fixture. Branch control exists only in injected in-memory ranker output.'})
  current={}; context={'id':None,'kind':None}
  original_hybrid=ra.hybrid_rank; original_normalize=hs.normalize_query_for_search; original_dedup=hs._deduplicate_records; original_native=BM25Okapi.get_scores; original_trust=ra._trust_weight; original_meta=ra._metadata_boost; original_chat=llm.chat
  def observed_normalize(*args,**kwargs):
   result=original_normalize(*args,**kwargs); current['query_preprocessing']={'original':args[0] if args else kwargs.get('query'),'normalized':result,'tokens':tokenize(result)}; return result
  def observed_dedup(*args,**kwargs):
   result=original_dedup(*args,**kwargs); current['deduplicated_source_ids']=[i['source_id'] for i in result]; return result
  def observed_native(model,query):
   result=original_native(model,query); current['native_bm25']={'tokens':query,'scores':result.tolist(),'order':'deduplicated_source_ids'}; return result
  def observed_hybrid(*args,**kwargs):
   supplied=args[1] if len(args)>1 else kwargs.get('records',[])
   assert supplied==records
   result=original_hybrid(*args,**kwargs); current['hybrid_before_trust']=result; return result
  def observed_trust(record):
   result=original_trust(record); current.setdefault('trust_calls',[]).append({'source_id':record['source_id'],'trust':result}); return result
  def observed_meta(query,record):
   result=original_meta(query,record); current.setdefault('metadata_calls',[]).append({'source_id':record['source_id'],'query':query,'bonus':result}); return result
  def observed_chat(*args,**kwargs):
   call={'context':dict(context),'successful_return':False,'system_prompt':args[0] if args else kwargs.get('system_prompt'),'user_prompt':args[1] if len(args)>1 else kwargs.get('user_prompt')}; current.setdefault('llm_calls',[]).append(call); state['llm']['attempts']+=1
   try: response=original_chat(*args,**kwargs)
   except Exception as exc:
    call['error_type']=type(exc).__name__; state['llm']['error_types'].append(type(exc).__name__); raise
   call['successful_return']=True; call['response']=response; state['llm']['successful_returns']+=1; return response
  def expected_decision(score): return 'HIGH' if score>=high else 'UNCERTAIN' if score>=low else 'LOW'
  def get_solution(query,retrieval):
   solution=sa.recommend_solution(query,retrieval)
   calls=current.get('llm_calls',[])
   copied='\n\n'.join(f"Evidence source {x['source_id']} | {x['title']}\n{x['content']}" for x in retrieval['items'][:3])
   current['solution']=solution; current['provider_output_adopted']=bool(calls and calls[-1]['successful_return'] and solution['message']==calls[-1]['response'].strip()); current['message_equals_evidence_blocks']=solution['message']==copied
   current['recommendation_gate_matches']=solution['can_recommend']==(retrieval['decision']=='HIGH' and bool(retrieval['items']))
   current['routing_scope']='Direct component call only. Escalation wording is not persisted ticket state, queue visibility or human action.'
   return solution
  # Patch only observation wrappers during natural searches. Original arguments/returns preserved.
  with patch.object(hs,'normalize_query_for_search',observed_normalize),patch.object(hs,'_deduplicate_records',observed_dedup),patch.object(BM25Okapi,'get_scores',observed_native),patch.object(ra,'hybrid_rank',observed_hybrid),patch.object(ra,'_trust_weight',observed_trust),patch.object(ra,'_metadata_boost',observed_meta),patch.object(llm,'chat',observed_chat):
   progress('bounded natural-query screening: 16 fixed queries')
   natural=[]
   for ident,query in QUERIES:
    current={'id':ident,'kind':'natural_original_retrieval','query':query,'started_at_utc':now()}; context={'id':ident,'kind':current['kind']}
    start=time.perf_counter()
    with Session(engine) as session: retrieval=ra.search_knowledge(session,query,top_k=5)
    state['natural_searches']+=1
    current.update({'retrieval':retrieval,'expected_decision':expected_decision(retrieval['best_score']),'decision_matches':retrieval['decision']==expected_decision(retrieval['best_score']),'elapsed_seconds':round(time.perf_counter()-start,3)})
    natural.append(current); save(folder/'natural',ident+'.json',current)
   selections=[]
   for name,threshold in [('UNCERTAIN',low),('HIGH',high)]:
    for side in ('below','at_or_above'):
     candidates=[n for n in natural if (n['retrieval']['best_score']<threshold if side=='below' else n['retrieval']['best_score']>=threshold)]
     chosen=min(candidates,key=lambda n:(abs(n['retrieval']['best_score']-threshold),n['id'])) if candidates else None
     selections.append({'threshold_name':name,'threshold':threshold,'side':side,'id':chosen['id'] if chosen else None,'query':chosen['query'] if chosen else None,'score':chosen['retrieval']['best_score'] if chosen else None,'absolute_distance':abs(chosen['retrieval']['best_score']-threshold) if chosen else None,'within_predeclared_near_window_0_025':abs(chosen['retrieval']['best_score']-threshold)<=.025 if chosen else False})
   save(folder,'natural_selection.json',{'recorded_before_solution_calls_at_utc':now(),'rule':'Closest observed score per side of each threshold; tie by fixed query ID; no adaptive query rewriting or additional searches','near_window':.025,'selections':selections})
   selected_ids={x['id'] for x in selections if x['id']}
   progress('reviewable answers for selected natural queries')
   for n in natural:
    if n['id'] not in selected_ids: continue
    current=n; context={'id':n['id'],'kind':'natural_selected_solution'}
    get_solution(n['query'],n['retrieval']); state['selected_solution_calls']+=1
    save(folder/'natural',n['id']+'.json',current)
   save(folder,'natural_summary.json',[{'id':n['id'],'query':n['query'],'best_score':n['retrieval']['best_score'],'decision':n['retrieval']['decision'],'decision_matches':n['decision_matches'],'top_source':n['retrieval']['items'][0]['source_id'] if n['retrieval']['items'] else None,'selected_for_answer':n['id'] in selected_ids} for n in natural])
   # Controlled score fixtures: only hybrid_rank output is substituted, in memory.
   # Original SQL eligibility, trust, metadata, comparisons and solution function remain active.
   weight=original_trust(CONTROL_RECORD); bonus=original_meta(CONTROL_QUERY,CONTROL_RECORD)
   assert weight==1.0 and bonus==.08
   fixtures=[]
   for name,threshold in [('UNCERTAIN',low),('HIGH',high)]:
    for position,target in [('below',math.nextafter(threshold,-math.inf)),('equal',threshold),('above',math.nextafter(threshold,math.inf))]:
     ident=f'{name}_{position}'; pretrust=(target-bonus)/weight
     expected={'UNCERTAIN':{'below':'LOW','equal':'UNCERTAIN','above':'UNCERTAIN'},'HIGH':{'below':'UNCERTAIN','equal':'HIGH','above':'HIGH'}}[name][position]
     assert pretrust*weight+bonus==target
     fixtures.append({'id':ident,'kind':'CONTROLLED_SCORE_BRANCH_ONLY','query':CONTROL_QUERY,'record':CONTROL_RECORD,'threshold_name':name,'threshold':threshold,'position':position,'target_final':target,'target_hex':target.hex(),'injected_pretrust':pretrust,'injected_pretrust_hex':pretrust.hex(),'expected_trust':weight,'expected_metadata':bonus,'expected_decision':expected,'expected_can_recommend':expected=='HIGH','BM25_and_semantic_provenance':'Synthetic placeholder fields equal to injected pretrust; no native BM25 or embeddings calculated for these records'})
   save(folder,'controlled_inputs.json',{'recorded_before_controlled_calls_at_utc':now(),'scope':'Six in-memory ranker-output fixtures; never inserted in DB and not natural retrieval accuracy','inputs':fixtures})
   progress('six exact controlled boundary comparisons')
   for fixture in fixtures:
    current={'id':fixture['id'],'kind':'CONTROLLED_SCORE_BRANCH_ONLY','input':fixture,'stub_calls':0}; context={'id':fixture['id'],'kind':current['kind']}
    item={**CONTROL_RECORD,'bm25_score':fixture['injected_pretrust'],'semantic_score':fixture['injected_pretrust'],'hybrid_score':fixture['injected_pretrust'],'exact_error_match':False}
    def fixture_hybrid(query,supplied,top_k=5):
     assert query==CONTROL_QUERY and supplied==records and top_k==5
     current['stub_calls']+=1; current['injected_hybrid_output']=[dict(item)]; current['original_SQL_record_count_before_stub']=len(supplied); return [dict(item)]
    with patch.object(ra,'hybrid_rank',fixture_hybrid):
     with Session(engine) as session: retrieval=ra.search_knowledge(session,CONTROL_QUERY,top_k=5)
    state['controlled_searches']+=1
    solution=get_solution(CONTROL_QUERY,retrieval); state['controlled_solution_calls']+=1
    current.update({'retrieval':retrieval,'actual_final_hex':retrieval['best_score'].hex(),'actual_final_exactly_equals_target':retrieval['best_score']==fixture['target_final'],'decision_matches_expected':retrieval['decision']==fixture['expected_decision'],'recommendation_matches_expected':solution['can_recommend']==fixture['expected_can_recommend'],'synthetic_native_BM25':None,'synthetic_embedding_similarity':None})
    current['citation_gate_matches']=(len(solution['citations'])==1 and solution['source_id']==CONTROL_RECORD['source_id']) if fixture['expected_can_recommend'] else (not solution['citations'] and solution['source_id']=='')
    current['no_unexpected_LLM_call']=len(current.get('llm_calls',[]))==(1 if fixture['expected_can_recommend'] else 0)
    assert current['stub_calls']==1 and 'native_bm25' not in current
    save(folder/'controlled',fixture['id']+'.json',current)
  assert ra.hybrid_rank is original_hybrid and ra._trust_weight is original_trust and ra._metadata_boost is original_meta and llm.chat == original_chat and BM25Okapi.get_scores is original_native and hs._deduplicate_records is original_dedup and hs.normalize_query_for_search is original_normalize
  with Session(engine) as session: after=ra._records_from_db(session)
  with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as con:
   con.execute('PRAGMA query_only=ON'); after_counts={table:con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in counts}
  post={'eligible_records_unchanged':after==records,'row_counts_unchanged':counts==after_counts,'counts':after_counts,'seeded_database_main_file_unchanged':digest(db)==db_before,'private_snapshot_unchanged':digest(snapshot)==snapshot_hash,'all_monkeypatches_restored':True,'ticket_submissions':0,'HTTP_requests':0}
  save(folder,'postflight.json',post)
  assert all(post[key] for key in ('eligible_records_unchanged','row_counts_unchanged','seeded_database_main_file_unchanged','private_snapshot_unchanged','all_monkeypatches_restored'))
  state['status']='Executed; awaiting branch and answer review'; state['stage']='execution completed'; state['mode']='Direct local components, natural original ranking then controlled ranker-output fixtures; no HTTP/ticket workflow'
 except Exception as exc:
  import traceback
  state['status']='Execution error; review required'; state['error']={'type':type(exc).__name__,'message':str(exc)}; traceback.print_exc()
 finally:
  state['finished_at_utc']=now(); save(folder,'execution.json',state); print(clean(json.dumps(state)),flush=True)
 return 0 if state['status']=='Executed; awaiting branch and answer review' else 1

def parent():
 folder=ROOT/'audit/evidence/IR-12'/('run-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
 folder.mkdir(parents=True,exist_ok=False); (folder/'natural').mkdir(); (folder/'controlled').mkdir()
 before=code_hashes(); original_db=digest(ROOT/'knowgap.db'); baseline=read(ROOT/'audit/evidence/baseline/environment.json'); backup=read(ROOT/'audit/evidence/baseline/database_backup.json')
 prior={p.relative_to(ROOT).as_posix():digest(p) for name in ['baseline']+[f'IR-{i:02d}' for i in range(1,12)] for p in (ROOT/'audit/evidence'/name).rglob('*') if p.is_file()}
 backup_verified=Path(backup['path']).is_file() and digest(Path(backup['path']))==backup['backup_sha256']
 save(folder,'inputs.json',{'recorded_before_execution_at_utc':now(),'natural_queries':[{'id':ident,'query':q} for ident,q in QUERIES],'natural_search_limit':16,'no_adaptive_variants':True,'selection_rule':'Closest below and at/above each effective threshold, tie by query ID; selected unique queries get solution once using same saved actual retrieval','near_window':.025,'controlled_rule':'nextafter(threshold,-inf), exact threshold, nextafter(threshold,+inf) for both thresholds; pretrust computed by inversion of original trust/metadata','controlled_record':CONTROL_RECORD,'controlled_query':CONTROL_QUERY,'no_HTTP_or_ticket_requests':True})
 save(folder,'expected_result.md','\n'.join([
  '# IR-12 criteria fixed before execution','',
  '- Scope: direct original search_knowledge(session,query,top_k=5) and recommend_solution(query,retrieval) component calls on isolated original synthetic corpus; no HTTP authentication, ticket persistence or support routing exercised.',
  '- Record effective settings actually used, without secret values. Preserve application files, thresholds and weights.',
  '- Submit exactly the 16 inputs.json natural queries to original retrieval. No adaptive wording additions. Capture native BM25, normalization, semantic/pretrust/final scores, actual trust/metadata, full text and decisions for each.',
  '- Choose closest score below and at/above each threshold; deterministic tie by ID. Save selection before selected solution calls. Near means distance <=0.025; if none lies near a side report a search-coverage limitation, never claim exact natural-boundary coverage.',
  '- Natural branch PASS when actual decisions match effective >= HIGH, else >= UNCERTAIN, else LOW. Selected solution eligibility must match HIGH plus nonempty items; unavailable prerequisites are Inconclusive, not fabricated PASS.',
  '- Six controlled cases supply only in-memory hybrid_rank output. Keep original database read, trust, metadata, adjustment, comparisons and solution behavior. Use approved internal_kb, category empty, OS Any: trust1 and status bonus0.08. Source is not a real DB article.',
  '- Inputs saved before controlled calls: adjacent floating-point values below/equal/above each threshold. Derive pretrust from exact target minus actual bonus, not rounded constants. Require actual final == target and save float.hex; if adjustment misses target, fixture is invalid rather than branch FAIL.',
  '- Expected ordered branches: LOW/UNCERTAIN/UNCERTAIN at lower boundary; UNCERTAIN/HIGH/HIGH at upper boundary. Only two HIGH controls recommend, cite control source and attempt generation; remaining four return no source/citations and do not call LLM.',
  '- Primary branch PASS requires all valid natural and six boundary classifications and selected/controlled recommendation gates to match. FAIL is a valid mismatch. A HIGH classification does not excuse irrelevant/unsupported advice: review selected natural answers separately with a distinct PASS/FAIL/inconclusive grounding result.',
  '- Capture original solution result/provider adoption. Disabled Groq limits answer coverage to fallback. Escalation wording in this component test does not establish a saved ticket or real support-queue entry.',
  '- Synthetic BM25/semantic fields are placeholders only; no actual retrieval accuracy or calibrated probability claimed for branch fixtures. No threshold tuning, score ablation, repair, source write, security exploit claim or IR-13/later test.',
  '- Verify original private backup, snapshot seeded DB before component calls, preserve earlier evidence and verify original/seeded databases and source hashes after execution.',
 ]))
 save(folder,'preconditions.json',{'recorded_before_execution_at_utc':now(),'original_database_main_file_sha256':original_db,'production_source_sha256':before,'sources_match_baseline':before==baseline['source_sha256'],'database_matches_baseline':original_db==baseline['original_database_sha256'],'private_phase1_backup_verified':backup_verified,'scope':'Original project synthetic CSVs and seed users only; local temporary database; read-only component calls after seeding','prior_evidence_file_count':len(prior)})
 if before!=baseline['source_sha256'] or original_db!=baseline['original_database_sha256'] or not backup_verified:
  save(folder,'execution.json',{'status':'Not ready','reason':'Source/database/backup precondition failed','outcome':'Unassessed'}); print(str(folder)); return 1
 print('IR-12 evidence: '+str(folder),flush=True)
 command=[sys.executable,'-B',str(Path(__file__).resolve()),'--worker',str(folder)]; started=time.perf_counter(); timed_out=False
 try:
  run=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding='utf-8',errors='replace',timeout=300,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)); output=run.stdout+'\n'+run.stderr; exit_code=run.returncode
 except subprocess.TimeoutExpired as exc:
  timed_out=True; exit_code=None
  def decode(x): return x.decode('utf-8',errors='replace') if isinstance(x,bytes) else x or ''
  output=decode(exc.stdout)+'\n'+decode(exc.stderr)
 save(folder,'terminal_log.txt',output)
 result={'case':'IR-12','finished_at_utc':now(),'process_exit_code':exit_code,'timed_out':timed_out,'elapsed_seconds':round(time.perf_counter()-started,3),'source_files_unchanged':before==code_hashes(),'original_database_main_file_unchanged':original_db==digest(ROOT/'knowgap.db'),'prior_evidence_unchanged':all(digest(ROOT/name)==value for name,value in prior.items()),'evidence_directory':folder.relative_to(ROOT).as_posix(),'integrity_limit':'Main-file hash does not cover unrelated concurrent SQLite WAL writes','outcome':'Unassessed; awaiting review'}
 save(folder,'process_result.json',result); print(clean(json.dumps(result)),flush=True)
 return 0 if exit_code==0 and not timed_out and all(result[k] for k in ('source_files_unchanged','original_database_main_file_unchanged','prior_evidence_unchanged')) else 1
if __name__=='__main__':
 parser=argparse.ArgumentParser(); parser.add_argument('--worker',type=Path); args=parser.parse_args()
 if args.worker:
  folder=args.worker.resolve()
  if not folder.is_relative_to((ROOT/'audit/evidence/IR-12').resolve()): raise SystemExit('Invalid evidence path')
  raise SystemExit(worker(folder))
 raise SystemExit(parent())
