# Endpoint inventory

This source review records **42 application handlers**, four expected default framework routes, and one static-file mount. Authentication classifications describe checks written in the application. They are **not security attack results**. Runtime availability and deployed proxy controls must be established separately by baseline checks.

“Public” means the handler does not require an existing login. Password-reset submission still requires a valid reset token. Two legacy admin handlers deny every request; their public classification does not mean article changes are permitted.

## Application handlers

| Endpoint | Method | Purpose | Authentication | Role | Input |
|---|---|---|---|---|---|
| / | GET | Login page; redirect signed-in users. Source: app/main.py:38 | Public | Any | None |
| /home | GET | Customer ticket list or staff landing redirect. Source: app/main.py:46 | Authenticated | Any signed-in role; customers receive own tickets | Optional query: category, status, min_confidence, from_date, to_date |
| /tickets/{ticket_id} | GET | Ticket detail, citations, feedback and associated logs. Source: app/main.py:70 | Authenticated | CUSTOMER: owner only; other roles: no ownership restriction in handler | Integer path ticket_id |
| /support | GET | Support queue and resolved tickets. Source: app/main.py:108 | Role-restricted | IT_SUPPORT, ADMIN; admin receives an empty escalated queue | Optional query: category, status, min_confidence, from_date, to_date |
| /knowledge | GET | Knowledge article listing, including selectable statuses. Source: app/main.py:133 | Authenticated | Any signed-in role | Optional query: category, os, status, from_date, to_date |
| /dashboard | GET | Knowledge analytics, agent logs and security events. Source: app/main.py:215 | Role-restricted | KNOWLEDGE_ANALYST only | None |
| /health | GET | Application health/name. Source: app/main.py:237 | Public | Any | None |
| /register | GET | Registration form. Source: app/routes/auth.py:40 | Public | Any | None |
| /register | POST | Create CUSTOMER account. Source: app/routes/auth.py:45 | Public | Any; resulting role fixed to CUSTOMER | Form: username, full_name, password, confirm_password |
| /forgot-password | GET | Recovery form. Source: app/routes/auth.py:80 | Public | Any | None |
| /forgot-password | POST | Generate reset record and render recovery response. Source: app/routes/auth.py:85 | Public | Any | Form: username |
| /reset-password | GET | Reset form. Source: app/routes/auth.py:108 | Public | Any | Optional query: token |
| /reset-password | POST | Replace password using reset token. Source: app/routes/auth.py:113 | Public | Requester possessing a valid reset token | Form: token, password, confirm_password |
| /profile | GET | Own profile. Source: app/routes/auth.py:147 | Authenticated | Any signed-in role | None |
| /profile | POST | Update own name or password. Source: app/routes/auth.py:155 | Authenticated | Any signed-in role | Form: full_name; optional current_password, new_password, confirm_password |
| /login | POST | Verify credentials and issue JWT cookie. Source: app/routes/auth.py:187 | Public | Any active account with valid credentials | Form: username, password |
| /logout | GET | Delete browser access-token cookie. Source: app/routes/auth.py:202 | Public | Any | None |
| /tickets/create | POST | Create ticket for current user and invoke agent workflow. Source: app/routes/tickets.py:29 | Authenticated | Any signed-in role | Form: title, description |
| /tickets/{ticket_id}/solved | POST | Close own ticket and record helpful feedback. Source: app/routes/tickets.py:56 | Authenticated | Ticket owner, regardless of role | Integer path ticket_id |
| /tickets/{ticket_id}/not-solved | POST | Escalate own ticket and record negative feedback. Source: app/routes/tickets.py:77 | Authenticated | Ticket owner, regardless of role | Integer path ticket_id |
| /tickets/{ticket_id}/approve | POST | Approve AI recommendation. Source: app/routes/tickets.py:97 | Role-restricted | IT_SUPPORT, ADMIN | Integer path ticket_id |
| /tickets/{ticket_id}/reject | POST | Reject recommendation and escalate ticket. Source: app/routes/tickets.py:121 | Role-restricted | IT_SUPPORT, ADMIN | Integer path ticket_id |
| /tickets/{ticket_id}/feedback | POST | Save own feedback and close/escalate ticket. Source: app/routes/tickets.py:143 | Authenticated | Ticket owner, regardless of role | Integer path ticket_id; form rating; optional comment |
| /support/tickets/{ticket_id}/resolve | POST | Record resolution and optionally generate knowledge draft. Source: app/routes/support.py:20 | Role-restricted | IT_SUPPORT only; handler explicitly rejects ADMIN | Integer path ticket_id; form root_cause, resolution_notes; optional create_kb_draft, default "yes" |
| /knowledge/articles/{article_id} | POST | Edit article and draft/approved status. Source: app/routes/knowledge.py:36 | Role-restricted | KNOWLEDGE_ANALYST only | Integer path article_id; form doc_id, title, content, category, status; optional supported_os |
| /knowledge/{article_id}/approve | POST | Mark article approved and authoritative. Source: app/routes/knowledge.py:71 | Role-restricted | KNOWLEDGE_ANALYST only | Integer path article_id |
| /agents/security/check | POST | Invoke security input check. Source: app/routes/agents.py:14 | Public | Any; no route login/role check | AgentMessage JSON; handler reads payload.text |
| /agents/ticket/analyze | POST | Invoke ticket analysis agent. Source: app/routes/agents.py:19 | Public | Any; no route login/role check | AgentMessage JSON; handler reads payload.text |
| /agents/retrieval/search | POST | Invoke knowledge retrieval agent. Source: app/routes/agents.py:24 | Public | Any; no route login/role check | AgentMessage JSON; handler reads payload.issue |
| /agents/solution/recommend | POST | Recommend from supplied retrieval object. Source: app/routes/agents.py:29 | Public | Any; no route login/role check | AgentMessage JSON; payload.query and dictionary payload.retrieval |
| /agents/knowledge/analyze | POST | Invoke knowledge-health analysis. Source: app/routes/agents.py:38 | Public | Any; no route login/role check | No request-body fields declared |
| /admin | GET | Administration page; initialize missing categories. Source: app/routes/admin.py:76 | Role-restricted | ADMIN only | Optional query message, error for page notices |
| /admin/users/create | POST | Create user with an allowed role. Source: app/routes/admin.py:98 | Role-restricted | ADMIN only | Form: username, full_name, password, role |
| /admin/users/{user_id} | POST | Update name, role and activation. Source: app/routes/admin.py:124 | Role-restricted | ADMIN only | Integer path user_id; form full_name, role; optional Boolean is_active, default false |
| /admin/users/{user_id}/delete | POST | Delete eligible user. Source: app/routes/admin.py:149 | Role-restricted | ADMIN only | Integer path user_id |
| /admin/articles/create | POST | Create draft for analyst approval. Source: app/routes/admin.py:168 | Role-restricted | ADMIN only | Form title, content, category; optional status, supported_os; stored status is always draft |
| /admin/articles/{article_id} | POST | Disabled edit handler; returns 403 if reached. Source: app/routes/admin.py:199 | Public | None permitted; always denies | Integer path article_id; required form doc_id, title, content, category, status; optional supported_os |
| /admin/articles/{article_id}/delete | POST | Disabled delete handler; returns 403. Source: app/routes/admin.py:214 | Public | None permitted; always denies | Integer path article_id |
| /admin/categories/create | POST | Create category. Source: app/routes/admin.py:219 | Role-restricted | ADMIN only | Form name; optional description |
| /admin/categories/{category_id} | POST | Update category and activation. Source: app/routes/admin.py:238 | Role-restricted | ADMIN only | Integer path category_id; form name; optional description, Boolean is_active |
| /admin/categories/{category_id}/delete | POST | Delete category if no article uses it. Source: app/routes/admin.py:263 | Role-restricted | ADMIN only | Integer path category_id |
| /chat/message | POST | Retrieve approved articles and generate answer. Source: app/routes/chat.py:41 | Authenticated | Any signed-in active account | ChatMessageRequest JSON: message; optional history |

