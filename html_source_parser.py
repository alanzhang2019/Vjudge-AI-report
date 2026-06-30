"""html_source_parser.py - v3.11.0

解析洛谷【个人练习】页面 HTML 源码 (用户从浏览器 Ctrl+U 复制粘贴),
复用 algobeatcontest.github.io/practice 的清洗+提取思路, 转化成
与 zip_bundle_loader 同构的 export_data 字典。

输入: 完整的 HTML 源码字符串 (含 <script>__NEXT_DATA__</script> 等)
输出: {
  schema_version: 1,
  source: "html_source",
  user: {"uid": int|None, "name": str|None},
  passed_items: [...],
  failed_items: [...],
  records: [...],
  ...
}
"""

from __future__ import annotations

import json
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

# ---------- 关键正则 (来自 algobeatcontest.github.io/practice) ----------

# 匹配 "passed":[...], "submitted" 的非贪婪抓取
# 容忍嵌套: 支持 [a, [b, c], d] 这种 1 层嵌套 (洛谷的 practiceData.passed 偶尔会嵌)
_RE_PASSED = re.compile(
    r'"passed"\s*:\s*(\[(?:[^\[\]]|\[[^\[\]]*\])*\])\s*,\s*"submitted"',
    re.S,
)
# 匹配 "submitted":[...], 后面跟随 "}" 或 "," (避免吃掉下一个字段)
_RE_SUBMITTED = re.compile(
    r'"submitted"\s*:\s*(\[(?:[^\[\]]|\[[^\[\]]*\])*\])\s*[,}]',
    re.S,
)
# 提取 uid (从 URL / __NEXT_DATA__)
_RE_UID = re.compile(r'/user/(\d+)')
# 提取用户名 (洛谷 <title>...</title> 通常是 "用户名 的个人中心 - 洛谷")
_RE_TITLE = re.compile(r'<title>\s*([^<\s]+)(?:\s+的个人[^\-]*)?\s*-\s*洛谷\s*</title>')

# __NEXT_DATA__ 块 (整个 JSON)
_RE_NEXT_DATA = re.compile(
    r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.+?)</script>',
    re.S,
)


# ---------- 清洗 (跟 algobeatcontest 一致, 解决 LaTeX / 真换行问题) ----------

def _safe_parse_array(raw: str) -> List[Any]:
    """
    清洗并解析一段 JSON 数组字符串。

    洛谷 __NEXT_DATA__ 里的 "passed":[...] 经常有这些问题:
      1) 含 \\n (转义换行)
      2) 含 \\n 真换行 (在用户复制粘贴时可能混入)
      3) 含 LaTeX $$...$$ (有大量花括号, 会让 JSON.parse 爆炸)
      4) 字段值含 < > (HTML 实体, 会破坏 JSON 字符串)
    algobeatcontest 的解法是 4 行 replace + JSON.parse, 我们照搬
    (注意: algobeatcontest 把 < 替换成 " 是为了前端 XSS 防御, 我们后端
     也照做; 但要小心, 真换行 \\n 必须先去掉, 否则 LaTeX 块里
     的换行会让 json.loads 失败)
    """
    s = raw
    s = s.replace("\\\n", "")         # 去 \\n
    s = re.sub(r"\n", "", s)          # 去真换行
    # LaTeX 块 -> 占位 (匹配 "$$...$$" 整体, 保留外面的引号)
    s = re.sub(r'"\$\$.+?\$\$"', '"LaTeX"', s)
    s = s.replace("<", '"').replace(">", '"')  # XSS 防御 (跟 algobeatcontest 一致)
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析失败: {e}; head={s[:200]!r}") from e


# ---------- 提取引擎 ----------

def _extract_passed_array(html: str) -> Optional[List[Any]]:
    m = _RE_PASSED.search(html)
    if not m:
        return None
    try:
        arr = _safe_parse_array(m.group(1))
    except ValueError:
        return None
    return arr if isinstance(arr, list) else None


def _extract_submitted_array(html: str) -> Optional[List[Any]]:
    m = _RE_SUBMITTED.search(html)
    if not m:
        return None
    try:
        arr = _safe_parse_array(m.group(1))
    except ValueError:
        return None
    return arr if isinstance(arr, list) else None


def _extract_user(html: str) -> Tuple[Optional[int], Optional[str]]:
    uid = None
    m = _RE_UID.search(html)
    if m:
        try:
            uid = int(m.group(1))
        except ValueError:
            uid = None
    name = None
    m = _RE_TITLE.search(html)
    if m:
        name = m.group(1).strip() or None
    return uid, name


