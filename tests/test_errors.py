import unittest

import httpx

from pyLuogu.errors import (
    AuthenticationError,
    LuoguAPIError,
    NeedCaptcha,
    NotFoundError,
    RateLimitError,
    RequestError,
    ServerError,
)
from pyLuogu.request_helpers import decode_json_response, handle_luogu_json_payload
from pyLuogu.transport import SyncLuoguTransportMixin
from pyLuogu.types import LuoguCookies


class TestLuoguAPIErrors(unittest.TestCase):
    def test_error_hierarchy(self):
        self.assertIsInstance(AuthenticationError("auth"), LuoguAPIError)
        self.assertIsInstance(NotFoundError("missing"), LuoguAPIError)
        self.assertIsInstance(RateLimitError("slow down"), LuoguAPIError)
        self.assertIsInstance(ServerError("server"), LuoguAPIError)
        self.assertIsInstance(NeedCaptcha("captcha"), LuoguAPIError)

    def test_request_error_stores_status_code(self):
        error = RequestError("boom", status_code=429)

        self.assertEqual(str(error), "boom")
        self.assertEqual(error.status_code, 429)

    def test_auth_login_payload_raises_authentication_error(self):
        with self.assertRaises(AuthenticationError):
            handle_luogu_json_payload(
                {"instance": "auth", "template": "login", "status": 200, "data": {}},
                "record/list",
            )

    def test_decode_json_response_recognizes_html_login_page_as_auth_error(self):
        request = httpx.Request("GET", "https://www.luogu.com.cn/user/123/practice")
        response = httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text="<html><body>login required</body></html>",
            request=request,
        )

        with self.assertRaises(AuthenticationError):
            decode_json_response(response)

    def test_response_data_or_retry_retries_when_html_contains_c3vk_challenge(self):
        class DummyTransport(SyncLuoguTransportMixin):
            def __init__(self):
                self._init_transport("https://www.luogu.com.cn", LuoguCookies({"__client_id": "a", "_uid": "1"}), 2)
                self.client = httpx.Client()

        transport = DummyTransport()
        request = httpx.Request("GET", "https://www.luogu.com.cn/record/list?page=1")
        response = httpx.Response(
            200,
            headers={"content-type": "text/html; charset=UTF-8"},
            text='<script>window.open("/record/list?page=1","_self");document.cookie="C3VK=61e891; path=/; max-age=300;"</script>',
            request=request,
        )

        try:
            result = transport._response_data_or_retry(response, "record/list", "json")
            self.assertEqual(getattr(result, "delay", None), 0.2)
            self.assertEqual(transport.client.cookies.get("C3VK"), "61e891")
        finally:
            transport.client.close()


if __name__ == "__main__":
    unittest.main()
