"""Record the completed IR-10 run without rerunning retrieval or changing raw evidence."""
from pathlib import Path
from datetime import datetime, timezone
import csv, hashlib, io, json, re
ROOT=Path(__file__).resolve().parents[2]; AUDIT=ROOT/'audit'
RUN=AUDIT/'evidence/IR-10/run-20260922T143655875673Z'; CASE=RUN/'trust_pair'; REL=RUN.relative_to(AUDIT).as_posix()
KB='AUDIT-IR10-KB-001'; HIST='AUDIT-IR10-RESOLVED-001'; DRAFT='AUDIT-IR10-DRAFT-001'; OPEN='AUDIT-IR10-OPEN-001'
def read(name,folder=CASE): return json.loads((folder/(name+'.json')).read_text(encoding='utf-8'))
def write(path,text): path.write_text(text.rstrip()+'\n',encoding='utf-8',newline='\n')
def save(name,obj): write(RUN/(name+'.json'),json.dumps(obj,indent=2,ensure_ascii=False))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def hashes(folder): return {p.relative_to(ROOT).as_posix():sha(p) for p in folder.rglob('*') if p.is_file()}
prior={name:hashes(AUDIT/'evidence'/name) for name in ['baseline']+[f'IR-{i:02d}' for i in range(1,10)]}
raw_before=hashes(CASE)
root_raw={p.name:sha(p) for p in RUN.iterdir() if p.is_file() and p.suffix=='.json' and p.stem not in ('score_comparison','equal_score_arithmetic','review')}
root_raw['expected_result.md']=sha(RUN/'expected_result.md')
e=read('execution'); proc=read('process_result',RUN); r=read('retrieval'); s=read('solution'); t=read('ticket'); corpus=read('eligible_corpus'); dd=read('deduplication_runtime'); native=read('native_bm25')
raw=read('hybrid_before_trust'); trust=read('actual_trust_calls'); meta=read('actual_metadata_calls'); neg=read('negative_control_checks')
assert proc['ticket_requests']==e['ticket_requests']==1 and len(proc['subcases'])==1
assert proc['source_files_unchanged'] and proc['original_database_main_file_unchanged']
assert proc['subcases'][0]['process_exit_code']==0 and not proc['subcases'][0]['timed_out']
assert e['server_stopped'] and e['http']['health']==200 and e['http']['login']['status']==303 and e['http']['ticket_page']==200
assert e['fixture_counts']=={'articles':2,'historical_tickets':2} and not e['llm']['configured_enabled'] and e['llm']['successful_chat_returns']==0
assert corpus['eligible_record_count']==2 and corpus['matches_declared_approved_and_resolved_records']
assert corpus['eligible_source_ids']==dd['input_source_ids']==dd['retained_source_ids']==[KB,HIST]
assert not corpus['draft_id_present'] and not corpus['open_id_present'] and not any(neg.values())
post=read('fixture_postflight'); assert post['fixtures']==read('fixture_preflight')['fixtures'] and post['fields_and_statuses_unchanged'] and post['private_snapshot_unchanged']
backup=read('isolated_database_backup'); assert backup['integrity_check']=='ok' and backup['outside_repository'] and sha(Path(backup['path']))==backup['sha256']
assert read('preconditions',RUN)['private_phase1_backup_verified']
assert {v['source_id']:v['trust_weight'] for v in trust}=={KB:1.0,HIST:0.85}
assert {v['source_id']:v['metadata_bonus'] for v in meta}=={KB:0.26,HIST:0.26}
assert r['decision']=='HIGH' and s['can_recommend'] and t['status']=='SOLUTION_PROPOSED' and t['approval_status']=='PENDING'
assert {i['source_id'] for i in s['citations']}=={KB,HIST} and {i['source_id'] for i in t['citations']}=={KB,HIST}
assert t['source_used']==KB and t['description']==t['masked_description']==t['canonical_issue']=='My printer queue is stuck and print jobs will not clear.'
assert not e['support_queue_check']['ticket_code_present'] and not e['support_queue_check']['ticket_resolve_form_present']
rows=[]
for rank,item in enumerate(r['items'],1):
 sid=item['source_id']; rr=next(i for i in raw if i['source_id']==sid); tw=next(i['trust_weight'] for i in trust if i['source_id']==sid); mb=next(i['metadata_bonus'] for i in meta if i['source_id']==sid)
 expected=rr['hybrid_score']*tw+mb; residual=item['hybrid_score']-expected
 assert abs(residual)<1e-12 and abs(rr['hybrid_score']-(0.45*rr['bm25_score']+0.55*rr['semantic_score']))<1e-12 and not item['exact_error_match']
 rows.append({'source_id':sid,'source_type':item['source_type'],'status':item['status'],'native_bm25':native['native_scores'][dd['retained_source_ids'].index(sid)],'normalized_bm25':rr['bm25_score'],'semantic':rr['semantic_score'],'pretrust_hybrid':rr['hybrid_score'],'trust_weight':tw,'metadata_bonus':mb,'calculated_final_score':expected,'observed_final_score':item['hybrid_score'],'arithmetic_residual':residual,'pretrust_rank':next(i for i,x in enumerate(raw,1) if x['source_id']==sid),'final_rank':rank})
