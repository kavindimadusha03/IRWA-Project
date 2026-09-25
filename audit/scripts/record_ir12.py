"""Review saved IR-12 evidence only; never rerun searches or mutate raw captures."""
from pathlib import Path
from datetime import datetime,timezone
import csv,hashlib,io,json,math,re
ROOT=Path(__file__).resolve().parents[2]; AUDIT=ROOT/'audit'; RUN=AUDIT/'evidence/IR-12/run-20260922T190826464494Z'; REL=RUN.relative_to(AUDIT).as_posix()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(name,folder=RUN): return json.loads((folder/(name+'.json')).read_text(encoding='utf-8'))
def write(path,text): path.write_text(text.rstrip()+'\n',encoding='utf-8',newline='\n')
def save(name,value): write(RUN/(name+'.json'),json.dumps(value,indent=2,ensure_ascii=False))
def hashes(folder): return {p.relative_to(ROOT).as_posix():sha(p) for p in folder.rglob('*') if p.is_file()}
def csv_save(name,rows):
 b=io.StringIO(newline=''); w=csv.DictWriter(b,fieldnames=list(rows[0]),lineterminator='\n'); w.writeheader(); w.writerows(rows); write(RUN/(name+'.csv'),b.getvalue())
assert not (RUN/'review.json').exists(), 'Review already exists; do not rerun writer'
prior={name:hashes(AUDIT/'evidence'/name) for name in ['baseline']+[f'IR-{i:02d}' for i in range(1,12)]}; raw_before=hashes(RUN)
e=read('execution'); proc=read('process_result'); cfg=read('effective_configuration'); post=read('postflight'); inputs=read('inputs'); selection=read('natural_selection'); summaries=read('natural_summary'); fixture_inputs=read('controlled_inputs')['inputs']; corpus=read('eligible_records')
low=cfg['uncertain_threshold']; high=cfg['high_threshold']; assert low==.55 and high==.68
assert proc['process_exit_code']==0 and not proc['timed_out'] and all(proc[k] for k in ('source_files_unchanged','original_database_main_file_unchanged','prior_evidence_unchanged'))
assert e['natural_searches']==16 and e['selected_solution_calls']==4 and e['controlled_searches']==e['controlled_solution_calls']==6 and e['ticket_requests']==e['http_requests']==0
assert not e['llm']['configured_enabled'] and e['llm']['attempts']==3 and e['llm']['successful_returns']==0
assert all(post[k] for k in ('eligible_records_unchanged','row_counts_unchanged','seeded_database_main_file_unchanged','private_snapshot_unchanged','all_monkeypatches_restored'))
assert len(corpus)==427 and all(x['source_id']!='AUDIT-IR12-CONTROL' for x in corpus)
backup=read('isolated_database_backup'); assert backup['integrity_check']=='ok' and backup['outside_repository'] and sha(Path(backup['path']))==backup['sha256']
baseline=read('environment',AUDIT/'evidence/baseline'); assert all(sha(ROOT/name)==digest for name,digest in baseline['source_sha256'].items()) and sha(ROOT/'knowgap.db')==baseline['original_database_sha256']
natural=[read(q['id'],RUN/'natural') for q in inputs['natural_queries']]
assert len(natural)==16 and len(list((RUN/'natural').glob('*.json')))==16
expected_decision=lambda score:'HIGH' if score>=high else 'UNCERTAIN' if score>=low else 'LOW'
score_rows=[]
for n,declared in zip(natural,inputs['natural_queries']):
 assert n['id']==declared['id'] and n['query']==declared['query']==n['retrieval']['query'] and n['kind']=='natural_original_retrieval'
 assert n['decision_matches'] and n['retrieval']['decision']==expected_decision(n['retrieval']['best_score']) and len(n['deduplicated_source_ids'])==50
 assert len(n['retrieval']['items'])==5
 trusts={x['source_id']:x['trust'] for x in n['trust_calls']}; bonuses={x['source_id']:x['bonus'] for x in n['metadata_calls']}
 for rank,item in enumerate(n['retrieval']['items'],1):
  sid=item['source_id']; pre=next(x for x in n['hybrid_before_trust'] if x['source_id']==sid); final=pre['hybrid_score']*trusts[sid]+bonuses[sid]
  assert abs(final-item['hybrid_score'])<1e-12 and not item['exact_error_match']
  assert abs(pre['hybrid_score']-(cfg['bm25_weight']*item['bm25_score']+cfg['semantic_weight']*item['semantic_score']))<1e-12
  score_rows.append({'query_id':n['id'],'query':n['query'],'rank':rank,'source_id':sid,'native_bm25':n['native_bm25']['scores'][n['deduplicated_source_ids'].index(sid)],'normalized_bm25':item['bm25_score'],'semantic':item['semantic_score'],'pretrust_hybrid':pre['hybrid_score'],'trust':trusts[sid],'metadata_bonus':bonuses[sid],'calculated_final':final,'observed_final':item['hybrid_score'],'residual':item['hybrid_score']-final,'source_type':item['source_type'],'status':item['status'],'cited':sid in [c['source_id'] for c in n.get('solution',{}).get('citations',[])]})
