import unittest
from typing import Literal

from pyLuogu.bits.ultility import JsonSerializable
from pyLuogu.types import (
    Attachment,
    ContestSummary,
    ContestListRequestParams,
    LuoguCookies,
    ProblemSetSummary,
    ProblemListRequestParams,
    ProblemRequestParams,
    ProblemSettings,
    TeamProblemListRequestParams,
    TestCaseSettings,
)


class NestedForParse(JsonSerializable):
    __type_dict__ = {
        "value": int | str,
    }
    value: int | str


class UnionParseTarget(JsonSerializable):
    __type_dict__ = {
        "optional": int | None,
        "union": int | str,
        "items": list[int | str],
        "mapping": dict[str, int | str],
        "nested": NestedForParse | str,
        "mode": Literal["a", "b"],
    }
    optional: int | None
    union: int | str
    items: list[int | str]
    mapping: dict[str, int | str]
    nested: NestedForParse | str
    mode: Literal["a", "b"]


class TestLuoguTypes(unittest.TestCase):
    def test_luogu_cookies_round_trip(self):
        cookies = LuoguCookies(json={"__client_id": "client", "_uid": "1_user"})

        self.assertEqual(
            cookies.to_json(),
            {"__client_id": "client", "_uid": "1_user"},
        )

    def test_request_params_skip_none_values(self):
        params = ProblemListRequestParams(
            json={"page": 1, "keyword": None, "difficulty": 3, "order": "asc"}
        )

        self.assertEqual(params.to_json(), {"page": 1, "difficulty": 3, "order": "asc"})

    def test_current_request_param_names(self):
        problem = ProblemRequestParams(json={"contestId": 7})
        contest = ContestListRequestParams(json={"name": "abc", "method": 1, "public": 2})
        team_problem = TeamProblemListRequestParams(
            json={"keyword": "dp", "orderBy": "pid", "order": "desc"}
        )

        self.assertEqual(problem.to_json(), {"contestId": 7})
        self.assertEqual(contest.to_json(), {"name": "abc", "method": 1, "public": 2})
        self.assertEqual(
            team_problem.to_json(),
            {"keyword": "dp", "orderBy": "pid", "order": "desc"},
        )

    def test_json_serializable_parses_optional_and_sum_types(self):
        parsed = UnionParseTarget(
            json={
                "optional": None,
                "union": "x",
                "items": [1, "two"],
                "mapping": {"a": 1, "b": "two"},
                "nested": {"value": "inner"},
                "mode": "a",
            }
        )

        self.assertIsNone(parsed.optional)
        self.assertEqual(parsed.union, "x")
        self.assertEqual(parsed.items, [1, "two"])
        self.assertEqual(parsed.mapping, {"a": 1, "b": "two"})
        self.assertIsInstance(parsed.nested, NestedForParse)
        assert isinstance(parsed.nested, NestedForParse)
        self.assertEqual(parsed.nested.value, "inner")
        self.assertEqual(parsed.mode, "a")

    def test_json_serializable_rejects_invalid_sum_type(self):
        with self.assertRaises(TypeError):
            UnionParseTarget(json={"union": []})

        with self.assertRaises(TypeError):
            UnionParseTarget(json={"mode": "c"})

    def test_problem_settings_tag_helpers(self):
        settings = ProblemSettings.get_default()

        settings.append_tags([1, 2, 2])
        settings.remove_tags(1)

        self.assertEqual(settings.tags, [2])
        self.assertEqual(settings.to_json()["difficulty"], 0)

    def test_current_response_field_aliases_are_preserved(self):
        attachment = Attachment(
            json={
                "id": "a",
                "filename": "data.zip",
                "size": 10,
                "uploadTime": 1,
                "downloadLink": "https://example.test/data.zip",
            }
        )
        problem_set = ProblemSetSummary(
            json={
                "id": 1,
                "name": "training",
                "type": 1,
                "provider": {"uid": 1, "name": "u"},
                "createTime": 1,
                "deadline": None,
                "problemCount": 1,
                "marked": False,
                "markCount": 0,
            }
        )
        contest = ContestSummary(
            json={
                "id": 1,
                "name": "contest",
                "startTime": 1,
                "endTime": 2,
                "method": 2,
                "visibility": 1,
                "invitationCodeType": 0,
                "rated": 1,
                "host": {"uid": 1, "name": "u"},
                "problemCount": 3,
                "squad": False,
            }
        )

        self.assertEqual(attachment.filename, "data.zip")
        self.assertEqual(attachment.fileName, "data.zip")
        self.assertEqual(problem_set.name, "training")
        self.assertEqual(problem_set.title, "training")
        self.assertEqual(contest.method, 2)
        self.assertEqual(contest.ruleType, 2)
        self.assertEqual(contest.visibility, 1)
        self.assertEqual(contest.visibilityType, 1)

    def test_test_case_settings_parses_nested_types(self):
        settings = TestCaseSettings(
            json={
                "cases": [
                    {
                        "upid": 1,
                        "inputFileName": "1.in",
                        "outputFileName": "1.out",
                        "timeLimit": 1000,
                        "memoryLimit": 256,
                        "fullScore": 100,
                        "isPretest": False,
                        "subtaskId": 0,
                    }
                ],
                "subtaskScoringStrategies": {
                    "0": {"type": 0, "script": ""},
                },
                "scoringStrategy": {"type": 0, "script": ""},
                "showSubtask": True,
            }
        )

        self.assertEqual(settings.cases[0].inputFileName, "1.in")
        self.assertEqual(settings.subtaskScoringStrategies["0"].type, 0)
        self.assertTrue(settings.showSubtask)


if __name__ == "__main__":
    unittest.main()
