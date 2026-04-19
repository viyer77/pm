# Execution Plan for Project Management MVP

## Part 1: Plan ✓

**Status:** Completed

**Substeps:**
- [x] Enrich PLAN.md with detailed execution steps (THIS DOCUMENT)
- [x] Create frontend/AGENTS.md describing existing frontend code
- [x] User reviews and approves the plan

**Success Criteria:**
- PLAN.md contains all 10 parts with substeps and tests
- frontend/AGENTS.md accurately documents components, data model, and tests
- User approves plan before proceeding

**Test Plan:**
- N/A (planning phase)

---

## Part 2: Docker Scaffolding

**Objective:** Set up Docker infrastructure with working FastAPI backend serving hello-world HTML and supporting a test API call.
**Status:** Completed

**Substeps:**
- [x] Create Dockerfile with Python 3.12, uv package manager, FastAPI setup
- [x] Create docker-compose.yml for local development
- [x] Initialize FastAPI backend structure in `backend/` with:
  - [x] `backend/app/main.py` - FastAPI app entry point
  - [x] `backend/app/routes/` - API route directory
  - [x] `backend/requirements.txt` - Dependencies (fastapi, uvicorn)
  - [x] `backend/pyproject.toml` - uv configuration
- [x] Create `scripts/start.sh` (Mac/Linux) - Starts Docker container
- [x] Create `scripts/start.ps1` (Windows) - Starts Docker container
- [x] Create `scripts/stop.sh` (Mac/Linux) - Stops Docker container
- [x] Create `scripts/stop.ps1` (Windows) - Stops Docker container
- [x] Add hello-world static HTML at `/static/index.html`
- [x] Add test API route `/api/test` that returns JSON
- [x] Create README in docs/ explaining Docker setup

**Success Criteria:**
- Docker image builds without errors
- `scripts/start.sh` launches the app
- Browser at `localhost:8000` serves hello-world HTML
- `curl localhost:8000/api/test` returns JSON response
- `scripts/stop.sh` cleanly stops the container
- No hardcoded secrets (use .env)

**Test Plan:**
- Integration test: Docker startup/shutdown
- API test: `/api/test` endpoint returns expected JSON

---

## Part 3: Integrate Frontend

**Objective:** Build Next.js frontend to static files and serve at `/` through FastAPI.
**Status:** Completed

**Substeps:**
- [x] Add frontend build step to Dockerfile
- [x] Configure FastAPI to serve static Next.js build at `/`
- [x] Update Next.js build output to `frontend/out/` (static export)
- [x] Configure `next.config.ts` for standalone export
- [x] Copy built frontend to backend `static/` directory in Docker
- [x] Test frontend loads at `localhost:8000/`
- [x] Verify all frontend assets load correctly (CSS, JS, fonts)
- [x] Create integration tests for frontend asset loading

**Success Criteria:**
- Frontend serves at `localhost:8000/` with all styling intact
- Kanban board is fully visible and interactive (locally, no backend yet)
- All CSS and images load correctly
- No 404 errors in browser console for frontend assets

**Test Plan:**
- Integration test: Verify frontend loads with correct DOM structure
- Asset loading test: All CSS/JS files present
- Visual regression: Kanban board renders with correct colors

---

## Part 4: Authentication (Hardcoded)

**Objective:** Add login/logout flow with hardcoded credentials ("user"/"password").
**Status:** Completed

**Substeps:**
- [x] Create `backend/app/routes/auth.py` with POST `/auth/login` endpoint
- [x] Implement session management (HTTP-only cookies or JWT)
- [x] Create login page frontend component
- [x] Add logout button to Kanban page
- [x] Protect Kanban route with auth middleware
- [x] Redirect unauthenticated users to login page
- [x] Implement session persistence across page reloads
- [x] Create tests for login/logout flow

**Success Criteria:**
- Visiting `localhost:8000/` redirects to login page
- Login with "user"/"password" succeeds
- Login with wrong credentials shows error
- After login, Kanban board is visible
- Logout clears session and redirects to login
- Refreshing page maintains login state

**Test Plan:**
- Unit test: Auth middleware validates credentials
- Integration test: Login → Kanban → Logout flow
- Session persistence test: Reload page after login

---

## Part 5: Database Schema

**Objective:** Design SQLite schema for users, kanban boards, columns, and cards.
**Status:** Completed

**Substeps:**
- [x] Design schema: users, boards, columns, cards tables
- [x] Define relationships and constraints
- [x] Save schema as JSON document at `docs/DATABASE_SCHEMA.md`
- [x] Include migration strategy
- [x] Document sample queries
- [x] User reviews and approves schema

**Schema Overview:**
```
users:
  - id (primary key)
  - username (unique)
  - password_hash

boards:
  - id (primary key)
  - user_id (foreign key)
  - title
  - created_at

columns:
  - id (primary key)
  - board_id (foreign key)
  - title
  - position

cards:
  - id (primary key)
  - column_id (foreign key)
  - title
  - description
  - position
```

**Success Criteria:**
- Schema supports all MVP features
- Relationships are clearly defined
- No data redundancy
- Schema document includes migration approach
- User approves schema

**Test Plan:**
- Schema validation: Can create tables without errors
- Relationship test: Foreign keys work correctly

---

## Part 6: Backend API

**Objective:** Build API routes for reading/updating Kanban data with database persistence.
**Status:** Completed

**Substeps:**
- [x] Create SQLAlchemy models for users, boards, columns, cards
- [x] Create `backend/app/database.py` - DB initialization (auto-create if missing)
- [x] Create API routes in `backend/app/routes/`:
  - [x] `GET /api/boards` - Get user's board
  - [x] `POST /api/columns` - Create column (rename)
  - [x] `POST /api/cards` - Create card
  - [x] `PUT /api/cards/{id}` - Update card
  - [x] `DELETE /api/cards/{id}` - Delete card
  - [x] `PUT /api/cards/{id}/move` - Move card to column