for selected in selection['selections']:
 threshold=selected['threshold']; side=selected['side']; candidates=[n for n in natural if (n['retrieval']['best_score']<threshold if side=='below' else n['retrieval']['best_score']>=threshold)]
 chosen=min(candidates,key=lambda n:(abs(n['retrieval']['best_score']-threshold),n['id']))
 assert selected['id']==chosen['id'] and selected['within_predeclared_near_window_0_025'] and abs(chosen['retrieval']['best_score']-threshold)<=.025
selected_ids=[x['id'] for x in selection['selections']]; assert selected_ids==['N04','N07','N05','N11']
selected=[next(n for n in natural if n['id']==ident) for ident in selected_ids]
for n in natural:
 assert ('solution' in n)==(n['id'] in selected_ids)
 if 'solution' not in n: continue
 assert n['recommendation_gate_matches'] and n['solution']['can_recommend']==(n['retrieval']['decision']=='HIGH') and not n['provider_output_adopted']
 if n['id']=='N11':
  assert n['message_equals_evidence_blocks'] and len(n['llm_calls'])==1 and not n['llm_calls'][0]['successful_return']
  assert [x['source_id'] for x in n['solution']['citations']]==['SYN-0008','SYN-0005','SYN-0010']
 else:
  assert not n['solution']['citations'] and not n['solution']['source_id'] and not n.get('llm_calls')
save('score_comparison',{'kind':'Derived from saved natural original runtime scores, not score fixtures','formula':'final = pretrust * observed trust + observed metadata; pretrust=0.45*normalized_BM25+0.55*semantic here; no exact-code boost','rows':score_rows}); csv_save('score_comparison',score_rows)
boundaries=[]
for fixture in fixture_inputs:
 c=read(fixture['id'],RUN/'controlled'); target=fixture['target_final']; actual=c['retrieval']['best_score']; expected=fixture['expected_decision']
 assert c['input']==fixture and c['kind']=='CONTROLLED_SCORE_BRANCH_ONLY'
 assert c['stub_calls']==1 and c['original_SQL_record_count_before_stub']==427 and c['synthetic_native_BM25'] is None and c['synthetic_embedding_similarity'] is None
 assert all(c[k] for k in ('actual_final_exactly_equals_target','decision_matches_expected','recommendation_matches_expected','citation_gate_matches','no_unexpected_LLM_call','recommendation_gate_matches'))
 assert actual==target and actual.hex()==fixture['target_hex']==c['actual_final_hex'] and c['retrieval']['decision']==expected
 assert c['trust_calls']==[{'source_id':'AUDIT-IR12-CONTROL','trust':1.0}] and c['metadata_calls'][0]['bonus']==.08
 assert fixture['injected_pretrust']*1+.08==target and not c['provider_output_adopted']
 if expected=='HIGH': assert c['message_equals_evidence_blocks'] and len(c['llm_calls'])==1 and not c['llm_calls'][0]['successful_return']
 else: assert not c.get('llm_calls') and not c['solution']['citations'] and not c['solution']['source_id']
 boundaries.append({'id':c['id'],'threshold':fixture['threshold'],'position':fixture['position'],'target_final':target,'target_hex':target.hex(),'injected_pretrust':fixture['injected_pretrust'],'pretrust_hex':fixture['injected_pretrust_hex'],'actual_trust':1.0,'actual_metadata':.08,'actual_final':actual,'actual_hex':actual.hex(),'exact_target_match':True,'expected_decision':expected,'actual_decision':c['retrieval']['decision'],'can_recommend':c['solution']['can_recommend'],'citation_count':len(c['solution']['citations']),'LLM_attempts':len(c.get('llm_calls',[])),'outcome':'PASS'})
assert len(boundaries)==6 and [x['actual_decision'] for x in boundaries]==['LOW','UNCERTAIN','UNCERTAIN','UNCERTAIN','HIGH','HIGH']
save('boundary_comparison',{'kind':'CONTROLLED SCORE BRANCH TEST; no native BM25/semantic ranking performed','rows':boundaries,'exact_floating_point_targets_matched':6,'scope':'Original trust, metadata, final score comparison and recommendation gate, with only hybrid_rank output substituted. Not confidence calibration, natural accuracy or persisted routing.'}); csv_save('boundary_comparison',boundaries)
n11=next(n for n in selected if n['id']=='N11'); solution=n11['solution']
claims=[]
for item in n11['retrieval']['items'][:3]:
 for line in item['content'].splitlines():
  if line.startswith('Problem:') or line.startswith('Resolution:'):
   claims.append({'id':f'C{len(claims)+1:02d}','text':line,'source_id':item['source_id'],'textual_support':'Exact historical quotation','applicability':'No evidence this different update/restart/blue-screen/slowness case diagnoses or fixes the submitted screen-flicker-at-startup issue'})
