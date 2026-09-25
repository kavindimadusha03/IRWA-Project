# IR-09 criteria fixed before requests

- Submit the draft-only marker once, then the distinct approved-control marker once, with identical seeded corpus/fixtures/config in separate temporary databases. No approval or source-status change during testing.
- Verify markers and response-only witnesses absent from original CSVs; save exact queries/fixture metadata before requests. Both markers must survive the actual canonical/normalized query for the intended probe.
- Verify existing private working-DB backup. Create and integrity-check a separate SQLite snapshot of each seeded isolated database before the request; save draft/approved statuses before and after.
- PASS: draft is absent from the full actual eligible corpus passed to hybrid_rank, raw shortlist, final ranking, persisted source/citations and recommendation content; the approved control is present in the corpus and retrieved by its own marker query.
- FAIL: valid run includes the draft in authoritative retrieval or uses/cites its witness/source as a recommendation, or excludes the approved control. If control is eligible but retrieval misses it, report that positive-control limitation without inventing draft leakage.
- Record the full corpus before deduplication/top-k. A low rank or trust=0 does not establish exclusion. Observe real ranking trust calls separately from pure _trust_weight calls on stored fixtures (draft expected 0; approved expected 1).
- Draft query text may legitimately appear in submitted description/history/UI. Use draft source ID, response-only witness and actual content/attribution to distinguish source leakage; do not call query echo a vulnerability.
- Capture normal login, original pipeline returns, scores, decision, stored ticket/citations, customer HTML and read-only support queue. Keep any relevance/answer weakness separate from the exclusion criterion.
- Missing login/model/backup/fixture/query prerequisites are Not ready/Inconclusive; do not fabricate outcomes. Record configured Groq mode and scope fallback-only results appropriately.
- Do not approve the draft, mutate production sources, run alternative routes/variants, fix code or execute IR-10 and later cases. No stress/DoS or real user data.
