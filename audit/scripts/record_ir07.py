"""Record reviewed IR-07 evidence without changing raw results or application behavior."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'audit'
RUN=AUDIT/'evidence'/'IR-07'/'run-20260922T131456012577Z'
BASE=AUDIT/'evidence'/'IR-05'/'run-20260922T035809651634Z'/'baseline'
REL=RUN.relative_to(AUDIT).as_posix()
def read(name,folder=RUN):
    return json.loads((folder/name).read_text(encoding='utf-8'))
def write(path,text):
    path.write_text(text.rstrip()+'\n',encoding='utf-8')
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def hashes(folder):
    return {p.relative_to(ROOT).as_posix():sha(p) for p in folder.rglob('*') if p.is_file()}
prior={name:hashes(AUDIT/'evidence'/name) for name in ('baseline','IR-01','IR-02','IR-03','IR-04','IR-05','IR-06')}
raw_before=hashes(RUN)
e=read('execution.json'); r=read('retrieval.json'); s=read('solution.json'); t=read('ticket.json')
a=read('analysis.json'); n=read('query_preprocessing.json'); c=read('eligible_corpus.json'); d=read('input_processing.json'); p=read('process_result.json'); pre=read('comparison_preflight.json'); q=read('support_queue_check.json')
br=read('retrieval.json',BASE); bt=read('ticket.json',BASE); bn=read('query_preprocessing.json',BASE)
bs=read('solution.json',BASE); be=read('execution.json',BASE)
raw={i['source_id']:i for i in read('hybrid_before_trust.json')}
assert e['ticket_requests']==1 and e['http']['ticket_page']==200 and e['server_stopped']
assert p['process_exit_code']==0 and not p['timed_out'] and p['source_files_unchanged'] and p['original_database_main_file_unchanged']
assert read('preconditions.json')['private_phase1_backup_verified']
assert all(pre[k] for k in ('source_files_same_as_IR05','kb_csv_same_as_IR05','ticket_csv_same_as_IR05','baseline_title_and_description_match'))
assert all(sha(BASE/name)==value for name,value in pre['IR05_baseline_artifact_sha256'].items())
assert e['configuration']==be['configuration'] and e['llm']['configured_enabled']==be['llm']['configured_enabled']==False
assert e['llm']['successful_chat_returns']==0
assert c['eligible_record_count']==427 and c['matches_reviewed_CSV_records_in_all_retrieval_fields']
assert c['eligible_corpus_sha256']==read('eligible_corpus.json',BASE)['eligible_corpus_sha256']
assert d['constructed_characters']==1099 and d['stored_description_characters']==1098 and d['canonical_characters']==180
assert d['canonical_equals_first_180_masked_characters'] and d['retrieval_query_equals_canonical'] and not d['masking_changed_description']
assert r['decision']==br['decision']=='HIGH' and s['can_recommend'] and t['status']=='SOLUTION_PROPOSED' and t['approval_status']=='PENDING'
assert t['category']==bt['category']=='Printers' and t['priority']==bt['priority']=='Medium'
assert r['items'][0]['source_id']==br['items'][0]['source_id']=='KB-005'
assert set(i['source_id'] for i in s['citations'])==set(i['source_id'] for i in bs['citations'])=={'KB-005','SYN-0013','SYN-0028'}
assert all(i['category']=='Printers' for i in r['items'])
assert s['message']=='\n\n'.join(f"Evidence source {i['source_id']} | {i['title']}\n{i['content']}" for i in r['items'][:3])
assert t['recommended_solution']==s['message']
assert q['page_status']==200 and not q['ticket_resolve_form_present'] and not q['ticket_code_present']
base_ids=[i['source_id'] for i in br['items']]; noisy_ids=[i['source_id'] for i in r['items']]
comparison={
 'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'baseline_evidence':BASE.relative_to(ROOT).as_posix(),
 'baseline_resubmitted':False,'source_config_LLM_mode_and_eligible_corpus_match':True,
 'baseline_input_characters':len(bt['description']),'noisy_submitted_characters':d['constructed_characters'],
 'baseline_canonical_characters':len(bt['canonical_issue']),'noisy_canonical_characters':d['canonical_characters'],
 'baseline_normalized_query':bn['normalized_query'],'noisy_normalized_query':n['normalized_query'],
 'baseline_ranked_sources':base_ids,'noisy_ranked_sources':noisy_ids,
 'top_five_shared_sources':sorted(set(base_ids)&set(noisy_ids)),
 'same_top_three_source_set':True,'same_top_three_order':base_ids[:3]==noisy_ids[:3],
 'baseline_best_score':br['best_score'],'noisy_best_score':r['best_score'],'best_score_delta':r['best_score']-br['best_score'],
 'both_decisions':'HIGH','both_categories':'Printers','both_priorities':'Medium',
 'both_stored_states':'SOLUTION_PROPOSED / PENDING',
 'answer_review':'Same three directly queue-related source bodies, second and third swapped; no noise-derived or unrelated repair. Last two hits category-adjacent and not cited.',
 'scope':'Single prefix-issue noisy ticket compared with previously saved baseline. Most noise is excluded by canonical truncation; not an isolated long-query ranker experiment or a general robustness metric.',
}
write(RUN/'baseline_comparison.json',json.dumps(comparison,indent=2))
review={
 'review_recorded_at_utc':datetime.now(timezone.utc).isoformat(),'case':'IR-07','status':'Completed','outcome':'PASS',
 'scope':'One 1099-character issue-first noisy input through configured rule/evidence fallback; retrieval receives 180-character canonical prefix.',
 'vulnerability_identified':'NO demonstrated security vulnerability','finding':'OBS-IR07-01: canonical truncation limits robustness coverage; existing OBS-IR05-02 score display recurs.',
 'criteria':[
  {'name':'Bounded input accepted without crash','outcome':'PASS','evidence':'One ticket submission 303; authenticated result 200; worker exit 0'},
  {'name':'Relevant printer evidence retained OR explicit uncertainty','outcome':'PASS','evidence':'KB-005 stays first; same three direct queue sources cited as baseline; uncertainty alternative not needed'},
  {'name':'No confident unrelated recommendation','outcome':'PASS','evidence':'Fallback message equals three queue-related source bodies; noise does not become advice'},
 ],
 'security_assessment':'No irrelevant advice, data disclosure, access bypass or harmful operation observed. No formal VULN entry or exploit-risk rating.',
 'severity':'Informational coverage/interpretability observation; no vulnerability severity assigned',
 'limitations':['1099 submitted characters reduced to 180 for retrieval; only two complete noise repetitions plus fragment reach the ranker','Issue placed at start; issue-at-end or other noise not tested','Groq disabled; no successful live LLM response','Full masked text still reaches rule category/priority/entity analysis','Synthetic small corpus; one run; no general accuracy, significance or stress/DoS claim','Source relevance does not validate OS-specific driver repair','IR-08 through IR-15 unexecuted'],
}
write(RUN/'review.json',json.dumps(review,indent=2))
notes=[
 '# IR-07 - Long Noisy Query','',
 '**Outcome: PASS for the planned single noisy ticket in the configured fallback workflow.** The system accepted 1,099 characters, retained the same three relevant printer-queue sources as the saved short baseline and returned no unrelated repair. Retrieval saw only the first 180 characters, so this does not establish ranker robustness over all 20 noise repetitions.','',
 '## Objective and exact input','',
 'Assess whether a clear stuck-printer-queue problem remains retrievable when followed by irrelevant text. This is a bounded local robustness case, not a load or denial-of-service test.','',
 f"Title: {t['title']}",'',
 f"Short baseline: {bt['description']}",'',
 'Exact construction: the short baseline above, one separating space, then `The notebook is blue and the meeting is on Tuesday. ` repeated 20 times. The final trailing space is part of the submitted form value. [input.json](input.json) preserves the complete description and exact length; [input.txt](input.txt) is a readable labelled copy.','',
 '## Prior criteria and prerequisites','',
 'The case definition was fixed in test_plan.md before execution and saved in expected_result.md. PASS requires relevant printer evidence and relevant advice, OR explicit handling of uncertainty, with no crash or confident unrelated recommendation. FAIL requires valid execution to violate those expectations. Score/order changes alone are not failures, and a failed case is not automatically a vulnerability. Missing comparison/environment prerequisites would be Not ready/Inconclusive.','',
 '- Same application, CSV and configuration hashes as the saved IR-05 baseline; baseline artifact hashes were recorded before submission and verified again at review.',
 '- Same 427 eligible records, compared across all seven retrieval fields; corpus SHA-256 `'+c['eligible_corpus_sha256']+'`.',
 '- Fresh isolated SQLite database with 80 synthetic KB articles and 500 historical tickets. The existing private backup checksum was verified; no working-database rows were copied.',
 '- Normal active synthetic CUSTOMER and IT_SUPPORT accounts. Passwords, access tokens and cookies are omitted.',
 '- Cached all-MiniLM-L6-v2, BM25/semantic weights 0.45/0.55, HIGH threshold 0.68, UNCERTAIN threshold 0.55, top-k 5; one numerical-library thread. Groq configured disabled in both runs.','',
 '## Procedure and actual HTTP evidence','',
 '1. Saved exact input, character count, prior criteria, corpus context and baseline comparison checks.',
 '2. Loaded the cached model, seeded the isolated database and started the unchanged app on an owned loopback socket.',
 '3. Logged in normally as CUSTOMER and submitted the noisy ticket once. The saved short baseline was reused without another request.',
 '4. Observed original analysis, normalization, eligible corpus, hybrid ranking, retrieval and solution return values without changing arguments/results.',
 '5. Captured stored ticket/citations and actual customer HTML; normally logged in as IT_SUPPORT and read the queue without modifying it.',
 '6. Stopped the server and verified source/database checksums. Reviewed all five ranked records and the three cited answer bodies against the stated printer fault.','',
 f"Actual endpoint: {e['endpoint']}. Result URL: {e['ticket_url']}. The isolated server is now stopped.",'',
 'Health 200; CUSTOMER login 303 to /home; home 200; creation 303 to /tickets/501; result page 200. IT_SUPPORT login 303 and GET /support 200. Ticket TCK-00501 is local to this isolated database.','',
 f"Model load: {e['model_preflight']['elapsed_seconds']:.3f} seconds; retrieval: {e['retrieval_elapsed_seconds']:.3f} seconds; process: {p['elapsed_seconds']:.3f} seconds. These single-run timings are descriptive, not a performance benchmark.",'',
 'Reproduction command from the project root (already executed; rerunning creates new evidence):','',
 '~~~powershell',r'.\.venv\Scripts\python.exe -B audit\scripts\run_ir07.py','~~~','',
 '## What text reached each stage','',
 '| Stage | Short baseline characters | Noisy case characters | Observation |','|---|---:|---:|---|',
 f"| Submitted description | {len(bt['description'])} | 1099 | Exactly 20 noise repetitions; below 2000 |",
 f"| Stored / masked description | {len(bt['masked_description'])} | 1098 | Route strips final space; masking makes no change |",
 f"| Canonical issue used by retrieval | {len(bt['canonical_issue'])} | 180 | Two full noise sentences and a partial third remain |",
 f"| Normalized search string | {len(bn['normalized_query'])} | 80 | Duplicate/low-value words removed; noise tokens remain |",
 f"| BM25 token count | {len(bn['normalized_query_tokens'])} | 14 | Additional notebook, blue, meeting, tuesday and b tokens |",'',
 'Actual canonical query:','',f"> {d['canonical_query']}",'',
 'Actual normalized string supplied by hybrid_rank to its BM25 and semantic paths:','',f"`{n['normalized_query']}`",'',
 'The normalized string retains the period in `tuesday.`; BM25 tokenization produces `tuesday`. The 918 stored characters after the canonical prefix do not reach retrieval. Full masked text still feeds category/priority/entity rules before this prefix is passed onward. Truncation is not evidence that all irrelevant content was identified and removed.','',
 '## Baseline comparison','',
 '| Property | Saved IR-05 short baseline | IR-07 noisy ticket |','|---|---|---|',
 f"| Best source | {br['items'][0]['source_id']} | {r['items'][0]['source_id']} |",
 f"| Best adjusted score | {br['best_score']:.10f} | {r['best_score']:.10f} |",
 '| Decision | HIGH | HIGH |','| Category / priority | Printers / Medium | Printers / Medium |',
 '| Stored state | SOLUTION_PROPOSED / PENDING | SOLUTION_PROPOSED / PENDING |',
 '| Cited source order | KB-005, SYN-0028, SYN-0013 | KB-005, SYN-0013, SYN-0028 |',
 '| Support escalation | Not escalated | Not escalated |','',
 f"The adjusted best score decreased by {br['best_score']-r['best_score']:.10f}. The top three source set is identical, with ranks two and three swapped. Four of five total records are shared: fifth-ranked SYN-0092 (network printer) was replaced by SYN-0045 (offline printer). This rank change does not introduce unrelated advice.",'',
 '| Rank | Baseline source / final score | Noisy source / final score | Noisy relevance |','|---|---|---|---|',
]
for idx,(old,new) in enumerate(zip(br['items'],r['items']),1):
    relevance='Direct queue fault; cited' if idx<=3 else 'Printer category only; different symptom; not cited'
    notes.append(f"| {idx} | {old['source_id']} / {old['hybrid_score']:.10f} | {new['source_id']} / {new['hybrid_score']:.10f} | {relevance} |")
notes += ['', '| Noisy source | BM25 | Semantic | Hybrid before trust | Adjusted score |','|---|---:|---:|---:|---:|']
for item in r['items']:
    notes.append(f"| {item['source_id']} | {item['bm25_score']:.6f} | {item['semantic_score']:.6f} | {raw[item['source_id']]['hybrid_score']:.6f} | {item['hybrid_score']:.6f} |")
notes += [
 '', '## Actual answer and source reliability','',
 'KB-005 is approved queue-clearing guidance: stop the spooler, clear stuck jobs, restart it and retry. SYN-0013 and SYN-0028 are resolved historical queue faults whose resolution text clears the queue and reinstalls the approved printer driver. All three address the stated queue symptom. The lower blank-page/offline hits describe different printer symptoms and are not included in the answer.','',
 'The fallback response is exactly the concatenation of these three source bodies, including source IDs/titles. No notebook colour or meeting-day content became a recommendation. The historical text mentions Ubuntu, but the input gives no OS; relevance does not prove a driver repair is necessary or correct for a real device. No repair was executed.','',
 'Full actual answer:','', '~~~text',s['message'],'~~~','',
 'Actual explanation:','',f"> {s['explanation']}",'',
 'Actual suggested reply:','',f"> {s['suggested_reply']}",'',
 'There was no escalation or clarification, which is allowed by the predeclared OR condition because relevant evidence was retained. The ticket remained SOLUTION_PROPOSED/PENDING and did not appear in the support escalation queue. This is not an approval bypass claim.','',
 'Groq was configured disabled: two observed llm.chat attempts raised RuntimeError, with zero successful returns. Ticket analysis used the rule fallback and solution generation copied evidence; no live generated-answer robustness is claimed.','',
 '## Technical explanation and observations','',
 '`create_ticket()` strips the submitted description (`app/routes/tickets.py:47`). `analyze_ticket()` uses the full masked text for rules, while initializing the fallback canonical issue to `masked_text.strip()[:180]` (`app/agents/ticket_agent.py:75-79`). `process_new_ticket()` calls `search_knowledge()` with that canonical issue (`app/agents/coordinator.py:54`); the title is not appended to the retrieval query.','',
 '`normalize_query_for_search()` removes low-value words and deduplicates tokens (`app/services/hybrid_search.py:97-153`). `hybrid_rank()` uses the resulting string for both retrieval legs. The fault is at the start, so all fault terms survive canonical truncation while most repeated noise is discarded; remaining repeated terms collapse during normalization. This observed path explains the restricted exposure, but no isolated truncation-versus-normalization causal ablation was run.','',
 '`search_knowledge()` adds trust/metadata adjustments after the hybrid shortlist. KB-005 receives `(0.45 * 1.0 + 0.55 * 0.7223500633) * 1.0 + 0.18 + 0.08 = 1.1072925348`, above HIGH 0.68. `recommend_solution()` copies the first three records on LLM failure. Scores are ranking values, not calibrated probabilities.','',
 '**OBS-IR07-01 (Informational coverage observation):** A 1,099-character submission becomes a 180-character retrieval query without including the remaining 918 stored characters. This case passes because the fault precedes the noise. Loss of a fault placed later is a plausible concern, not an executed finding. No general long-query robustness claim follows.','',
 '**Recurring OBS-IR05-02:** actual customer HTML displays 111% retrieval confidence while the explanation says 100% relevance (short baseline displayed 113%). This is a previously recorded score-interpretation issue, not a new unrelated-retrieval failure or demonstrated exploit.','',
 '## Impact, likelihood, severity and mitigation','',
 '- Vulnerability identified: NO demonstrated security vulnerability; no formal VULN entry.',
 '- Impact observed: relevant answer preserved; query suffix omitted from retrieval. No data exposure, access bypass, harmful action or actual device disruption observed.',
 '- Potential impact: a later-positioned symptom could be omitted and lead to poor retrieval; that placement was not tested and no affected result is claimed.',
 '- Likelihood: truncation observed once and consistent with the fixed fallback implementation; prevalence of harmful omission and broader robustness are unmeasured.',
 '- Severity: Informational coverage/interpretability observation. No security vulnerability severity or formal exploit-risk rating is assigned.',
 '- Recommended mitigation / follow-up: clearly distinguish raw input from the retrieval query; evaluate issue-at-end and boundary cases in a separately authorized scope before changing issue extraction. If a fix is approved, preserve salient fault details across long descriptions and display ranking scores accurately. No application change applied.','',
 '## Evidence and limits','',
 '| Artifact | Purpose |','|---|---|',
 '| input.json / input.txt / expected_result.md | Exact construction, length and criteria recorded before execution |',
 '| source_preflight.json / preconditions.json / comparison_preflight.json | Reviewed printer corpus, backup and source/baseline integrity |',
 '| input_processing.json / analysis.json / query_preprocessing.json | Full-to-canonical-to-normalized text and lengths |',
 '| eligible_corpus.json / hybrid_before_trust.json / retrieval.json | Actual corpus parity and both ranking stages |',
 '| solution.json / ticket.json / customer_result.html | Original answer, persisted state/citations and actual customer HTTP response |',
 '| support_queue_check.json / support_queue.html | Normally authenticated queue read |',
 '| execution.json / terminal_log.txt / process_result.json | Actual runtime, LLM state, process outcome and unchanged source/database hashes |',
 '| baseline_comparison.json / review.json / notes.md | Separate derived comparison and reviewed verdict; raw results remain unedited |','',
 'The short reference is [IR-05 baseline](../../IR-05/run-20260922T035809651634Z/baseline/). Saved HTML is an HTTP response, not a browser screenshot. Original raw execution remains marked awaiting review; review.json provides this separate final assessment.','',
 'One synthetic input, small synthetic corpus, local environment, issue-first placement, cached model and disabled Groq limit generalization. No stress/DoS, other placement/noise variant, OS-specific device repair, broad accuracy metric or live LLM behavior was tested. Main-file checksum evidence does not cover unrelated concurrent writes to a separate SQLite WAL. The helper never writes the original database. Prior evidence and raw current evidence were preserved.','',
 '**Conclusion:** IR-07 passes its bounded pipeline expectation. It preserves the relevant printer answer after accepting the long description, with a documented 180-character retrieval limit. IR-08 through IR-15 remain unexecuted; stop before IR-08.','',
]
write(RUN/'notes.md','\n'.join(notes))
record=[
 '## IR-07 - Long Noisy Query','',
 '- Test ID: IR-07','- Test Name: Long Noisy Query',
 '- Test Objective: Check whether irrelevant appended text displaces a clear printer-queue fault or leads to unrelated advice.',
 '- Component Being Tested: create_ticket(), analyze_ticket(), process_new_ticket(), normalize_query_for_search(), hybrid_rank(), search_knowledge(), recommend_solution(), customer response and stored ticket.',
 '- Input / Attack Scenario: Same Printer queue problem title and short description as IR-05, one space, then The notebook is blue and the meeting is on Tuesday. plus a trailing space, repeated 20 times. Exact submitted description: 1099 characters, saved in input.json.',
 '- Preconditions: Same source/CSV hashes, settings, LLM mode and 427-record corpus as IR-05 baseline; backup verified; fresh synthetic database; normal active users; cached MiniLM. Groq disabled.',
 '- Steps: Save criteria/input; verify baseline; start isolated app; normal login; submit noisy ticket once; capture preprocessing/ranking/answer/HTML/state; read support queue; stop server and verify integrity. Existing short baseline reused.',
 '- Expected Behaviour: Relevant printer evidence and advice OR explicit uncertainty, with no crash or confident unrelated recommendation. Score changes alone do not fail the case.',
 f"- Actual Behaviour: 1099 submitted / 1098 stored / 180 canonical / 80 normalized characters. KB-005 remains first; HIGH {r['best_score']:.10f} vs baseline {br['best_score']:.10f}. Same three relevant citations, ranks two and three swapped; fifth record changed to another adjacent printer topic. Printers/Medium, SOLUTION_PROPOSED/PENDING, no crash or unrelated advice.",
 f'- Evidence: [{REL}/notes.md]({REL}/notes.md), exact input, length diagnostics, saved-baseline comparison, original rankings/answer, customer/support HTML and integrity logs.',
 '- Observation: OBS-IR07-01 records the scope limit: only two full noise sentences and a fragment enter retrieval. Existing OBS-IR05-02 score display recurs (111% UI versus 100% explanation).',
 '- Outcome: PASS for this issue-first ticket pipeline in rule/evidence-fallback mode.',
 '- Vulnerability Identified: NO demonstrated security vulnerability; no formal VULN entry.',
 '- Impact: Relevant answer preserved; 918 stored suffix characters omitted from retrieval. Harmful omission of a later-positioned fault is untested, not an observed exploit.',
 '- Likelihood: Truncation observed once and explained by code; harmful omission rate and general robustness unmeasured.',
 '- Severity: Informational coverage/interpretability observation; no vulnerability severity or exploit-risk rating.',
 '- Technical Explanation: analyze_ticket clips canonical issue to 180 characters; normalization deduplicates retained noise. Same eligible corpus and source settings; KB score (0.45*1 + 0.55*0.7223500633) + 0.26 = 1.1072925348. First-three fallback stays queue-related.',
 '- Recommended Mitigation: Make query truncation transparent; separately evaluate later-positioned/boundary symptoms before changing extraction; use accurate score labels. No fix applied.',
 '- Conclusion: Relevant retrieval survives this bounded prefix case. This does not show all 20 noise repetitions reached the ranker, general long-query robustness or live Groq behavior. Stop before IR-08.',
]
for name,area in [('test_results.md','Retrieval robustness'),('test_plan.md','Retrieval robustness: noisy text')]:
    path=AUDIT/name; text=path.read_text(encoding='utf-8')
    text=text.replace('IR-07 through IR-15 remain Not run.','IR-07 passed its bounded noisy-prefix case in fallback mode; retrieval saw only 180 canonical characters. IR-08 through IR-15 remain Not run.',1)
    text,count=re.subn(r'^\| IR-07 \|.*$',f'| IR-07 | {area} | Completed (prefix/fallback scope) | [{REL}/notes.md]({REL}/notes.md) | PASS | NO demonstrated; truncation limitation recorded |',text,flags=re.M); assert count==1
    if name=='test_results.md':
        text,count=re.subn(r'^## IR-07[^\n]*\n.*?(?=^## IR-08)',lambda m:'\n'.join(record)+'\n\n',text,flags=re.M|re.S); assert count==1
    write(path,text)
path=AUDIT/'README.md'; text=path.read_text(encoding='utf-8')
text=text.replace('the completed IR-01, IR-02, IR-04, IR-05 and IR-06 cases','the completed IR-01, IR-02, IR-04, IR-05, IR-06 and IR-07 cases')
text=text.replace('- evidence/IR-01/ through evidence/IR-06/: actual retrieval, escalation, manipulation and ambiguity evidence; IR-07 through IR-15 remain reserved.','- evidence/IR-01/ through evidence/IR-07/: actual retrieval, escalation, manipulation, ambiguity and noisy-query evidence; IR-08 through IR-15 remain reserved.')
text=text.replace('IR-07 through IR-15 remain Not run.',f'IR-07 passed the bounded noisy-printer case; the 1099-character input becomes a 180-character retrieval prefix. See [{REL}/notes.md]({REL}/notes.md). IR-08 through IR-15 remain Not run.')
write(path,text)
path=AUDIT/'evidence'/'README.md'; text=path.read_text(encoding='utf-8')
text=text.replace('IR-07/ through IR-15/ contain placeholders only.',f'IR-07/{RUN.name}/ contains the noisy-query PASS, exact lengths and comparison with the saved short printer baseline, with the 180-character retrieval limit documented. IR-08/ through IR-15/ contain placeholders only.')
write(path,text)
additions={
 'vulnerability_register.md':f'''## IR-07 review

IR-07 passed its bounded noisy-printer pipeline case. No security vulnerability was demonstrated and no VULN entry is created. See [{REL}/notes.md]({REL}/notes.md).

- Observation ID: OBS-IR07-01.
- Title: Canonical prefix truncation limits long-input retrieval coverage.
- Related test / components: IR-07; analyze_ticket(), coordinator retrieval input and query normalization.
- Description: 1099 characters were accepted; 1098 stored/masked; only the first 180 formed the retrieval query. Two full noise sentences and a fragment remained; 918 stored suffix characters were omitted.
- Evidence: input_processing.json, original analysis/query captures and baseline_comparison.json in the linked run.
- Impact: this prefix case retained relevant guidance. A later-positioned fault could be omitted, but no such failure, harmful action or exploit was demonstrated.
- Likelihood: truncation observed and code-explained; harmful omission frequency not measured.
- Severity / risk: Informational coverage observation; no security vulnerability severity or formal exploit-risk score.
- Technical explanation: fallback canonical_issue=masked_text.strip()[:180]; coordinator passes only that value to retrieval, then normalization deduplicates retained words. Full text still feeds classification/entity rules.
- Recommended mitigation: accurately describe the tested stage, make truncation transparent and separately evaluate symptom placement before an authorized extraction change.
- Status: documented; no fix applied.

OBS-IR05-02 also recurs: raw adjusted score displays as 111% while explanation clamps to 100%. It is not counted as a new vulnerability. Groq was disabled; this PASS does not measure live generated answers or general long-query robustness.
''',
 'risk_matrix.md':f'''## IR-07 assessment

The noisy printer case passed. OBS-IR07-01 documents canonical truncation and a coverage limitation, without a demonstrated harmful omission or exploit. No formal vulnerability matrix entry or likelihood-impact product is assigned. Detailed evidence and prospective limits are in [{REL}/notes.md]({REL}/notes.md).
''',
 'viva_notes.md':'''## IR-07 observed result

The planned 1099-character noisy printer ticket passed in fallback mode: KB-005 stayed first, the same three queue-related sources formed the answer, and no unrelated repair appeared. The score moved from 1.1337826574 to 1.1072925348, remaining HIGH. The ticket stayed Printers/Medium and SOLUTION_PROPOSED/PENDING.

The key limitation is stage-specific: the route stored 1098 characters after trimming, but the analysis fallback passed only the first 180 into retrieval. That prefix contains the complete fault, two noise sentences and a partial third; normalization reduced it to 80 characters. Full masked text still fed classification rules. Therefore I can defend this bounded issue-first pipeline PASS, but cannot claim the ranker handled all 20 repetitions or a fault at the end. Groq was disabled, no repair was executed, and no security vulnerability was demonstrated.
''',
 'commands.md':f'''## IR-07 reproduction after explicit case authorization

~~~powershell
.\\.venv\\Scripts\\python.exe -B audit\\scripts\\run_ir07.py
~~~

Submits one exact 1099-character noisy printer ticket to a fresh synthetic local database. Reuses the saved IR-05 short baseline after source/config/corpus checks, captures input lengths and original responses, then stops its server. A rerun creates a new timestamped folder; no rerun is needed to read the completed [{REL}/notes.md]({REL}/notes.md). IR-08 and later cases are not executed.
''',
}
for name,addition in additions.items():
    path=AUDIT/name; text=path.read_text(encoding='utf-8')
    if addition.splitlines()[0] not in text:
        write(path,text.rstrip()+'\n\n'+addition)
assert all(hashes(AUDIT/'evidence'/name)==before for name,before in prior.items())
current=hashes(RUN); assert all(current[name]==value for name,value in raw_before.items())
print('IR-07 scoped PASS recorded. Prior and raw evidence unchanged. IR-08 through IR-15 unexecuted.')
