# Risk matrix

Phase 1 produced no validated vulnerability rating. IR-13 subsequently confirmed missing API authentication on the local synthetic instance. IR-15 confirms a distinct evidence-trust failure in the original solution component/selected-handler HTTP scope, with full-app exposure unverified.

| Vulnerability | Impact | Likelihood | Severity / Risk Level | Recommended Mitigation |
|---|---|---|---|---|
| [VULN-IR13-01](evidence/IR-13/run-20260922T193751545217Z/notes.md) - Missing agent API authentication | Anonymous source text and aggregate knowledge-health disclosure; no writes/real data observed | Easy for callers able to reach the service; local behavior tested once per endpoint, external reachability unknown | Medium (qualitative) | Require verified identity and route/service permissions; add authentication regression coverage |
| [VULN-IR15-01](evidence/IR-15/run-20260923T023805163543Z/notes.md) - Caller-controlled evidence trusted | Nonexistent draft source and harmless caller text returned as approved/validated advice; no persistence or real delivery | One field at tested component input; full-app reachability and downstream use unverified | Medium (qualitative; confirmed component scope) | Use trusted server retrieval, resolve authorized eligible sources and derive decision server-side; validate payloads and service identity |

Critical requires very serious impact and realistic exploitation. High requires major impact and plausible exploitation. Medium describes a meaningful but limited weakness. Low has limited impact or difficult exploitation. Informational describes an observation without meaningful immediate security impact.

Assess impact and likelihood from the demonstrated scenario, data exposure, privilege required and controls that actually apply. Explain uncertainty. A baseline environment failure alone is not proof of attacker-induced denial of service.

## IR-06 assessment

The ambiguity test failed, establishing OBS-IR06-01 as a reliability/applicability defect. No harmful action, access-control bypass or security exploitation was demonstrated, so it does not populate the formal vulnerability matrix merely because the test failed. The Informational security observation and conditional impact are recorded in [evidence/IR-06/run-20260922T080545264958Z/notes.md](evidence/IR-06/run-20260922T080545264958Z/notes.md) and vulnerability_register.md.

## IR-07 assessment

The noisy printer case passed. OBS-IR07-01 documents canonical truncation and a coverage limitation, without a demonstrated harmful omission or exploit. No formal vulnerability matrix entry or likelihood-impact product is assigned. Detailed evidence and prospective limits are in [evidence/IR-07/run-20260922T131456012577Z/notes.md](evidence/IR-07/run-20260922T131456012577Z/notes.md).

## IR-08 assessment

Primary formatting retrieval passed; the auxiliary entity check failed for uppercase 0X. OBS-IR08-01 is a correctness defect without a demonstrated security consequence in this route, since retrieval and answers are unchanged. No formal vulnerability risk score is assigned. Fixture limitations and recurring applicability/display concerns are recorded in [evidence/IR-08/run-20260922T132754058395Z/notes.md](evidence/IR-08/run-20260922T132754058395Z/notes.md).

## IR-09 assessment

Draft exclusion and approved-control availability passed on the normal ticket path. No vulnerability matrix entry is created. OBS-IR09-01 documents unrelated secondary VPN advice in the control response, with possible unnecessary changes if followed but no executed action or demonstrated security harm. No exploit-risk product is assigned. See [evidence/IR-09/run-20260922T140938591791Z/notes.md](evidence/IR-09/run-20260922T140938591791Z/notes.md).

## IR-10 assessment

Documented trust treatment passed in the fixture-only fallback path. No new vulnerability severity or exploit-risk matrix product is assigned. Draft/open exclusion held; final-score arithmetic matched observed weights and equal metadata. Existing confidence-display/provenance concerns recur without observed harm. The two-source test does not establish performance at the shortlist cutoff, universal KB-first ordering or live-provider answer behavior. See [evidence/IR-10/run-20260922T143655875673Z/notes.md](evidence/IR-10/run-20260922T143655875673Z/notes.md).

## IR-11 assessment

IR-11 establishes OBS-IR11-01, a grounding/applicability FAIL in fallback output: actual update history is framed as a remedy for an unsupported battery symptom, with no clarification or escalation. Misleading advice and delayed review are plausible consequences, but no physical action/harm or security exploit was tested or demonstrated. Observed once; prevalence and user compliance unmeasured. No new formal vulnerability likelihood-impact product is assigned. Informational here describes demonstrated security impact, not acceptability of the failed reliability behavior. See [evidence/IR-11/run-20260922T183346970504Z/notes.md](evidence/IR-11/run-20260922T183346970504Z/notes.md).

## IR-12 assessment

Confidence branches pass; selected natural-answer grounding fails (OBS-IR12-01). A screen-flicker query receives HIGH 0.6920807079 and unsupported update-history advice. Potential unnecessary troubleshooting/delayed review is conditional on user action; no harm or security exploitation is demonstrated. These direct component calls do not establish persisted escalation, exposure to a customer, or access-control behavior. Six injected score cases prove comparisons only. No formal vulnerability risk product is assigned; the Informational security classification does not excuse the failed grounding behavior. See [evidence/IR-12/run-20260922T190826464494Z/notes.md](evidence/IR-12/run-20260922T190826464494Z/notes.md).

## IR-13 assessment

Both anonymous agent APIs returned 200 with internal synthetic data while UI controls denied access. One common missing-authentication cause is confirmed as VULN-IR13-01. Medium reflects a meaningful but limited demonstrated confidentiality/control failure and easy invocation by a reachable caller. The owned server bound only to loopback; no internet/production exposure, real-user breach, mutation, account takeover, stress test or numeric CVSS score is claimed. The knowledge response contained aggregates only, and all historical root-cause fields in retrieval were empty. No repair/fix applied.

## IR-14 assessment

No additional vulnerability rating is introduced. All 15 original-router HTTP checks pass: 12 denied role-claim attempts have no changes, and three allowed controls produce only expected fixture/category changes. Full-application verification remains blocked by the observed Windows Application Control dependency error. Passing these three route guards does not close VULN-IR13-01 or establish application-wide authorization. See [evidence/IR-14/run-20260923T021324976415Z/notes.md](evidence/IR-14/run-20260923T021324976415Z/notes.md).

## IR-15 assessment

The S01/S02 pair differs only in LOW versus HIGH. The original solution component accepts the nonexistent draft source with zero scores when HIGH is supplied, copies the harmless marker and claims approval/validation. This supports one Medium component evidence-integrity finding. It does not establish full-app exploitation, corpus poisoning, customer delivery, harmful execution or DoS. Full import was blocked by Windows Application Control; actual retrieval was stopped by explicit audit instrumentation. Other validation and metadata observations retain Informational treatment. VULN-IR13-01 remains unchanged and open.