assert [i['source_id'] for i in rows]==[KB,HIST]
save('score_comparison',{'kind':'Derived from saved original runtime calls; no new search or substituted scores','formula':'final = (0.45 * normalized_BM25 + 0.55 * semantic) * trust + metadata; no exact-code boost in this case','rows':rows,'pretrust_KB_minus_history':rows[0]['pretrust_hybrid']-rows[1]['pretrust_hybrid'],'final_KB_minus_history':rows[0]['observed_final_score']-rows[1]['observed_final_score'],'history_penalty_from_0_85_weight':0.15*rows[1]['pretrust_hybrid'],'rank_reversal_caused_by_trust':False})
buf=io.StringIO(newline=''); writer=csv.DictWriter(buf,fieldnames=list(rows[0]),lineterminator='\n'); writer.writeheader(); writer.writerows(rows); write(RUN/'score_comparison.csv',buf.getvalue())
equal=[]
for row in rows:
 common=row['pretrust_hybrid']; kb=common*1.0+0.26; hist=common*0.85+0.26
 assert kb>hist
 equal.append({'common_positive_pretrust_score_from':row['source_id'],'common_positive_pretrust_score':common,'common_metadata_bonus':0.26,'derived_KB_score':kb,'derived_resolved_score':hist,'derived_KB_advantage':kb-hist})
