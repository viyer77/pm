"""Tests for AI routes (Parts 8 & 9)"""
import json
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.database import reset_db_for_tests
from app.main import app
from app.routes.ai import _conversation_history
from app.routes.auth import _login_attempts, _sessions


def _make_ai_response(response_text: str, actions: list = None) -> str:
    return json.dumps({"response": response_text, "actions": actions or []})


class AITestRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_db_for_tests()
        _sessions.clear()
        _login_attempts.clear()
        self.client = TestClient(app)

    def _login(self) -> None:
        self.client.post("/auth/login", json={"username": "user", "password": "password"})

    def test_ai_test_requires_auth(self) -> None:
        response = self.client.get("/api/ai/test")
        self.assertEqual(response.status_code, 401)

    @patch("app.routes.ai.get_ai_service")
    def test_ai_test_returns_answer(self, mock_get_service) -> None:
        mock_service = AsyncMock()
        mock_service.query = AsyncMock(return_value="4")
        mock_get_service.return_value = mock_service

        self._login()
        response = self.client.get("/api/ai/test")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["question"], "2+2")
        self.assertIn("answer", data)

    @patch("app.routes.ai.get_ai_service")
    def test_ai_test_handles_service_error(self, mock_get_service) -> None:
        mock_service = AsyncMock()
        mock_service.query = AsyncMock(side_effect=Exception("timeout"))
        mock_get_service.return_value = mock_service

        self._login()
        response = self.client.get("/api/ai/test")
        self.assertEqual(response.status_code, 503)

    def test_ai_test_handles_missing_api_key(self) -> None:
        self._login()
        with patch("app.routes.ai.get_ai_service", side_effect=ValueError("OPENROUTER_API_KEY not found")):
            response = self.client.get("/api/ai/test")
            self.assertEqual(response.status_code, 503)


class AIChatRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_db_for_tests()
        _sessions.clear()
        _login_attempts.clear()
        _conversation_history.clear()
        self.client = TestClient(app)

    def _login(self) -> None:
        self.client.post("/auth/login", json={"username": "user", "password": "password"})

    def _get_board(self) -> dict:
        return self.client.get("/api/boards").json()

    def test_chat_requires_auth(self) -> None:
        response = self.client.post("/api/ai/chat", json={"message": "hello"})
        self.assertEqual(response.status_code, 401)

    @patch("app.routes.ai.get_ai_service")
    def test_chat_returns_response(self, mock_get_service) -> None:
        mock_service = AsyncMock()
        mock_service.chat = AsyncMock(return_value=_make_ai_response("Hello! How can I help?"))
        mock_get_service.return_value = mock_service

        self._login()
        response = self.client.post("/api/ai/chat", json={"message": "hello"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["response"], "Hello! How can I help?")
        self.assertEqual(data["actions_executed"], 0)

    @patch("app.routes.ai.get_ai_service")
    def test_chat_creates_card(self, mock_get_service) -> None:
        self._login()
        board = self._get_board()
        column_id = board["columns"][0]["id"]
        initial_card_count = len(board["cards"])

        mock_service = AsyncMock()
        mock_service.chat = AsyncMock(return_value=_make_ai_response(
            "Created a card for you.",
            [{"action": "create", "column_id": column_id, "title": "AI Created Card", "description": "From AI"}],
        ))
        mock_get_service.return_value = mock_service

        response = self.client.post("/api/ai/chat", json={"message": "Add a card"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["actions_executed"], 1)

        board_after = self._get_board()
        self.assertEqual(len(board_after["cards"]), initial_card_count + 1)
        titles = [c["title"] for c in board_after["cards"]]
        self.assertIn("AI Created Card", titles)

    @patch("app.routes.ai.get_ai_service")
    def test_chat_updates_card(self, mock_get_service) -> None:
        self._login()
        board = self._get_board()
        card = board["cards"][0]

        mock_service = AsyncMock()
        mock_service.chat = AsyncMock(return_value=_make_ai_response(
            "Updated the card.",
            [{"action": "update", "card_id": card["id"], "title": "AI Updated Title"}],
        ))
        mock_get_service.return_value = mock_service

        response = self.client.post("/api/ai/chat", json={"message": "Rename first card"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["actions_executed"], 1)

        board_after = self._get_board()
        updated = next(c for c in board_after["cards"] if c["id"] == card["id"])
        self.assertEqual(updated["title"], "AI Updated Title")

    @patch("app.routes.ai.get_ai_service")
    def test_chat_moves_card(self, mock_get_service) -> None:
        self._login()
        board = self._get_board()
        card = board["cards"][0]
        source_col = card["column_id"]
        target_col = next(col["id"] for col in board["columns"] if col["id"] != source_col)

        mock_service = AsyncMock()
        mock_service.chat = AsyncMock(return_value=_make_ai_response(
            "Moved the card.",
            [{"action": "move", "card_id": card["id"], "target_column_id": target_col, "position": 0}],
        ))
        mock_get_service.return_value = mock_service

        response = self.client.post("/api/ai/chat", json={"message": "Move first card"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["actions_executed"], 1)

        board_after = self._get_board()
        moved = next(c for c in board_after["cards"] if c["id"] == card["id"])
        self.assertEqual(moved["column_id"], target_col)

    @patch("app.routes.ai.get_ai_service")
    def test_chat_deletes_card(self, mock_get_service) -> None:
        self._login()
        board = self._get_board()
        card = board["cards"][0]
        initial_count = len(board["cards"])

        mock_service = AsyncMock()
        mock_service.chat = AsyncMock(return_value=_make_ai_response(
            "Deleted the card.",
            [{"action": "delete", "card_id": card["id"]}],
        ))
        mock_get_service.return_value = mock_service

        response = self.client.post("/api/ai/chat", json={"message": "Delete first card"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["actions_executed"], 1)

        board_after = self._get_board()
        self.assertEqual(len(board_after["cards"]), initial_count - 1)
        self.assertNotIn(card["id"], {c["id"] for c in board_after["cards"]})

    @patch("app.routes.ai.get_ai_service")
    def test_chat_history_accumulates(self, mock_get_service) -> None:
        mock_service = AsyncMock()
        mock_service.chat = AsyncMock(return_value=_make_ai_response("Reply"))
        mock_get_service.return_value = mock_service

        self._login()
        self.client.post("/api/ai/chat", json={"message": "first"})
        self.client.post("/api/ai/chat", json={"message": "second"})

        self.assertEqual(len(_conversation_history), 4)  # 2 user + 2 assistant
        self.assertEqual(_conversation_history[0]["role"], "user")
        self.assertEqual(_conversation_history[0]["content"], "first")
        self.assertEqual(_conversation_history[2]["role"], "user")
        self.assertEqual(_conversation_history[2]["content"], "second")

    def test_clear_chat(self) -> None:
        _conversation_history.append({"role": "user", "content": "test"})
        self._login()
        response = self.client.delete("/api/ai/chat")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(_conversation_history), 0)

    @patch("app.routes.ai.get_ai_service")
    def test_chat_handles_unparseable_response(self, mock_get_service) -> None:
        mock_service = AsyncMock()
        mock_service.chat = AsyncMock(return_value="not json at all")
        mock_get_service.return_value = mock_service

        self._login()
        response = self.client.post("/api/ai/chat", json={"message": "hello"})
        self.assertEqual(response.status_code, 502)

    @patch("app.routes.ai.get_ai_service")
    def test_chat_skips_invalid_action_gracefully(self, mock_get_service) -> None:
        mock_service = AsyncMock()
        mock_service.chat = AsyncMock(return_value=_make_ai_response(
            "Done.",
            [{"action": "delete", "card_id": 99999}],  # non-existent card
        ))
        mock_get_service.return_value = mock_service

        self._login()
        response = self.client.post("/api/ai/chat", json={"message": "delete card"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["actions_executed"], 0)


if __name__ == "__main__":
    unittest.main()