- [x] Add request validation with Pydantic models
- [x] Create comprehensive backend unit tests
- [x] Ensure database is auto-created on first run

**Success Criteria:**
- All API routes respond correctly
- Database is created automatically
- Data persists across restarts
- Auth middleware protects all routes
- Unit tests cover all routes with >90% coverage
- No SQL injection vulnerabilities

**Test Plan:**
- Unit tests: Each route tested with valid/invalid inputs
- Integration test: Full CRUD cycle with database
- Database test: Auto-creation works
- Security test: Unauthorized requests rejected

---

## Part 7: Frontend → Backend Integration

**Objective:** Connect frontend to backend API for persistent Kanban board.
**Status:** Completed

**Substeps:**
- [x] Create frontend API client (`frontend/src/lib/api.ts`)
- [x] Replace mock data with backend calls
- [x] Implement optimistic updates for UX
- [x] Add error handling and retry logic
- [x] Handle loading/error states in UI
- [x] Create integration tests for API interactions
- [x] Test drag-and-drop persistence
- [x] Test card creation/deletion/editing persistence

**Success Criteria:**
- Kanban board loads from backend
- Drag-and-drop updates persist to database
- Card CRUD operations persist
- Logout clears state and requires re-login
- Error states display user-friendly messages
- Optimistic updates prevent UI flickering

**Test Plan:**
- Integration test: Create card → verify in DB
- Persistence test: Logout/login → board data unchanged
- Error handling test: API failures show error message
- Performance test: API calls are minimal and efficient

---

## Part 8: AI Connectivity

**Objective:** Establish connection to OpenRouter API and verify AI is working.
**Status:** Completed

**Substeps:**
- [x] Create `backend/app/services/ai.py` - OpenRouter integration
- [x] Load `OPENROUTER_API_KEY` from .env
- [x] Implement simple test route: `GET /api/ai/test` (ask AI "2+2")
- [x] Handle API errors and timeouts gracefully
- [x] Create unit tests for AI service
- [x] Log all AI interactions for debugging

**Success Criteria:**
- `curl localhost:8000/api/ai/test` returns AI response
- AI correctly answers simple math questions
- API key is loaded from .env (not hardcoded)
- Errors are handled gracefully (no crashes)
- Tests verify AI connectivity

**Test Plan:**
- Unit test: AI service initialization
- Integration test: Simple question answered correctly
- Error test: Timeout/invalid key handled gracefully

---

## Part 9: Structured AI Output

**Objective:** AI assistant receives Kanban board state and conversation history; returns structured output with text response + optional board updates.
**Status:** Completed

**Substeps:**
- [x] Define Structured Output schema (Pydantic model)
  - [x] `response: str` - AI's text response
  - [x] `actions: List[CardAction]` - Optional board changes
- [x] Create `POST /api/ai/chat` endpoint that:
  - [x] Accepts user message + conversation history
  - [x] Fetches current board state
  - [x] Calls AI with system prompt + board context
  - [x] Parses structured output
  - [x] Executes any card actions (create/update/move/delete)
  - [x] Returns response + updated board state
- [x] Implement conversation history storage (in-memory for MVP)
- [x] Create comprehensive tests for all action types
- [ ] Document AI system prompt in docs/

**Success Criteria:**
- AI can parse and execute card creation/update/move/delete
- Conversation history is maintained correctly
- Structured output is reliable (>95% parse rate)
- Board state updates reflect AI actions
- All tests pass for all action types

**Test Plan:**
- Unit tests: All card action types (create, update, move, delete)
- Integration test: AI creates card → visible on board
- Conversation test: History maintained across requests
- Edge case test: Invalid actions handled gracefully

---

## Part 10: AI Chat Sidebar UI

**Objective:** Add beautiful chat sidebar to frontend; LLM-driven Kanban updates reflected in real-time UI.

**Substeps:**
- [ ] Create `ChatSidebar` component with:
  - [ ] Chat message display area
  - [ ] Input field for user messages
  - [ ] Send button
  - [ ] Clear/reset conversation option
- [ ] Implement WebSocket or polling for real-time updates
- [ ] Style sidebar with accent colors (yellow, blue, purple)
- [ ] Add loading states and error handling
- [ ] Implement real-time board refresh when AI updates cards
- [ ] Create responsive layout (sidebar + main board)
- [ ] Add animations for card updates (highlight, slide)
- [ ] Comprehensive tests for chat flow and updates

**Success Criteria:**
- Chat sidebar renders at 100% height on right side
- Messages display correctly with timestamps
- User can send messages and receive AI responses
- AI-generated card actions update board immediately
- New cards/edits highlighted with animation
- Responsive design works on desktop/tablet
- No UI jank or performance issues

**Test Plan:**
- Component test: Chat messages render correctly
- Integration test: User message → AI response → board updates
- Real-time test: Multiple users don't interfere (if applicable)
- Accessibility test: ARIA labels, keyboard navigation
- Performance test: No lag with rapid messages

---

## Success Metrics (Overall)

By completion:
- ✅ Docker container runs locally on macOS/Linux/Windows
- ✅ User logs in → sees persistent Kanban board
- ✅ Drag/drop, create, edit, delete cards all work
- ✅ AI understands board state and can modify it
- ✅ Chat sidebar allows full conversation with AI
- ✅ All changes persist across sessions
- ✅ >90% test coverage on backend
- ✅ Comprehensive integration tests
- ✅ Zero hardcoded secrets (all in .env)
