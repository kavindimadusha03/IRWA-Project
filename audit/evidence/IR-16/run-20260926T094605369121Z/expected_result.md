# IR-16 ? Cross-user ticket access (IDOR)

## Test objective
Check whether a customer can read another customer's private ticket.

## Input / attack scenario
Create synthetic Customer A and Customer B. Customer A creates a ticket containing IR16-PRIVATE-CUSTOMER-A. While authenticated as Customer B, request Customer A's /tickets/{id} URL.

## Expected behavior
Customer B cannot access Customer A's ticket or its private content. Verify the legitimate owner can access it.

## Execution procedure
Use two isolated synthetic customer accounts. Create exactly one test ticket. Capture the owner response, then request that ticket using Customer B's session. Do not use real customer records.

## Required evidence
User roles, ticket ownership, HTTP status codes, response HTML, marker exposure and database integrity.

## Actual behavior
NOT EXECUTED ? complete after testing.

## Observations
NOT RECORDED.

## Conclusion
UNASSESSED.

## Risk classification and mitigation
Assign only after reviewing actual findings.
