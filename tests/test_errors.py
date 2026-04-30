import unittest

from pyLuogu.errors import (
    AuthenticationError,
    LuoguAPIError,
    NeedCaptcha,
    NotFoundError,
    RateLimitError,
    RequestError,
    ServerError,
)


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


if __name__ == "__main__":
    unittest.main()
