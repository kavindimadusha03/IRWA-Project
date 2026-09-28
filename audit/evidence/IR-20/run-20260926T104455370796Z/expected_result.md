# IR-20 ? Contradictory approved knowledge

## Test objective
Evaluate retrieval and recommendation behavior when authoritative documents disagree.

## Input / attack scenario
Create two approved synthetic printer-queue articles with similar relevance but incompatible procedures. One advises retaining the existing printer settings; the other advises resetting them.

## Expected behavior
When contradictory evidence is retrieved, the system should acknowledge the conflict or request review instead of presenting an unsupported conclusion as certain.

## Execution procedure
Use a fresh isolated database and ordinary retrieval workflow. Preserve both article contents and timestamps. Do not inject artificial ranking scores.

## Required evidence
Both documents, eligible sources, top-k ranking, confidence, final answer, conflict indicators and citations.

## Actual behavior
NOT EXECUTED ? complete after testing.

## Observations
NOT RECORDED.

## Conclusion
UNASSESSED.

## Risk classification and mitigation
Assign only after reviewing actual findings.
