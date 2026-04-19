# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Kanban Studio: a single-container web app where a FastAPI backend serves both the REST API and the statically built Next.js frontend. State is persisted in SQLite. An AI chat sidebar (via OpenRouter) is planned but partially implemented.

Review `docs/PLAN.md` before starting any new work to understand what is complete and what remains.

## Commands

### Docker (primary workflow)

```bash
./scripts/start.sh   # build image and start at http://localhost:8000
./scripts/stop.sh    # stop container
```

Requires `.env` in project root with `OPENROUTER_API_KEY=...`.

### Frontend (local dev)

```bash
cd frontend
npm install
npm run dev          # dev server on localhost:3000
npm run build        # static export -> frontend/out/
npm run lint         # eslint
npm run test:unit    # vitest (one-shot)
npm run test:unit:watch
npm run test:e2e     # playwright (auto-starts dev server)
npm run test:all     # unit + e2e
```

### Backend (local dev, outside Docker)

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Backend tests

```bash
python -m pytest backend/app/tests/
```

## Architecture

```
Browser
  |── HTTP :8000
  v
FastAPI (backend/app/main.py)
  |── /auth/*   → routes/auth.py       cookie session (hardcoded user/password)
  |── /api/*    → routes/boards.py     Kanban CRUD, requires session cookie
  |── /*        → static file serving  frontend/out/ (Next.js static export)
  v
SQLAlchemy ORM → SQLite (/app/data/pm.db via Docker volume "pm_data")
```

**Frontend state flow:**
- `page.tsx` calls `GET /auth/check` on load; renders login form or `<KanbanBoard>`
- `KanbanBoard` fetches `GET /api/boards`, maps backend numeric IDs to UI IDs (`col-{n}`, `card-{n}`)
- All mutations use optimistic updates — UI changes immediately, rolled back on API failure
- `lib/api.ts` wraps fetch with retry logic (2 retries, 200ms delay, on 5xx/429)
- `lib/kanban.ts` contains pure drag-and-drop reorder logic (`moveCard`)
- dnd-kit handles drag-and-drop; `KanbanBoard.handleDragEnd` computes new position and calls the API

**Card reordering:** uses a staged offset algorithm in the move endpoint to avoid SQLite unique constraint violations on the `position` column.

**AI service:** `backend/app/services/ai.py` has an `AIService` class for OpenRouter calls (model: `openai/gpt-oss-120b`) but is not yet connected to any route. Parts 8-10 of the plan cover the `POST /api/ai/chat` endpoint and the `ChatSidebar` UI component.

## Coding Standards

- No over-engineering. No unnecessary defensive programming. No extra features.
- No emojis anywhere.
- Keep READMEs minimal.
- When debugging: identify root cause with evidence before fixing. Do not guess.
- Use latest idiomatic versions of libraries.

## Brand Colors

```
--accent-yellow:    #ecad0a   (highlights, accent lines)
--primary-blue:     #209dd7   (links, key sections)
--secondary-purple: #753991   (submit buttons, important actions)
--navy-dark:        #032147   (main headings)
--gray-text:        #888888   (labels, supporting text)
```
