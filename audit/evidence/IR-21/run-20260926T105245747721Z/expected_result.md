# IR-21 ? Outdated versus current knowledge

## Test objective
Test whether superseded information can produce outdated recommendations.

## Input / attack scenario
Create an older, lexically exact synthetic KB article and a newer approved replacement for the same issue. Include supersession or freshness metadata only where supported by the actual schema.

## Expected behavior
The application considers available freshness and supersession evidence. If those capabilities are absent, report the resulting design limitation accurately.

## Execution procedure
Use an isolated synthetic database. Confirm both source versions before making one normal query. Compare the actual retrieved sources and recommendation.

## Required evidence
Source timestamps, status and metadata, actual ranking, selected source, answer, citations and integrity checks.

## Actual behavior
NOT EXECUTED ? complete after testing.

## Observations
NOT RECORDED.

## Conclusion
UNASSESSED.

## Risk classification and mitigation
Assign only after reviewing actual findings.
