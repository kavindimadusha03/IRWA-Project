"""Record IR-09 draft-exclusion evidence; preserve original data and raw captures."""
from pathlib import Path
from datetime import datetime, timezone
import csv, hashlib, io, json, re
ROOT=Path(__file__).resolve().parents[2]; AUDIT=ROOT/'audit'
RUN=AUDIT/'evidence/IR-09/run-20260922T140938591791Z'; REL=RUN.relative_to(AUDIT).as_posix()
NAMES=('draft_probe','approved_control'); DID='AUDIT-IR09-DRAFT-001'; CID='AUDIT-IR09-CONTROL-001'
DM='quartzmeadow729'; CM='cobaltlantern463'; DW='violetcompassstamp'; CW='amberharborreceipt'
def read(name,folder=RUN): return json.loads((folder/name).read_text(encoding='utf-8'))
def write(path,text): path.write_text(text.rstrip()+'\n',encoding='utf-8',newline='\n')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def object_hash(obj): return hashlib.sha256(json.dumps(obj,sort_keys=True).encode('utf-8')).hexdigest()
def hashes(folder): return {p.relative_to(ROOT).as_posix():sha(p) for p in folder.rglob('*') if p.is_file()}
prior={name:hashes(AUDIT/'evidence'/name) for name in ('baseline','IR-01','IR-02','IR-03','IR-04','IR-05','IR-06','IR-07','IR-08')}; raw_before=hashes(RUN)
p=read('process_result.json'); fixtures=read('fixtures.json')['fixtures']; pre=read('preconditions.json')
assert p['ticket_requests']==2 and len(p['subcases'])==2 and p['source_files_unchanged'] and p['original_database_main_file_unchanged']
assert pre['private_phase1_backup_verified'] and not any(read('source_preflight.json')['original_marker_collisions'].values())
keys=('input','execution','analysis','query_preprocessing','eligible_records','eligible_corpus','hybrid_before_trust','retrieval','solution','ticket','fixture_preflight','fixture_postflight','isolated_database_backup','trust_preflight','actual_trust_calls','leakage_checks','process_result','support_queue_check')
cases={name:{key:read(key+'.json',RUN/name) for key in keys} for name in NAMES}
base=cases['draft_probe']; rows=[]; fixture_hashes=[]
for name,case in cases.items():
 e=case['execution']; r=case['retrieval']; s=case['solution']; t=case['ticket']; c=case['eligible_corpus']; records=case['eligible_records']; n=case['query_preprocessing']; leak=case['leakage_checks']; q=case['support_queue_check']; proc=case['process_result']; backup=case['isolated_database_backup']
 assert e['ticket_requests']==1 and e['http']['ticket_page']==200 and e['http']['ticket_create']['status']==303 and e['server_stopped']
 assert proc['process_exit_code']==0 and not proc['timed_out'] and proc['source_files_unchanged'] and proc['original_database_main_file_unchanged']
 assert e['fixture_counts']=={'articles':82,'historical_tickets':500}
 assert e['configuration']==base['execution']['configuration'] and not e['llm']['configured_enabled'] and e['llm']['successful_chat_returns']==0
 assert case['fixture_preflight']['fixtures']==case['fixture_postflight']['fixtures']==fixtures
 assert case['fixture_postflight']['fields_and_statuses_unchanged'] and case['fixture_postflight']['private_snapshot_unchanged']
 assert backup['integrity_check']=='ok' and backup['outside_repository'] and sha(Path(backup['path']))==backup['sha256']
 assert backup['fixture_statuses']=={DID:'draft',CID:'approved'}
 assert len(records)==c['eligible_record_count']==428 and c['matches_original_approved_resolved_plus_approved_control']
 assert records==base['eligible_records'] and c['eligible_corpus_sha256']==base['eligible_corpus']['eligible_corpus_sha256']
 assert c['approved_control_present'] and not c['draft_id_present'] and not c['draft_marker_present'] and not c['draft_witness_present']
 assert DID not in c['eligible_source_ids'] and CID in c['eligible_source_ids']
 assert all(i['status'] in ('approved','resolved') for i in records)
 assert not any(leak[k] for k in ('draft_id_in_raw_shortlist','draft_id_in_final_ranking','draft_id_in_solution_citations','draft_id_in_stored_citations','draft_witness_in_recommendation','draft_witness_in_customer_HTML','draft_source_id_in_customer_HTML','draft_marker_in_recommendation'))
 assert t['source_used']!=DID and n['marker_preserved_in_normalized_query']
 marker=case['input']['description']
 assert marker==t['description']==t['masked_description']==t['canonical_issue']==n['original_query']==n['normalized_query']
 assert {v['source_id']:v['trust_weight'] for v in case['trust_preflight']['values']}=={DID:0.0,CID:1.0}
 assert not any(v['source_id']==DID for v in case['actual_trust_calls'])
 assert next(v['trust_weight'] for v in case['actual_trust_calls'] if v['source_id']==CID)==1.0
 assert q['page_status']==200 and t['approval_status']=='PENDING'
 fixture_hashes.append({'case':name,'before_fields_sha256':object_hash(case['fixture_preflight']['fixtures']),'after_fields_sha256':object_hash(case['fixture_postflight']['fixtures']),'all_fixture_fields_equal':True,'private_snapshot_hash_verified_at_review':True})
 if name=='draft_probe':
  assert r['decision']=='LOW' and not s['can_recommend'] and t['status']=='ESCALATED' and t['source_used']==''
  assert not s['citations'] and not t['citations'] and q['ticket_resolve_form_present'] and q['exact_description_present']
 else:
  assert r['items'][0]['source_id']==CID and r['decision']=='HIGH' and s['can_recommend'] and t['status']=='SOLUTION_PROPOSED'
  assert leak['approved_control_cited'] and leak['approved_control_witness_in_recommendation'] and not q['ticket_resolve_form_present']
  assert s['message']=='\n\n'.join(f"Evidence source {i['source_id']} | {i['title']}\n{i['content']}" for i in r['items'][:3])
  assert [i['source_id'] for i in s['citations']]==[CID,'SYN-0001','KB-002']
 assert t['recommended_solution']==s['message']
 rows.append({'case':name,'query':marker,'eligible_record_count':len(records),'draft_in_corpus':False,'draft_in_ranking_or_citations':False,'draft_witness_in_recommendation':False,'approved_control_in_corpus':True,'control_rank':next((idx for idx,i in enumerate(r['items'],1) if i['source_id']==CID),None),'best_score':r['best_score'],'decision':r['decision'],'cited_source_ids':[i['source_id'] for i in s['citations']],'stored_status':t['status'],'approval':t['approval_status'],'support_queue_visible':q['ticket_resolve_form_present'],'draft_status_after':'draft','approved_status_after':'approved','outcome':'PASS','llm_successes':e['llm']['successful_chat_returns'],'process_seconds':proc['elapsed_seconds']})
