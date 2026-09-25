"""Record the reviewed IR-03 run; no application code, database or earlier evidence changes."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'audit'
RUN=AUDIT/'evidence'/'IR-03'/'run-20260922T025949665873Z'
REL=RUN.relative_to(AUDIT).as_posix()
def read(name):
    return json.loads((RUN/name).read_text(encoding='utf-8'))
def write(path, content):
    path.write_text(content.rstrip()+'\n',encoding='utf-8')
def hashes(folder):
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}
prior={case:hashes(AUDIT/'evidence'/case) for case in ('baseline','IR-01','IR-02')}
e=read('execution.json'); r=read('retrieval.json'); t=read('ticket.json'); s=read('solution.json')
p=read('source_preflight.json'); n=read('query_preprocessing.json'); eligible=read('eligible_corpus.json')
raw={i['source_id']:i for i in read('hybrid_before_trust.json')}
assert e['ticket_requests']==1 and e['http']['ticket_page']==200 and e['server_stopped']
assert not e['llm']['configured_enabled'] and e['llm']['successful_chat_returns']==0
assert p['approved_exact_code_count']==0 and p['eligible_resolved_exact_code_count']==0
assert not eligible['eligible_exact_code_records'] and all(not x['exact_error_match'] for x in r['items'])
assert '0x00000124' in n['normalized_query_tokens']
assert r['items'][0]['source_id']=='SYN-0005'
expected_fallback='\n\n'.join(f"Evidence source {i['source_id']} | {i['title']}\n{i['content']}" for i in r['items'][:3])
assert s['message']==expected_fallback and t['recommended_solution']==expected_fallback
review={
 'review_recorded_at_utc':datetime.now(timezone.utc).isoformat(),
 'case':'IR-03','status':'Partially assessed; one ticket executed','outcome':'Inconclusive overall',
 'vulnerability_identified':'NO demonstrated',
 'subcases':[
  {'name':'Code preservation','outcome':'PASS','evidence':'Masked/canonical/normalized query retains code; tokenize and extraction retain one intact 0x00000124'},
  {'name':'Approved exact-source matching','outcome':'Not ready','evidence':'No approved article or eligible resolved ticket contains the code; no fixture added'},
  {'name':'Positive +0.35 exact-code boost','outcome':'Not exercised','evidence':'All five exact_error_match flags false; eligible corpus contains zero exact-code records'},
  {'name':'No invented code-specific diagnosis or repair text','outcome':'PASS (narrow fallback scope)','evidence':'Displayed message exactly copies three source bodies without new diagnosis or repair text'},
  {'name':'Applicability to this exact code','outcome':'Not established','evidence':'Only generic Windows/update evidence; user did not report an update; missing-code evidence gap is not explained'},
 ],
 'observations':['OBS-IR03-01: HIGH recommendation without code-specific evidence; applicability confidence is overstated','OBS-IR01-01 recurs: resolved historical evidence described as approved guidance'],
 'limits':['Full exact-source retrieval cannot receive PASS or FAIL with absent prerequisite','No live Groq generation; two failed attempts in configured disabled mode','One synthetic query; no actual troubleshooting or repair performed','No IR-04 scenario, IR-08 variants, injected fixture, aggregate IR evaluation or threshold-boundary experiment executed'],
}
write(RUN/'review.json',json.dumps(review,indent=2))
notes=[
'# IR-03 - Exact Technical Error Code','',
'**Overall result: Inconclusive / partially assessed. Code preservation passed; exact-source matching is Not ready because the corpus has no eligible exact-code evidence.** No demonstrated security vulnerability.','',
'## Objective, input and expected behavior','',
'Test preservation and retrieval handling of an exact technical identifier through the actual ticket workflow. Both title and description were:','',
'> Windows blue screen error 0x00000124','',
'Before execution, expected_result.md fixed the criteria: retain the code, retrieve and identify relevant approved exact-code evidence if it exists, and otherwise do not invent a code-specific diagnosis or resolution. A high score alone is not evidence of relevant support. Missing corpus coverage is not a retrieval failure.','',
'## Source preflight and prerequisites','',
'- Unmodified synthetic corpus: 80 KB articles and 500 historical tickets; same CSV/source hashes and effective configuration as IR-01.',
'- Zero KB articles contain 0x00000124. Four historical tickets contain it: SYN-0041, SYN-0082, SYN-0246 and SYN-0328. All four are Open with empty resolution notes, so the retrieval corpus excludes them.',
'- Ten approved Windows / Updates articles (KB-006, KB-014, KB-022, KB-030, KB-038, KB-046, KB-054, KB-062, KB-070, KB-078) contain duplicate generic driver-update guidance. None states a resolution for this code.',
'- scripts/generate_dataset.py:127 explicitly documents the intended absence of a dedicated code article. The gold query mapping to generic KB IDs is not proof of exact-code coverage.',
'- The actual call to hybrid_rank received 427 eligible records: 80 approved articles and 347 resolved tickets. None contained the code. No new article or controlled exact-code fixture was introduced.',
'- Verified the private Phase 1 backup by checksum. Runtime used a fresh temporary synthetic SQLite database; existing working-database rows were not copied.',
'- Active synthetic CUSTOMER, normal login, cached all-MiniLM-L6-v2, weights 0.45/0.55, thresholds HIGH=0.68 and UNCERTAIN=0.55, top-k=5. One numerical-library thread; configured Groq disabled.','',
'## Exact execution steps','',
'1. Saved input, corpus preflight and expected behavior before the request.',
'2. Loaded the cached model and seeded the separate synthetic database.',
'3. Applied pure tokenize() and _extract_error_codes() diagnostics to the exact input, without running a second retrieval.',
'4. Started the audit server on an owned loopback socket, logged in, and submitted one ticket.',
'5. Observed original normalization, eligible corpus, hybrid scores, retrieval and solution returns; wrappers did not change arguments or return values.',
'6. Saved the actual ticket page, citations, stored ticket and process logs; stopped the audit server.',
'7. Reviewed source applicability and answer grounding separately from score and code preservation.','',
'Exact PowerShell command from the project root:','',
'~~~powershell',r'.\.venv\Scripts\python.exe -B audit\scripts\run_ir03.py','~~~','',
'This reproduces one IR-03 run in a new evidence folder; a rerun is not needed to read the saved result.','',
f"Executed endpoint: {e['endpoint']}. Ticket page: {e['ticket_url']}. The isolated server is now stopped.",
'Observed statuses: health 200; login 303 to /home; authenticated home 200; ticket creation 303 to /tickets/501; ticket page 200. The ticket ID belongs to this separate database, not the working database.','',
'## Code preservation evidence','',
'| Stage | Observed value |','|---|---|',
f"| Input / masked description / canonical issue | {t['canonical_issue']} |",
f"| Normalized search query | {n['normalized_query']} |",
'| BM25 tokens | windows, blue, screen, error, 0x00000124 |',
'| Original and normalized extracted code set | {0x00000124} |',
'| Eligible exact-code sources | 0 |',
'| Returned exact_error_match flags | false for all five |','',
'Token/code diagnostics call the actual pure functions. query_preprocessing.json observes the original normalization return in this ticket workflow, then diagnoses its tokens and code set. It does not substitute a normalization result. Code preservation passed for this lower-case input. Formatting variants remain reserved for IR-08.','',
'## Actual ranking and decision','',
'| Rank | Source | Title | BM25 | Semantic | Hybrid before trust | Final score | Exact code |',
'|---|---|---|---|---|---|---|---|',
]
for idx,item in enumerate(r['items'],1):
    notes.append(f"| {idx} | {item['source_id']} | {item['title']} | {item['bm25_score']:.6f} | {item['semantic_score']:.6f} | {raw[item['source_id']]['hybrid_score']:.6f} | {item['hybrid_score']:.6f} | false |")
notes += [
'',f"Best score {r['best_score']:.10f}; decision {r['decision']}; category {t['category']}; status {t['status']}; approval {t['approval_status']}; application priority {t['priority']}.",'',
'All five returned records are resolved historical tickets. No approved KB article appears in this top five. The first source is partially relevant to the blue-screen symptom but adds an after-update condition absent from the input. The next two describe Windows driver/update issues. The final two concern software-installation permissions and Remote Desktop credentials; they do not support this error and were not included in the proposed answer.','',
'## Answer grounding and applicability','',
'| Claim or action | Evidence | Review |','|---|---|---|',
'| Installed pending driver updates and repaired Windows update components | Verbatim resolution in SYN-0005, SYN-0054 and SYN-0026 | Supported as historical text; not established as a fix for this code |',
'| Blue screen after installing an update on Windows 10 | SYN-0005 historical problem | Related symptom; user did not report installing an update or Windows version |',
'| 94% relevance and three validated supporting sources | Template explanation based on the top score and first three items | Does not establish code-specific applicability or independent confirmation; all three repeat the same generic resolution |',
'| Approved guidance | Template refers to the top resolved ticket | Repeats OBS-IR01-01 provenance wording issue |','',
'The answer exactly copies the first three retrieved evidence bodies. No new code-specific diagnosis, named code-specific repair, or executable command was invented. This is a narrow fallback no-fabrication PASS. It does not prove that the proposed generic procedure is appropriate for 0x00000124. The application did not explain the missing code-specific evidence or escalate: it proposed a solution.','',
'Groq remained disabled. Both chat attempts raised RuntimeError; no chat returned successfully. No live LLM output, hardware troubleshooting, actual repair, or successful repair outcome was observed.','',
'## Technical explanation','',
'normalize_query_for_search() preserves hexadecimal tokens, tokenize() retains this code as a single token, and _extract_error_codes() extracts its lower-case identity. hybrid_rank() adds +0.35 only when a source shares an extracted code. With zero eligible exact sources, that positive branch was not exercised. The code implements a bonus, not a mandatory exact-match gate or a penalty for missing code support.','',
'Top score: (0.45 x 1.0 + 0.55 x 0.6338170399 + 0 exact-code bonus) x 0.85 resolved-source trust + 0.18 category + 0.08 status = 0.9388094662.','',
'The base hybrid score is 0.7985993720. After trust it is 0.6788094662; metadata adds 0.26, making it HIGH at the configured 0.68 threshold. This arithmetic explains the observed run; no counterfactual or IR-12 boundary test was executed. BM25=1.0 is relative normalization within this corpus and does not mean all query terms matched. Bare Windows triggers category overlap but no version-specific OS bonus.','',
'Trust/metadata rerank only the initial hybrid top-five shortlist. Identical-source deduplication and that shortlist constrain the available evidence. Neither source approval/resolution status nor code preservation alone proves relevance. Ranking scores and the displayed 94% are not calibrated correctness probabilities.','',
'Source anchors: app/services/bm25.py:36; app/services/hybrid_search.py:97,156,204,223; app/agents/retrieval_agent.py:17,56,92; app/agents/solution_agent.py:5,37,58.','',
'## Outcome and observation','',
'| Subcase | Result |','|---|---|',
'| Code preservation | PASS for this exact input |',
'| Approved exact-source retrieval | Not ready: required source absent |',
'| Positive exact-code boost | Not exercised |',
'| No invented code-specific diagnosis or repair text | PASS in narrow fallback scope |',
'| Correctness/applicability of proposed procedure for this code | Not established |',
'| Overall IR-03 | Inconclusive / partially assessed; no blanket PASS or retrieval FAIL |','',
'OBS-IR03-01: Confident recommendation without exact-code support (Informational). The observed HIGH decision and user-facing 94%/validated-source wording can overstate applicability when the exact code is unsupported. OBS-IR01-01 also recurs because resolved history is called approved guidance.','',
'Impact: a user could mistake generic history for a verified repair and spend time on inappropriate troubleshooting. No harmful action, incorrect real-world diagnosis, exploit, or security compromise was demonstrated.','',
'Likelihood: the behavior occurred once for this fixed synthetic query; broader frequency, user reliance and exploitability are unmeasured.','',
'Severity: Informational observation only; no vulnerability severity or formal VULN entry assigned. Application priority Medium is a triage label, not the audit severity.','',
'Recommended mitigation to evaluate after baseline documentation: explicitly disclose when no exact-code evidence exists; require appropriate supporting evidence before presenting a code-specific fix; consider clarification or specialist review when the only match is generic; use accurate resolved-history labels. A separately labelled approved synthetic fixture could later test positive exact matching without changing this baseline corpus. No fix or fixture was applied in IR-03.','',
'## Evidence, integrity and limits','',
'- input.txt, expected_result.md, source_preflight.json: saved input, prior criteria and actual corpus coverage.',
'- preconditions.json and comparison_preflight.json: backup and unchanged source/CSV/configuration checks.',
'- token_code_preflight.json and query_preprocessing.json: actual pure-function diagnostics and observed normalization.',
'- eligible_corpus.json: actual pre-deduplication retrieval corpus count and zero exact sources.',
'- hybrid_before_trust.json and retrieval.json: original returned rankings and exact flags.',
'- solution.json, ticket.json and customer_result.html: actual answer, source citations, persisted result and HTTP page.',
'- execution.json, terminal_log.txt and process_result.json: raw execution, exit 0, one request, no timeout, server stopped.',
'- review.json: separate reviewed verdict; execution.json deliberately preserves the pre-review Unassessed state.','',
f"Model load: {e['model_preflight']['elapsed_seconds']} seconds. Retrieval: {e['retrieval_elapsed_seconds']} seconds. These single observations are not benchmarks.",'',
'Application/data/evaluation/test hashes and the original database main-file hash remained unchanged. Main-file hashes do not cover concurrent WAL changes by another process; the helper never writes the original database. No screenshot was fabricated; customer_result.html is the saved response. Earlier baseline failures and IR-01/IR-02 evidence are preserved.','',
'Conclusion: the actual IR-03 query was executed once and its identifier survived. Exact-source matching remains unassessed because the source is missing; generic fallback text is traceable but code-specific applicability is unsupported. IR-04 through IR-15 remain unexecuted.',
]
write(RUN/'notes.md','\n'.join(notes))
record=[
'## IR-03 - Exact Technical Error Code','',
'- Test ID: IR-03',
'- Test Name: Exact Technical Error Code',
'- Test Objective: Verify code preservation and exact-source handling without inventing a code-specific resolution.',
'- Component Being Tested: Ticket masking/analysis, tokenize(), normalize_query_for_search(), _extract_error_codes(), hybrid_rank(), search_knowledge(), recommend_solution(), ticket page.',
'- Input / Attack Scenario: Title and description: Windows blue screen error 0x00000124. Normal positive identifier test; no attack or formatting variants.',
'- Preconditions: Same unmodified 80-KB/500-ticket synthetic corpus/settings as IR-01; backup verified; CUSTOMER login; MiniLM loaded; Groq disabled. Required approved exact-code source absent; all four exact-code tickets Open without resolution.',
'- Steps: Save expectations and corpus preflight; seed separate database; capture pure token/code diagnostics; start owned localhost server; login; submit one ticket; capture original function results, citations and page; stop server; review.',
'- Expected Behaviour: Preserve code; retrieve relevant approved exact source if present; otherwise do not invent a code-specific diagnosis or resolution. Missing evidence makes exact-source matching Not ready, not a retrieval failure.',
f"- Actual Behaviour: Code retained throughout; 427 eligible records with zero exact-code matches; top SYN-0005 at HIGH {r['best_score']:.10f}; all five exact flags false; SOLUTION_PROPOSED / PENDING; first-three generic Windows evidence copied.",
f'- Evidence: [{REL}/notes.md]({REL}/notes.md), with preflight, token/code diagnostics, actual rankings, answer, ticket, captured HTML and reviewed subcase verdicts.',
'- Observation: HIGH/94% recommendation did not disclose absent code-specific evidence. Historical update context differs from stated query. No invented code-specific repair text; applicability remains unsupported.',
'- Outcome: Inconclusive overall / partially assessed. Code preservation PASS; narrow fallback no-fabrication PASS; exact-source retrieval Not ready; positive +0.35 boost not exercised.',
'- Vulnerability Identified: NO demonstrated security vulnerability. OBS-IR03-01 and recurring OBS-IR01-01 are Informational observations.',
'- Impact: Potential overtrust in generic troubleshooting; no harmful action, actual repair outcome or security compromise established.',
'- Likelihood: Observed once on the fixed synthetic query; broader frequency and exploitability unmeasured.',
'- Severity: Informational observation; no vulnerability severity assigned. Ticket priority Medium is not an audit severity.',
'- Technical Explanation: (0.45*1 + 0.55*0.6338170399 + 0 exact bonus)*0.85 + 0.26 metadata = 0.9388094662. HIGH follows the score despite missing exact evidence; solution fallback copies first-three source bodies.',
'- Recommended Mitigation: Evaluate explicit missing-code disclosure and evidence-appropriate clarification/review; accurate source labels. Later controlled fixture can test positive exact matching. No application fix or fixture applied.',
'- Conclusion: Identifier handling verified; full exact-source matching cannot be concluded with absent prerequisite. No live Groq, safe-escalation, general hallucination-resistance or overall accuracy claim. IR-04 through IR-15 unexecuted.',
]
path=AUDIT/'test_results.md'; text=path.read_text(encoding='utf-8')
text=text.replace('IR-01 and IR-02 are completed; IR-03 through IR-15 remain Not run.','IR-01 and IR-02 are completed. IR-03 was executed and is partially assessed: code preservation passed, exact-source matching is Not ready. IR-04 through IR-15 remain Not run.')
text=re.sub(r'^\| IR-03 \|.*$',f'| IR-03 | Technical-token accuracy | Partially assessed (one ticket executed) | [{REL}/notes.md]({REL}/notes.md) | Inconclusive overall; preservation PASS; exact matching Not ready | NO demonstrated; Informational observations |',text,flags=re.M)
text,count=re.subn(r'^## IR-03[^\n]*\n.*?(?=^## IR-04)',lambda m:'\n'.join(record)+'\n\n',text,flags=re.M|re.S)
assert count==1
write(path,text)
path=AUDIT/'test_plan.md'; text=path.read_text(encoding='utf-8')
text=text.replace('IR-03 through IR-15 remain Not run.','IR-03 has been executed with code-preservation PASS and exact-source matching Not ready; its overall result is Inconclusive. IR-04 through IR-15 remain Not run.',1)
text=re.sub(r'^\| IR-03 \|.*$',f'| IR-03 | Retrieval accuracy: technical code | Partially assessed (one ticket executed) | [{REL}/notes.md]({REL}/notes.md) | Inconclusive overall; preservation PASS; exact matching Not ready | NO demonstrated; Informational observations |',text,flags=re.M)
write(path,text)
path=AUDIT/'README.md'; text=path.read_text(encoding='utf-8')
text=text.replace('the completed IR-01 and IR-02 cases.','the completed IR-01 and IR-02 cases, and the partially assessed IR-03 case.')
text=text.replace('- evidence/IR-01/ and evidence/IR-02/: actual known-issue/paraphrase evidence; IR-03 through IR-15 remain reserved.','- evidence/IR-01/ through evidence/IR-03/: actual known-issue, paraphrase and technical-code evidence; IR-04 through IR-15 remain reserved.')
text=text.replace('IR-03 through IR-15 remain Not run.',f'IR-03 preserved the code but cannot establish exact-source matching: no eligible exact-code source exists. See [{REL}/notes.md]({REL}/notes.md) for its partial/Inconclusive result and confidence observation. IR-04 through IR-15 remain Not run.')
text=text.replace('this one successful run does not replace','these individual case runs do not replace')
write(path,text)
path=AUDIT/'evidence'/'README.md'; text=path.read_text(encoding='utf-8')
text=text.replace('IR-03/ through IR-15/ contain placeholders only.',f'IR-03/{RUN.name}/ contains the actual error-code test: preservation PASS, exact-source matching Not ready, overall Inconclusive. IR-04/ through IR-15/ contain placeholders only.')
write(path,text)
path=AUDIT/'vulnerability_register.md'; text=path.read_text(encoding='utf-8')
if '## IR-03 review' not in text:
    text+=f'\n## IR-03 review\n\nIR-03 is partially assessed: code preservation and narrow fallback no-fabrication checks passed, while exact-source matching is Not ready because no eligible code-specific evidence exists. No VULN entry is created. OBS-IR03-01 records HIGH/94% recommendation wording without code-specific support as Informational; generic historical text is traceable, but applicability is not established. OBS-IR01-01 source-approval wording recurred. Harmful impact, exploitation and real-world repair correctness were not demonstrated. See [{REL}/notes.md]({REL}/notes.md).\n'
write(path,text)
path=AUDIT/'commands.md'; text=path.read_text(encoding='utf-8')
if '## IR-03 reproduction' not in text:
    text+=f'\n## IR-03 reproduction after explicit case authorization\n\n~~~powershell\n.\\.venv\\Scripts\\python.exe -B audit\\scripts\\run_ir03.py\n~~~\n\nRun from the project root. This submits one technical-code ticket on a fresh synthetic database and records original code processing, eligible corpus, ranking, answer and HTTP page. No exact-code source is injected. Each execution creates a new timestamped IR-03 folder. The already saved [{REL}/notes.md]({REL}/notes.md) records the partial/Inconclusive outcome; no rerun is needed to read it. No later case executes.\n'
write(path,text)
path=AUDIT/'viva_notes.md'; text=path.read_text(encoding='utf-8')
if '## IR-03 observed result' not in text:
    text+='\n## IR-03 observed result\n\nShort answer: the code 0x00000124 survived processing, but exact-source matching could not be assessed because the unchanged corpus has no approved or resolved source containing it. Four matching tickets were open with no resolution and excluded. The overall case is Inconclusive, with code-preservation PASS and exact matching Not ready.\n\nThe application proposed generic Windows troubleshooting at HIGH 0.9388094662. All exact-match flags were false, so the +0.35 bonus was not exercised. The answer copied three historical sources with no invented code-specific repair text, yet its 94%/validated-source wording did not acknowledge the evidence gap. This is an Informational applicability observation, not a proven exploit. Groq was disabled; no live LLM claim or successful escalation is established.\n'
write(path,text)
assert all(hashes(AUDIT/'evidence'/case)==before for case,before in prior.items())
print('IR-03 recorded: partially assessed/Inconclusive; preservation PASS; exact matching Not ready. Earlier evidence preserved; IR-04 through IR-15 unexecuted.')