## Framework routes and static assets

The application uses the default FastAPI documentation configuration at app/main.py:20, without an application-wide authentication dependency. The following framework routes are expected from those defaults. Their availability and methods should be reconciled with baseline route enumeration. They are not additional hand-written application handlers.

| Endpoint | Method | Purpose | Authentication | Role | Input |
|---|---|---|---|---|---|
| /openapi.json | GET, HEAD | Generated API schema; inferred from default FastAPI setup. Source: app/main.py:20 | Public | Any | None |
| /docs | GET, HEAD | Swagger UI; inferred from default FastAPI setup. Source: app/main.py:20 | Public | Any | None |
| /docs/oauth2-redirect | GET, HEAD | Default Swagger OAuth redirect helper; does not establish that the app uses OAuth login. Source: app/main.py:20 | Public | Any | Framework/browser redirect parameters |
| /redoc | GET, HEAD | ReDoc UI; inferred from default FastAPI setup. Source: app/main.py:20 | Public | Any | None |
| /static/{path} | GET, HEAD | Mounted CSS, JavaScript and other assets. Source: app/main.py:21 | Public | Any | Relative asset path under static directory |

## Authentication architecture

1. Password verification uses pwdlib.PasswordHash.recommended(); user records store hashed_password. Sources: app/services/auth.py:9; app/models.py:6.
2. Login checks that the account exists, is active and has a matching password. It issues an HS256 JWT containing sub, username, role and exp, signed with the configured secret. No secret values were inspected or recorded. Sources: app/routes/auth.py:187; app/services/auth.py:21.
3. The access_token cookie uses HttpOnly and SameSite=Lax. This call does not explicitly enable Secure. Source: app/routes/auth.py:198.
4. current_user_from_request decodes the cookie, converts JWT sub to an integer and retrieves the user from the database. Route role checks use the current database role, not the JWT role claim directly. Missing, invalid or unresolvable credentials produce no current user. Source: app/routes/auth.py:26.
5. Guards are implemented inside handlers. The shared helper does not check is_active; login and chat perform their own activation checks. Existing-session behavior after account deactivation is a source observation for later testing. Sources: app/routes/auth.py:26, 194; app/routes/chat.py:47.
6. Logout deletes the client cookie. Password changes and resets do not show JWT-revocation state in the reviewed files. Sources: app/routes/auth.py:138, 179, 202.
7. Recovery stores a hash of a random token, applies a 30-minute expiry and marks successful tokens used. The local-demo response renders the generated reset link to its requester. This is source-confirmed behavior, not an executed account-access test. Sources: app/routes/auth.py:85, 113; app/templates/forgot_password.html:9.

