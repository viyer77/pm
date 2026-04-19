# AI System Prompt

The system prompt is built dynamically on every `POST /api/ai/chat` request in `backend/app/routes/ai.py` (`_build_system_prompt`). It is never hardcoded — board state is injected fresh each call so the AI always sees accurate column and card IDs.

## Structure

```
You are a Kanban board assistant. You help the user manage their project board.

Current board state:
Columns:
  - id=<n>  title="<title>"
  ...

Cards:
  - id=<n>  column_id=<n>  title="<title>"  description="<desc>"
  ...

You MUST respond with valid JSON only, matching this schema:
{
  "response": "<conversational reply>",
  "actions": [ ... ]
}

Rules:
  ...
```

## Response schema

The AI must reply with a JSON object. OpenAI's JSON mode (`response_format: {"type": "json_object"}`) enforces this at the API level.

```json
{
  "response": "string — conversational reply shown to the user",
  "actions": [
    { "action": "create", "column_id": 1, "title": "Card title", "description": "optional" },
    { "action": "update", "card_id": 5, "title": "New title", "description": "New desc" },
    { "action": "move",   "card_id": 3, "target_column_id": 2, "position": 0 },
    { "action": "delete", "card_id": 7 }
  ]
}
```

`actions` may be an empty list when no board changes are requested.

## Action rules enforced by the prompt

| Action | Required fields | Optional fields |
|--------|----------------|-----------------|
| create | `column_id`, `title` | `description` |
| update | `card_id` | `title`, `description` (at least one) |
| move   | `card_id`, `target_column_id`, `position` | — |
| delete | `card_id` | — |

- Only exact `column_id` and `card_id` values from the board state are valid.
- Actions are only included when the user explicitly requests a board change.
- The `response` field confirms what was done in natural language.

## Conversation history

Turns are stored in-memory as a module-level list in `backend/app/routes/ai.py` (`_conversation_history`). Each entry is `{"role": "user"|"assistant", "content": "..."}`. The full history is prepended to every request after the system prompt, giving the AI multi-turn context. History is cleared via `DELETE /api/ai/chat`.

## Model

**OpenAI `gpt-4o-mini`** via `https://api.openai.com/v1/chat/completions`. Temperature `0.7`, max tokens `1000`.