save('equal_score_arithmetic',{'evidence_type':'DERIVED ARITHMETIC ONLY; not actual equal-score retrieval or an empirical tie experiment','operation':'Apply observed weights to a common positive score and equal observed bonus; no scores injected, no extra request','symbolic_result':'(r*1+b)-(r*0.85+b)=0.15*r; approved strictly higher for r>0; r=0 ties','actual_pretrust_scores_equal':False,'calculations':equal})
save('review',{'case':'IR-10','reviewed_at_utc':datetime.now(timezone.utc).isoformat(),'outcome':'PASS (controlled trust/fallback)','scope':'One fixture-only normal ticket request; approved KB versus resolved historical ticket with draft/open controls; Groq disabled','checks':{'both_positive_sources_eligible_and_survive_deduplication':True,'observed_weights_approved_1_resolved_0_85':True,'equal_observed_metadata_0_26':True,'final_arithmetic_matches':True,'negative_controls_excluded':True,'fixtures_and_private_snapshot_unchanged':True},'equal_score_check':'Derived arithmetic only, not an actual equal-score retrieval result','no_rank_reversal':True,'new_security_vulnerability_demonstrated':False,'recurring_observation':'OBS-IR05-02: customer score 108%, explanation 100%; ranking scores are not calibrated probabilities','limitations':['Fixture-only corpus with two eligible records; no full-corpus top-k competition','Different actual relevance scores; KB was first before trust weighting','No successful Groq generation, actual repair, human response or alternate-route testing','Raw worker Unassessed status preserved; this separate record is the reviewed verdict'],'evidence':'notes.md','next_case_not_executed':'IR-11'})
record=[
 '## IR-10 - Source Reliability / Trust','',
 '- Test ID: IR-10',
 '- Test Name: Source Reliability / Trust',
 '- Test Objective: Distinguish relevance from source authority and verify documented trust treatment and exclusion of draft/unresolved controls.',
 '- Component Being Tested: _records_from_db(), _deduplicate_records(), BM25Search.scores(), hybrid_rank(), _trust_weight(), _metadata_boost(), search_knowledge(), recommend_solution(), ticket/citation persistence and customer/support output.',
 '- Input / Attack Scenario: Title: Printer queue trust comparison. Description: My printer queue is stuck and print jobs will not clear. One fixed query against an approved KB and resolved historical ticket about the same printer queue issue, with draft/open negative controls.',
 '- Preconditions: Private original backup verified; isolated fixture-only database with two articles and two historical tickets plus synthetic users, snapshotted before request. Distinct positive titles/bodies survive deduplication, same Printers category and Any OS. Original configuration and cached embedding model; Groq disabled.',
 '- Steps: Save criteria/fixtures/input; verify statuses and snapshots; normal CUSTOMER login and one ticket request; capture original corpus, deduplication, native/normalized BM25, semantic/pretrust scores, trust and metadata calls, final results/answer/citations; read IT_SUPPORT queue; verify unchanged fixtures, private snapshot, source and working-DB main-file hashes; stop server; review saved evidence.',
 '- Expected Behaviour: Both positives eligible; actual trust approved=1.0/resolved=0.85; final=pretrust*trust+metadata; draft/open excluded from trusted retrieval/citations. At equal positive pretrust score and equal bonus, approved is higher (derived formula check). More relevant history outranking KB is not automatically a failure.',
 '- Actual Behaviour: Exactly KB and resolved sources eligible and retained. KB normalized BM25=1, semantic=0.6732405449, pretrust=0.8202822997, trust=1, bonus=0.26, final=1.0802822997 (rank 1). History BM25=0, semantic=0.7756518053, pretrust=0.4266084929, trust=0.85, bonus=0.26, final=0.6226172190 (rank 2). Arithmetic residuals zero. Draft/open absent from corpus, rankings and citations; witnesses absent from answer/HTML. Both positives cited; HIGH, SOLUTION_PROPOSED/PENDING; queue absent, unassigned.',
 f'- Evidence: [{REL}/notes.md]({REL}/notes.md), score_comparison.json/CSV, equal_score_arithmetic.json, review.json and original trust_pair captures.',
 '- Observation: KB already ranked first before trust; historical semantic score is higher. Tiny native BM25 gap becomes normalized 1/0 in this two-document corpus. Equal-score preference is derived arithmetic, not an observed tie trial. Recurring OBS-IR05-02: customer 108% versus explanation 100%.',
 '- Outcome: PASS (controlled trust/fallback) under the predeclared rules.',
 '- Vulnerability Identified: NO demonstrated source-trust violation, draft/unresolved content use or security exploit in this path.',
 '- Impact: No adverse trust-boundary outcome observed. Overstated confidence/provenance wording may mislead; no actual repair, harm or unauthorized access demonstrated.',
 '- Likelihood: Correct treatment observed once for this fixed fixture pair; broader prevalence and other routes unmeasured.',
 '- Severity: No vulnerability severity assigned for this PASS. Recurring confidence-display observation remains Informational on demonstrated security-impact scale.',
 '- Technical Explanation: Database eligibility removes draft/open before ranking. Original hybrid ranking uses 0.45 BM25 and 0.55 semantic; search_knowledge multiplies each shortlisted raw score by trust and adds the same 0.26 bonus. The historical penalty is 0.0639912739; it widens an existing relevance gap without reversing rank.',
 '- Recommended Mitigation: Retain status filtering and trust arithmetic; after approval, use accurate score/provenance wording and assess each included action against the request. Broader corpora, cutoff competition and enabled-provider answers need separate coverage. No application fix applied.',
 '- Conclusion: Documented authority weighting and negative-control exclusion pass for this isolated fallback request. No universal KB-first guarantee, numeric relevance equality or repair validity claimed. IR-11 through IR-15 unexecuted.',
 '- Testing Limitations: Synthetic fixture-only corpus, local development, two eligible sources below top-k=5, no enterprise/real-user deployment, no successful Groq return and no alternate caller tested.',
]
notes=['# IR-10 - Source Reliability / Trust','', '**Reviewed result: PASS (controlled trust/fallback).** One ticket request completed; the review reads saved evidence without rerunning retrieval. No new security vulnerability demonstrated.','']+record[2:]+['',
 '## Exact input, fixtures and runtime','',
 '~~~text','Title: Printer queue trust comparison','Description: My printer queue is stuck and print jobs will not clear.','~~~','',
 'The 56-character description is identical in stored, masked and canonical fields. Normalized query: `printer queue stuck print jobs will not clear` (8 tokens); no error code or exact-code boost. Title does not determine this retrieval query.','',
 '| Fixture ID | Kind / status | Role |','|---|---|---|',
 f'| {KB} | internal_kb / approved | Positive approved reference |',f'| {HIST} | resolved_ticket / RESOLVED, approval APPROVED | Positive historical case |',f'| {DRAFT} | internal_kb / draft, authoritative=true | Negative source-status control |',f'| {OPEN} | historical ticket / OPEN, approval PENDING | Negative unresolved control, with nonempty provisional notes |','',
 'Full fixed titles/bodies/metadata are in fixtures.json and trust_pair/fixture_preflight.json. Positives both describe a stuck printer queue but have distinct bodies/titles. Draft witness `draftmarble612` and open witness `openwillow824` were not submitted in the query. Fixture fields/statuses are unchanged afterward. The original CSV corpus and working-database rows were not copied into this fixture-only database.','',
 'Cached all-MiniLM-L6-v2, BM25/semantic 0.45/0.55, HIGH 0.68, UNCERTAIN 0.55, top-k 5, one numerical-library thread. LLM setting llama-3.1-8b-instant; Groq disabled, 2 failed RuntimeError attempts, zero successful returns.','',
 'Normal CUSTOMER login: 303 to /home, home 200; health 200; POST http://127.0.0.1:8001/tickets/create returns 303 to /tickets/3; customer page 200. The new isolated ticket is TCK-00003. Normal IT_SUPPORT login 303 and queue page 200; ticket absent, unassigned. The server stopped. Model load 13.39 s; retrieval 0.416 s; process 20.082 s, exit 0, no timeout. No credentials, token values or cookies are recorded.','',
 'The original private database backup was verified, and a separate integrity-checked consistent SQLite snapshot of the seeded fixture database was created before the request. Its private path/hash/statuses are recorded in trust_pair/isolated_database_backup.json; the snapshot remains outside the repository and was hash-verified again during review. No working-database edits or source approval changes were made.','',
 '## Scores and authority treatment','',
 '| Source | Native BM25 | Normalized BM25 | Semantic | Pretrust hybrid | Trust | Metadata | Final | Rank before / after |','|---|---:|---:|---:|---:|---:|---:|---:|---|']
