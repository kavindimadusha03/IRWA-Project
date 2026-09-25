# Expected result recorded before execution

- Use the unmodified application ticket workflow with a synthetic CUSTOMER.
- Submit exactly one ticket with the saved paraphrased title and description.
- Compare relevance and decisions with IR-01; identical source order or numeric scores are not required.
- Hybrid success does not isolate semantic embeddings from query preprocessing and lexical matching.
- Relevant Wi-Fi/no-internet evidence should remain available for the paraphrase; a category label alone is not proof.
- Returned sources must be eligible approved knowledge or resolved historical tickets.
- Any recommended actions must be supported by relevant retrieved content.
- Record the actual confidence/decision; a high percentage alone is not a PASS.
- If a required model, login or environment precondition fails, record Not ready/Inconclusive rather than inventing a ranking verdict.
- Assess live Groq generation only if a successful generation was actually observed. Otherwise label fallback-only results.
- This single synthetic case does not prove overall accuracy or absence of security weaknesses.

Pre-reviewed relevant approved CSV guide IDs: KB-001, KB-009, KB-017, KB-025, KB-033, KB-041, KB-049, KB-057, KB-065, KB-073
Content evidence is in source_preflight.json; equivalent duplicate IDs are accepted.