claims += [{'id':'C07','text':solution['explanation'],'source_id':solution['source_id'],'textual_support':'Title and rounded 69% ranking value exist; three real historical sources cited','applicability':'Matched/approved/validated wording asserts applicability without support; ranking percentage is not calibrated correctness'}, {'id':'C08','text':solution['suggested_reply'],'source_id':solution['source_id'],'textual_support':'Update/driver procedures exist for other historical symptoms','applicability':'Follow these procedures and confirm resolution is an unsupported recommendation for the current screen flicker query'}]
grounding=[]
for n in selected:
 grounding.append({'id':n['id'],'query':n['query'],'outcome':'FAIL (unsupported applicability)' if n['id']=='N11' else 'PASS (withholding unsupported repair only)','decision':n['retrieval']['decision'],'can_recommend':n['solution']['can_recommend'],'cited_sources':[x['source_id'] for x in n['solution']['citations']],'assessment':'Copies three unrelated update histories and confidently recommends their procedures without evidence gap or clarification' if n['id']=='N11' else 'Returns no repair, citations or source and acknowledges weak/incomplete evidence; escalation wording is unverified routing in this direct call','routing_tested':False,'provider_output_adopted':False})
save('answer_grounding_review',{'scope':'Four deterministically selected natural component answers only; no final-answer claim about twelve screening-only queries','outcome':'FAIL for N11; other three withhold unsupported repair','observation':'OBS-IR12-01','selected_answers':grounding,'N11_claim_source_mapping':claims,'N11_full_solution':solution,'N11_normalized_query':n11['query_preprocessing']['normalized'],'not_claimed':['No new fabricated source text or causal diagnosis demonstrated','No live provider answer was adopted','No actual ticket escalation, customer UI or support-queue state tested','No normalization ablation, attack or physical action performed']})
normalization=[{'id':n['id'],'original':n['query'],'normalized':n['query_preprocessing']['normalized'],'tokens':n['query_preprocessing']['tokens']} for n in selected]
save('normalization_observations',{'scope':'Observed original function outputs; descriptive, not ablation or quantified cause','selected':normalization,'observations':['N04 hinge became change while no recommendation was allowed','N11 starts became restarts; flickers retained; the top record concerns repeated restarts after updates','Original fuzzy matching permits close corpus terms; no proof that disabling it alone corrects N11'],'N05_metadata_note':'Original query contains single-letter a; category-token substring condition matches Software Installation and adds .18 on top of resolved-status .08. Describes current code/output, not a tested metadata ablation.'})
review={'case':'IR-12','reviewed_at_utc':datetime.now(timezone.utc).isoformat(),'status':'Completed (direct components; natural plus controlled fixtures)','outcome':'PASS (branch logic); FAIL (selected natural-answer grounding)','primary_branch_outcome':'PASS','secondary_grounding_outcome':'FAIL (N11)','natural_decisions_correct':16,'controlled_boundaries_correct':6,'controlled_targets_exact':6,'natural_recommendation_gates_correct':4,'controlled_recommendation_gates_correct':6,'near_boundary_sides_found':4,'near_window':.025,'effective_thresholds':{'UNCERTAIN':low,'HIGH':high},'observation_id':'OBS-IR12-01','formal_vulnerability_added':False,'vulnerability_identified':'No security exploit demonstrated; answer reliability defect','provider_outputs_adopted':0,'HTTP_requests':0,'ticket_submissions':0,'next_case_not_executed':'IR-13','limitations':['Component-only; no ticket/UI/queue routing assurance','Synthetic corpus, 16 fixed queries; four selected answers; no statistical accuracy or calibration estimate','Six in-memory score fixtures test comparisons, not natural relevance','Groq disabled; no live generated-answer assurance','Normalization and score observations do not establish ablation causality'],'evidence':'notes.md'}
save('review',review)
record=[
 '## IR-12 - Confidence Threshold Boundary','',
 '- Test ID: IR-12',
 '- Test Name: Confidence Threshold Boundary',
 '- Test Objective: Verify effective score-boundary comparisons and recommendation eligibility while separately assessing whether a selected HIGH answer is grounded.',
 '- Component Being Tested: normalize_query_for_search(), hybrid_rank(), _records_from_db(), _trust_weight(), _metadata_boost(), search_knowledge(), recommend_solution().',
 '- Input / Attack Scenario: Sixteen fixed ordinary natural queries in inputs.json; nearest per threshold side N04 broken hinge, N07 hot after charging, N05 loose keyboard key, N11 screen flicker at startup. Six labelled in-memory scores immediately below/equal/above effective 0.55 and 0.68; no malicious payload.',
 '- Preconditions: Original source/working-DB hashes and private backup verified; fresh original synthetic CSV corpus (427 eligible records, 50 after dedup), seeded snapshot verified; actual settings 0.55/0.68, weights 0.45/0.55; cached model; Groq disabled.',
 '- Steps: Save all inputs/criteria; run 16 original retrieval calls; deterministically select nearest below/at-or-above each threshold within 0.025; save selection then call original solution for four saved results; separately inject six hybrid outputs while retaining original trust/metadata/comparisons/solution; capture and review every score/gate plus four answers; verify integrity.',
 '- Expected Behaviour: Comparisons follow HIGH >=0.68, else UNCERTAIN >=0.55, else LOW; only HIGH with items recommends. All six adjusted fixture values must exactly equal intended floats. A correct branch does not excuse unsupported advice; review answer grounding separately.',
 '- Actual Behaviour: All 16 natural decisions and six exact controlled boundaries match; all four selected natural and six controlled recommendation gates match. Natural scores 0.5407814051 LOW, 0.5600731634 UNCERTAIN, 0.6674615510 UNCERTAIN and 0.6920807079 HIGH are near the four sides. N11 HIGH copies unrelated update history and recommends its steps without support or caution; other three withhold repair.',
 f'- Evidence: [{REL}/notes.md]({REL}/notes.md), natural/ and controlled/ original JSON, score_comparison.json/CSV, boundary_comparison.json/CSV, answer_grounding_review.json and review.json.',
 '- Observation: OBS-IR12-01: threshold-correct HIGH still permits unsupported flicker advice. N04 hinge->change and N11 starts->restarts are observed fuzzy-normalization changes, without causal ablation. Historical source/validation wording concerns recur.',
 '- Outcome: PASS (primary branch logic); FAIL (secondary selected natural-answer grounding). No unqualified overall safe-answer PASS.',
 '- Vulnerability Identified: No new demonstrated security exploit; confirmed answer-reliability defect. A failed grounding result does not automatically establish a formal vulnerability.',
 '- Impact: Misleading troubleshooting or delayed appropriate review is plausible if advice is used. No actual user, repair, harm, disclosure or unauthorized action observed.',
 '- Likelihood: One selected HIGH natural query demonstrates this behavior on the fixed synthetic corpus; prevalence and user action are unmeasured. Boundary results are deterministic component observations, not an attack success rate.',
 '- Severity: Informational on the demonstrated security-impact scale; no formal vulnerability severity/risk product. Grounding FAIL remains a product correctness concern.',
 '- Technical Explanation: Original >= comparisons and solution HIGH/item gate behave as written. Controlled pretrust=target-0.08 with original trust1/bonus0.08 hits exact boundary floats. N11 original pretrust0.7200949505 *0.85 +0.08=0.6920807079, then first-three evidence/template advice proceeds without symptom applicability checks.',
 '- Recommended Mitigation: Retain inclusive boundary behavior; after approval add boundary regressions, require symptom/action support separately from score, abstain on coverage gaps, and constrain fuzzy correction of meaningful words. Tune thresholds only with a labelled validation set, not this bounded sample. No code or configuration fix applied.',
 '- Conclusion: Numeric boundary behavior passes but selected HIGH advice grounding fails. No live LLM output, HTTP/ticket routing or confidence calibration was assessed; stop before IR-13.',
 '- Testing Limitations: Direct local components only; original synthetic corpus and 16 fixed queries; six synthetic scores; four selected answers; Groq disabled; no enterprise/real users, ticket writes, actual escalation or prevalence estimate.',
]
notes=['# IR-12 - Confidence Threshold Boundary','',
 '**Result: PASS for branch logic; FAIL for selected natural-answer grounding.** All 16 original natural-query classifications, six exact boundary comparisons and ten tested recommendation gates matched the declared rules. The selected HIGH screen-flicker query nevertheless received unsupported update-repair advice. No security exploit or live-provider answer was demonstrated.','']+record[2:]+['',
 '## Predeclared scope and procedure','',
 'This is a direct local component test, not an HTTP/ticket workflow. `search_knowledge(session, query, top_k=5)` and `recommend_solution(query, retrieval)` were called in the audit process. No authentication route, customer page, ticket creation, coordinator persistence or support queue was exercised. Returned escalation wording is only text in this test; it does not establish that a ticket was escalated.','',
 'inputs.json fixes 16 ordinary natural queries before execution. All were searched once with original hybrid ranking. Selection was deterministic: closest observed score below and at/above each effective threshold, tie by query ID. A distance <=0.025 was fixed as the near-boundary window before searching. natural_selection.json records the four selections before their solution calls. Those calls reuse the original captured retrieval results without a second search. Twelve screening-only inputs have no final answer result in this run. There were no adaptive query variants.','',
 'The effective settings were read from the original get_settings(): UNCERTAIN=0.55, HIGH=0.68, BM25/semantic=0.45/0.55, top-k=5, cached all-MiniLM-L6-v2. The configured LLM model is llama-3.1-8b-instant; Groq was disabled. Natural query inputs go directly to search_knowledge, bypassing ticket analysis, masking and canonicalization. Observed search normalization is captured for every query.','',
 'Primary PASS requires every valid classification and recommendation gate to follow the declared comparisons. Six controlled targets must be reached exactly before judging the branch. Grounding is separately reviewed; HIGH classification does not establish evidence applicability. Missing prerequisites would be Inconclusive, not a scoring failure. These rules are preserved in expected_result.md.','',
 'The original corpus contains 80 approved articles and 500 historical tickets; eligibility yields 80 approved articles and 347 resolved histories. All seven actual retrieval fields match the CSV expectations. Original deduplication retains 50 records for each natural query. No article fixture was inserted into this corpus.','',
 '## Natural-query observations','',
 '| ID | Exact query | Best adjusted score | Decision | Selected for answer |',
 '|---|---|---:|---|---|']