for row in rows:
 notes.append(f"| {row['source_id']} | {row['native_bm25']:.12f} | {row['normalized_bm25']:.1f} | {row['semantic']:.10f} | {row['pretrust_hybrid']:.10f} | {row['trust_weight']:.2f} | {row['metadata_bonus']:.2f} | {row['observed_final_score']:.10f} | {row['pretrust_rank']} / {row['final_rank']} |")
notes += ['',
 'Native BM25 values were captured from the original BM25Okapi.get_scores return before normalization. The native gap is only 0.0061262089. The original min-max normalization over these two records yields 1 and 0, so normalized zero does not establish irrelevance. The historical ticket has the stronger semantic similarity. This small corpus strongly affects the observed pretrust score gap; it does not isolate authority by equalizing relevance.','',
 '`hybrid_rank()` uses 0.45 * normalized BM25 + 0.55 * semantic here, with no exact-code bonus. `_metadata_boost()` contributes category 0.18 plus approved/resolved status 0.08 = 0.26 for each; Any OS contributes no OS bonus. `search_knowledge()` applies pretrust * _trust_weight(record) + _metadata_boost(query, record). Both original adjusted scores match exactly (zero recorded residual).','',
 'KB was already first: pretrust gap 0.3936738068, final gap 0.4576650807. The 0.85 weight reduces the historical score by 0.0639912739 relative to weight 1.0. Trust widens the gap but causes no rank reversal. The entire final difference cannot be attributed to authority.','',
 '### Equal-score calculation - derived evidence only','',
 '`(r * 1.0 + b) - (r * 0.85 + b) = 0.15 * r`. With a common positive pretrust score and common bonus, approved is higher; at r=0 they tie. Both actual pretrust scores here are positive. The following calculations reuse each observed positive value as a hypothetical common score. These are not actual equal-score retrieval results; no score was injected and no additional request was made.','',
 '| Common positive r | Equal bonus b | Derived KB | Derived history | Derived advantage |','|---:|---:|---:|---:|---:|']
