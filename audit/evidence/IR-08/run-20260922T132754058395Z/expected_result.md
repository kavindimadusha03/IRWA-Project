# IR-08 criteria fixed before any request

- Submit each of the five planned variants exactly once in the same full sentence and same title, with fresh independently seeded databases and the same labelled fixture.
- The original corpus has no eligible exact-code source. The added article is an isolated synthetic lookup control, not proof of a real code diagnosis or repair. Do not change IR-03's missing-prerequisite result.
- Primary retrieval PASS: all five valid executions preserve the code identity 0x00000124 in canonical-query extraction, normalized extraction and BM25 tokens, retain the same exact-code fixture in top-k with correct exact_error_match flags, and exhibit no formatting-driven transition to unsupported confident advice.
- Primary FAIL: valid formatting variation loses code identity or exact fixture relevance/flags, crashes, or causes an unsupported confident-answer transition. Numerical/rank changes alone do not fail if relevance and behavior remain appropriate.
- Verify actual exact-match bonus using raw hybrid score minus weighted BM25/semantic components; +0.35 should apply only to the code-matching fixture. This arithmetic check is not an ablation or independent search.
- Auxiliary entity check: all five equivalent codes should populate analysis.entities.error_code consistently after case normalization. Record any mismatch as its own PASS/FAIL because the entity field is not the query passed into retrieval.
- Review complete rankings, original fallback message/explanation/reply/citations and persisted state for each case. Fixture retrieval does not certify source approval security, real troubleshooting applicability or calibrated confidence.
- Record generic repair overstatement if present across all forms separately from a formatting-induced failure; do not hide it behind a primary retrieval PASS.
- Same source/configuration/LLM mode, eligible corpus and fixture across all variants; original functions observed without changed arguments/results. A missing prerequisite yields Not ready/Inconclusive.
- Normal CUSTOMER login and one ticket per variant; read-only IT_SUPPORT queue observation. No approval, repair, resolution or other mutation beyond declared isolated setup/ticket creation.
- Verify private backup; preserve original database and CSV/source files. Run cached model only. Disabled Groq yields fallback-only conclusions.
- No other formats, no corpus-only replay of IR-03, no load testing, no fixes and no IR-09 or later cases. A failed subcheck is not automatically a security vulnerability.
