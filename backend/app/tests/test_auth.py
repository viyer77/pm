import unittest

from fastapi.testclient import TestClient

from app.main import app


class AuthFlowTests(unittest.TestCase):
    def setUp(self) -> None:
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

        # Session cookie should be reused automatically by this client instance.
        auth_response = self.client.get("/auth/check")
        self.assertEqual(auth_response.status_code, 200)
        self.assertEqual(auth_response.json(), {"authenticated": True})

        logout_response = self.client.post("/auth/logout")
        self.assertEqual(logout_response.status_code, 200)
        self.assertEqual(logout_response.json()["success"], True)

        post_logout_auth_response = self.client.get("/auth/check")
        self.assertEqual(post_logout_auth_response.status_code, 200)
        self.assertEqual(post_logout_auth_response.json(), {"authenticated": False})


if __name__ == "__main__":
    unittest.main()