## Role and ownership model

Allowed roles are CUSTOMER, IT_SUPPORT, KNOWLEDGE_ANALYST and ADMIN (app/routes/admin.py:19). Self-registration fixes CUSTOMER; administration validates selected roles against this list.

| Actor | Access permitted by source | Boundaries |
|---|---|---|
| Anonymous requester | Login, registration, recovery, logout, health, five agent endpoints, default docs/static assets | Normal protected page/action guards require a user; legacy admin article edit/delete always deny |
| Any signed-in user | Own profile; ticket creation; article listing; own-ticket feedback actions; chat when active | Knowledge listing is not analyst-only; ticket creation is not customer-only |
| CUSTOMER | Own ticket list and ticket detail | Other users' ticket detail denied; solved/not-solved/feedback require ownership |
| IT_SUPPORT | Support page; ticket detail across owners; AI approval/rejection; manual resolution and optional draft creation | Cannot use analyst article editing/approval or admin management |
| KNOWLEDGE_ANALYST | Analytics dashboard; article editing/approval; ticket detail across owners | Cannot use support approval/rejection/resolution or admin management |
| ADMIN | Admin management; support page; ticket detail across owners; AI approval/rejection; article draft creation | Cannot resolve through support endpoint or use analyst dashboard/edit/approval; legacy admin article edit/delete always deny |

Customer ownership is enforced at app/main.py:52 and 78. Solved, not-solved and feedback enforce ownership for every role at app/routes/tickets.py:62, 83 and 155. Staff approval/rejection and manual resolution have role checks but no ticket-owner or existing-assignee restriction. ADMIN is not a universal override.

## Input validation relevant to later tests

- Registration checks username length/characters, name length, password minimum length, confirmation and duplicate usernames. Source: app/routes/auth.py:54.
- Ticket creation strips strings and checks minimum lengths only. TicketCreate declares maximum lengths, but this form handler does not use that schema. Sources: app/routes/tickets.py:29; app/schemas.py:15.
- Support resolution accepts required form strings and strips them without applying the length-constrained ResolutionRequest model. Sources: app/routes/support.py:20; app/schemas.py:55.
- Feedback uses a rating allowlist and truncates stored comments to 1,000 characters. Sources: app/routes/tickets.py:24, 157.
- Article editing checks nonblank core fields, unique document ID and draft/approved status. Admin creation always stores a draft. Sources: app/routes/knowledge.py:54; app/routes/admin.py:181.
- AgentMessage requires string message_id, request_id, sender, receiver and task, plus dictionary payload. These metadata fields do not authenticate the sender. The model has no string-length constraints or task/sender allowlists. Source: app/schemas.py:20.
- ChatMessageRequest limits messages to 2–2,000 characters and history to eight dictionaries. Included history entries are restricted to user/assistant labels, with content truncated to 1,000 characters before prompting. The security agent checks the current message. Sources: app/schemas.py:10; app/routes/chat.py:51, 85.

