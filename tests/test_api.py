import unittest
from unittest.mock import patch

import httpx

from pyLuogu.api import luoguAPI
from pyLuogu.static_api import staticLuoguAPI
from pyLuogu.types import ProblemSettings


class TestLuoguAPI(unittest.TestCase):
    def setUp(self):
        self.api = luoguAPI()

    def test_send_request_rebuilds_post_request_after_csrf_refresh(self):
        self.api.x_csrf_token = "stale-token"
        seen_tokens = []

        def fake_send(request: httpx.Request) -> httpx.Response:
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
                json={"currentData": {"pid": "P1000"}},
            )

        def refresh_csrf(endpoint=""):
            self.api.x_csrf_token = "fresh-token"
            return self.api.x_csrf_token

        with patch.object(self.api.client, "send", side_effect=fake_send), patch.object(
            self.api, "_get_csrf", side_effect=refresh_csrf
        ) as get_csrf:
            result = self.api._send_request(
                endpoint="fe/api/problem/edit/P1000",
                method="POST",
                data={"settings": {}},
            )

        self.assertEqual(result["pid"], "P1000")
        self.assertEqual(seen_tokens, ["stale-token", "fresh-token"])
        self.assertEqual(get_csrf.call_count, 1)

    def test_get_problem_list_flattens_nested_response(self):
        payload = {
            "problems": {
                "count": 1,
                "perPage": 50,
                "result": [
                    {
                        "pid": "P1000",
                        "title": "A+B Problem",
                        "difficulty": 1,
                        "type": "P",
                        "submitted": False,
                        "accepted": False,
                        "tags": [1, 2],
                        "totalSubmit": 10,
                        "totalAccepted": 5,
                        "flag": 0,
                        "fullScore": 100,
                    }
                ],
            }
        }

        with patch.object(self.api, "_send_request", return_value=payload):
            result = self.api.get_problem_list(page=2)

        self.assertEqual(result.count, 1)
        self.assertEqual(result.perPage, 50)
        self.assertEqual(result.problems[0].pid, "P1000")
        self.assertEqual(result.problems[0].tags, [1, 2])

    def test_get_problem_zips_time_and_memory_limits(self):
        payload = {
            "problem": {
                "pid": "P1000",
                "title": "A+B Problem",
                "difficulty": 1,
                "type": "P",
                "submitted": False,
                "accepted": False,
                "tags": [],
                "totalSubmit": 10,
                "totalAccepted": 5,
                "flag": 0,
                "fullScore": 100,
                "content": {
                    "user": {
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
                    },
                    "version": 1,
                    "name": "A+B Problem",
                    "background": "",
                    "description": "",
                    "formatI": "",
                    "formatO": "",
                    "hint": "",
                    "locale": "zh-CN",
                },
                "samples": [],
                "provider": {
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
                },
                "attachments": [],
                "limits": {
                    "time": [1000, 2000],
                    "memory": [128, 256],
                },
                "showScore": True,
                "score": 100,
                "stdCode": "",
                "vjudge": None,
                "acceptLanguages": [0],
            },
            "problemSolutions": [],
            "contests": [],
            "userScore": None,
            "canEdit": False,
            "recommendations": [],
            "discussions": [],
            "lastLanguage": 0,
            "lastCode": "",
            "canSeeSolution": True,
            "acceptSolution": True,
        }

        with patch.object(self.api, "_send_request", return_value=payload):
            result = self.api.get_problem("P1000")

        self.assertEqual(result.problem.limits, [(1000, 128), (2000, 256)])

    def test_get_problem_uses_current_contest_id_param(self):
        payload = {
            "problem": {
                "pid": "P1000",
                "title": "A+B Problem",
                "difficulty": 1,
                "type": "P",
                "submitted": False,
                "accepted": False,
                "tags": [],
                "totalSubmit": 10,
                "totalAccepted": 5,
                "flag": 0,
                "fullScore": 100,
                "content": None,
                "samples": [],
                "provider": None,
                "attachments": [],
                "limits": {"time": [], "memory": []},
                "showScore": True,
                "score": 100,
                "stdCode": "",
                "vjudge": None,
                "acceptLanguages": [],
            },
        }

        with patch.object(self.api, "_send_request", return_value=payload) as send:
            self.api.get_problem("P1000", contest_id=123)

        call_args = send.call_args
        assert call_args is not None
        params = call_args.kwargs["params"]
        self.assertEqual(params.to_json(), {"contestId": 123})

    def test_update_problem_settings_uses_current_payload_shape(self):
        settings = ProblemSettings.get_default()
        settings.comment = "legacy comment"
        settings.providerID = 42

        with patch.object(self.api, "_send_request", return_value={"pid": "P1000"}) as send:
            result = self.api.update_problem_settings("P1000", settings)

        self.assertEqual(result.pid, "P1000")
        call_args = send.call_args
        assert call_args is not None
        payload = call_args.kwargs["data"]
        self.assertEqual(set(payload), {"settings"})
        self.assertNotIn("comment", payload["settings"])
        self.assertNotIn("providerID", payload["settings"])

    def test_transfer_problem_uses_shared_payload_builder(self):
        with patch.object(self.api, "_send_request", return_value={"pid": "P1000"}) as send:
            result = self.api.transfer_problem("P1000", target=42, is_clone=True)

        call_args = send.call_args
        assert call_args is not None
        self.assertEqual(result.pid, "P1000")
        self.assertEqual(
            call_args.kwargs["data"],
            {"type": "T", "teamID": 42, "operation": "clone"},
        )

    def test_explicit_extra_api_uses_route_table(self):
        with patch.object(self.api, "_send_request", return_value={"ok": True}) as send:
            result = self.api.vote_article("a1", 1)

        call_args = send.call_args
        assert call_args is not None
        self.assertEqual(result.data, {"ok": True})
        self.assertEqual(call_args.kwargs["endpoint"], "api/article/vote/a1")
        self.assertEqual(call_args.kwargs["method"], "POST")
        self.assertEqual(call_args.kwargs["params"].to_json(), {"vote": 1})

    def test_explicit_extra_api_supports_form_and_raw_response_type(self):
        with patch.object(self.api, "_send_request", return_value="ok") as send:
            result = self.api.update_blog_admin_list(form={"method": "update"}, page_type="list")

        call_args = send.call_args
        assert call_args is not None
        self.assertEqual(result, "ok")
        self.assertEqual(call_args.kwargs["form"], {"method": "update"})
        self.assertEqual(call_args.kwargs["response_type"], "text")

    def test_static_api_exposes_cache_pools(self):
        api = staticLuoguAPI()

        self.assertTrue(hasattr(api, "problem_cache_pool"))
        self.assertTrue(hasattr(api, "problem_setting_cache"))


if __name__ == "__main__":
    unittest.main()
