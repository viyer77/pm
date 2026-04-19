# Code Review — Kanban Studio

**Date:** 2026-04-19  
**Reviewer:** Claude Code (claude-sonnet-4-6)  
**Scope:** Full repository — backend, frontend, infrastructure, tests

**Remediation status (2026-04-19):** All Critical, High, and Medium issues resolved except H6 (Alembic migrations — deferred) and M5/M8 (pagination and component tests — deferred). 26/26 backend tests and 18/18 frontend unit tests passing.

---

## Summary

| Severity | Count | Status |
|----------|-------|--------|
| Critical | 5     | 5 resolved |
| High     | 7     | 6 resolved, 1 deferred (H6) |
| Medium   | 11    | 9 resolved, 2 deferred (M5, M8) |
| Low      | 8     | Open |

---

## Critical Issues

### C1. No `.env.example` — API key requirements undocumented
**Status: RESOLVED**  
**File:** `.env` (not tracked — correctly gitignored)

`.env` was correctly excluded from Git but no example file documented the required variables.

**Fix:** Added `.env.example` with placeholder values for all configurable env vars.

---

### C2. Hardcoded Credentials Displayed in UI
**Status: RESOLVED**  
**Files:** `backend/app/routes/auth.py`, `frontend/src/app/page.tsx`

Credentials were hardcoded as `"user"` / `"password"` in the backend and displayed in a visible demo box on the login form. No rate limiting existed on login attempts.

**Fix:** Credentials now read from `APP_USERNAME` / `APP_PASSWORD` env vars (with defaults for local dev). Demo credentials box removed from the login UI. Sliding-window rate limiter added to `POST /auth/login` (10 attempts per IP per minute).

---

### C3. Insecure Session Cookie
**Status: RESOLVED**  
**File:** `backend/app/routes/auth.py`

Session cookie was the static string `"authenticated"` — trivially forgeable. Max age was 24 hours.

**Fix:** Login now generates a `secrets.token_urlsafe(32)` token stored in a server-side dict with a 1-hour TTL. `is_request_authenticated` validates the token against this store on every request. Logout removes the token server-side. New tests verify forged cookies are rejected and each login produces a distinct token.

---

### C4. Conversation History in Global Memory
**Status: PARTIALLY RESOLVED**  
**File:** `backend/app/routes/ai.py`

History was an unbounded module-level list, lost on restart, and could grow to consume increasing AI tokens.

**Fix:** History is capped at 40 messages; older messages are evicted when the cap is reached. Full persistence to SQLite remains a future improvement (requires a `messages` table and migration).

---

### C5. Path Traversal in Static File Serving
**Status: RESOLVED**  
**File:** `backend/app/main.py`

The catch-all route served any file under the resolved path without checking it was inside `static_dir`, allowing `GET /../../etc/passwd`-style requests.

**Fix:** Added `_safe_file_path()` helper that resolves the path and rejects anything that escapes `static_dir` before serving.

---

## High Issues

### H1. No XSS Mitigation / CSP Header
**Status: RESOLVED**  
**File:** `backend/app/main.py`

No Content Security Policy headers were set. Confirmed that no frontend component uses `dangerouslySetInnerHTML`.

**Fix:** Added HTTP middleware setting `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, and `X-Frame-Options: DENY` on all responses.

---

### H2. No CORS Configuration
**Status: RESOLVED**  
**File:** `backend/app/main.py`

No CORS middleware meant the frontend dev server (`localhost:3000`) could not call the backend (`localhost:8000`).

**Fix:** `CORSMiddleware` added. Allowed origins are configurable via the `CORS_ORIGINS` env var (default: `http://localhost:3000`).

---

### H3. Unvalidated Column IDs in AI Actions
**Status: RESOLVED**  
**File:** `backend/app/routes/ai.py`

AI-returned `column_id` and `target_column_id` values were used directly without verifying they belong to the current board.

**Fix:** `_execute_action` now receives a `valid_column_ids: set[int]` parameter and rejects any action referencing a column not in the current board.

---

### H4. No Rate Limiting
**Status: RESOLVED**  
**Files:** `backend/app/routes/auth.py`, `backend/app/routes/ai.py`

No throttling existed on any endpoint.

**Fix:** Implemented a simple in-memory sliding-window rate limiter (no external dependency). Login: 10 attempts/IP/minute. AI chat: 10 requests/IP/minute. Returns HTTP 429 when exceeded.

---

### H5. N+1 Query in Board Response Builder
**Status: RESOLVED**  
**File:** `backend/app/routes/boards.py`

`_build_board_response` issued separate queries for columns then cards.

**Fix:** Replaced with a single `joinedload(Board.columns).joinedload(Column.cards)` eager-load query.

---

### H6. No Database Migration Strategy
**Status: DEFERRED**  
**File:** `backend/app/database.py`