# ---------- 字段归一化 ----------

def _coerce_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None


def _normalize_item(it: Any) -> Optional[Dict[str, Any]]:
    """
    把洛谷 passed/submitted 数组里的每条数据归一化成与 ZIP 模式同构的 item:

        {
            "problem": {                  # ← luogu_evaluator.generate_ai_report 期望的嵌套结构
                "pid": ...,
                "title": ...,
                "difficulty": ...,
                "difficulty_name": ...,
                "tags": [...],
            },
            "record": None,               # ← 源码粘贴模式没有源码, 显式置 None
            "status": "passed" | "failed",
            "submitTime": "...",
        }

    同时把扁平字段 (pid / title / ...) 保留在顶层,
    兼容下游部分对扁平字段的访问 (例如 _prefill_cached_records)。
    """
    if not isinstance(it, dict):
        return None
    pid = str(it.get("pid") or "").strip()
    if not pid:
        return None
    difficulty = _coerce_int(it.get("difficulty"))
    # 计算 difficulty_name (若缓存可用)
    difficulty_name: Optional[str] = None
    try:
        # 延迟导入, 避免强依赖
        from problemset_index import get_difficulty_name
        difficulty_name = get_difficulty_name(difficulty)
    except Exception:  # noqa: BLE001
        difficulty_name = None
    tags_raw = it.get("tags") or []
    if not isinstance(tags_raw, list):
        tags_raw = []
    tags: List[int] = []
    for t in tags_raw:
        ti = _coerce_int(t)
        if ti is not None:
            tags.append(ti)
    title = (it.get("title") or "").strip()
    status_raw = it.get("status")
    if isinstance(status_raw, int):
        # 洛谷 status: 12=AC, others=...
        status = "passed" if status_raw == 12 else "failed"
    elif isinstance(status_raw, str):
        status = status_raw
    else:
        status = "unknown"
    submit_time = it.get("submitTime") or it.get("submitTimeMs") or it.get("time")
    submit_time_str: Optional[str] = None
    if isinstance(submit_time, (int, float)):
        # 洛谷 submitTime 是 ms
        if submit_time > 10_000_000_000:  # ms
            submit_time_str = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(submit_time / 1000)
            )
        elif submit_time > 10_000_000:  # s
            submit_time_str = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(submit_time)
            )
    elif isinstance(submit_time, str):
        submit_time_str = submit_time
    problem_payload: Dict[str, Any] = {
        "pid": pid,
        "title": title,
        "difficulty": difficulty,
        "difficulty_name": difficulty_name,
        "tags": tags,
    }
    return {
        # 嵌套: 与 ZIP 模式 luogu_evaluator.generate_ai_report 期望一致
        "problem": problem_payload,
        # 源码粘贴模式没有真实提交记录源码, 显式 None
        # (luogu_evaluator 会用 item.get("record") 兜底跳过代码样本)
        "record": None,
        # 顶层扁平字段 (兼容部分下游对扁平访问的代码, 例如
        # _prefill_cached_records / failed_items 错题本聚合)
        "pid": pid,
        "title": title,
        "difficulty": difficulty,
        "difficulty_name": difficulty_name,
        "tags": tags,
        "status": status,
        "submitTime": submit_time_str,
    }


# ---------- 主入口 ----------

class HtmlSourceParseError(Exception):
    pass