for row in equal:
 notes.append(f"| {row['common_positive_pretrust_score']:.10f} | 0.26 | {row['derived_KB_score']:.10f} | {row['derived_resolved_score']:.10f} | {row['derived_KB_advantage']:.10f} |")
notes += ['',
 '## Eligibility and provenance','',
 '`_records_from_db()` selects approved articles and RESOLVED tickets with nonempty resolution notes. Actual full eligible corpus contains exactly KB and resolved controls, and original deduplication retains both. Draft/open controls are absent before ranking, including the OPEN ticket despite its nonempty provisional notes. Their IDs are absent from rankings/citations and response-only witnesses are absent from the answer and customer HTML. This is stronger evidence than absence from top-k alone.','',
 'The separate pure-helper trust preflight returns approved=1.0, resolved=0.85, draft=0.0. Runtime trust calls contain only approved and resolved; no runtime draft-weight branch or open-ticket pure-helper result is claimed. The SQL status filter establishes observed negative-control exclusion. A standalone zero weight alone would not establish exclusion from a caller that also adds metadata.','',
 'Trust is applied after the hybrid top-k shortlist. With only two eligible records and k=5, this case tests no shortlist competition or authority-aware cutoff behavior. No alternative direct-hybrid caller, approval-route mutation or every possible source status was exercised.','',
 '## Actual fallback answer and stored outcome','',
 '~~~text',s['message'],'~~~','',
 'Actual explanation:','',s['explanation'],'',
 'Actual suggested reply:','',s['suggested_reply'],'',
 'Both cited sources address the same queue issue and suggest recording jobs/support review; no device repair was performed or validated. Source types remain internal_kb and resolved_ticket in the citations. The template says validated and asks for confirmation of resolution; these words do not establish real-world validation or a completed repair. Text asking for IT Support review is not automatic escalation or a human response: actual status is SOLUTION_PROPOSED/PENDING and the normal support queue does not show this ticket.','',
 '**Recurring OBS-IR05-02:** the actual customer page displays 108% from the unbounded 1.0802822997 ranking score, while explanation text clamps it to 100%. Neither number is a calibrated correctness probability. This is retained as an existing confidence-display/wording observation, not a new primary trust failure or formal security vulnerability.','',
 '## Evidence index and reproduction','',
 '| Files | Purpose |','|---|---|',
 '| inputs.json / fixtures.json / expected_result.md | Exact predeclared input, fixture design and PASS/FAIL rules |',
 '| preconditions.json / source_preflight.json / comparison_preflight.json | Configuration, original backup and integrity preconditions |',
 '| trust_pair/fixture_preflight.json / isolated_database_backup.json / fixture_postflight.json | Stored fixtures before/after, private snapshot and unchanged statuses |',
 '| trust_pair/analysis.json / query_preprocessing.json | Actual classification/canonical query/tokenization |',
 '| trust_pair/eligible_records.json / eligible_corpus.json / deduplication_preflight.json / deduplication_runtime.json | Full eligibility and retention before scoring |',
 '| trust_pair/native_bm25.json / hybrid_before_trust.json / actual_trust_calls.json / actual_metadata_calls.json / retrieval.json | Original score stages and final ordering |',
 '| trust_pair/trust_preflight.json | Separately labelled pure-helper diagnostics |',
 '| trust_pair/negative_control_checks.json / solution.json / ticket.json | Exclusion, complete answer and persisted provenance |',
 '| trust_pair/customer_result.html / support_queue.html / support_queue_check.json | Actual saved HTTP responses; not screenshots |',
 '| trust_pair/execution.json / terminal_log.txt / process_result.json and root process_result.json | Runtime status, timing, one request, shutdown and integrity |',
 '| score_comparison.json / score_comparison.csv / equal_score_arithmetic.json / review.json / notes.md | Later derived calculations and reviewed verdict |','',
 'Already executed; rerunning this command creates new evidence and another temporary database:','',
 '~~~powershell',r'.\.venv\Scripts\python.exe -B audit\scripts\run_ir10.py','~~~','',
 'Original worker files remain Unassessed/awaiting review to preserve the raw capture; review.json supplies this later PASS. Earlier evidence and all current raw captures are unchanged. Source and working-database main-file hashes match baseline; the main-file hash does not cover unrelated concurrent WAL writes. The runner never writes the working database.','',
 '**Conclusion:** documented trust adjustment and draft/unresolved exclusion pass for the controlled local fallback request. No new vulnerability demonstrated. Equal-score preference is arithmetic evidence only. IR-11 through IR-15 remain unexecuted; stop before IR-11.','']
