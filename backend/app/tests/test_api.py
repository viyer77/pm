import unittest
import random

from fastapi.testclient import TestClient

from app.database import reset_db_for_tests
from app.main import app


class ApiFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_db_for_tests()
        self.client = TestClient(app)

    def _login(self) -> None:
        response = self.client.post(
            "/auth/login",
            json={"username": "user", "password": "password"},
        )
        self.assertEqual(response.status_code, 200)

    def test_api_routes_require_auth(self) -> None:
        response = self.client.get("/api/boards")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Unauthorized")

    def test_get_board_returns_seeded_data(self) -> None:
        self._login()
        response = self.client.get("/api/boards")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("id", data)
        self.assertEqual(data["title"], "My Project Board")
        self.assertEqual(len(data["columns"]), 5)
        self.assertGreaterEqual(len(data["cards"]), 8)

    def test_rename_column(self) -> None:
        self._login()
        board = self.client.get("/api/boards").json()
        column_id = board["columns"][0]["id"]

        response = self.client.post("/api/columns", json={"column_id": column_id, "title": "Now"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Now")

        refreshed = self.client.get("/api/boards").json()
        renamed = [column for column in refreshed["columns"] if column["id"] == column_id][0]
        self.assertEqual(renamed["title"], "Now")

    def test_card_crud_and_move(self) -> None:
        self._login()
        board = self.client.get("/api/boards").json()
        source_column_id = board["columns"][0]["id"]
        target_column_id = board["columns"][1]["id"]

        create_response = self.client.post(
            "/api/cards",
            json={"column_id": source_column_id, "title": "New Card", "description": "Draft"},
        )
        self.assertEqual(create_response.status_code, 201)
        created = create_response.json()
        card_id = created["id"]
        self.assertEqual(created["column_id"], source_column_id)

        update_response = self.client.put(
            f"/api/cards/{card_id}",
            json={"title": "Updated Card", "description": "Updated details"},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["title"], "Updated Card")
        self.assertEqual(update_response.json()["description"], "Updated details")

        move_response = self.client.put(
            f"/api/cards/{card_id}/move",
            json={"column_id": target_column_id, "position": 0},
        )
        self.assertEqual(move_response.status_code, 200)
        self.assertEqual(move_response.json()["column_id"], target_column_id)
        self.assertEqual(move_response.json()["position"], 0)

        board_after_move = self.client.get("/api/boards").json()
        moved = [card for card in board_after_move["cards"] if card["id"] == card_id][0]
        self.assertEqual(moved["column_id"], target_column_id)

        delete_response = self.client.delete(f"/api/cards/{card_id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json(), {"success": True})

        board_after_delete = self.client.get("/api/boards").json()
        remaining_ids = {card["id"] for card in board_after_delete["cards"]}
        self.assertNotIn(card_id, remaining_ids)

    def test_move_card_is_stable_under_repeated_reorders(self) -> None:
        self._login()
        rng = random.Random(7)

        for _ in range(50):
            board = self.client.get("/api/boards").json()
            cards = board["cards"]
            columns = board["columns"]
            self.assertGreater(len(cards), 0)
            moving = rng.choice(cards)
            target_column = rng.choice(columns)
            target_count = len([card for card in cards if card["column_id"] == target_column["id"]])
            target_position = rng.randint(0, target_count)

            move_response = self.client.put(
                f"/api/cards/{moving['id']}/move",
                json={"column_id": target_column["id"], "position": target_position},
            )
            self.assertEqual(move_response.status_code, 200)

        final_board = self.client.get("/api/boards").json()
        cards_by_column: dict[int, list[int]] = {}
        for card in final_board["cards"]:
            cards_by_column.setdefault(card["column_id"], []).append(card["position"])

        for positions in cards_by_column.values():
            ordered = sorted(positions)
            self.assertEqual(ordered, list(range(len(ordered))))


if __name__ == "__main__":
    unittest.main()