for n in natural:
 notes.append(f"| {n['id']} | {n['query']} | {n['retrieval']['best_score']:.10f} | {n['retrieval']['decision']} | {'Yes' if n['id'] in selected_ids else 'No'} |")
notes += ['',
 'All 16 observed branches match `score >= 0.68 -> HIGH`, otherwise `score >= 0.55 -> UNCERTAIN`, otherwise LOW. This is comparison correctness on a deliberately selected set, not retrieval precision, calibrated probability, or a random-sample accuracy estimate. HIGH screening results without a selected solution call are not reported as observed final answers.','',
 '| Boundary side | Selected ID | Score | Distance | Decision | Recommend |',
 '|---|---|---:|---:|---|---|']
for choice,n in zip(selection['selections'],selected):
 notes.append(f"| {choice['threshold_name']} {choice['side']} | {n['id']} | {choice['score']:.10f} | {choice['absolute_distance']:.10f} | {n['retrieval']['decision']} | {n['solution']['can_recommend']} |")
notes += ['',
 'All four sides were found within the predeclared 0.025 window. The natural queries have different meanings; these are nearest scores in the fixed search set, not a controlled wording perturbation or numerical equality trial. Equality and immediately adjacent floats are covered only by the separate fixtures below.','',
 '| ID / top source | Native BM25 | Normalized BM25 | Semantic | Pretrust | Trust | Metadata | Final |',
 '|---|---:|---:|---:|---:|---:|---:|---:|']
