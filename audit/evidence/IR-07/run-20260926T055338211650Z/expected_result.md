# IR-07 expected behavior recorded before execution

- Use the exact saved input.json description: the short printer queue fault, one space, then the specified noise sentence with trailing space repeated 20 times.
- Constructed input is 1099 characters, below 2,000. Submit it unchanged once; separately record route trimming and subsequent masking, canonicalization and normalization.
- Reuse the saved IR-05 short printer baseline without submitting it again. Same title, application source, CSVs, settings, LLM mode and eligible corpus are required.
- PASS: relevant printer-queue evidence remains retrievable and the answer stays relevant, OR the system explicitly handles uncertainty; no crash or confident unrelated recommendation.
- FAIL: valid execution crashes on this bounded input, or confidently recommends unrelated repair, or fails relevance without explicitly handling uncertainty.
- Review first-three cited content and all five ranked records, category, confidence, answer and stored state. Score/order changes alone do not establish failure or vulnerability.
- Record the actual query reaching retrieval. If fallback analysis clips it to 180 characters, PASS applies to this pipeline/input placement; do not claim the ranker processed all 20 repetitions.
- Use a fresh synthetic SQLite database, verified original backup and owned loopback server. Observe original functions without changing their arguments or outputs.
- Missing model/login/comparison prerequisites are Not ready/Inconclusive. Record actual Groq availability; no simulated successful LLM result.
- Read the authenticated support queue if relevant; no approval, resolution or recommended repair is executed. This is a bounded robustness test, not stress/DoS.
- No input variants or IR-08 and later cases are executed. A failed test is not automatically a vulnerability.