## Review boundary

This inventory was produced by source inspection. No app code was changed. No attack payloads, ownership-bypass attempts, credential attacks or runtime vulnerability confirmations were performed for this inventory. Baseline executions recorded elsewhere must remain distinct from later authorized security tests.

## IR-13 runtime addendum

The Phase 1 classifications above remain descriptions of original source enforcement. IR-13 now verifies four routes on an isolated original synthetic dataset. Anonymous GET /home and POST /tickets/create return 303 to / with no data or ticket creation. Anonymous POST /agents/retrieval/search and POST /agents/knowledge/analyze return 200 with internal synthetic source text and aggregate analytics. These Public-in-source agent routes FAIL the audit's intended protection policy, confirming VULN-IR13-01 (Medium). Other route classifications are not additional runtime test results. See [evidence/IR-13/run-20260922T193751545217Z/notes.md](evidence/IR-13/run-20260922T193751545217Z/notes.md); no application guard was changed.

## IR-14 runtime addendum

Original-router HTTP integration confirmed the following intended roles with normal login/profile controls and five separate synthetic databases:

| Endpoint | Method | Allowed role observed | Other tested roles | Persistent effects of allowed request |
|---|---|---|---|---|
| /knowledge/81/approve | POST | KNOWLEDGE_ANALYST (303) | CUSTOMER, IT_SUPPORT, ADMIN, AUDIT_VIEWER: 403 | Only fixture status, authoritative and updated_at changed |
| /admin | GET | ADMIN (200) | CUSTOMER, IT_SUPPORT, KNOWLEDGE_ANALYST, AUDIT_VIEWER: 403 | Eight missing default categories initialized |
| /admin/categories/create | POST | ADMIN (303) | CUSTOMER, IT_SUPPORT, KNOWLEDGE_ANALYST, AUDIT_VIEWER: 403 | One submitted active category created |

Denied callers submitted privileged role/user_id claims in ordinary fields, but the resolved identity remained their authenticated database user and all tables stayed unchanged. This is evidence for these original routers only. Full-app startup was blocked by Windows Application Control before any HTTP in a separate attempt, so IR-14 remains partially assessed. No finding from IR-13 is closed and no additional routes were tested. See [evidence/IR-14/run-20260923T021324976415Z/notes.md](evidence/IR-14/run-20260923T021324976415Z/notes.md).

## IR-15 runtime addendum

Full app import failed on SciPy _batched_linalg under Windows Application Control. The following results come from exact AST-selected original handler functions in an audit HTTP app with the original AgentMessage and recommend_solution component. The full agents router was not imported. Actual retrieval stopped at an explicitly substituted observer.

| Endpoint | Method | Observed validation | Authentication/protocol evidence | Scope limit |
|---|---|---|---|---|
| /agents/retrieval/search | POST | Missing payload/sender and malformed JSON: 422; empty/object/list issues accepted or stringified; all 4000 characters and Unicode preserved at boundary | No-cookie request reaches observer; sender/receiver/task changes leave dispatch unchanged | Observer returns audit 503; no actual ranking/data disclosure or impersonation demonstrated |
| /agents/solution/recommend | POST | Missing/non-object retrieval: 422; malformed nested item: plain 500; synthetic HIGH accepted and recommended | Caller decision promotes nonexistent draft zero-score source into approved/validated advice; VULN-IR15-01 Medium in original component scope | Normal CUSTOMER cookie sent; no demonstrated endpoint verification of it; no full-app exposure or persistence claim |
| /docs and /openapi.json | GET | Actual documentation responses: 200 | No cookie required in audit app | These show selected-app schema only, not full application routes |

VULN-IR13-01 remains open on its earlier original-app evidence. Validation responses do not prove authentication, and client envelope labels do not authenticate a service. No route classification or baseline source was altered. See [evidence/IR-15/run-20260923T023805163543Z/notes.md](evidence/IR-15/run-20260923T023805163543Z/notes.md).
