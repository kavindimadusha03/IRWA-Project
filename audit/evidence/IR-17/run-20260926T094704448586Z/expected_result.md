# IR-17 ? Authenticated API rate limiting

## Test objective
Evaluate whether repeated retrieval requests are subject to an appropriate configured limit.

## Input / attack scenario
Using an authorized synthetic account, send at most six sequential, identical, valid requests to /agents/retrieval/search with a one-second interval.

## Expected behavior
Any configured threshold is enforced consistently. If no threshold exists or is reached, record the observed control gap or coverage limitation without claiming a denial-of-service vulnerability.

## Execution procedure
First inspect rate-limit configuration. Use the valid request envelope from IR-15. Run only against the isolated loopback server. Do not increase concurrency or perform load testing.

## Required evidence
Configuration, request payloads, timestamps, HTTP responses, rate-limit headers and server logs.

## Actual behavior
NOT EXECUTED ? complete after testing.

## Observations
NOT RECORDED.

## Conclusion
UNASSESSED.

## Risk classification and mitigation
Assign only after reviewing actual findings.