for n in selected:
 row=next(x for x in score_rows if x['query_id']==n['id'] and x['rank']==1)
 notes.append(f"| {n['id']} / {row['source_id']} | {row['native_bm25']:.10f} | {row['normalized_bm25']:.10f} | {row['semantic']:.10f} | {row['pretrust_hybrid']:.10f} | {row['trust']:.2f} | {row['metadata_bonus']:.2f} | {row['observed_final']:.10f} |")
notes += ['',
 'score_comparison.json/CSV contains all 80 returned natural-result rows, including native BM25 mapped through retained source order, normalized BM25, semantic similarity, pretrust hybrid, observed trust/metadata and final score. Every calculated final matches the observed score within 1e-12; no exact-code boost applies. Natural ranking values were observed from original functions without changing inputs or results.','',
 'For N05 the final winner SYN-0030 is not the best normalized BM25 hit. Its 0.26 metadata comprises status0.08 plus category0.18. The original raw query includes the token `a`, which satisfies the category substring test against Software Installation. N04/N07/N11 top-source bonuses are status0.08 only. This describes captured scores and code logic; no metadata ablation was executed.','',
 '## Six controlled boundary fixtures','',
 'These are deliberately injected scores, not natural retrieval results. The actual `_records_from_db()` still reads the original 427 eligible records, but the audit replaces only `hybrid_rank` output with one in-memory record:','',
 '~~~json',json.dumps(inputs['controlled_record'],indent=2),'~~~','',
 'Query: `Boundary diagnostic note.` The record is absent from the database. Its approved/internal_kb metadata gives original trust=1.0 and status bonus=0.08; empty category and Any OS prevent other metadata bonuses. BM25 and semantic fields are labelled synthetic placeholders equal to the injected pretrust value; there is no native BM25 or embedding measurement for this record. Only original adjustment, comparison, solution and citation gates are tested.','',
 'The target is the immediately adjacent Python float below/equal/above each effective threshold, generated with math.nextafter. `pretrust = (target - bonus) / trust`; the resulting original calculation `pretrust * trust + bonus` must equal the exact target. controlled_inputs.json was saved before the first fixture call and records all float values and hexadecimal forms.','',
 '| Fixture | Injected pretrust | Actual final (exact repr) | Expected / actual branch | Recommend | Citations |',
 '|---|---:|---:|---|---|---:|']
for b in boundaries:
 notes.append(f"| {b['id']} | {b['injected_pretrust']!r} | {b['actual_final']!r} | {b['expected_decision']} / {b['actual_decision']} | {b['can_recommend']} | {b['citation_count']} |")
notes += ['',
 'All six actual final values exactly equal their intended targets. Lower boundary: LOW/UNCERTAIN/UNCERTAIN. Upper boundary: UNCERTAIN/HIGH/HIGH. Only the two HIGH controls recommend, cite AUDIT-IR12-CONTROL and attempt generation; the other four return no source/citations and make no LLM attempt. This confirms inclusive >= comparisons and the HIGH/items recommendation gate.','',
 'The equality pretrust value at HIGH is `0.6000000000000001`. Substituting rounded `0.60` would yield `0.6799999999999999`, the immediately lower value, and would not test equality. boundary_comparison.json/CSV preserves exact decimal and float.hex forms; rounded percentages cannot distinguish adjacent boundary values.','',
 'Both HIGH controls return the benign fixture evidence on disabled-provider fallback. Their generic suggested reply still says to follow documented troubleshooting steps although the fixture explicitly contains no action. No grounding assurance is inferred from these deliberately artificial controls. The recommendation field/citation/attempt gates are the scope; the separate natural-answer failure below supplies an actual source-applicability observation.','',
 '## Selected natural-answer review','',
 'N04 (hinge), N07 (hot after charging) and N05 (loose keyboard key) each returned can_recommend=false, an empty source, zero citations and no LLM attempt. Their shared actual message:','',
 '~~~text',selected[0]['solution']['message'],'~~~','',
 'Their shared explanation:','',selected[0]['solution']['explanation'],'',
 'Their shared suggested reply:','',selected[0]['solution']['suggested_reply'],'',
 'These three pass the narrow check of acknowledging insufficient evidence and withholding an unsupported repair. The claimed escalation is not verified by these direct component calls: no ticket exists for them, no coordinator ran and no queue was visited. This is an explicit coverage limit, not a claimed persisted-routing PASS.','',
 'N11 exact input: `The screen flickers when the laptop starts.` Original normalization returns `screen flickers laptop restarts`. The final best score is 0.692080707884829, computed from `0.7200949504527401 * 0.85 + 0.08`; its HIGH comparison and recommendation gate are correct. Its actual answer follows:','',
 '~~~text',solution['message'],'~~~','',
 'Actual explanation:','',solution['explanation'],'',
 'Actual suggested reply:','',solution['suggested_reply'],'',
 '| Cited source | Final score | Evidence topic | Applicability to N11 |',
 '|---|---:|---|---|']
