"""The preview Basic gate is the only thing standing in front of a public preview URL."""

import base64
from unittest.mock import patch

from c4_project.preview_auth import basic_auth_middleware
from django.test import RequestFactory, SimpleTestCase

ENV = {"DJANGO_SUPERUSER_USERNAME": "preview", "DJANGO_SUPERUSER_PASSWORD": "s3cret"}


def _request(credentials=None):
    """Builds a request carrying the given 'user:password' as a Basic header."""
    request = RequestFactory().get("/")
    if credentials is not None:
        request.META["HTTP_AUTHORIZATION"] = "Basic " + base64.b64encode(credentials.encode()).decode()
    return request


class PreviewBasicAuthTest(SimpleTestCase):
    def setUp(self):
        self.reached = []

    def _middleware(self, env=ENV):
        """Credentials are read when the middleware is built, so build it under the patch."""
        with patch.dict("os.environ", env, clear=True):
            return basic_auth_middleware(lambda request: self.reached.append(request) or "ok")

    def test_correct_credentials_reach_the_app(self):
        self.assertEqual(self._middleware()(_request("preview:s3cret")), "ok")
        self.assertEqual(len(self.reached), 1)

    def test_no_header_is_challenged(self):
        response = self._middleware()(_request())
        self.assertEqual(response.status_code, 401)
        self.assertIn("Basic", response["WWW-Authenticate"])
        self.assertEqual(self.reached, [])

    def test_wrong_password_is_rejected(self):
        self.assertEqual(self._middleware()(_request("preview:wrong")).status_code, 401)
        self.assertEqual(self.reached, [])

    def test_wrong_username_is_rejected(self):
        self.assertEqual(self._middleware()(_request("admin:s3cret")).status_code, 401)
        self.assertEqual(self.reached, [])

    def test_unset_password_fails_closed(self):
        middleware = self._middleware(env={})
        self.assertEqual(middleware(_request("preview:")).status_code, 401)
        self.assertEqual(middleware(_request()).status_code, 401)
        self.assertEqual(self.reached, [])

    def test_malformed_header_is_rejected(self):
        request = RequestFactory().get("/")
        request.META["HTTP_AUTHORIZATION"] = "Basic not-base64!!"
        self.assertEqual(self._middleware()(request).status_code, 401)
        self.assertEqual(self.reached, [])
