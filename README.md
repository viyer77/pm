# Kanban Studio

A single-container Kanban board with an AI assistant. Built with FastAPI, Next.js, and SQLite. The AI sidebar understands your board state and can create, move, update, or delete cards on your behalf.

## Features

- Drag-and-drop Kanban board with five columns
- Persistent state (SQLite, survives container restarts)
- AI chat sidebar powered by OpenAI — ask it to modify your board in plain English
- Session-based authentication

## Quick start

**Requirements:** Docker, an [OpenAI](https://platform.openai.com) API key.

1. Create a `.env` file in the project root:
   ```
   OPENAI_API_KEY=your_key_here
   ```

2. Start the container:
   ```bash
   ./scripts/start.sh
   ```

3. Open [http://localhost:8000](http://localhost:8000) and sign in with `user` / `password`.

4. To stop:
   ```bash
   ./scripts/stop.sh
   ```

## Architecture

```
Browser
  |── HTTP :8000
  v
FastAPI  (backend/app/main.py)
  |── /auth/*     cookie session
  |── /api/*      Kanban CRUD + AI chat
  |── /*          Next.js static export (frontend/out/)
  v
SQLAlchemy ORM → SQLite (/app/data/pm.db via Docker volume)
```

The frontend is a static Next.js export served directly by FastAPI — no separate Node server.

## AI chat

The sidebar sends your message to `POST /api/ai/chat`. The backend:

1. Fetches the current board state
2. Builds a system prompt with column/card IDs and titles
3. Calls OpenAI (model: `gpt-4o-mini`) in JSON mode
4. Parses a structured response: `{ response, actions[] }`
5. Executes any card actions, then refreshes the board in the UI

Example prompts:
- "Move all In Progress cards to Done"
- "Add a card called 'Write tests' to the Backlog column"
- "What's currently in Review?"

## Local development

**Frontend** (hot reload on port 3000):
```bash
cd frontend
npm install
npm run dev
```

**Backend** (outside Docker):
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Tests:**
```bash
# Backend
docker exec <container> python -m pytest /app/app/tests/ -v

# Frontend
cd frontend
npm run test:unit
npm run test:e2e
```

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy, SQLite |
| Frontend | Next.js 16, TypeScript, Tailwind CSS, dnd-kit |
| AI | OpenAI API — `gpt-4o-mini`, JSON-mode structured output |
| Container | Docker, uv package manager |