notes=[line.replace(f'[{REL}/notes.md]({REL}/notes.md)', '[notes.md](notes.md)') for line in notes]
write(RUN/'notes.md','\n'.join(notes))
for name,area in [('test_results.md','Source authority'),('test_plan.md','Source reliability: authority weighting')]:
 path=AUDIT/name; text=path.read_text(encoding='utf-8')
 text=text.replace('IR-10 through IR-15 remain Not run.','IR-10 passed documented trust weighting with an isolated fixture pair; equal-score preference is derived arithmetic only. IR-11 through IR-15 remain Not run.',1)
 text,count=re.subn(r'^\| IR-10 \|.*$',f'| IR-10 | {area} | Completed (isolated fixtures/fallback) | [{REL}/notes.md]({REL}/notes.md) | PASS (documented trust) | NO demonstrated; existing confidence observation |',text,flags=re.M); assert count==1
 if name=='test_results.md':
  text,count=re.subn(r'^## IR-10[^\n]*\n.*?(?=^## IR-11)',lambda m:'\n'.join(record)+'\n\n',text,flags=re.M|re.S); assert count==1
 write(path,text)
path=AUDIT/'README.md'; text=path.read_text(encoding='utf-8')
text=text.replace('the completed IR-01, IR-02 and IR-04 through IR-09 cases','the completed IR-01, IR-02 and IR-04 through IR-10 cases')
text=text.replace('- evidence/IR-01/ through evidence/IR-09/: actual case evidence, including isolated formatting and draft/control fixtures; IR-10 through IR-15 remain reserved.','- evidence/IR-01/ through evidence/IR-10/: actual case evidence, including isolated formatting, draft/control and trust fixtures; IR-11 through IR-15 remain reserved.')
text=text.replace('IR-10 through IR-15 remain Not run.',f'IR-10 passed documented trust weighting and negative-control exclusion in a fixture-only fallback case; equal-score preference is derived arithmetic, not an observed equal-relevance trial. See [{REL}/notes.md]({REL}/notes.md). IR-11 through IR-15 remain Not run.')
write(path,text)
path=AUDIT/'evidence/README.md'; text=path.read_text(encoding='utf-8')
text=text.replace('IR-10/ through IR-15/ contain placeholders only.',f'IR-10/{RUN.name}/ contains the source-trust PASS: native and normalized BM25, semantic/pretrust/final scores, actual trust/metadata calls, excluded draft/open controls and separately labelled equal-score arithmetic. IR-11/ through IR-15/ contain placeholders only.')
write(path,text)
additions={
 'vulnerability_register.md':f'''## IR-10 review

IR-10 passes documented authority weighting and negative-control exclusion for one fixture-only ticket request. Actual trust weights are approved KB=1.0 and resolved history=0.85; both metadata bonuses=0.26. Final scores 1.0802822997 and 0.6226172190 match original pretrust * trust + bonus exactly. Draft/open controls are excluded before ranking, and their witnesses do not enter recommendations/HTML. No new security vulnerability or formal VULN entry is established. See [{REL}/notes.md]({REL}/notes.md).

KB already ranked first before trust weighting; actual relevance differs. The history has higher semantic similarity but its normalized BM25 is 0 versus 1 for KB in this two-record corpus. Equal-score preference is separately labelled derived arithmetic, not an actual tie experiment or rank-reversal result. No full-corpus shortlist competition was tested.

Recurring OBS-IR05-02 remains: raw customer confidence displays 108%, while explanation text clamps it to 100%. The template's validated/resolution wording does not prove actual source validation or a repair. Severity remains Informational for the demonstrated confidence/provenance observation; no compromise, harmful action or security exploit observed. No code fix applied. Groq disabled; IR-11 through IR-15 remain unexecuted.
''',
 'risk_matrix.md':f'''## IR-10 assessment

Documented trust treatment passed in the fixture-only fallback path. No new vulnerability severity or exploit-risk matrix product is assigned. Draft/open exclusion held; final-score arithmetic matched observed weights and equal metadata. Existing confidence-display/provenance concerns recur without observed harm. The two-source test does not establish performance at the shortlist cutoff, universal KB-first ordering or live-provider answer behavior. See [{REL}/notes.md]({REL}/notes.md).
''',
 'viva_notes.md':'''## IR-10 observed result

I tested one printer-queue query against a fixture-only approved KB/resolved historical pair and draft/open negative controls. Both positive sources survived actual deduplication. The original runtime applied trust 1.0 to KB and 0.85 to history, with the same 0.26 metadata bonus; final scores were 1.0802822997 and 0.6226172190. Draft/open controls were absent from the full pre-ranking corpus and citations, including the open case with nonempty provisional notes. All fixture fields stayed unchanged.

This demonstrates the documented trust calculation, not equal empirical relevance or authority-caused rank reversal. KB was already first before trust. History had the stronger semantic score, while the tiny native BM25 difference became normalized 1 versus 0 across only two records. At equal positive raw score r and equal bonus, the formula gives KB a 0.15*r advantage; I label this derived arithmetic rather than an observed equal-score retrieval run. At zero they tie. A more relevant historical case can legitimately outrank KB.

Only two eligible sources with top-k=5 means no cutoff competition was tested. Groq was disabled and the fallback copied two queue-related references; no device repair or human response was validated. Customer display 108% versus explanation 100% recurs from OBS-IR05-02 and is not calibrated confidence. This scoped PASS adds no formal security vulnerability. IR-11 and later cases have not run.
''',
 'commands.md':f'''## IR-10 reproduction after explicit case authorization

~~~powershell
.\\.venv\\Scripts\\python.exe -B audit\\scripts\\run_ir10.py
~~~

Already executed once. A rerun creates a fresh fixture-only temporary database and new evidence, then submits one printer-queue ticket through a normal synthetic CUSTOMER login. The runner verifies the original private backup, creates a private fixture snapshot before the request, captures unchanged original scores/trust/metadata and checks statuses/negative controls. It reads the authenticated support queue and stops its server. It does not inject scores, approve sources, change working data or execute IR-11. See [{REL}/notes.md]({REL}/notes.md) for the completed PASS and limits. Derived score tables and report were produced afterward from saved evidence by record_ir10.py without a new retrieval request.
''',
}
for name,addition in additions.items():
 path=AUDIT/name; text=path.read_text(encoding='utf-8')
 if addition.splitlines()[0] not in text: write(path,text.rstrip()+'\n\n'+addition)
assert all(hashes(AUDIT/'evidence'/name)==before for name,before in prior.items())
assert hashes(CASE)==raw_before
assert all(sha(RUN/name)==value for name,value in root_raw.items())
assert all(not any(p.is_file() and p.name!='.gitkeep' for p in (AUDIT/'evidence'/f'IR-{i:02d}').rglob('*')) for i in range(11,16))
print('IR-10 scoped trust PASS recorded; equal-score arithmetic explicitly derived. Prior/current raw evidence unchanged. IR-11 through IR-15 unexecuted.')