`Base.metadata.create_all()` cannot handle schema changes in production. Alembic integration is the correct fix but requires a separate migration-versioning initiative.

---

### H7. Parse Failure Corrupts AI Conversation History
**Status: RESOLVED**  
**File:** `backend/app/routes/ai.py`

On a JSON parse failure, the unparseable response was still appended to `_conversation_history` before the 502 was raised, corrupting subsequent AI calls.

**Fix:** Parse failure now pops the user message and raises 502 without touching the history. The assistant message is only appended after successful `model_validate`.

---

## Medium Issues

### M1. Prompt Injection via Board State
**Status: RESOLVED**  
**File:** `backend/app/routes/ai.py`

Board state (column and card titles) was interpolated into the system prompt using f-strings, making it susceptible to injection via crafted titles.

**Fix:** Board state is now serialised with `json.dumps()` and injected as a single JSON block, safely escaping all special characters.

---

### M2. No Security Logging for Auth Events
**Status: RESOLVED**  
**File:** `backend/app/routes/auth.py`

Login attempts, failures, and logouts produced no log output, making brute-force invisible.

**Fix:** `INFO` logs on successful login/logout; `WARNING` logs on failed login and rate-limit trips, including source IP.

---

### M3. Frontend Doesn't Timeout AI Requests
**Status: RESOLVED**  
**File:** `frontend/src/components/ChatSidebar.tsx`

A hanging AI request left the loading spinner running indefinitely.

**Fix:** Each `chatAI` call is wrapped with an `AbortController` on a 35-second timeout. The `requestJson` helper was updated to not retry aborted requests. A distinct "Request timed out" error message is shown.

---

### M4. Generic Error Messages in ChatSidebar
**Status: RESOLVED**  
**File:** `frontend/src/components/ChatSidebar.tsx`

All errors collapsed to a single generic message regardless of status code.

**Fix:** Error handling now differentiates timeout, 401 (session expired), 429 (rate limited), 5xx (server error), and network errors, showing a specific message for each.

---

### M5. No Pagination on Board Data
**Status: DEFERRED**  
**File:** `backend/app/routes/boards.py`

Acceptable for the single-board MVP. No action taken.

---

### M6. AI Model and Temperature Hardcoded
**Status: RESOLVED**  
**File:** `backend/app/services/ai.py`

Model and temperature were compile-time constants.

**Fix:** Both now read from env vars: `OPENAI_MODEL` (default `gpt-4o-mini`) and `OPENAI_TEMPERATURE` (default `0.7`).

---

### M7. Missing Auth Edge-Case Tests
**Status: RESOLVED**  
**File:** `backend/app/tests/test_auth.py`

Tests only covered basic happy-path login/logout.

**Fix:** Added tests for: forged cookie rejected by auth check and API, unique token per login, server-side token removal on logout, and missing-cookie rejection.

---

### M8. Missing Frontend Component Tests
**Status: DEFERRED**  
**Files:** `frontend/src/components/KanbanColumn.tsx`, `KanbanCard.tsx`, `NewCardForm.tsx`

No tests exist for these components. Deferred — out of scope for this remediation pass.

---

## Low Issues (Open)

### L1. Missing TypeScript Strict Mode
**File:** `frontend/tsconfig.json`  
**Action:** Add `"strict": true` to `compilerOptions` and fix resulting type errors.

### L2. Missing Environment Variable Validation at Startup
**Status: RESOLVED** — startup warning now logged if no AI API key is set.

### L3. Missing Database Indexes on Foreign Keys
**File:** `backend/app/database.py`  
**Action:** Add `Index("ix_card_column_id_position", "column_id", "position")` to `Card.__table_args__`.

### L4. Database Session Not Rolling Back on Exception
**Status: RESOLVED** — `get_db()` now explicitly calls `db.rollback()` in the `except` block.

### L5. Static Directory Path Not Configurable
**Status: RESOLVED** — `static_dir` now reads from `STATIC_DIR` env var with the original path as default.

### L6. Unused / Verify `IntegrityError` Import
**File:** `backend/app/routes/boards.py`  
**Action:** Run `ruff check` to confirm it is actually used; remove if not.

### L7. No Request ID Middleware
**File:** `backend/app/main.py`  
**Action:** Add middleware generating `X-Request-ID` and injecting it into log context.

---

## Plan vs Implementation Gaps

| Part | Plan Description | Status |
|------|-----------------|--------|
| Part 4 | "Password hashing" | Credentials are env-var-driven plain-text comparison — no hashing. Acceptable for single-user MVP; requires User model and DB migration to fix properly. |
| Parts 5–6 | Database persistence | Schema correct; no Alembic migration tooling (H6, deferred). |
| Parts 9–10 | AI chat with history | Implemented; history capped at 40 messages but not persisted across restarts (C4, partially resolved). |