write(RUN/'comparison.json',json.dumps({'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'case':'IR-09','outcome':'PASS (draft exclusion and approved control)','cases':rows,'fixture_integrity':fixture_hashes,'separate_quality_observation':'Approved control answer also copies unrelated low-score VPN sources; no draft leakage'},indent=2))
output=io.StringIO(newline=''); fields=list(rows[0]); writer=csv.DictWriter(output,fieldnames=fields,lineterminator='\n'); writer.writeheader()
for row in rows: writer.writerow({k:json.dumps(v) if isinstance(v,list) else v for k,v in row.items()})
write(RUN/'comparison.csv',output.getvalue())
review={'review_recorded_at_utc':datetime.now(timezone.utc).isoformat(),'case':'IR-09','status':'Completed (isolated fixtures; fallback mode)','outcome':'PASS','vulnerability_identified':'NO demonstrated security vulnerability','criteria':[
 {'name':'Draft excluded before ranking','outcome':'PASS','evidence':'Both actual 428-record corpora exclude draft ID, marker and witness; approved control present'},
 {'name':'Draft absent from ranked/cited/recommended evidence','outcome':'PASS','evidence':'No draft ID/content witness in raw shortlist, final ranking, stored or solution citations, recommendation or customer HTML'},
 {'name':'Approved control remains eligible and retrievable','outcome':'PASS','evidence':'Control first for own query at 0.8533253620, cited with response witness'},
 {'name':'Fixtures remain unchanged and backed up','outcome':'PASS','evidence':'Draft remains draft and control approved; all stored fields equal; pre-request snapshots integrity ok and hashes preserved'},
 {'name':'Auxiliary trust helper values','outcome':'PASS (pure diagnostic)','evidence':'Draft 0.0 and approved 1.0; draft never reaches actual ranking trust calls'}],
 'separate_observation':'OBS-IR09-01: low-scoring unrelated VPN sources copied into approved-control recommendation. Confirmed quality defect; does not constitute draft leakage or overturn the exclusion result.',
 'security_assessment':'No unapproved-source use, approval bypass, disclosure or executed harmful action demonstrated. Primary source-status boundary held. No formal VULN entry.',
 'severity':'No vulnerability severity for passed exclusion case; separate quality observation Informational on demonstrated security-impact scale',
 'limitations':['Two queries with fixed synthetic markers and fixtures on one ticket path','Fixture statuses set during isolated setup, not approval-route testing','Direct hybrid_rank callers with arbitrary records and other retrieval routes were not tested','Groq disabled; template/evidence fallback only','No production deployment, device repair or actual human response','IR-10 through IR-15 unexecuted']}
write(RUN/'review.json',json.dumps(review,indent=2))
control=cases['approved_control']; notes=[
 '# IR-09 - Draft / Unapproved KB Exclusion','',
 '**Outcome: PASS for draft exclusion and the approved control on the tested ticket workflow.** The draft was absent from the complete eligible corpus before ranking and from all ranked/cited/recommended evidence in both runs. The control remained eligible and was retrieved and cited for its own marker. A separate unrelated-VPN recommendation defect was observed in the control answer and is documented below.','',
 '## Objective and exact input','',
 'Verify that unreviewed draft knowledge is not treated as approved retrieval evidence. Use one harmless unique draft marker and a separate approved positive control.','',
 '| Subcase | Exact description | Length | Title |','|---|---|---:|---|',
 f'| draft_probe | `{DM}` | {len(DM)} | Audit reference lookup |',
 f'| approved_control | `{CM}` | {len(CM)} | Audit reference lookup |','',
 'Both markers exceed the route minimum and survive masking, canonicalization and normalization unchanged. Each was submitted exactly once, with both fixtures present in each fresh database. The paired queries use identical eligible records, settings and source code; they are not a matched-score or relative-authority experiment.','',
 '## Fixed fixtures and backups','',
 '| Field | Draft | Approved control |','|---|---|---|',
 f'| Source ID | {DID} | {CID} |',
 '| Title | Draft lookup quartzmeadow729 | Approved lookup cobaltlantern463 |',
 '| Status before / after | draft / draft | approved / approved |',
 '| Source type | internal_kb | internal_kb |',
 '| Authoritative flag | true | true |',
 '| Category / OS | Audit / Lookup / Any | Audit / Lookup / Any |',
 '| Response-only witness | violetcompassstamp | amberharborreceipt |','',
 'Both author fields are IR-09 synthetic audit fixture, security class internal, and creation/update metadata 2026-09-22. These are synthetic setup values, not proof of an approval workflow or validated support advice. The draft remains excluded despite its internal_kb type and authoritative flag. This is the tested configuration, not a broad metadata-attack matrix.','',
 'Draft body:','',f"> {fixtures[0]['content']}",'',
 'Approved body:','',f"> {fixtures[1]['content']}",'',
 'All four unique marker/witness strings were absent from the original CSVs before setup. The response-only witnesses were not submitted in either query. The two new records exist only in temporary synthetic databases. Original articles, CSVs, app behavior and working knowgap.db were not modified.','',
 'The existing private working-DB backup was verified. Each isolated database was also snapshotted with sqlite3.Connection.backup from a read-only source after seeding and before requests; PRAGMA integrity_check returned ok. Both snapshot files remain private outside the repository, with only metadata/hashes in evidence. All fixture fields/statuses and snapshot hashes were checked after execution and at review.','',
 'The documented backup command is `python -B audit/scripts/collect_baseline.py backup`. IR-09 independently creates its own before_requests.sqlite snapshots; it does not overwrite the earlier backup evidence.','',
 '## Criteria declared before requests','',
 '- PASS: draft absent from the entire actual eligible corpus, both ranking stages, selected source/citations and recommendation content; approved control remains eligible and is retrieved by its own query.',
 '- FAIL: valid execution includes or recommends the draft as authoritative evidence, or excludes the approved control. A control retrieval miss with correct eligibility would be reported separately, not invented draft leakage.',
 '- Inspect actual pre-ranking records; absence from top-k alone is insufficient. Pure trust=0 output is a separate check and does not prove exclusion.',
 '- Distinguish legitimate query echo in description/history/UI from source leakage using the draft ID, response-only witness and content/attribution.',
 '- Missing backup, model, login, fixture or query prerequisites would mean Not ready/Inconclusive. Preserve status throughout; no approving the draft or fixing code during the test.','',
 '## Preconditions and procedure','',
 'Each database held 82 articles (80 original approved articles plus one draft and one approved control), 500 historical tickets and active synthetic CUSTOMER/IT_SUPPORT accounts. The actual eligible corpus contained 81 approved articles and 347 resolved tickets: 428 records. No original working-database rows were copied.','',
 f"Both full eligible-corpus hashes: `{base['eligible_corpus']['eligible_corpus_sha256']}`. The saved seven-field records exactly match the original CSV-derived approved/resolved records plus the control, with the draft excluded.",'',
 'Settings matched earlier cases: all-MiniLM-L6-v2 cached model, BM25/semantic 0.45/0.55, HIGH=0.68, UNCERTAIN=0.55, top-k=5 and one numerical-library thread. Groq model setting llama-3.1-8b-instant; Groq disabled.','',
 '1. Saved exact markers, fixtures, uniqueness check and expected_result.md before requests.',
 '2. Loaded the cached model, verified database isolation, seeded both fixtures and the original synthetic corpus, checked statuses and created a private consistent snapshot.',
 '3. Started an owned loopback server and logged in normally as CUSTOMER.',
 '4. Submitted the subcase once; observed original analysis, full eligible corpus, preprocessing, rankings, trust calls and solution results without changing arguments/results.',
 '5. Saved ticket/citations and actual customer HTML; logged in as IT_SUPPORT and read the queue.',
 '6. Verified unchanged fixture fields and backups, stopped each server and compared application/source/main-database hashes. No approval, resolution, manual escalation or repair was performed.','',
 'Reproduction command (already run; a rerun creates new evidence and temporary databases):','',
 '~~~powershell',r'.\.venv\Scripts\python.exe -B audit\scripts\run_ir09.py','~~~','',
 'Both sequential local servers used POST http://127.0.0.1:8001/tickets/create and GET /tickets/501. Each TCK-00501 belongs to its own isolated DB. Health 200, CUSTOMER login 303 to /home, home 200, creation 303, ticket page 200, IT_SUPPORT login 303 and support page 200 in both runs. Both servers stopped. Passwords, cookies and access tokens are not recorded.','',
 '## Results','',
 '| Check | Draft-marker query | Approved-control query |','|---|---|---|',
 '| Marker preserved into retrieval | Yes | Yes |',
 '| Draft in full corpus / rankings / citations | Absent / absent / absent | Absent / absent / absent |',
 '| Draft witness in recommendation or customer HTML | Absent | Absent |',
 '| Approved control eligible / rank | Yes / 1 | Yes / 1 |',
 '| Best score / decision | 0.2510261122 / LOW | 0.8533253620 / HIGH |',
 '| Citation count | 0 | 3 |',
 '| Stored state / approval | ESCALATED / PENDING | SOLUTION_PROPOSED / PENDING |',
 '| Support queue | Present | Absent |',
 '| Draft status after query | draft | draft |',
 '| Primary outcome | PASS | PASS |','',
 'The control can appear as a weak semantic candidate for the unrelated draft marker without revealing draft content. Its draft-query BM25 score is zero, and the LOW result suppresses recommendations/citations. The query marker appears in the customer description/history, as expected; its absence is not the confidentiality criterion. The unsubmitted draft witness and draft ID are absent from the page and answer.','',
 '## Complete ranked results','']
for name,case in cases.items():
 notes += [f'### {name}','', '| Rank | Source | Status | BM25 | Semantic | Raw hybrid | Final score | Cited |','|---|---|---|---:|---:|---:|---:|---|']
 raw={i['source_id']:i for i in case['hybrid_before_trust']}; cited={i['source_id'] for i in case['solution']['citations']}
 for idx,item in enumerate(case['retrieval']['items'],1):
  notes.append(f"| {idx} | {item['source_id']} | {item['status']} | {item['bm25_score']:.6f} | {item['semantic_score']:.6f} | {raw[item['source_id']]['hybrid_score']:.6f} | {item['hybrid_score']:.10f} | {'Yes' if item['source_id'] in cited else 'No'} |")
 notes += ['', 'Actual final message:','', '~~~text',case['solution']['message'],'~~~','', 'Actual explanation:','', '> '+case['solution']['explanation'],'', 'Actual suggested reply:','', '> '+case['solution']['suggested_reply'],'']
notes += [
 '## Exclusion mechanism and trust diagnostics','',
 '`_records_from_db()` selects KnowledgeArticle.status == approved before constructing the records sent to hybrid_rank (`app/agents/retrieval_agent.py:56-71`). Only RESOLVED tickets with resolution notes are added. The actual full corpus capture establishes exclusion before deduplication, BM25, embeddings and top-k. The draft did not merely receive a low rank.','',
 '`_trust_weight()` checks draft status before the internal_kb rule (`app/agents/retrieval_agent.py:43-52`). Direct calls to the original helper on the declared fixture records returned draft=0.0 and control=1.0; these are labelled pure diagnostics. Actual search trust calls included the control at 1.0 and never included the draft. Therefore the runtime exclusion conclusion rests on the database filter and actual corpus evidence, not on executing a draft-weight branch during ranking.','',
 '`search_knowledge()` multiplies the hybrid score by trust and then adds metadata (`:101`). A zero trust multiplier alone is not a guarantee that an arbitrary supplied record cannot receive a metadata bonus. No alternate direct-ranker path was tested here; the observed ticket path excludes the draft earlier.','',
 'For the control marker, `(0.45*1 + 0.55*0.5878642946)*1 + 0.08 = 0.8533253620`. For the draft marker, the weak control candidate receives `(0.45*0 + 0.55*0.3109565676)*1 + 0.08 = 0.2510261122`. Category/OS bonuses and exact-code boosts do not explain either control score. These are descriptive values, not probabilities or an IR-10 trust comparison.','',
 'The LOW draft probe triggers recommend_solution() template escalation, so no source is proposed and no citations are stored. The ticket is visible in the normal authenticated support queue, still unassigned. Queue visibility is not human acknowledgment or completed assistance.','',
 '## Separate quality observation: unrelated secondary advice','',
 '**OBS-IR09-01:** the approved control is correctly retrieved, but its HIGH best score causes recommend_solution() to include the first three results. SYN-0001 (0.1656920711) and KB-002 (0.1655982335) are unrelated VPN sources; each has BM25=0 and a score far below UNCERTAIN 0.55. The marker query describes no VPN fault. Their VPN profile/update guidance nevertheless appears verbatim in the answer, and the template calls all three sources validated and tells the user to follow troubleshooting steps.','',
 'This is a confirmed relevance/applicability defect in this synthetic control response, consistent with earlier first-three-source observations. The fallback text is copied from eligible approved/resolved sources, not invented or leaked from the draft. The control body explicitly says it is not a device repair. The source-status exclusion PASS does not certify the relevance or safety of all recommended actions.','',
 'Impact: unnecessary VPN profile changes or delayed triage would be possible if the advice were followed, but no action or real harm occurred. Likelihood: observed once with this control marker; general prevalence is unmeasured. Severity: Informational on the demonstrated security-impact scale; no exploit-risk score or formal VULN entry. Suggested mitigation: after approval, validate each cited action against the actual request, avoid copying irrelevant low-score results simply to fill three slots, and use accurate source/uncertainty wording. No application fix applied.','',
 '## Security assessment, limits and conclusion','',
 '- Vulnerability identified: NO demonstrated unapproved-source use, approval bypass, data exposure or security exploit. The primary source-status boundary held in both cases.',
 '- Primary impact/severity: no adverse exclusion failure observed; no vulnerability severity assigned. The separate answer-quality defect remains documented above.',
 '- Likelihood/generalization: two queries, one fixed draft/control fixture pair and one normal ticket route. No production prevalence or universal exclusion claim.',
 '- Groq limitation: configured disabled; draft probe has one failed analysis attempt and no solution-generation attempt, control has two failed attempts. Zero successful provider returns. Results apply to rule/template/evidence fallback.',
 '- Scope limitation: statuses were set in isolated setup, not through an approval route. No malicious status mutation, alternate API/direct-ranker caller, every non-approved status, live generated answer or IR-10 authority comparison was tested.',
 '- Data/environment: small synthetic dataset, local servers, no real user data, no actual human response or device repair. Private snapshots stay outside the repository.',
 '- Recommended retention: preserve the approved-only database filter and keep regression coverage for draft/control exclusion when implementation changes. The direct helper result does not replace corpus-level evidence.','',
 '## Evidence index','',
 '| Files | Evidence |','|---|---|',
 '| inputs.json / fixtures.json / expected_result.md | Exact predeclared queries, fixtures and PASS/FAIL rules |',
 '| source_preflight.json / preconditions.json / comparison_preflight.json | Marker uniqueness, source hashes, working-DB backup and settings assumptions |',
 '| Each subcase: fixture_preflight.json / isolated_database_backup.json / fixture_postflight.json | Stored status/content before/after and private consistent snapshots |',
 '| Each subcase: analysis.json / query_preprocessing.json | Actual marker survival through input processing |',
 '| Each subcase: eligible_records.json / eligible_corpus.json | Complete observed pre-ranking corpus and equality checks |',
 '| Each subcase: trust_preflight.json / actual_trust_calls.json | Pure helper diagnostics separately from runtime trust calls |',
 '| Each subcase: hybrid_before_trust.json / retrieval.json / solution.json / ticket.json / leakage_checks.json | Rankings, decisions, full answers, citations and draft-leakage checks |',
 '| Each subcase: customer_result.html / support_queue.html / support_queue_check.json | Actual HTTP responses and normal support-queue observation |',
 '| Each subcase: execution.json / terminal_log.txt / process_result.json | One request, timings, LLM mode, server stop and integrity |',
 '| comparison.json / comparison.csv / review.json / notes.md | Separate derived comparison and reviewed verdict |','',
 'HTML files are actual saved responses, not screenshots. Raw worker status remains awaiting review; review.json provides the later verdict. All prior evidence and raw current captures remain unchanged. Application/data/evaluation/test and working-database main-file hashes match baseline; main-file hashes do not cover unrelated concurrent WAL writes. The helper never writes the working database.','',
 '**Conclusion:** IR-09 passes draft exclusion and approved-control availability for this ticket path. A separate secondary-source recommendation defect is recorded without claiming a draft leak or security exploit. IR-10 through IR-15 remain unexecuted; stop before IR-10.','']
write(RUN/'notes.md','\n'.join(notes))
record=[
 '## IR-09 - Draft / Unapproved KB Exclusion','',
 '- Test ID: IR-09','- Test Name: Draft / Unapproved KB Exclusion',
 '- Test Objective: Verify that a stored draft is excluded from authoritative retrieval/recommendations while an approved control remains available.',
 '- Component Being Tested: _records_from_db(), _trust_weight(), search_knowledge(), hybrid_rank(), recommend_solution(), ticket/citation persistence and customer/support output.',
 '- Input / Attack Scenario: Exact draft marker quartzmeadow729 and approved marker cobaltlantern463, once each, same title Audit reference lookup. Response-only witnesses violetcompassstamp and amberharborreceipt distinguish source use from query echo.',
 '- Preconditions: Same draft/control pair in two freshly seeded temporary databases; both source_type=internal_kb and authoritative=true but different statuses. Unique markers absent from original CSVs, source/config unchanged, private working-DB backup verified and both isolated DBs snapshotted before requests; Groq disabled.',
 '- Steps: Save inputs/fixtures/criteria; verify statuses/backups; normal CUSTOMER login and one query each; capture full eligible corpus, original preprocessing/rankings/trust calls/answer and persisted citations; read support queue; verify fixture fields/snapshot hashes, stop servers and check source/database integrity.',
 '- Expected Behaviour: Draft absent before ranking and from rankings, selected source/citations and recommendation content; approved control eligible and retrievable. Pure trust=0 and absence from top-k alone are insufficient proof.',
 '- Actual Behaviour: Both corpora contain identical 428 approved/resolved records including control and excluding draft. No draft ID or response witness in rankings/citations/recommendations/HTML. Draft query LOW 0.2510261122, ESCALATED/PENDING, no citations and visible support queue. Control first at HIGH 0.8533253620, cited with witness, SOLUTION_PROPOSED/PENDING. Fixture fields/statuses unchanged.',
 f'- Evidence: [{REL}/notes.md]({REL}/notes.md), full eligible-record captures, pre/post fixture metadata, backup checks, both original output sets, comparison JSON/CSV and reviewed verdict.',
 '- Observation: Draft exclusion demonstrated before deduplication/ranking; query echo is not source leakage. Pure trust diagnostic draft=0.0/control=1.0; no actual draft trust call. OBS-IR09-01 separately records unrelated low-score VPN guidance in the approved-control answer.',
 '- Outcome: PASS for source-status exclusion and the positive control in the tested ticket/fallback path.',
 '- Vulnerability Identified: NO demonstrated draft-source use, approval bypass or security exploit. Separate confirmed recommendation-relevance defect.',
 '- Impact: No draft-derived content reached recommendation output. Unnecessary VPN changes from unrelated control advice are possible if followed, but no action or harm observed.',
 '- Likelihood: Exclusion observed in two controlled queries; unrelated advice in one control query. No broader prevalence estimate.',
 '- Severity: No vulnerability severity for the passed boundary; separate quality observation Informational on demonstrated security-impact scale.',
 '- Technical Explanation: SQL eligibility filter selects approved articles before ranking. Draft status takes precedence in the pure trust helper. Control best score alone triggers first-three fallback, including unrelated secondary VPN sources around 0.1656.',
 '- Recommended Mitigation: Retain the approved-only filter and source-status regression coverage; after approval, assess relevance of each included source/action rather than copying a fixed three solely because top1 is HIGH. No fix applied.',
 '- Conclusion: Draft exclusion passes without certifying every recommendation or alternate retrieval route. Groq disabled and source statuses were isolated setup metadata. IR-10 through IR-15 unexecuted.',
]
for name,area in [('test_results.md','Source approval'),('test_plan.md','Source reliability: unapproved exclusion')]:
 path=AUDIT/name; text=path.read_text(encoding='utf-8')
 text=text.replace('IR-09 through IR-15 remain Not run.','IR-09 passed draft exclusion with an approved control; unrelated secondary advice is documented separately. IR-10 through IR-15 remain Not run.',1)
 text,count=re.subn(r'^\| IR-09 \|.*$',f'| IR-09 | {area} | Completed (isolated fixtures/fallback) | [{REL}/notes.md]({REL}/notes.md) | PASS (draft exclusion/control) | NO demonstrated; separate quality observation |',text,flags=re.M); assert count==1
 if name=='test_results.md':
  text,count=re.subn(r'^## IR-09[^\n]*\n.*?(?=^## IR-10)',lambda m:'\n'.join(record)+'\n\n',text,flags=re.M|re.S); assert count==1
 write(path,text)
path=AUDIT/'README.md'; text=path.read_text(encoding='utf-8')
text=text.replace('the completed IR-01, IR-02, IR-04, IR-05, IR-06, IR-07 and IR-08 cases','the completed IR-01, IR-02 and IR-04 through IR-09 cases')
text=text.replace('- evidence/IR-01/ through evidence/IR-08/: actual case evidence, including the isolated formatting fixture; IR-09 through IR-15 remain reserved.','- evidence/IR-01/ through evidence/IR-09/: actual case evidence, including isolated formatting and draft/control fixtures; IR-10 through IR-15 remain reserved.')
text=text.replace('IR-09 through IR-15 remain Not run.',f'IR-09 passed draft exclusion and approved-control availability; unrelated secondary advice is a separate quality observation. See [{REL}/notes.md]({REL}/notes.md). IR-10 through IR-15 remain Not run.')
write(path,text)
path=AUDIT/'evidence/README.md'; text=path.read_text(encoding='utf-8')
text=text.replace('IR-09/ through IR-15/ contain placeholders only.',f'IR-09/{RUN.name}/ contains the draft/control exclusion PASS, full eligible corpora, pre/post fixture status and private snapshot checks; unrelated control-answer advice is separately documented. IR-10/ through IR-15/ contain placeholders only.')
write(path,text)
additions={
 'vulnerability_register.md':f'''## IR-09 review

IR-09 passes draft-source exclusion and the approved positive control. The draft is absent from the entire actual corpus before ranking and from recommendation/citation output in both requests; statuses remain unchanged. No source-status bypass, draft leakage or formal VULN entry is established. See [{REL}/notes.md]({REL}/notes.md).

A separate answer-quality observation is recorded without changing the exclusion verdict:

- Observation ID: OBS-IR09-01.
- Title: Irrelevant low-score VPN evidence copied into a marker-lookup recommendation.
- Related test / component: IR-09 approved control; recommend_solution() first-three selection and template framing.
- Description: a valid approved marker hit at 0.8533253620 caused HIGH and inclusion of SYN-0001 and KB-002 at 0.1656920711 and 0.1655982335. Their VPN update/profile advice is unrelated to the marker query and neither contains the marker. The control fixture itself says it is not a device repair.
- Evidence: approved_control/retrieval.json, solution.json, ticket.json and customer_result.html in the linked run. All advice is copied from eligible sources; no draft content is used.
- Impact: unnecessary VPN profile changes or delayed triage are possible if the advice is followed. No repair, actual disruption, data exposure or compromise was observed.
- Likelihood: one observed control response; broader prevalence unmeasured.
- Severity: Informational on demonstrated security-impact scale; confirmed relevance/applicability defect without a security vulnerability severity.
- Risk level: no formal exploit-risk score; downstream harm unproven.
- Technical explanation: HIGH is based on the best score; solution fallback copies the first three records without an individual applicability gate and calls them validated.
- Recommended mitigation: after approval, validate each action/source against the request and omit unrelated low-relevance sources; use accurate confidence/provenance wording.
- Status: documented; no application fix applied.

The independent trust diagnostic returns draft=0 and control=1, but no draft entered actual trust calls. The exclusion evidence is the SQL eligibility boundary and full runtime corpus, not a zero multiplier. This test did not exercise draft approval, alternate API/direct-ranker inputs or IR-10 relative-authority comparisons.
''',
 'risk_matrix.md':f'''## IR-09 assessment

Draft exclusion and approved-control availability passed on the normal ticket path. No vulnerability matrix entry is created. OBS-IR09-01 documents unrelated secondary VPN advice in the control response, with possible unnecessary changes if followed but no executed action or demonstrated security harm. No exploit-risk product is assigned. See [{REL}/notes.md]({REL}/notes.md).
''',
 'viva_notes.md':'''## IR-09 observed result

Draft exclusion passed. I seeded one draft and one approved control into each isolated synthetic database, verified their statuses, created private snapshots and queried each unique marker once. The draft was absent from all 428 actual eligible records before ranking, and its ID and response-only witness never appeared in recommendations or citations. Its query returned LOW 0.2510261122 and reached the IT Support queue. The approved marker returned its control first at HIGH 0.8533253620 and included its witness in the answer. Neither article changed status or content.

The full corpus matters: missing top-k output alone could mean poor ranking rather than exclusion. Likewise, draft trust=0 was a separate pure-helper check; the actual query excluded the draft before ranking. Echoing the user marker in their description was expected and not a draft-source leak.

The control answer still copied unrelated VPN sources around 0.1656 because the top hit made the first-three fallback run. I recorded this as a separate relevance defect, not draft leakage or a demonstrated exploit. Source approval and answer applicability are different checks. Groq was disabled, no repair was executed and IR-10 was not run.
''',
 'commands.md':f'''## IR-09 reproduction after explicit case authorization

~~~powershell
.\\.venv\\Scripts\\python.exe -B audit\\scripts\\run_ir09.py
~~~

Submits the draft marker and approved-control marker once each using two fresh temporary databases with identical original synthetic data plus the same fixture pair. Verifies the private working-DB backup and creates an integrity-checked private snapshot of each seeded test DB before its request. Records full eligible corpora, unchanged statuses, original rankings/answers/citations and response-only leakage checks. No draft is approved; working data/source stays unchanged; servers stop after capture. A rerun creates new evidence; read [{REL}/notes.md]({REL}/notes.md) for the completed result. IR-10 and later cases are not executed.
''',
}
for name,addition in additions.items():
 path=AUDIT/name; text=path.read_text(encoding='utf-8')
 if addition.splitlines()[0] not in text: write(path,text.rstrip()+'\n\n'+addition)
assert all(hashes(AUDIT/'evidence'/name)==before for name,before in prior.items())
current=hashes(RUN); assert all(current[name]==value for name,value in raw_before.items())
print('IR-09 draft-exclusion PASS recorded; unrelated-advice observation separate. Prior/raw evidence unchanged; IR-10 through IR-15 unexecuted.')
