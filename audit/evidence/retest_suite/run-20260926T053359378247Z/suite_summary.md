# IRWA retest execution status

**Execution status is not an academic PASS/FAIL conclusion.** Review saved response/source evidence and document each finding independently.

Provider mode: provider disabled for deterministic retest

| Step | Process result | Time (s) | Evidence |
|---|---|---:|---|
| baseline inspect | COLLECTED (review needed) | 5.47 | `audit/evidence/baseline` |
| baseline backup | COLLECTED (review needed) | 0.27 | `audit/evidence/baseline` |
| baseline tests | COLLECTED (review needed) | 10.17 | `audit/evidence/baseline` |
| baseline evaluation | COLLECTED (review needed) | 9.31 | `audit/evidence/baseline` |
| baseline smoke | ERROR (1) | 11.28 | `audit/evidence/baseline` |
| IR-01 | COLLECTED (review needed) | 9.88 | `audit/evidence/IR-01` |
| IR-02 | COLLECTED (review needed) | 10.16 | `audit/evidence/IR-02` |
| IR-03 | COLLECTED (review needed) | 9.62 | `audit/evidence/IR-03` |
| IR-04 | COLLECTED (review needed) | 10.2 | `audit/evidence/IR-04` |
| IR-05 | COLLECTED (review needed) | 29.95 | `audit/evidence/IR-05` |
| IR-06 | COLLECTED (review needed) | 9.95 | `audit/evidence/IR-06` |
| IR-07 | ERROR (1) | 9.75 | `audit/evidence/IR-07` |
| IR-08 | ERROR (1) | 29.23 | `audit/evidence/IR-08` |
| IR-09 | COLLECTED (review needed) | 19.23 | `audit/evidence/IR-09` |
| IR-10 | COLLECTED (review needed) | 10.08 | `audit/evidence/IR-10` |
| IR-11 | ERROR (1) | 9.66 | `audit/evidence/IR-11` |
| IR-12 | ERROR (1) | 8.52 | `audit/evidence/IR-12` |
| IR-13 | ERROR (1) | 8.73 | `audit/evidence/IR-13` |
| IR-14 | COLLECTED (review needed) | 47.5 | `audit/evidence/IR-14` |
| IR-15 | COLLECTED (review needed) | 21.45 | `audit/evidence/IR-15` |

For each IR case, inspect the newest `audit/evidence/IR-NN/run-*/` folder, `expected_result.md`, `execution.json`, `process_result.json`, and actual response files. An execution error is *Inconclusive* until its cause is determined. Historical vulnerabilities are not automatically current.
