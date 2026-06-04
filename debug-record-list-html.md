# [OPEN] Debug Session: record-list-html

## Bug Summary
- Symptom: report page shows `record/list` decode failure with `status=200` and `content_type=text/html; charset=UTF-8`, causing `pure_error_records = 579`.
- Expected: `record/list` should return JSON, or the system should classify HTML as auth/risk-control and degrade gracefully instead of turning the whole batch into pure errors.

## Falsifiable Hypotheses
1. `record/list` returns a normal login page HTML, which should be classified as `AuthenticationError`.
2. `record/list` returns an anti-bot / risk-control HTML page rather than a login page, so current login-page detection misses it.
3. `record/list` requires additional request context (cookie/header) that is not needed by `practice`, so only this endpoint fails.
4. The batch degrades to pure errors because list fetching fails before summary fallback can be built.

## Evidence Plan
- Add instrumentation around JSON decode failure classification to capture endpoint, content type, and HTML prefix classification result.
- Add instrumentation around record list retrieval and fallback path selection to confirm whether fallback is skipped before record summaries are available.
- Reproduce with controlled inputs and compare pre-fix vs post-fix behavior.

## Status
- Evidence collected and minimal fix applied.

## Evidence
- Pre-fix real reproduction on `record/list?page=1&uid=570175&pid=P4785&user=570175` returned `status=200` with `content_type=text/html; charset=UTF-8`.
- HTML prefix was a script page that sets `document.cookie="C3VK=61e891; ..."` and then `window.open(..., "_self")`, which confirms a C3VK challenge page rather than a normal JSON payload.
- Pre-fix `_pick_record_for_problem()` failed before any summary fallback could be built, producing pure error records.
- Post-fix reproduction changed `api.get_record_list(...)` from `RequestError(Failed to decode JSON response ...)` to `AuthenticationError(Need Login)`, proving the C3VK challenge page is now handled.
- Post-fix `_pick_record_for_problem()` returns a skip fallback payload with `_detail_skipped` and `_record_list_unavailable` while tripping a circuit breaker for subsequent problems.

## Root Cause
- The transport layer already knew how to extract `C3VK` from HTML, but only reused that logic in CSRF fetching.
- Normal JSON GET requests such as `record/list` did not reuse the same challenge handling, so the first HTML challenge page was treated as a JSON decode failure.
- After the request moved past the challenge, invalid/insufficient cookies still caused `Need Login`; meanwhile, record selection code had no list-level fallback, so every problem became a pure error.

## Fix
- Added transport-layer handling to detect HTML C3VK challenge pages during JSON requests, store `C3VK`, and retry automatically.
- Added list-level fallback and circuit breaker in `_pick_record_for_problem()` so blocking list failures degrade to `_detail_skipped` instead of pure per-problem errors.