for item in n11['retrieval']['items'][:3]:
 notes.append(f"| {item['source_id']} | {item['hybrid_score']:.10f} | {item['title']} | Different symptom; no evidence for screen flicker at startup |")
notes += ['',
 'SYN-0008 covers repeated restarts after Windows updates; SYN-0005 covers a blue screen after an update; SYN-0010 covers slowness after an update. Their quoted resolutions all concern driver updates/Windows update components. The submitted query supplies neither an update event nor repeated restarts. The copied text and source IDs are genuine, but those records do not establish the current diagnosis or remedy. Generic driver guidance in the approved corpus also does not validate the current symptom. Content review and absence of flicker-specific text corroborate this assessment; keyword absence alone is not the reasoning.','',
 'N11 contains no acknowledgement of the evidence gap or clarification request. Matched/approved/validated wording plus advice to follow the steps asserts applicability without support. The first-three policy also includes two candidates with final scores below 0.55 (0.5025393442 and 0.3874387599); individual supporting candidates are not gated by the best-score decision. This illustrates the difference between selecting a branch and checking each action/evidence pair. It does not claim the last two were themselves classified HIGH.','',
 'answer_grounding_review.json maps all six substantive quoted problem/resolution statements plus the explanation and suggested reply. Blank root-cause fields assert no diagnosis. No new causal assertion or fabricated source quotation was observed. The secondary grounding outcome is FAIL (OBS-IR12-01), recurring unsupported-applicability behavior also seen in IR-11; no successful live LLM hallucination is claimed.','',
 'Observed normalization changes are recorded separately: N04 hinge -> change, N11 starts -> restarts. `normalize_query_for_search()` uses a corpus vocabulary and fuzzy close matches, allowing these alterations. N04 still withheld advice. N11 retains flickers but changes the startup term. No experiment disabled normalization, so this run does not quantify its contribution or prove it alone caused the failure.','',
 '## Provider mode, integrity and limitations','',
 'Across all component calls, Groq was disabled: three chat attempts (N11 plus the two HIGH controls), three RuntimeErrors, zero successful returns and zero adopted provider outputs. All other selected/control answers used non-HIGH templates without a provider attempt. Natural original ranking ran 16 times; controlled search ran six times; recommend_solution ran four natural plus six controlled times. No analysis agent, HTTP request, login, ticket, customer page, support queue, real repair or source mutation was tested.','',
 'A fresh temporary SQLite database was seeded only from original synthetic CSVs and four synthetic users. The recorded original private backup was verified. A separate SQLite snapshot was taken before component calls with integrity_check=ok, outside the repository; its SHA256 is `'+backup['sha256']+'`. Postflight confirms 80 articles, 500 tickets and four users, identical eligible records, unchanged seeded database main file/snapshot and restored temporary patches. The working database and baseline application hashes are unchanged; main-file hashes do not cover unrelated concurrent WAL writes. Private paths remain in isolated_database_backup.json and execution.json, not database contents.','',
 f"Execution started {e['started_at_utc']} and finished {e['finished_at_utc']} UTC. Parent elapsed time {proc['elapsed_seconds']} seconds, exit0, no timeout. Recorded get_model() call duration {e['model_load_seconds']} seconds excludes earlier import time; it is not total startup time.",'',
 'The screen-flicker result is a confirmed reliability defect. Plausible consequences include unnecessary troubleshooting or delayed appropriate review if used; no user action, injury, unauthorized access or disclosure occurred. It was observed once on this bounded sample, so general prevalence and exploitability are unmeasured. Security severity remains Informational for the demonstrated observation; no formal vulnerability or risk product is assigned. This does not make the failed grounding behavior acceptable.','',
 'Recommended changes are not applied: retain the correct inclusive comparisons, add their regression coverage when fixes are authorized, check actual symptom/action support separately from score, abstain when evidence is insufficient, and constrain fuzzy correction of valid meaningful words. Describe source types accurately and avoid treating ranking percentages as probabilities. Threshold calibration requires an independent labelled validation dataset; these fixtures and selected queries do not justify changing weights or cutoffs.','',
 '## Evidence and reproduction','',
 '| Artifacts | Purpose |','|---|---|',
 '| inputs.json, expected_result.md | Exact 16 inputs, selection window and rules fixed before execution |',
 '| effective_configuration.json, preconditions.json | Actual nonsecret settings, source/main DB and original backup checks |',
 '| eligible_records.json, corpus_preflight.json | Full original eligible text and CSV equality |',
 '| isolated_database_backup.json, postflight.json | Seeded snapshot and post-call preservation/restoration |',
 '| natural/N01.json through N16.json | Original normalization, retained-source order, native/pretrust/final scores, full retrieved text and four selected solutions |',
 '| natural_summary.json, natural_selection.json | All scores and deterministic selections saved before answer calls |',
 '| controlled_inputs.json, controlled/*.json | Declared injected targets and original comparison/solution results, explicit synthetic provenance |',
 '| score_comparison.json/CSV, boundary_comparison.json/CSV | Later derived tables for 80 natural result rows and six boundary cases |',
 '| answer_grounding_review.json, normalization_observations.json | Selected-answer claim mapping and observed input transformations |',
 '| execution.json, process_result.json, terminal_log.txt | Counts, timing, provider state, completion and original integrity observations |',
 '| review.json, evidence_integrity.json, notes.md | Separate reviewed verdict and raw/prior-evidence preservation |','',
 'Already executed once; rerunning creates new evidence and a new temporary database:','',
 '~~~powershell',r'.\.venv\Scripts\python.exe -B audit\scripts\run_ir12.py','~~~','',
 'No page/endpoint is used in this branch/component test. It is not equivalent to POST /tickets/create or an authenticated API request. The original application functions are in [retrieval_agent.py](../../../../app/agents/retrieval_agent.py) (adjustment line101, comparisons113/115), [solution_agent.py](../../../../app/agents/solution_agent.py) (gate line9, first-three selection30) and [hybrid_search.py](../../../../app/services/hybrid_search.py) (normalization97). No application files were edited.','',
 '**Conclusion:** numeric boundary logic PASS, selected natural-answer grounding FAIL. Raw captures remain Unassessed as originally collected; review.json supplies this later split verdict. Earlier cases remain unchanged. IR-13 through IR-15 are unexecuted; stop before IR-13.','']
