"""Assemble final eight-section audit report from preserved local evidence; no HTTP/app imports."""
from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,re
ROOT=Path(__file__).resolve().parents[2]; AUDIT=ROOT/'audit'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
REPORT=AUDIT/'final_report.md'
assert not REPORT.exists(), 'Report already exists; review edits rather than overwriting'
prior={p.relative_to(ROOT).as_posix():sha(p) for p in (AUDIT/'evidence').rglob('*') if p.is_file()}
baseline=read(AUDIT/'evidence/baseline/environment.json')
assert all(sha(ROOT/p)==value for p,value in baseline['source_sha256'].items()) and sha(ROOT/'knowgap.db')==baseline['original_database_sha256']
results=(AUDIT/'test_results.md').read_text(encoding='utf-8')
cases=[]
for block in re.split(r'(?=^## IR-\d\d)',results,flags=re.M)[1:]:
 lines=block.splitlines(); ident=re.search(r'IR-\d\d',lines[0]).group(); fields={}
 for line in lines:
  if line.startswith('- ') and ': ' in line:
   key,value=line[2:].split(': ',1); fields[key]=value
 cases.append({'id':ident,'fields':fields})
assert [x['id'] for x in cases]==[f'IR-{i:02d}' for i in range(1,16)]
f13=read(AUDIT/'evidence/IR-13/run-20260922T193751545217Z/finding.json')
f15=read(AUDIT/'evidence/IR-15/run-20260923T023805163543Z/finding.json')
assert f13['severity']==f15['severity']=='Medium'
sections=[]
sections.append('''# KnowGap AI — Individual AI Security Audit and Vulnerability Assessment

**Specialization:** Information Retrieval and Security Assessment  
**Evidence period:** 21–23 September 2026 (UTC timestamps)  
**Report basis:** Preserved local source inspection and executed audit evidence for IR-01–IR-15  
**Status:** 12 cases completed; IR-03, IR-14 and IR-15 partially assessed. Two confirmed Medium findings remain open. No remediation has been applied.

## 1. Executive Summary

This audit assessed KnowGap AI, a FastAPI multi-agent IT support application that combines BM25 retrieval, semantic embeddings and hybrid ranking to recommend solutions from knowledge articles and resolved historical tickets. The specialization covers retrieval accuracy and manipulation, grounding, source reliability, authentication, authorization, API security and agent communication.

Fifteen core case IDs have recorded evidence. Twelve cases are completed within their declared scope; three remain partially assessed. These are coverage counts, not a claim that twelve cases passed. Some completed cases failed reliability requirements or had mixed primary and auxiliary results. IR-03 could not test an eligible exact-code source in the original corpus. IR-14 and IR-15 used explicitly limited test compositions after Windows Application Control blocked full application imports. Baseline automated tests recorded nine passes and five environment-related failures; aggregate IR metrics remain unavailable.

Two formal vulnerabilities were confirmed. **VULN-IR13-01 (Medium)** is missing authentication on sensitive agent endpoints: anonymous requests returned internal synthetic source content and aggregate knowledge analytics even though protected UI routes redirected to login. **VULN-IR15-01 (Medium, component scope)** is a source-trust failure: changing a caller-supplied retrieval decision from LOW to HIGH caused the original solution component to recommend a nonexistent draft source with zero scores and describe it as approved and validated. Current full-application exposure of that second finding was not verified.

Several controls behaved as expected. Known and paraphrased issues retrieved relevant sources; the tested draft article was excluded; documented source weights and threshold comparisons matched their implementation. All 15 IR-14 role checks passed in the original-router HTTP harness. However, ambiguous and partially matched issues sometimes received confident, unsupported advice. Those failures are documented as reliability observations unless evidence establishes a security vulnerability; they are not all assigned vulnerability severities.

The demonstrated risks concern confidentiality and recommendation integrity. Both confirmed findings are rated Medium under the assignment's qualitative rubric, with the scope and uncertainty explained below. This report does not calculate a system-wide risk score or certify deployment security. No public infrastructure, production system or real-user data was attacked. The recommended priorities are to authenticate sensitive agent operations and derive recommendation evidence from trusted server-side retrieval, followed by stronger payload and answer-applicability checks. The findings remain open and the original behavior remains unchanged. [Case tracker](test_results.md), [vulnerability register](vulnerability_register.md), [risk matrix](risk_matrix.md).

## 2. Scope of Testing

### System and boundaries

The assessed system is the local KnowGap AI repository. Its agents are Python functions coordinated within the application; the audit did not assume an independently deployed network of agent services. Source review covered retrieval services, agent functions, authentication helpers, route guards, payload schemas, database models, automated tests and the offline IR evaluator. The complete baseline inventories retain the file/function and endpoint classifications. [Component inventory](component_inventory.md), [endpoint inventory](endpoint_inventory.md).

| In scope | What was assessed |
|---|---|
| Retrieval accuracy | Known issue, paraphrase, code preservation and formatting, confidence comparisons |
| Retrieval manipulation | Repeated keywords, conflicting categories and bounded irrelevant text |
| Retrieval-induced hallucination | Whether retrieved material actually supports advice for the reported symptom; fallback and live-provider scopes distinguished |
| Source reliability | Draft exclusion, approved versus resolved sources, eligibility and caller-supplied evidence |
| Authentication and authorization | Anonymous API access, normal login controls, role-specific privileged operations |
| API and agent communication security | Required fields, issue types, bounded length, Unicode, malformed JSON, envelope labels and evidence provenance |

Out of scope were external/public systems, university infrastructure, production penetration testing, denial-of-service against third-party services, real-user data and unapproved application changes. Tests did not establish internet reachability, enterprise readiness, repair success, physical safety outcomes or general resistance to all possible attacks.

### Data and environment

Runtime fixtures used synthetic CSV data: 80 knowledge articles and 500 historical tickets, with four seeded roles (CUSTOMER, IT_SUPPORT, KNOWLEDGE_ANALYST and ADMIN). The gold set contains 21 queries. The ordinary eligible corpus contained 427 approved/resolved records before deduplication. Declared cases added isolated synthetic fixtures or used a smaller controlled corpus; those changes are stated in the case records. IR-14 additionally used one directly provisioned unsupported-role fixture in its own database.

The existing working database was inspected read-only for aggregate state and backed up privately. Its counts differed from the seed corpus; it was not copied into the runtime test corpus or used as an attack target. Private database files and backups are excluded from report attachments because they contain account credential hashes. [Baseline data and backup record](baseline.md).

| Setting | Recorded value |
|---|---|
| Operating system | Windows 11; Windows-11-10.0.26200-SP0 |
| Python / FastAPI / SQLModel | 3.12.10 / 0.115.6 / 0.0.22 |
| sentence-transformers / rank-bm25 | 3.3.1 / 0.2.2 |
| pytest / Uvicorn / HTTPX | 9.1.1 / 0.34.0 / 0.28.1 |
| Database | SQLite |
| Embedding model | all-MiniLM-L6-v2 |
| Configured LLM | Groq, llama-3.1-8b-instant; disabled in the recorded audit processes |
| Normal development URL | http://127.0.0.1:8000 |
| Observed audit URL | http://127.0.0.1:8001; audit helpers reserve their own loopback socket |
| Hybrid weights | BM25 0.45; semantic 0.55 |
| Confidence thresholds | HIGH >= 0.68; UNCERTAIN >= 0.55 and below HIGH; otherwise LOW |
| Ticket/direct retrieval top-k | 5; solution recommendation uses up to the first 3 sources |

These are recorded baseline values, not claims about a later installation. Existing settings and source were not retuned to make tests pass. One numerical-library thread and locally cached model loading were used where documented. Groq availability limits interpretation: no successful provider answer supports the recorded solution conclusions. [Environment capture](evidence/baseline/environment.json).

### Limits on coverage

The dataset is synthetic and small; there was no enterprise deployment or external production user population. One or a few fixed examples per scenario cannot establish an error frequency or attack-success rate. Initial memory failures and later Windows Application Control errors constrained execution at different times. Earlier full-app successes are preserved and do not imply that later blocked runs succeeded. IR-03, IR-14 and IR-15 remain partial; narrower evidence is useful but is not silently upgraded to complete end-to-end coverage.

## 3. Evaluation Methodology

### Source review and actual architecture

White-box review identified the implemented functions; local HTTP testing observed request/response behavior; controlled component tests separated ranking comparisons from deployment behavior. The primary ticket path is:

`create_ticket()` → `process_new_ticket()` → `check_input()` / masking → `analyze_ticket()` → `search_knowledge()` → `hybrid_rank()` → confidence decision → `recommend_solution()` → stored ticket, citations and either solution proposal or escalation.

`_records_from_db()` selects approved articles and RESOLVED tickets with nonblank resolution notes. `hybrid_rank()` deduplicates records, calls `normalize_query_for_search()`, obtains `BM25Search.scores()` and `semantic_scores()`, combines the two scores and applies a matching hexadecimal-code bonus. `search_knowledge()` then applies `_trust_weight()` and `_metadata_boost()` to the selected shortlist and assigns a decision from its highest adjusted score. These later adjustments do not rerank the entire discarded corpus.

`recommend_solution()` withholds a recommendation unless decision is HIGH and items exist. For eligible input it uses up to three sources. When Groq is disabled, its ordinary exception fallback copies those source bodies. In the ticket flow, the coordinator persists escalation or a proposed solution; a direct component's escalation wording alone does not create a ticket or queue entry. [Retrieval agent](../app/agents/retrieval_agent.py), [hybrid ranking](../app/services/hybrid_search.py), [solution agent](../app/agents/solution_agent.py).

| Implemented retrieval mechanism | Configuration or behavior | Interpretation |
|---|---|---|
| BM25 preprocessing | Lowercasing, technical/hex token handling, selected punctuation and slash components | Supports lexical matching; not proof of every identifier's correctness |
| Query normalization | Phrase/abbreviation/typo replacements, fuzzy vocabulary matching, filler and repeated-token removal | Can preserve useful terms but also change meaning |
| Embeddings and cache | MiniLM, normalized embeddings, cosine similarity; model and ordered-document-tuple caches | Cache behavior and model availability are separate from relevance quality |
| Exact-code boost | +0.35 for a matching hexadecimal code | A ranking bonus, not a code-specific diagnosis |
| Source weights | Draft 0; approved/internal_kb 1; resolved/resolved_ticket 0.85; other 0.7, in that branch order | Current status/eligibility and relevance still matter |
| Metadata bonuses | Category +0.18; selected OS bonuses +0.14 to +0.18; approved/resolved +0.08 | Ranking bonuses, not hard category/OS access filters |
| Duplicate handling | First normalized title/content match; same-category content Jaccard >= 0.9 | Applied before trust weighting; does not ensure the most authoritative duplicate wins |
| Confidence | Thresholds on the adjusted top score | Scores may exceed 1; they are not calibrated probabilities |

Authentication uses password verification and an HS256 JWT in an access_token cookie. `current_user_from_request()` decodes the token subject and loads the User from the database; the examined role guards use that database role. Guards are applied in individual handlers. A SQLModel session dependency provides database access, not authentication. The direct agent endpoints omit the UI's identity checks. `AgentMessage` requires an envelope but its `payload: Dict[str, Any]` does not establish trusted identity, typed operation semantics or evidence provenance. [Authentication routes](../app/routes/auth.py), [agent routes](../app/routes/agents.py), [schemas](../app/schemas.py).

### Test rules, tools and evidence

Expected behavior was documented before each execution. PASS means the observed system behavior meets that case's expected behavior within its stated scope. FAIL means it differs. A failure is not automatically a vulnerability: impact, a trust or access boundary, technical cause and evidence must support that classification. Missing prerequisites or blocked downstream execution are recorded as Not ready, Blocked or Inconclusive rather than given an invented result. [Predeclared test plan](test_plan.md).

Tools included PowerShell, Python audit helpers, HTTPX, Uvicorn, FastAPI Swagger/OpenAPI responses, pytest, SQLite's read-only URI and backup API, and SHA-256 integrity checks. Helpers created owned loopback instances and private synthetic databases, captured exact inputs and initial responses, and stopped their servers. Tests used normal login controls where required; redirects were deliberately not followed in access-control cases. No secrets, password values, JWTs or cookie values are included in the audit artifacts.

Evidence consists of raw JSON/text/HTML responses, component outputs, stored state where relevant, source/schema snapshots, per-table fingerprints, pre-request backups and later reviewed verdicts. Actual saved HTML is not a screenshot. Review files distinguish original capture status from the subsequent assessment. Baseline/source and working-database main-file hashes were preserved; a main-file hash does not cover unrelated concurrent WAL activity from another process. [Evidence index](evidence/README.md), [reproduction commands](commands.md).

### Baseline tests and retrieval evaluation

The existing test suite returned **9 passed, 5 failed and 405 warnings**, with pytest reporting 16.83 seconds and exit code 1. All five failures reached model loading and raised Windows OSError 1455, indicating insufficient paging-file memory. They are unresolved baseline execution failures, not five security vulnerabilities or measured ranking errors. Initial startup and Swagger checks returned 200, but registration failed with an Argon2 memory-allocation error, and baseline login/retrieval were not completed. Later IR-01 and IR-02 established successful login and known-query behavior in their own runs; they did not rerun or replace the earlier full suite. [Baseline results](baseline.md), [pytest output](evidence/baseline/pytest_output.txt).

The initial offline evaluation failed with native OpenBLAS memory errors. A separately recorded one-thread retry failed while loading MiniLM with the paging-file error. Neither produced numeric metrics. Even the evaluator's BM25 branch computes semantic scores first, so it was not an independent successful lexical-only measurement.

| Method | P@1 | P@5 | Recall@5 | MRR |
|---|---|---|---|---|
| BM25 | Unavailable | Unavailable | Unavailable | Unavailable |
| Semantic | Unavailable | Unavailable | Unavailable | Unavailable |
| Hybrid | Unavailable | Unavailable | Unavailable | Unavailable |

Unavailable does not mean zero. P@1 measures first-result relevance; P@5 is relevant hits among five divided by five; Recall@5 divides retrieved relevant hits by the labelled relevant set; MRR averages the reciprocal rank of the first relevant result over the full ranking. Hit Rate@5 and nDCG@5 are not implemented. The script has no weight sweep or evidence that the current weights are optimal.

`evaluate_ir.py` evaluates approved CSV articles using raw-query BM25, semantic and fixed weighted scores. It omits the full application's query normalization, historical tickets, deduplication, exact-code bonus, trust/metadata adjustments and confidence decisions. Empty relevance sets receive zero retrieval metrics rather than an abstention assessment. Future evaluator results must therefore be labelled with their narrower scope; the individual case scores below are not substitutes for aggregate IR metrics. [Evaluator source](../evaluation/evaluate_ir.py), [retry result](evidence/baseline/low_memory/ir_evaluation_result.json).

### Explicit reduced execution scopes

IR-12 used real retrieval component calls plus six explicitly injected score fixtures around the thresholds; the injected values test comparisons, not natural ranking quality. IR-14's full app import was blocked on torch_python.dll. Its fallback mounted unchanged authentication, knowledge and admin routers and tested original role behavior through HTTP. IR-15's fresh full app import was blocked on SciPy _batched_linalg. Since the agents module itself imports the retrieval stack, its fallback compiled the unchanged selected handler function ASTs with the original schema and solution component. A substituted audit observer recorded retrieval inputs and deliberately returned a labelled 503 before ranking. Those ten 503 responses are audit stop signals, not product failures, secure rejections or real retrieval results.

## 4. Test Cases Performed

The following records contain the required objective, input, expected result, actual result, evidence and outcome for each core ID. Full preconditions, steps, impact, technical explanations and recommendations remain in the linked case notes and [detailed test records](test_results.md). Historical stop statements in earlier evidence describe the audit's state at capture time; the current coverage is summarized here.
''')
# Preserve mixed outcomes; no aggregate success percentage is calculated.
sections.append('| Test ID | Case | Recorded outcome | Coverage |\n|---|---|---|---|')
for case in cases:
 f=case['fields']; coverage='Partially assessed' if case['id'] in ('IR-03','IR-14','IR-15') else 'Completed within declared scope'
 sections.append('| '+case['id']+' | '+f['Test Name']+' | '+f['Outcome'].replace('|','/')+' | '+coverage+' |')