def parse_html_source(
    html: str,
    *,
    uid_hint: Optional[int] = None,
    name_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    解析洛谷个人练习页 HTML 源码 → export_data dict (与 zip_bundle_loader 同构)。

    Args:
        html: 用户粘贴的整段 HTML 源码
        uid_hint: 用户手动填的 UID (URL 提取失败时使用)
        name_hint: 用户手动填的姓名 (title 提取失败时使用)

    Returns:
        export_data 字典, 至少含 schema_version / source / passed_items / failed_items / records

    Raises:
        HtmlSourceParseError: 未找到 passed 数组
    """
    if not isinstance(html, str) or not html.strip():
        raise HtmlSourceParseError("HTML 源码为空")

    if len(html) < 80:
        raise HtmlSourceParseError(
            f"HTML 源码过短 ({len(html)} 字符), 请粘贴完整的页面源代码"
        )

    # 1) 提取 passed 数组
    passed_raw = _extract_passed_array(html)
    if passed_raw is None:
        raise HtmlSourceParseError(
            "未找到 \"passed\" 数据, 请确认粘贴的是【洛谷个人练习】页面 "
            "(https://www.luogu.com.cn/user/<UID>/practice) 的完整源码"
        )

    # 2) 提取 submitted 数组 (可选, 部分旧版页面可能没有)
    submitted_raw = _extract_submitted_array(html) or []

    # 3) 提取 uid / name
    uid, name = _extract_user(html)
    if uid is None:
        uid = _coerce_int(uid_hint)
    if not name:
        name = (name_hint or "").strip() or None

    # 4) 归一化
    passed_items: List[Dict[str, Any]] = []
    for it in passed_raw:
        norm = _normalize_item(it)
        if norm:
            passed_items.append(norm)

    failed_items: List[Dict[str, Any]] = []
    for it in submitted_raw:
        norm = _normalize_item(it)
        if norm and norm.get("status") == "failed":
            failed_items.append(norm)

    # 5) 构造 records: 合并 passed + failed, 含 status
    records: List[Dict[str, Any]] = list(passed_items) + list(failed_items)

    # 6) 导出
    export_data: Dict[str, Any] = {
        "schema_version": 1,
        "source": "html_source",
        "exportedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "export_id": str(uuid.uuid4()),
        "user": {
            "uid": uid,
            "name": name,
        },
        "passed_items": passed_items,
        "failed_items": failed_items,
        "records": records,
        # 兼容 AI 报告生成需要的元字段
        "stats": {
            "passed": len(passed_items),
            "failed": len(failed_items),
            "total": len(records),
        },
    }
    return export_data


# ---------- CLI 自检 ----------

if __name__ == "__main__":
    # 一个最简单的 fixture: 模拟用户粘贴的源码片段
    sample = """
<!DOCTYPE html>
<html>
<head>
  <title>张三 的个人中心 - 洛谷</title>
  <script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{"user":{"uid":123456,"name":"张三"},"practiceData":{"passed":[{"pid":"P1000","title":"超级玛丽游戏","difficulty":1,"tags":[1,2],"status":12},{"pid":"P1001","title":"A+B Problem","difficulty":1,"tags":[1],"status":12}],"submitted":[{"pid":"P1002","title":"写文件","difficulty":2,"tags":[3],"status":4},{"pid":"P1003","title":"数组","difficulty":2,"tags":[3],"status":4}]}}}}
  </script>
</head>
<body><a href="/user/123456">主页</a></body>
</html>
"""
    try:
        out = parse_html_source(sample)
        print("=== PASSED ===")
        for p in out["passed_items"]:
            print(f"  {p['pid']:8s} | d={p['difficulty']} | {p['title']}")
        print("=== FAILED ===")
        for p in out["failed_items"]:
            print(f"  {p['pid']:8s} | d={p['difficulty']} | {p['title']}")
        print()
        print(json.dumps(out["stats"], ensure_ascii=False, indent=2))
        print()
        print(f"user: {out['user']}")
    except HtmlSourceParseError as e:
        print(f"FAIL: {e}")

    # 极端 case: 整页就一个 <script> (模拟用户只复制了 <script>...</script> 的内容)
    sample2 = '<script>{"props":{"pageProps":{"passed":[{"pid":"P1000","title":"X","difficulty":1,"status":12}],"submitted":[]}}}</script>'
    print()
    print("=== sample2 (极简 script) ===")
    out2 = parse_html_source(sample2, uid_hint=99, name_hint="匿名")
    print(json.dumps(out2["user"], ensure_ascii=False))
    print(f"stats: {out2['stats']}")

    # 错误 case: 完全没有 passed
    sample3 = '<html><body>foo bar baz lorem ipsum dolor sit amet</body></html>' * 5
    print()
    print("=== sample3 (无 passed) ===")
    try:
        parse_html_source(sample3)
        print("  [ERROR] should have raised")
    except HtmlSourceParseError as e:
        print(f"  [OK raised] {e}")

    # 边界: LaTeX 块
    sample4 = '<script>{"passed":[{"pid":"P1000","title":"X","difficulty":1,"status":12,"hint":"$$a^2+b^2=c^2$$"}],"submitted":[]}</script>'
    print()
    print("=== sample4 (含 LaTeX) ===")
    out4 = parse_html_source(sample4, uid_hint=1)
    if out4["passed_items"]:
        print(f"  P1000 hint = {out4['passed_items'][0].get('tags')!r}")
    print(f"  stats: {out4['stats']}")