notes=[line.replace(f'[{REL}/notes.md]({REL}/notes.md)','[notes.md](notes.md)') for line in notes]
write(RUN/'notes.md','\n'.join(notes))
progress='IR-12 passed primary confidence-boundary logic and failed selected natural-answer grounding; direct-component and injected-score scopes are explicit. IR-13 through IR-15 remain Not run.'
for name,area in [('test_results.md','Confidence decisions'),('test_plan.md','Confidence decision boundaries')]:
 path=AUDIT/name; text=path.read_text(encoding='utf-8'); assert 'IR-12 through IR-15 remain Not run.' in text
 text=text.replace('IR-12 through IR-15 remain Not run.',progress,1)
 text,count=re.subn(r'^\| IR-12 \|.*$',f'| IR-12 | {area} | Completed (components; natural and controlled) | [{REL}/notes.md]({REL}/notes.md) | PASS (branches); FAIL (selected answer grounding) | NO exploit demonstrated; OBS-IR12-01 reliability defect |',text,flags=re.M); assert count==1
 if name=='test_results.md':
  text,count=re.subn(r'^## IR-12[^\n]*\n.*?(?=^## IR-13)',lambda m:'\n'.join(record)+'\n\n',text,flags=re.M|re.S); assert count==1
 write(path,text)
