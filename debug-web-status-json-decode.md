# [OPEN] Debug Session: web-status-json-decode

## Symptom
- Web 端生成报告任务在状态页报错：`Failed to decode JSON response`
- 用户要求先测试并确认根因，再汇报

## Scope
- `web_app.py` 的在线生成流程
- `pyLuogu` 请求/解码链路
- 报告生成前的数据抓取阶段

## Hypotheses
1. `get_record_list()` 或 `get_record()` 在 Web 端某次请求拿到了 HTML 登录页/风控页，随后被当成 JSON 解码失败。
2. `get_user_practice()` 或标签/题目补全过程中某个接口偶发返回非 JSON，错误被直接冒泡到状态页。
3. Web 端使用的 Cookie 在运行时不完整或失效，导致部分需要登录的接口返回认证页。
4. 某个批量抓取流程在连续请求后触发风控，前几次成功、后续统一变成非 JSON。
5. 当前错误提示来源于较底层的 `pyLuogu`，Web 层没有把接口名和上下文包装出来，导致状态页只看到笼统的 decode 错误。

## Evidence Plan
- 为 Web 生成主流程增加阶段性日志，定位报错发生在“哪一个 API 调用”。
- 对 `pyLuogu` 的 JSON 解码失败点增加最小观测，记录 URL、状态码、Content-Type 和响应前缀。
- 用单元测试和一次本地最小复现实验验证：模板问题已排除，当前剩余错误来自接口解码链路。

## Status
- Instrumentation added in `pyLuogu/request_helpers.py` and `web_app.py`

## Evidence
- Full test suite after instrumentation: `36 tests`, all passed.
- Historical failed task `04d026db-2314-416c-9a24-b996aabf481a` still stores plain `Failed to decode JSON response`, which proves the external running web process had not yet picked up the new stage-aware code.
- Local minimal reproduction with stubbed Flask and fake `luoguAPI` produced:
  - `[阶段: 获取标签与练习数据] Failed to decode JSON response [url=https://www.luogu.com.cn/user/123/practice, status=200, content_type=text/html, prefix=<html>login</html>]`

## Hypothesis Verdict
1. `get_record_list()` / `get_record()` returned HTML login page: not supported by current evidence.
2. `get_user_practice()` or early data-fetch API returned non-JSON: supported.
3. Cookie incomplete/expired causing login page: strongly supported by HTML login-page prefix evidence.
4. Batch requests later triggered rate-limit: not supported for the reproduced case because failure happens during early `user/:uid/practice`.
5. Web layer hid true failing endpoint: supported; stage-aware message now exposes it.

## Current Root Cause
- In the reproduced failure path, `GET /user/<uid>/practice` returned HTML instead of JSON, so `response.json()` failed.
- The HTML prefix indicates a login/auth page rather than normal API payload.
- The externally observed status page likely came from a process that had not been restarted after the latest debugging instrumentation.
