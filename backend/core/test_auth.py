from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase


class SessionAuthenticationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="operator",
            email="operator@example.com",
            password="correct-horse-battery-staple",
        )

    def _csrf(self, client: Client) -> str:
        response = client.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        token = response.json()["csrfToken"]
        self.assertTrue(token)
        return token

    def _login(self, client: Client, *, identifier: str = "operator", remember: bool = False):
        token = self._csrf(client)
        return client.post(
            "/api/auth/login/",
            data=json.dumps(
                {
                    "identifier": identifier,
                    "password": "correct-horse-battery-staple",
                    "remember": remember,
                }
            ),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

    def test_csrf_bootstrap_sets_cookie_and_returns_token(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get("/api/auth/csrf/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["csrfToken"])
        self.assertIn("csrftoken", client.cookies)
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_me_requires_authenticated_session(self):
        client = Client(enforce_csrf_checks=True)

        response = client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["message"], "Authentication required.")

    def test_login_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)

        response = client.post(
            "/api/auth/login/",
            data=json.dumps(
                {
                    "identifier": "operator",
                    "password": "correct-horse-battery-staple",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

    def test_invalid_credentials_fail_closed(self):
        client = Client(enforce_csrf_checks=True)
        token = self._csrf(client)

        response = client.post(
            "/api/auth/login/",
            data=json.dumps({"identifier": "operator", "password": "wrong"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("sessionid", client.cookies)

    def test_valid_username_login_creates_session_and_me_returns_identity(self):
        client = Client(enforce_csrf_checks=True)

        response = self._login(client)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["authenticated"])
        self.assertEqual(response.json()["user"]["username"], "operator")
        self.assertIn("sessionid", client.cookies)
        self.assertTrue(client.session.get_expire_at_browser_close())

        me = client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertTrue(me.json()["authenticated"])
        self.assertEqual(me.json()["user"]["email"], "operator@example.com")

    def test_unique_email_can_be_used_as_login_identifier(self):
        client = Client(enforce_csrf_checks=True)

        response = self._login(client, identifier="OPERATOR@example.com")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["username"], "operator")

    def test_remember_me_uses_persistent_session_expiry(self):
        client = Client(enforce_csrf_checks=True)

        response = self._login(client, remember=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["remember"])
        self.assertFalse(client.session.get_expire_at_browser_close())

    def test_logout_requires_csrf_and_invalidates_session(self):
        client = Client(enforce_csrf_checks=True)
        login_response = self._login(client)
        self.assertEqual(login_response.status_code, 200)

        missing_csrf = client.post("/api/auth/logout/", data="{}", content_type="application/json")
        self.assertEqual(missing_csrf.status_code, 403)

        token = self._csrf(client)
        response = client.post(
            "/api/auth/logout/",
            data="{}",
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["authenticated"])

        me = client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 401)