path=AUDIT/'README.md'; text=path.read_text(encoding='utf-8')
text=text.replace('the completed IR-01, IR-02 and IR-04 through IR-11 cases','the completed IR-01, IR-02 and IR-04 through IR-12 cases')
text=text.replace('- evidence/IR-01/ through evidence/IR-11/: actual case evidence, including isolated fixtures and the original-corpus grounding failure; IR-12 through IR-15 remain reserved.','- evidence/IR-01/ through evidence/IR-12/: actual case evidence, including isolated fixtures, grounding failures and separately labelled component boundary checks; IR-13 through IR-15 remain reserved.')
text=text.replace('IR-12 through IR-15 remain Not run.',f'IR-12 passed inclusive threshold branches (16 natural searches, six exact score fixtures) while a selected HIGH screen-flicker answer failed grounding; no HTTP/ticket routing was tested. See [{REL}/notes.md]({REL}/notes.md). IR-13 through IR-15 remain Not run.')
write(path,text)
path=AUDIT/'evidence/README.md'; text=path.read_text(encoding='utf-8'); assert 'IR-12/ through IR-15/ contain placeholders only.' in text
text=text.replace('IR-12/ through IR-15/ contain placeholders only.',f'IR-12/{RUN.name}/ contains 16 natural component searches, four selected answers and six explicit score fixtures: primary branches PASS, selected HIGH-answer grounding FAIL. Exact float targets, full scores and component-only routing limits are saved. IR-13/ through IR-15/ contain placeholders only.')
write(path,text)
additions={
 'vulnerability_register.md':f'''## IR-12 review - OBS-IR12-01

Title: Threshold-correct HIGH permits unsupported screen-flicker advice.

Primary branch logic PASSES: 16 natural classifications, six exact floating-point boundary comparisons and ten selected/control recommendation gates matched the original inclusive rules. Separate selected natural-answer grounding FAILS. Query N11, The screen flickers when the laptop starts., scores 0.6920807079 HIGH and copies SYN-0008/SYN-0005/SYN-0010 update/restart/blue-screen/slowness history. Matched/validated wording and the recommendation to follow those procedures lack support for flicker at startup. The two secondary cited scores are below 0.55. Text/IDs are faithful; no new invented repair or live-provider output was observed. See [{REL}/notes.md]({REL}/notes.md) and answer_grounding_review.json.

Affected components: normalization, search_knowledge best-score decision, recommend_solution first-three selection and explanation/reply templates. N11 starts->restarts and N04 hinge->change are observed fuzzy changes; no ablation establishes their individual contribution. N04/N07/N05 withhold repair and citations. All checks use direct components: escalation prose does not prove actual routing, and no customer UI/ticket/security endpoint is tested. Controlled scores are explicitly synthetic and not evidence of natural retrieval precision.

Potential impact is misleading troubleshooting or delayed appropriate review if used. No real user action, physical harm, disclosure or unauthorized operation occurred. Observed once for this selected HIGH query; general prevalence, attack success and user compliance unmeasured. The reliability defect recurs from IR-11 but is not a new formal security vulnerability or exploit-risk score. Informational describes demonstrated security impact only. Source-authority wording also repeats OBS-IR01-01.

Recommend after approval: preserve inclusive boundary rules, add regression tests, check symptom/action evidence independently of score, abstain on coverage gaps and constrain fuzzy correction of meaningful words. Validate thresholds on separate labelled data before tuning. No application fix applied; IR-13 onward unexecuted.
''',
 'risk_matrix.md':f'''## IR-12 assessment

Confidence branches pass; selected natural-answer grounding fails (OBS-IR12-01). A screen-flicker query receives HIGH 0.6920807079 and unsupported update-history advice. Potential unnecessary troubleshooting/delayed review is conditional on user action; no harm or security exploitation is demonstrated. These direct component calls do not establish persisted escalation, exposure to a customer, or access-control behavior. Six injected score cases prove comparisons only. No formal vulnerability risk product is assigned; the Informational security classification does not excuse the failed grounding behavior. See [{REL}/notes.md]({REL}/notes.md).
''',
 'viva_notes.md':'''## IR-12 observed result

I read effective settings 0.55/0.68 and tested the original retrieval/solution components locally. Sixteen exact queries were fixed before execution. The closest four scores were 0.5407814051 LOW (broken hinge), 0.5600731634 UNCERTAIN (hot after charging), 0.6674615510 UNCERTAIN (loose key) and 0.6920807079 HIGH (screen flicker at startup). All were within the predeclared 0.025 window. Selection was deterministic, with no adaptive query rewriting.

I separately injected six hybrid outputs to test the immediately lower/equal/higher float at both cutoffs while retaining original trust1 and metadata0.08. Actual adjusted values exactly matched their targets. The expected LOW/UNCERTAIN/UNCERTAIN and UNCERTAIN/HIGH/HIGH sequences passed. At HIGH equality, pretrust0.6000000000000001 is necessary: rounded0.60 lands just below0.68. This tests comparisons, not natural accuracy or confidence calibration.

Numeric branches passed, but N11 screen-flicker advice failed grounding: it copied unrelated update histories and confidently recommended their procedures. Groq was disabled, so no live generation was assessed. The other three selected queries withheld repairs. Direct calls produced escalation wording but created no tickets or queue entries; I do not claim actual escalation. Fuzzy changes hinge->change and starts->restarts were observed without ablation. No application fixes, real repairs or IR-13 tests were performed.
''',
 'commands.md':f'''## IR-12 reproduction after explicit case authorization

~~~powershell
.\\.venv\\Scripts\\python.exe -B audit\\scripts\\run_ir12.py
~~~

Already executed once. A rerun creates new evidence and a private temporary database seeded from original synthetic CSVs, verifies the original backup and snapshots the seeded database. It performs 16 fixed natural component searches, four deterministically selected solution calls and six labelled injected-score branch/solution checks. It does not send HTTP requests, create tickets, insert the control source into the DB or test support routing. Read [{REL}/notes.md]({REL}/notes.md) for the branch PASS and selected-answer grounding FAIL. record_ir12.py derives the report from saved data only; its completed writer must not be rerun. IR-13 and later are outside this runner.
''',
}
for name,addition in additions.items():
 path=AUDIT/name; text=path.read_text(encoding='utf-8'); assert addition.splitlines()[0] not in text
 write(path,text.rstrip()+'\n\n'+addition)
assert all(hashes(AUDIT/'evidence'/name)==before for name,before in prior.items())
assert all(sha(ROOT/name)==digest for name,digest in raw_before.items())
assert all(p.name=='.gitkeep' for i in range(13,16) for p in (AUDIT/'evidence'/f'IR-{i:02d}').rglob('*') if p.is_file())
save('evidence_integrity',{'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'prior_evidence_directories_unchanged':list(prior),'prior_file_counts':{name:len(value) for name,value in prior.items()},'original_IR12_captures_unchanged':True,'raw_capture_sha256':raw_before,'source_files_match_baseline':True,'working_database_main_file_matches_baseline':True,'private_seeded_snapshot_unchanged':True,'IR13_to_IR15_unexecuted':True})
print('IR-12 recorded: primary branches PASS, selected natural-answer grounding FAIL; source/database/raw/prior evidence unchanged. Stopped before IR-13.')
