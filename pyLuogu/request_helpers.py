import re
from dataclasses import dataclass
from typing import Any

import httpx

from .errors import (
    AuthenticationError,
    ForbiddenError,
    NeedCaptcha,
    NotFoundError,
    RateLimitError,
    RequestError,
    ServerError,
)


USER_AGENT = "luogu_bot"
CONTENT_ONLY_HEADERS = {
    "User-Agent": USER_AGENT,
    "x-luogu-type": "content-only",
    "x-lentille-request": "content-only",
}


@dataclass
class RetryRequest(Exception):
    delay: float = 0
    refresh_csrf: bool = False


def normalize_endpoint(endpoint: str) -> str:
    return endpoint.lstrip("/")


def build_url(base_url: str, endpoint: str) -> str:
    return f"{base_url.rstrip('/')}/{normalize_endpoint(endpoint)}"


def build_headers(
        method: str,
        csrf_token: str | None = None,
        json_body: bool = True,
) -> dict[str, str]:
    headers = dict(CONTENT_ONLY_HEADERS)
    if method.upper() != "GET":
        headers["referer"] = "https://www.luogu.com.cn/"
        if json_body:
            headers["Content-Type"] = "application/json"
        if csrf_token:
            headers["x-csrf-token"] = csrf_token
    return headers


def csrf_fetch_headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT}


def captcha_headers(csrf_token: str | None) -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT}
    if csrf_token:
        headers["x-csrf-token"] = csrf_token
    return headers


def extract_c3vk(text: str) -> str | None:
    result = re.search(r"C3VK=([^;]+);", text)
    return None if result is None else result.group(1)


def decode_json_response(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        raise RequestError("Failed to decode JSON response") from None


def unwrap_luogu_data(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    if payload.get("currentData") is not None:
        payload = payload["currentData"]
    if isinstance(payload, dict) and payload.get("data") is not None:
        payload = payload["data"]
    return payload


def _error_message(payload: dict[str, Any]) -> str | None:
    current_data = payload.get("currentData")
    if isinstance(current_data, dict):
        return payload.get("errorMessage") or current_data.get("errorMessage")
    return payload.get("errorMessage")


def handle_luogu_json_payload(payload: Any, endpoint: str) -> Any:
    if not isinstance(payload, dict):
        return payload

    if payload.get("currentTemplate") == "AuthLogin":
        raise AuthenticationError("Need Login")

    code = payload.get("code")
    if code == 403:
        message = _error_message(payload)
        if message == "user.not_self":
            raise AuthenticationError("not yourself")
        if message in {"请求频繁，请稍候再试", "提交过于频繁，请过3分钟再尝试"}:
            raise RetryRequest(delay=180 if message.startswith("提交") else 5)
        if message == "验证码错误":
            raise NeedCaptcha("Need captcha")
        if message:
            raise ForbiddenError(message)
        raise RetryRequest(refresh_csrf=True)

    if code in {404, 418}:
        raise NotFoundError(f"Resource not found {endpoint}")

    return unwrap_luogu_data(payload)


def handle_http_status_error(
        response: httpx.Response,
        exc: httpx.HTTPStatusError,
) -> None:
    status_code = response.status_code

    if status_code == 401:
        raise AuthenticationError("Authentication failed") from exc
    if status_code == 403:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        message = payload.get("errorMessage") if isinstance(payload, dict) else None
        if message is None:
            raise ForbiddenError(f"Forbidden: {exc}") from exc
        if message == "提交过于频繁，请过3分钟再尝试":
            raise RetryRequest(delay=180)
        if message == "请求频繁，请稍候再试":
            raise RetryRequest(delay=5)
        if message == "验证码错误":
            raise NeedCaptcha("Need captcha") from exc
        if message == "user.not_self":
            raise AuthenticationError("not yourself") from exc
        raise RetryRequest(refresh_csrf=True)
    if status_code == 404:
        raise NotFoundError("Resource not found") from exc
    if status_code == 429:
        raise RateLimitError("Rate limit exceeded") from exc
    if 500 <= status_code < 600:
        raise ServerError("Server error") from exc

    raise RequestError(f"HTTP error: {exc}", status_code=status_code) from exc
