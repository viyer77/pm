"""AI routes for OpenRouter integration"""
from __future__ import annotations

import collections
import json
import logging
import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.ai import get_ai_service
from .auth import require_authenticated
from .boards import (
    CreateCardRequest,
    MoveCardRequest,
    UpdateCardRequest,
    _build_board_response,
    _get_current_user,
    _get_user_board,
    create_card,
    delete_card,
    move_card,
    update_card,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory conversation history — capped at MAX_HISTORY messages
_conversation_history: list[dict] = []
MAX_HISTORY = 40

# Simple sliding-window rate limiter for /api/ai/chat: 10 requests per IP per minute
_chat_rate: dict[str, collections.deque] = {}
_CHAT_LIMIT = 10
_CHAT_WINDOW = 60


def _check_chat_rate_limit(ip: str) -> bool:
    """Returns True if rate limit exceeded."""
    now = time.time()
    if ip not in _chat_rate:
        _chat_rate[ip] = collections.deque()
    window = _chat_rate[ip]
    while window and window[0] < now - _CHAT_WINDOW:
        window.popleft()
    if len(window) >= _CHAT_LIMIT:
        return True
    window.append(now)
    return False


# ---------- Pydantic models ----------

class CardAction(BaseModel):
    action: Literal["create", "update", "move", "delete"]
    column_id: int | None = None
    title: str | None = None
    description: str | None = None
    card_id: int | None = None
    target_column_id: int | None = None
    position: int | None = None


class AIStructuredResponse(BaseModel):
    response: str
    actions: list[CardAction] = []


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    actions_executed: int


# ---------- Helpers ----------

def _build_system_prompt(board_response) -> str:
    board_state = {
        "columns": [{"id": col.id, "title": col.title} for col in board_response.columns],
        "cards": [
            {
                "id": card.id,
                "column_id": card.column_id,
                "title": card.title,
                "description": card.description or "",
            }
            for card in board_response.cards
        ],
    }
    board_state_json = json.dumps(board_state, ensure_ascii=False)

    return f"""You are a Kanban board assistant. You help the user manage their project board.

Current board state (JSON):
{board_state_json}

You MUST respond with valid JSON only, matching this schema:
{{
  "response": "<your conversational reply to the user>",
  "actions": [
    // zero or more of the following action types:
    {{"action": "create", "column_id": <int>, "title": "<str>", "description": "<str (optional)>"}},
    {{"action": "update", "card_id": <int>, "title": "<str (optional)>", "description": "<str (optional)>"}},
    {{"action": "move",   "card_id": <int>, "target_column_id": <int>, "position": <int>}},
    {{"action": "delete", "card_id": <int>}}
  ]
}}

Rules:
- Only include actions when the user explicitly requests a board change.
- Use exact column_id and card_id values from the board state above.
- For "create", column_id and title are required.
- For "update", card_id is required plus at least one of title or description.
- For "move", card_id, target_column_id, and position are required.
- For "delete", card_id is required.
- Respond naturally and confirm what you did in the "response" field."""


def _execute_action(
    action: CardAction,
    request: Request,
    db: Session,
    valid_column_ids: set[int],
) -> str | None:
    """Execute a single card action. Returns error string or None on success."""
    try:
        if action.action == "create":
            if action.column_id is None or not action.title:
                return "create action missing column_id or title"
            if action.column_id not in valid_column_ids:
                return f"create action: column_id {action.column_id} not in current board"
            create_card(
                CreateCardRequest(
                    column_id=action.column_id,
                    title=action.title,
                    description=action.description or "",
                ),
                request,
                db,
            )

        elif action.action == "update":
            if action.card_id is None:
                return "update action missing card_id"
            update_card(
                action.card_id,
                UpdateCardRequest(title=action.title, description=action.description),
                request,
                db,
            )

        elif action.action == "move":
            if action.card_id is None or action.target_column_id is None or action.position is None:
                return "move action missing card_id, target_column_id, or position"
            if action.target_column_id not in valid_column_ids:
                return f"move action: target_column_id {action.target_column_id} not in current board"
            move_card(
                action.card_id,
                MoveCardRequest(column_id=action.target_column_id, position=action.position),
                request,
                db,
            )

        elif action.action == "delete":
            if action.card_id is None:
                return "delete action missing card_id"
            delete_card(action.card_id, request, db)

    except HTTPException as e:
        return f"{action.action} failed: {e.detail}"
    except Exception as e:
        logger.error(f"Action {action.action} error: {e}")
        return f"{action.action} failed: {e}"

    return None


# ---------- Routes ----------

@router.get("/api/ai/test")
async def ai_test(request: Request):
    require_authenticated(request)
    try:
        service = get_ai_service()
        answer = await service.query("What is 2+2? Reply with just the number.")
        return {"question": "2+2", "answer": answer.strip()}
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"AI test failed: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")


@router.post("/api/ai/chat", response_model=ChatResponse)
async def ai_chat(payload: ChatRequest, request: Request, db: Session = Depends(get_db)):
    require_authenticated(request)

    client_ip = request.client.host if request.client else "unknown"
    if _check_chat_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests")

    user = _get_current_user(db, request)
    board = _get_user_board(db, user)
    board_response = _build_board_response(db, board)
    valid_column_ids = {col.id for col in board_response.columns}

    system_prompt = _build_system_prompt(board_response)

    _conversation_history.append({"role": "user", "content": payload.message})

    # Keep history within the cap
    if len(_conversation_history) > MAX_HISTORY:
        del _conversation_history[: len(_conversation_history) - MAX_HISTORY]

    try:
        service = get_ai_service()
        raw = await service.chat(_conversation_history, system_prompt)
    except ValueError as e:
        _conversation_history.pop()
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        _conversation_history.pop()
        logger.error(f"AI chat failed: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")

    try:
        parsed = AIStructuredResponse.model_validate(json.loads(raw))
    except Exception as e:
        logger.error(f"Failed to parse AI response: {e}\nRaw: {raw}")
        # Do NOT add unparseable response to history — it would corrupt future context
        _conversation_history.pop()
        raise HTTPException(status_code=502, detail="AI returned unparseable response")

    _conversation_history.append({"role": "assistant", "content": raw})

    errors: list[str] = []
    for action in parsed.actions:
        err = _execute_action(action, request, db, valid_column_ids)
        if err:
            logger.warning(f"Action skipped: {err}")
            errors.append(err)

    executed = len(parsed.actions) - len(errors)
    return ChatResponse(response=parsed.response, actions_executed=executed)


@router.delete("/api/ai/chat")
async def clear_chat(request: Request):
    require_authenticated(request)
    _conversation_history.clear()
    return {"cleared": True}
