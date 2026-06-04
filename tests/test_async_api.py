import unittest
from unittest.mock import AsyncMock, patch

import httpx

from pyLuogu.async_api import asyncLuoguAPI


class TestAsyncLuoguAPI(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.api = asyncLuoguAPI()

    async def asyncTearDown(self):
        await self.api.client.aclose()

    async def test_send_request_rebuilds_post_request_after_csrf_refresh(self):
        self.api.x_csrf_token = "stale-token"
        seen_tokens = []

        async def fake_send(request: httpx.Request) -> httpx.Response:
            seen_tokens.append(request.headers.get("x-csrf-token"))
            if len(seen_tokens) == 1:
                return httpx.Response(
                    403,
                    request=request,
                    json={"errorMessage": "token_expired"},
                )
            return httpx.Response(
                200,
                request=request,
                json={"currentData": {"rid": 12345}},
            )

        async def refresh_csrf(endpoint=""):
            self.api.x_csrf_token = "fresh-token"
            return self.api.x_csrf_token

        with patch.object(self.api.client, "send", new=AsyncMock(side_effect=fake_send)), patch.object(
            self.api, "_get_csrf", new=AsyncMock(side_effect=refresh_csrf)
        ) as get_csrf:
            result = await self.api._send_request(
                endpoint="fe/api/problem/submit/P1000",
                method="POST",
                data={"code": "print(1)"},
            )

        self.assertEqual(result["rid"], 12345)
        self.assertEqual(seen_tokens, ["stale-token", "fresh-token"])
        self.assertEqual(get_csrf.await_count, 1)

    async def test_explicit_extra_api_uses_route_table(self):
        with patch.object(self.api, "_send_request", new=AsyncMock(return_value={"ok": True})) as send:
            result = await self.api.join_contest(123, request={"code": "abc"})

        call_args = send.call_args
        assert call_args is not None
        self.assertEqual(result.data, {"ok": True})
        self.assertEqual(call_args.kwargs["endpoint"], "contest/123/join")
        self.assertEqual(call_args.kwargs["method"], "POST")
        self.assertEqual(call_args.kwargs["data"], {"code": "abc"})

    async def test_explicit_extra_api_supports_raw_response_type(self):
        with patch.object(self.api, "_send_request", new=AsyncMock(return_value=b"image")) as send:
            result = await self.api.get_lg4_captcha()

        call_args = send.call_args
        assert call_args is not None
        self.assertEqual(result, b"image")
        self.assertEqual(call_args.kwargs["endpoint"], "lg4/captcha")
        self.assertEqual(call_args.kwargs["response_type"], "bytes")

    async def test_get_user_following_list_accepts_plain_user_arrays(self):
        payload = {
            "users": [
                {
                    "uid": 1,
                    "name": "user",
                    "avatar": "avatar",
                    "slogan": "",
                    "badge": "",
                    "isAdmin": False,
                    "isBanned": False,
                    "isRoot": False,
                    "color": "Blue",
                    "ccfLevel": 0,
                    "background": "",
                    "followingCount": 1,
                    "followerCount": 2,
                    "ranking": 3,
                    "registerTime": 4,
                    "introduction": "",
                    "prize": [],
                    "elo": None,
                    "eloMax": None,
                    "userRelationship": 0,
                    "reverseUserRelationship": 0,
                    "passedProblemCount": 5,
                    "submittedProblemCount": 6,
                }
            ]
        }

        with patch.object(self.api, "_send_request", new=AsyncMock(return_value=payload)):
            users = await self.api.get_user_following_list(1)

        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].uid, 1)
        self.assertEqual(users[0].submittedProblemCount, 6)


if __name__ == "__main__":
    unittest.main()