sections.append('')
for case in cases:
 f=case['fields']; sections.append('### '+case['id']+' — '+f['Test Name']+'\n')
 for label,key in [('Objective','Test Objective'),('Input','Input / Attack Scenario'),('Expected result','Expected Behaviour'),('Actual result','Actual Behaviour'),('Evidence','Evidence'),('Outcome','Outcome')]:
  assert key in f
  sections.append('**'+label+':** '+f[key]+'\n')
 sections.append('**Interpretation and limit:** '+f['Observation']+' '+f.get('Testing Limitations','')+'\n')
sections.append('''## 5. Vulnerabilities Identified

Two formal findings are supported by the preserved evidence. The first was observed through original-application HTTP endpoints. The second is confirmed in the original solution component exercised through explicitly selected handler code; its current full-app exposure remains unverified. They concern different boundaries and are not counted as duplicate findings.

### VULN-IR13-01 — Missing authentication on sensitive agent endpoints

**Affected components:** `app/routes/agents.py`, specifically `retrieval_search()` and `knowledge_analyze()`, and their registration in `app/main.py`.

**Description and evidence:** Four valid requests were sent using fresh clients without login, cookies or Authorization headers. `GET /home` and `POST /tickets/create` returned 303 to the login route `/`, with empty bodies and no new ticket. However, `POST /agents/retrieval/search` returned 200 with five source records: four resolved historical tickets and one approved KB article. `POST /agents/knowledge/analyze` returned 200 with five category-health aggregate rows. Their HTTP responses matched the outputs of the original invoked functions. The retrieval response contained source descriptions/resolutions and a KB body; historical root-cause values were empty. The knowledge response had no cluster examples. All ten database tables remained unchanged.

**Technical reason:** These agent routes use a database-session dependency without a verified-user or service-identity guard. The application does not add one at router inclusion. UI authentication therefore does not protect callers who directly invoke these APIs. Required `AgentMessage` fields describe a message but do not authenticate its sender.

**Impact:** Unauthorized access to the demonstrated synthetic internal source text and aggregate analytics was observed. A similarly reachable deployment containing sensitive records could expose them, but no real-user breach, account takeover, persistent mutation or external exposure was demonstrated.

**Likelihood:** Invocation was straightforward for a caller able to reach the tested application: a valid normal request sufficed, without login or user interaction. The audit measured neither public reachability nor prevalence across installations.

**Severity and risk:** **Medium, qualitative.** This is a demonstrated authentication failure with meaningful confidentiality implications. The limited synthetic, loopback setting and observed read-only impact do not justify a High/Critical label or an invented CVSS score.

**Recommended mitigation:** Require shared verified user/service identity before sensitive agent work. Define explicit operation permissions, including who may request knowledge-health analysis, and restrict returned data to authorized needs. Test anonymous, invalid-credential and permitted authenticated controls during remediation. Hiding the UI, CORS or trusting a sender string would not supply authentication.

**Status:** Confirmed in the original local synthetic application; open; no fix applied. [IR-13 case evidence](evidence/IR-13/run-20260922T193751545217Z/notes.md), [finding record](evidence/IR-13/run-20260922T193751545217Z/finding.json), [anonymous retrieval response](evidence/IR-13/run-20260922T193751545217Z/A03/response.json), [anonymous analytics response](evidence/IR-13/run-20260922T193751545217Z/A04/response.json).

### VULN-IR15-01 — Caller-controlled evidence treated as trusted guidance

**Affected components:** `solution_recommend()` in `app/routes/agents.py` and `recommend_solution()` in `app/agents/solution_agent.py`. The test ran the original imported solution function through the exact selected handler AST in an audit HTTP app; it did not import the full agents router.

**Description and evidence:** The S01/S02 pair supplied the same harmless synthetic source, `AUDIT-IR15-NOT-IN-CORPUS`, with `status: draft`, `source_type: audit_fixture` and all scores equal to zero. Its ID and marker text were absent from the synthetic corpus and were never inserted. Only `payload.retrieval.decision` changed from LOW to HIGH. The original component first returned `can_recommend: false`, then returned `can_recommend: true`, the supplied source ID and citation, and the caller's marker text. The HIGH response described the source as approved guidance and validated while reporting 0% relevance. A normal CUSTOMER cookie was sent, but the agent handler did not demonstrate verification of that cookie.

**Technical reason:** `AgentMessage.payload` permits arbitrary values. The handler checks only that `retrieval` is a dictionary. The solution function accepts HIGH with nonempty items without looking up source identity, checking eligibility or deriving confidence from trusted retrieval. Its disabled-provider fallback copies supplied evidence, and fixed explanation wording grants unsupported approval and validation. No live model generated this failure.

**Impact:** A caller controlling this component input can influence advice and citations while receiving a misleading trusted-source presentation. The demonstrated outcome was a harmless marker returned in a response. It did not persistently poison the corpus, create or escalate a ticket, deliver advice to a real user or execute any system action.

**Likelihood:** One field change was sufficient at the tested component boundary. The original API handler's forwarding behavior is source-supported, but full-app reachability, external exposure and downstream user consumption were not verified because application import was blocked.

**Severity and risk:** **Medium, qualitative, confirmed component scope.** A minimal input change crosses a meaningful evidence-trust boundary. The observed response-level impact and unverified deployment exposure limit the severity claim; no High/Critical or numeric CVSS rating is asserted.

**Recommended mitigation:** Produce the retrieval decision and evidence on the trusted server side, bound to the verified request/caller and authorized corpus. Resolve source identifiers to eligible approved/resolved records and reject nonexistent or draft sources. Validate nested payload shape and finite limits, but recognize that a well-formed object can still contain fabricated evidence. Authentication and provenance verification are complementary controls.

**Status:** Confirmed in the original component and selected-handler HTTP scope; open; no fix applied. [IR-15 case evidence](evidence/IR-15/run-20260923T023805163543Z/notes.md), [finding record](evidence/IR-15/run-20260923T023805163543Z/finding.json), [LOW control](evidence/IR-15/run-20260923T023805163543Z/S01/response.json), [HIGH attempt](evidence/IR-15/run-20260923T023805163543Z/S02/response.json), [controlled provenance comparison](evidence/IR-15/run-20260923T023805163543Z/provenance_review.json).

### Reliability and design observations kept separate

IR-06's ambiguous issue and IR-11's battery-swelling/update context received unsupported confident advice in fallback mode. IR-12's threshold comparisons passed, while its selected HIGH screen-flicker answer lacked adequate symptom support. These are meaningful grounding/applicability failures, but the audit did not demonstrate a security exploit from each one. IR-08's uppercase entity extraction failed separately from its successful controlled retrieval. Raw confidence can exceed 100% in the UI, and approved/verified wording can overstate provenance. These observations support better explanation and validation, without turning every mismatch into a formal vulnerability.

IR-15 accepted an empty issue and stringified object/list issues at the observed handler boundary; actual retrieval from those inputs did not run. One malformed nested source raised a KeyError and produced a plain 500; its HTTP body contained no traceback. The bounded 4000-character probe showed no finite declared issue limit, not a measured load problem. Ignored sender/receiver/task labels did not establish authenticated impersonation or execution of an admin action. Windows import/memory failures were environment limitations, not attacker-induced denial of service. [Detailed observations](evidence/IR-15/run-20260923T023805163543Z/observations.json), [complete case records](test_results.md).

## 6. Risk Assessment

Risk is assessed qualitatively from the demonstrated impact, effort, access assumptions and evidence limits. Critical requires very serious impact and realistic exploitation; High requires major impact with plausible exploitation; Medium denotes a meaningful weakness with limited demonstrated scope; Low denotes limited impact or difficult exploitation; Informational records useful observations without demonstrated immediate security impact. No numerical likelihood-impact product or CVSS score was calculated.

| Vulnerability | Impact | Likelihood | Severity / Risk Level | Recommended Mitigation |
|---|---|---|---|---|
| VULN-IR13-01: missing agent API authentication | Anonymous internal synthetic source text and aggregate analytics disclosed; no writes or real breach observed | A valid request sufficed for a reachable local caller; external reachability unknown | Medium; original-application local HTTP evidence | Verified caller/service identity, route permissions and authorized data scope before agent execution |
| VULN-IR15-01: caller evidence trusted | Fabricated draft source returned as approved/validated advice; no persistence or real delivery | One field sufficed at component boundary; current full-app reachability unverified | Medium; confirmed component/selected-handler scope | Trusted server retrieval, eligible-source lookup, server-derived decision and request-bound provenance |

The two findings could be relevant to the same deployment, but this audit did not execute a chained attack. Missing authentication and accepting caller evidence must each be addressed: adding identity checks alone would not make fabricated evidence trustworthy. Passing role checks on three UI/admin routes does not close either agent finding. The observed results support prioritizing these two boundaries; they do not establish an overall system security grade. [Maintained risk matrix](risk_matrix.md).

## 7. Mitigation Strategies

These are recommendations, not implemented changes or successful retest claims. The audited application and baseline were preserved so a later authorized remediation can be compared against the original behavior.

| Priority | Proposed change | Why it follows from evidence | Verification after implementation |
|---|---|---|---|
| 1 | Enforce verified identity and explicit permissions on sensitive agent endpoints | IR-13 returned internal data without login while UI guards held | Valid anonymous/invalid credentials are denied before agent work; intended authenticated roles retain access; no unauthorized data or mutation |
| 1 | Derive retrieval evidence/decision from trusted server sources | IR-15's caller HIGH promoted a nonexistent draft source | Reuse S01/S02: fabricated/draft sources cannot be recommended, while a genuine eligible-source control works; then verify full-app behavior |
| 2 | Define operation-specific nested schemas and bounded text policies | Blank/object/list issues reached dispatch; malformed item caused 500 | Missing, nontext, blank and invalid nested fields produce controlled 4xx; Unicode remains supported; documented limits are enforced |
| 2 | Add evidence-applicability checks and clarification/escalation | IR-06, IR-11 and a selected IR-12 answer failed symptom grounding despite confidence | Ambiguous or unsupported symptoms require clarification/review; known supported cases still produce evidence-linked advice |
| 2 | Correct confidence and source wording | Scores exceed one and approval/validation labels may overstate evidence | Display score meaning, true source type/status and decision reason consistently; avoid probability or independent-validation claims without support |
| 3 | Improve agent protocol checks and provenance records | Sender/receiver/task labels were not verified identity | Bind allowed operations to authenticated caller/service identity; reject inconsistent envelopes without treating labels as credentials |
| 3 | Align evaluation with the deployed retrieval pipeline | Existing evaluator omits major app transformations and depends on semantic loading in its BM25 branch | Separately label lexical/semantic/full-pipeline evaluation; use reviewed gold relevance sets, abstention measures and documented weight comparisons |
| 3 | Complete blocked verification in a legitimate working environment | Baseline memory failures and later policy-controlled imports limit conclusions | Preserve original failures; obtain new dated full-app/suite/evaluation evidence without changing OS policy or replacing blocked components to hide failure |

Continue using isolated synthetic databases and verified backups for tests that mutate data. Preserve the existing role separation: KNOWLEDGE_ANALYST approval and ADMIN management are distinct permissions, not a universal ADMIN override. When remediation is authorized, add meaningful negative and positive regression checks, confirm expected database effects, and review the actual output rather than treating any 4xx or 200 as sufficient proof.

The source-confidence thresholds should not be retuned merely to make the recorded examples pass. First define what evidence is relevant, eligible and sufficient, measure the behavior on a representative labelled set, and compare accuracy with appropriate abstention. A single high score or successful paraphrase does not establish calibrated confidence, optimal weights or live-LLM safety.

## 8. Reflection

### Challenges and lessons from the evidence

The main practical challenge was separating application behavior from environment failures. Initial memory/paging limits prevented baseline model loading and password hashing; later Application Control restrictions prevented full imports. The audit retained those failures instead of lowering security settings, changing ranking behavior or reporting unavailable metrics as zeros. Successful later case runs were recorded separately and did not rewrite the baseline.

A second challenge was interpreting output beyond its status or confidence label. A 200 can return unauthorized information; a 422 can demonstrate body validation without authentication; an audit-generated 503 cannot prove product protection; and a HIGH retrieval score can accompany unsuitable advice. Database comparisons, actual source text, exact input differences and original function outputs made these distinctions reviewable.

The controlled comparisons were particularly informative. IR-09 separated draft eligibility from an approved positive control. IR-10 distinguished implemented source weights from a universal authority guarantee. IR-15 held the source constant and changed only LOW to HIGH, making the cause of its recommendation change clear. In contrast, IR-03 could not prove exact-source matching when no eligible exact-code source existed. The later synthetic formatting fixture did not retroactively complete that original-corpus case.

### Responsible AI implications

Source citations help users only when the sources are relevant, eligible and accurately described. Copying real evidence is insufficient if it does not address the reported symptom; copying caller-supplied evidence with approval language can manufacture trust. Confidence must be communicated as a ranking signal rather than a probability of correctness. Unsupported or ambiguous cases need honest uncertainty and meaningful human review, and direct-component escalation wording should not be mistaken for a persisted support handoff.

The demonstrated disclosure also connects data access controls to responsible AI: an otherwise useful retrieval function can expose internal material if its direct endpoint lacks identity checks. This audit used only synthetic data, so it establishes the control failure rather than actual personal-data harm. Neither absence of observed harm nor a passing local case proves safety for an enterprise population.

### Limitations and future work

The evidence covers a small synthetic corpus, fixed examples and a local development system. There were no external production users, enterprise deployment, live-provider answer successes or measured population-level attack rates. No claim is made about JWT forgery, all ownership boundaries, inactive-session behavior, CSRF, all alternative endpoints, service-wide availability or physical repair outcomes. Source observations outside executed tests remain candidates rather than new confirmed findings.

All 15 core IDs have evidence, but three remain partial. IR-03 needs an eligible exact-code source to test the positive match while preserving its original absent-source record. IR-14 needs the same role controls verified in the full application once imports legitimately work. IR-15 needs full-agent/app validation and actual retrieval coverage; its demonstrated component trust failure remains valid within the recorded scope. The baseline suite must be rerun successfully, or any residual failures explained, and the original evaluation must produce real metrics before aggregate effectiveness can be claimed. No such rerun or correction is included in this report.

Future evaluation should use a larger, more varied gold set with reviewed relevance labels, ambiguous/unsupported queries, technical-code variants and independent semantic versus lexical controls. It should distinguish source trust, relevance, applicability and abstention, and separately evaluate live-provider outputs when permitted and available. Remediation should preserve before/after evidence for both formal findings and meaningful regression controls.

This report assembles the completed audit evidence and recommendations. It is not a claim that every test passed, every planned scope was achieved or the findings were repaired. The present record is 12 completed cases, three partially assessed cases and two open Medium findings. Original raw evidence, source configuration and the working database remain preserved.
''')
text='\n'.join(sections).rstrip()+'\n'
expected=['1. Executive Summary','2. Scope of Testing','3. Evaluation Methodology','4. Test Cases Performed','5. Vulnerabilities Identified','6. Risk Assessment','7. Mitigation Strategies','8. Reflection']
assert re.findall(r'^## (.+)$',text,re.M)==expected
assert len(re.findall(r'^### IR-\d\d',text,re.M))==15
for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',text):
 if '://' not in target: assert (AUDIT/target.split('#')[0]).exists(),target
REPORT.write_text(text,encoding='utf-8',newline='\n')
assert all(sha(ROOT/path)==value for path,value in prior.items())
assert all(sha(ROOT/path)==value for path,value in baseline['source_sha256'].items()) and sha(ROOT/'knowgap.db')==baseline['original_database_sha256']
manifest={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'report':'audit/final_report.md','report_sha256':sha(REPORT),'report_word_count_approx':len(re.findall(r'\b[\w-]+\b',re.sub(r'\]\([^)]*\)',']',text))),'required_eight_sections':expected,'case_count':15,'completed_cases':12,'partially_assessed':['IR-03','IR-14','IR-15'],'confirmed_findings':['VULN-IR13-01','VULN-IR15-01'],'findings_open':True,'source_files_match_baseline':True,'original_database_main_file_matches_baseline':True,'prior_evidence_files_unchanged':len(prior),'evidence_sha256':prior,'new_tests_or_HTTP_requests':0,'application_fixes_applied':False,'basis':'Existing reviewed evidence only; historical baseline/raw captures preserved. Main-file DB hash does not cover unrelated concurrent WAL writes.'}
(AUDIT/'final_report_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:v for k,v in manifest.items() if k!='evidence_sha256'},indent=2))
