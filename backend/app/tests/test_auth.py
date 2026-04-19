import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.routes.auth import _login_attempts, _sessions


class AuthFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        _sessions.clear()
        _login_attempts.clear()
        self.client = TestClient(app)

    def test_auth_check_is_false_without_session(self) -> None:
        response = self.client.get("/auth/check")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"authenticated": False})

    def test_login_rejects_invalid_credentials(self) -> None:
        response = self.client.post(
            "/auth/login",
            json={"username": "wrong", "password": "creds"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid credentials")

    def test_login_logout_and_session_persistence(self) -> None:
        login_response = self.client.post(
            "/auth/login",
            json={"username": "user", "password": "password"},
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.json()["success"], True)
        self.assertIn("session", login_response.cookies)

        auth_response = self.client.get("/auth/check")
        self.assertEqual(auth_response.status_code, 200)
        self.assertEqual(auth_response.json(), {"authenticated": True})

        logout_response = self.client.post("/auth/logout")
        self.assertEqual(logout_response.status_code, 200)
        self.assertEqual(logout_response.json()["success"], True)

        post_logout_auth_response = self.client.get("/auth/check")
        self.assertEqual(post_logout_auth_response.status_code, 200)
        self.assertEqual(post_logout_auth_response.json(), {"authenticated": False})

    def test_forged_session_cookie_is_rejected(self) -> None:
        """A random cookie value not in _sessions must not grant access."""
        client = TestClient(app)
        client.cookies.set("session", "not-a-real-token")
        response = client.get("/auth/check")
        self.assertEqual(response.json(), {"authenticated": False})

        api_response = client.get("/api/boards")
        self.assertEqual(api_response.status_code, 401)

    def test_session_token_is_cryptographically_random(self) -> None:
        """Each login must produce a distinct token, not a static value."""
        tokens = set()
        for _ in range(5):
            _sessions.clear()
            _login_attempts.clear()
            c = TestClient(app)
            c.post("/auth/login", json={"username": "user", "password": "password"})
            token = c.cookies.get("session")
            self.assertIsNotNone(token)
            self.assertNotEqual(token, "authenticated")
            tokens.add(token)
        self.assertEqual(len(tokens), 5, "Each login should produce a unique token")

    def test_logout_invalidates_token_server_side(self) -> None:
        """After logout the server-side token store must be empty."""
        self.client.post("/auth/login", json={"username": "user", "password": "password"})
        self.assertEqual(len(_sessions), 1)
        self.client.post("/auth/logout")
        self.assertEqual(len(_sessions), 0)

    def test_missing_cookie_rejected_by_api(self) -> None:
        response = TestClient(app).get("/api/boards")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
