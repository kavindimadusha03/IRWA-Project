# IR-10 criteria fixed before request

- One printer-queue issue through normal ticket workflow on fixture-only approved KB/resolved ticket/draft KB/open ticket corpus. No score substitution or application change.
- Positive sources cover the same issue with distinct bodies/titles, same Printers category and Any OS. Verify both survive original deduplication before trust interpretation. Top-k remains 5 with two expected eligible sources.
- PASS: both positives remain eligible/shortlisted; actual trust=1.0 approved and 0.85 resolved; final scores equal original pre-trust hybrid * actual trust + actual metadata bonus; draft/open controls excluded from trusted retrieval/citations.
- FAIL: valid execution applies wrong trust/arithmetic or treats negative controls as trusted. A more relevant historical source ranking above KB is not itself a failure.
- Capture native BM25 before normalization, normalized BM25, semantic, pre-trust hybrid, trust, metadata and final ranks. Comparable issue content is qualitative, not equal numeric relevance.
- Equal-score condition: separately calculate both adjustments using a common positive raw score taken from the run and equal observed metadata. This is formula verification, not actual equal-score retrieval; no scores injected. Zero raw score ties.
- Draft uses internal_kb/authoritative=true; open ticket has nonempty provisional notes. Neither may enter actual corpus. A standalone helper weight is not proof of eligibility.
- Verify original private backup, create a private seeded-DB snapshot before request, verify unchanged fixture fields/statuses afterward.
- Capture normal login, original pipeline/HTML/citations and read-only support queue. Review answer/provenance separately from numerical trust treatment.
- Missing environment/eligibility/dedup prerequisites are Not ready/Inconclusive; redesign before interpretation if necessary. Disabled Groq means fallback-only answers.
- One bounded local query; no real data, source approval/status changes, repairs, alternate-route probes, fixes, full-corpus comparison, forced scores or IR-11/later cases.
