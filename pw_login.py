#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v3.9.52 · Playwright 自动登录 + 自动 OCR 验证码 + 提取三参数
================================================================
设计要点:
  1) 每个登录请求 → 独立 LoginSession(独立浏览器上下文)
  2) 后端用 ddddocr 自动识别图形验证码, 失败自动重试
  3) 如果账号开了 2FA → 把浏览器 page 引用挂到 session, 等用户输 6 位码
  4) 登录成功 → 从 cookies 拿 __client_id / _uid / C3VK 三参数
  5) 会话有 TTL, 超时自动关浏览器

调用方式 (web_app.py 用):
    mgr = LoginSessionManager()
    sess = mgr.create(username, password)
    sess.start()                # 异步, 内部跑 Playwright
    while sess.running: time.sleep(0.2)
    if sess.need_2fa:
        # 前端弹 2FA 输入框
        sess.submit_2fa("123456")
    else:
        # sess.cookies 已经有值, 可直接用
================================================================
"""
from __future__ import annotations

import logging
import os
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# v3.9.52 debug · 输出到 stdout (docker logs 能看到)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] pw_login: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("pw_login")

# 默认 ddddocr 只识别 1 次, 失败就让用户手输
MAX_CAPTCHA_AUTO = int(os.environ.get("PWD_LOGIN_MAX_CAPTCHA", "6"))
# 登录会话 TTL (秒)
SESSION_TTL = int(os.environ.get("PWD_LOGIN_TTL", "300"))


# ----------------------------------------------------------------------
#  登录会话 (每个账号一个, 含独立 browser / context / page)
# ----------------------------------------------------------------------


@dataclass
class LoginSession:
    """单个登录请求的浏览器会话。线程安全。"""

    session_id: str
    username: str
    password: str
    state: str = "idle"            # idle | starting | captcha | need_2fa | done | failed
    message: str = ""
    error: str = ""
    cookies: Dict[str, str] = field(default_factory=dict)
    c3vk_source: str = ""
    captcha_attempts: int = 0
    created_at: float = field(default_factory=time.time)

    # 内部: Playwright 对象 (不序列化, 不进 JSON)
    _pw: Any = field(default=None, repr=False)
    _browser: Any = field(default=None, repr=False)
    _context: Any = field(default=None, repr=False)
    _page: Any = field(default=None, repr=False)
    _thread: Optional[threading.Thread] = field(default=None, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # ---------- 状态查询 ----------

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "state": self.state,
            "message": self.message,
            "error": self.error,
            "cookies": self.cookies,
            "captcha_attempts": self.captcha_attempts,
            "need_2fa": self.state == "need_2fa",
            "expired": self.is_expired(),
        }

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > SESSION_TTL

    # ---------- 启动后台登录线程 ----------

    def start(self) -> None:
        self.state = "starting"
        self.message = "正在启动浏览器…"
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def join(self, timeout: float = 60.0) -> None:
        if self._thread:
            self._thread.join(timeout=timeout)

    # ---------- 提交 2FA ----------

    def submit_2fa(self, code: str) -> bool:
        """2FA 阶段: 在已打开的 page 上填 6 位验证码并提交"""
        with self._lock:
            if self.state != "need_2fa":
                return False
            code = (code or "").strip()
            if not code or len(code) != 6 or not code.isdigit():
                self.error = "2FA 验证码必须是 6 位数字"
                return False
        # 后台跑
        t = threading.Thread(target=self._submit_2fa_run, args=(code,), daemon=True)
        t.start()
        return True

    # ---------- 关闭 ----------

    def close(self) -> None:
        try:
            if self._context is not None:
                self._context.close()
        except Exception:
            pass
        try:
            if self._browser is not None:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._pw is not None:
                self._pw.stop()
        except Exception:
            pass

    # ==================================================================
    #  后台线程: Playwright 跑登录
    # ==================================================================

    def _run(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            self._fail(f"Playwright 未安装: {e}")
            return

        try:
            with sync_playwright() as pw:
                self._pw = pw
                # v3.9.52 · 浏览器启动策略:
                #   1) 优先尝试 channel="chrome" (真 Google Chrome, 洛谷不大会认为是 bot)
                #   2) 退到 playwright 自带的 chromium
                #   3) 启动参数加上 user-agent 和 隐藏 webdriver 标识
                launch_kwargs = dict(
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                    chromium_sandbox=False,
                )
                browser = None
                # 优先级 1: 系统 Chrome
                if os.environ.get("PWD_LOGIN_USE_CHROME", "1") == "1":
                    for ch in ("chrome", "chromium"):
                        try:
                            browser = pw.chromium.launch(channel=ch, **launch_kwargs)
                            logger.info("pw_login: 用了 channel=%s", ch)
                            break
                        except Exception as e:
                            logger.info("pw_login: channel=%s 不可用: %s", ch, str(e)[:100])
                # 优先级 2: Playwright 自带 chromium (headless new 模式)
                if browser is None:
                    headless_env = os.environ.get("PWD_LOGIN_HEADLESS", "new")
                    browser = pw.chromium.launch(
                        headless=(headless_env not in (False, "no", "0")),
                        **launch_kwargs,
                    )
                    logger.info("pw_login: 用了 Playwright 自带 chromium, headless=%s",
                                headless_env)
                self._browser = browser
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 860},
                    locale="zh-CN",
                )
                self._context = context
                page = context.new_page()
                self._page = page

                # --- Step 1: 进登录页 + 输用户名 ---
                self._set("正在打开洛谷登录页…")
                page.goto("https://www.luogu.com.cn/auth/login",
                          wait_until="domcontentloaded", timeout=30000)
                page.locator("input[autocomplete='username webauthn']").fill(self.username)
                time.sleep(0.4)
                page.locator("button.solid.lform-size-middle")\
                    .filter(has_text="下一步").first.click()
                time.sleep(1.2)

                # --- Step 2: 等密码框 + 验证码出现 ---
                try:
                    page.wait_for_selector("input[type='password']", timeout=10000)
                    page.wait_for_selector("img[src*='/lg4/captcha']", timeout=10000)
                except Exception as e:
                    self._fail(f"未进入 step-2 (密码 + 验证码): {e}")
                    return
                time.sleep(0.5)

                # --- Step 3: OCR 验证码 + 提交 (重试 MAX_CAPTCHA_AUTO 次) ---
                ok = self._try_login_with_captcha(page, max_attempts=MAX_CAPTCHA_AUTO)
                if not ok:
                    return  # state 已经被设置

                # --- Step 4: 检测结果 ---
                #   成功: URL 离开 /auth/login
                #   2FA:  出现两步验证输入框
                #   错:   密码错 / 账号异常
                time.sleep(2)
                html = page.content()
                if self._looks_like_2fa(html):
                    self._set_need_2fa(page)
                    return

                if self._looks_like_login_error(html):
                    err = self._extract_swal_text(html) or "登录失败"
                    self._fail(err)
                    return

                if "/auth/login" in page.url:
                    self._fail("登录未跳转, 请检查账号状态")
                    return

                # --- Step 5: 触发 C3VK 发放 ---
                self._set("登录成功, 正在提取 Cookies…")
                for u in [
                    "https://www.luogu.com.cn/",
                    "https://www.luogu.com.cn/user/settings",
                    "https://www.luogu.com.cn/record/list",
                ]:
                    try:
                        page.goto(u, wait_until="domcontentloaded", timeout=15000)
                        time.sleep(1.0)
                    except Exception:
                        pass
                time.sleep(1.0)

                # v3.9.52 debug · dump 当前页 HTML, 看 C3VK 在哪
                try:
                    html_dump = page.content()
                    with open("/tmp/luogu_after_login.html", "w", encoding="utf-8") as f:
                        f.write(html_dump)
                    logger.info("pw_login: dumped /tmp/luogu_after_login.html (%d bytes)", len(html_dump))
                    # 找 C3VK 出现的所有位置
                    import re
                    for m in re.finditer(r"C3VK[^A-Za-z0-9_]{0,3}([A-Za-z0-9._+/=%-]{2,200})", html_dump):
                        logger.info("pw_login HTML C3VK match: %s...", m.group(1)[:40])
                except Exception as e:
                    logger.warning("pw_login dump html failed: %s", e)

                # --- Step 6: 提取三参数 ---
                self._extract_and_done(page)

        except Exception as e:
            logger.exception("pw_login._run failed")
            self._fail(f"登录流程异常: {str(e)[:200]}")
        finally:
            # 登录完 (成功 / 失败) 都关浏览器, need_2fa 时不关
            if self.state in ("done", "failed"):
                self.close()

    # ---------- 2FA 提交线程 ----------

    def _submit_2fa_run(self, code: str) -> None:
        page = self._page
        if page is None:
            self._fail("2FA 会话已失效, 请重试登录")
            return
        try:
            # 找 6 位验证码输入框
            totp_input = page.locator(
                "input[inputmode='numeric'], input[autocomplete='one-time-code'], "
                "input[maxlength='6']"
            ).first
            totp_input.fill(code)
            time.sleep(0.3)
            # 找提交按钮 (一般在 2FA 弹窗 / 同一个 form)
            for txt in ("确定", "提交", "登录", "验证"):
                btn = page.get_by_role("button", name=txt)
                if btn.count() > 0:
                    try:
                        btn.first.click(timeout=2000)
                        break
                    except Exception:
                        continue
            time.sleep(3)

            html = page.content()
            if self._looks_like_2fa(html):
                # 还是 2FA 页面 → 验证码错
                self._fail("2FA 验证码错误或已过期, 请重新登录")
                return

            if "/auth/login" in page.url:
                err = self._extract_swal_text(html) or "2FA 提交后未跳转"
                self._fail(err)
                return

            # 跳转了 → 触发 C3VK + 提取
            self._set("2FA 验证成功, 提取 Cookies…")
            for u in [
                "https://www.luogu.com.cn/",
                "https://www.luogu.com.cn/user/settings",
                "https://www.luogu.com.cn/record/list",
            ]:
                try:
                    page.goto(u, wait_until="domcontentloaded", timeout=15000)
                    time.sleep(1.0)
                except Exception:
                    pass
            self._extract_and_done(page)
        except Exception as e:
            self._fail(f"2FA 提交流程异常: {str(e)[:200]}")
        finally:
            if self.state in ("done", "failed"):
                self.close()

    # ==================================================================
    #  内部 helpers
    # ==================================================================

    def _try_login_with_captcha(self, page, max_attempts: int) -> bool:
        try:
            ocr = _get_ocr()
        except Exception as e:
            self._fail(f"ddddocr 未安装: {e}")
            return False

        for attempt in range(1, max_attempts + 1):
            self.captcha_attempts = attempt
            self._set(f"自动识别图形验证码… (第 {attempt}/{max_attempts} 次)")

            # 截验证码
            captcha_img = page.locator("img[src*='/lg4/captcha']").first
            try:
                png = captcha_img.screenshot(type="png")
            except Exception as e:
                self._fail(f"截验证码失败: {e}")
                return False
            code = ocr.classification(png)
            logger.info("captcha attempt=%d ocr=%r", attempt, code)
            if not code or len(code) < 4:
                continue

            # 输密码 + 验证码 + 点登录
            page.locator("input[type='password']").fill(self.password)
            page.locator("input[placeholder='请输入图形验证码']").fill(code)
            time.sleep(0.2)
            page.locator("button.solid.lform-size-middle")\
                .filter(has_text="使用账户密码登录").first.click()
            time.sleep(2.5)

            html = page.content()
            # 验证码错 → 换一张
            if "图形验证码错误" in html:
                # 关掉 swal 弹窗 + 刷一张新图
                if page.locator(".swal2-confirm").count() > 0:
                    try:
                        page.locator(".swal2-confirm").first.click(timeout=2000)
                        time.sleep(0.4)
                    except Exception:
                        pass
                # 点一下验证码图换新图
                try:
                    page.locator("img[src*='/lg4/captcha']").first.click()
                    time.sleep(0.6)
                except Exception:
                    pass
                continue
            # 验证码空
            if "请输入图形验证码" in html and "请输入" in html:
                if page.locator(".swal2-confirm").count() > 0:
                    try:
                        page.locator(".swal2-confirm").first.click(timeout=2000)
                    except Exception:
                        pass
                continue
            # 密码错 / 账号错
            if "账号或密码错误" in html or "密码错误" in html or "用户不存在" in html:
                err = self._extract_swal_text(html) or "账号或密码错误"
                self._fail(err)
                return False
            # 都没匹配 → 视为 OK, 跳出循环让外层判断 2FA / 跳转
            return True
        # 用完了次数
        self._fail(f"自动识别图形验证码连续 {max_attempts} 次失败, 请联系管理员")
        return False

    def _looks_like_2fa(self, html: str) -> bool:
        return (
            ("两步验证" in html and "验证" in html)
            or "二次验证" in html
            or ("6 位" in html and "验证" in html)
        )

    def _looks_like_login_error(self, html: str) -> bool:
        return any(k in html for k in (
            "账号或密码错误", "密码错误", "用户不存在", "账号不存在",
        ))

    def _extract_swal_text(self, html: str) -> str:
        import re
        m = re.search(r'class="swal2-html-container"[^>]*>([^<]+)<', html)
        if m:
            return m.group(1).strip()
        m = re.search(r'class="swal2-title"[^>]*>([^<]+)<', html)
        if m:
            return m.group(1).strip()
        return ""

    def _set_need_2fa(self, page) -> None:
        # 不关浏览器, 留着给 submit_2fa
        with self._lock:
            self.state = "need_2fa"
            self.message = "需要 2FA 验证码, 请在网页输入 6 位数字"

    def _extract_and_done(self, page) -> None:
        try:
            cookies = {c["name"]: c["value"] for c in self._context.cookies()}
        except Exception as e:
            self._fail(f"读 cookies 失败: {e}")
            return

        # v3.9.52 debug · 打印所有 cookies, 方便诊断 C3VK 哪里丢了
        try:
            logger.info("pw_login cookies after login: %s", {
                k: v[:20] + "..." if len(v) > 20 else v
                for k, v in cookies.items()
            })
        except Exception:
            pass

        client_id = cookies.get("__client_id", "")
        uid = cookies.get("_uid", "")
        c3vk = cookies.get("C3VK", "")

        # 兜底 0: 从 page 的 window 上拿 (洛谷常把 token 注入 window.userdata / window._user_)
        if not c3vk:
            try:
                v = page.evaluate("""() => {
                    // 找 window 上的 token 类变量
                    const out = {};
                    try { out.userdata_c3vk = window.userdata?.c3vk; } catch(e) {}
                    try { out.userdata_C3VK = window.userdata?.C3VK; } catch(e) {}
                    try { out.window_c3vk = window.c3vk; } catch(e) {}
                    try { out.window_C3VK = window.C3VK; } catch(e) {}
                    // 也遍历 document.cookie (含可能漏的)
                    out.document_cookie = document.cookie;
                    return out;
                }""")
                logger.info("pw_login window extract: %s", v)
                if isinstance(v, dict):
                    # 1) 直接是值
                    for k in ("userdata_c3vk", "userdata_C3VK", "window_c3vk", "window_C3VK"):
                        if v.get(k) and isinstance(v[k], str):
                            c3vk = v[k]
                            logger.info("pw_login C3VK from window.%s: %s...", k, c3vk[:20])
                            break
                    # 2) document.cookie 里有
                    if not c3vk:
                        import re
                        dc = v.get("document_cookie", "")
                        m = re.search(r"C3VK=([^;]+)", dc)
                        if m:
                            c3vk = m.group(1)
                            logger.info("pw_login C3VK from document.cookie: %s...", c3vk[:20])
            except Exception as e:
                logger.warning("pw_login window extract failed: %s", e)

        # 兜底 1: 监听网络响应, 抓 Set-Cookie 中的 C3VK
        if not c3vk:
            try:
                resp = self._context.request.get(
                    f"https://www.luogu.com.cn/api/user/profile/{uid}",
                    headers={"Accept": "application/json"},
                )
                import re
                # 抓所有 Set-Cookie
                set_cookies = resp.headers.get_list("set-cookie") if hasattr(resp.headers, "get_list") else []
                if not set_cookies and resp.headers.get("set-cookie"):
                    set_cookies = [resp.headers.get("set-cookie")]
                logger.info("pw_login /api/user/profile Set-Cookie: %s", set_cookies)
                for sc in set_cookies:
                    m = re.search(r"C3VK=([^;]+);", sc)
                    if m:
                        c3vk = m.group(1)
                        logger.info("pw_login C3VK from Set-Cookie: %s...", c3vk[:20])
                        break
            except Exception as e:
                logger.warning("pw_login profile Set-Cookie check failed: %s", e)

        # 兜底 2: 重新访问首页 (它通常会发 C3VK)
        if not c3vk:
            try:
                logger.info("pw_login: 重新访问 / 等页面触发 C3VK 发放")
                page.goto("https://www.luogu.com.cn/", wait_until="domcontentloaded", timeout=15000)
                time.sleep(2)
                cookies = {c["name"]: c["value"] for c in self._context.cookies()}
                c3vk = cookies.get("C3VK", "")
                if c3vk:
                    logger.info("pw_login: 二次访问首页后拿到 C3VK: %s...", c3vk[:20])
            except Exception as e:
                logger.warning("pw_login re-visit / failed: %s", e)

        # 兜底 3: 从 HTML 的 csrf-token meta 抓 (v3.9.52 关键发现!)
        # 洛谷把 C3VK 放在 <meta name="csrf-token" content="..."> 里, 而不是 cookie
        if not c3vk:
            try:
                html = page.content()
                import re
                m = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', html)
                if m:
                    c3vk = m.group(1)
                    logger.info("pw_login C3VK from csrf-token meta: %s...", c3vk[:20])
                # 兜底: 老格式
                if not c3vk:
                    m = re.search(r"C3VK=([A-Za-z0-9._+/=%-]+?);", html)
                    if m:
                        c3vk = m.group(1)
                        logger.info("pw_login C3VK from HTML (old format): %s...", c3vk[:20])
            except Exception as e:
                logger.warning("pw_login HTML check failed: %s", e)

        # 兜底 4: 试访问 /record/list 触发 challenge
        if not c3vk:
            try:
                logger.info("pw_login: 试访问 /record/list 触发 challenge")
                page.goto("https://www.luogu.com.cn/record/list",
                          wait_until="domcontentloaded", timeout=15000)
                time.sleep(2)
                # 也监听这次请求的 response headers
                cookies = {c["name"]: c["value"] for c in self._context.cookies()}
                c3vk = cookies.get("C3VK", "")
                if c3vk:
                    logger.info("pw_login: /record/list 后拿到 C3VK: %s...", c3vk[:20])
                else:
                    # 试 HTML
                    html = page.content()
                    import re
                    m = re.search(r"C3VK=([A-Za-z0-9._+/=%-]+?);", html)
                    if m:
                        c3vk = m.group(1)
                        logger.info("pw_login C3VK from /record/list HTML: %s...", c3vk[:20])
            except Exception as e:
                logger.warning("pw_login /record/list failed: %s", e)

        # 兜底 5: API 调用其实可能在 BODY 里返回 C3VK (json 字段)
        if not c3vk:
            try:
                resp = self._context.request.get(
                    "https://www.luogu.com.cn/api/user/me",
                    headers={"Accept": "application/json"},
                )
                logger.info("pw_login /api/user/me status=%d body=%s",
                            resp.status_code, resp.text[:200])
                import re
                m = re.search(r'"C3VK"\s*:\s*"([^"]+)"', resp.text)
                if m:
                    c3vk = m.group(1)
                    logger.info("pw_login C3VK from /api/user/me body: %s...", c3vk[:20])
            except Exception as e:
                logger.warning("pw_login /api/user/me failed: %s", e)

        if not (client_id and uid and c3vk):
            self._fail(
                f"提取三参数不完整: __client_id={'Y' if client_id else 'N'} "
                f"_uid={'Y' if uid else 'N'} C3VK={'Y' if c3vk else 'N'}"
            )
            return

        with self._lock:
            self.cookies = {
                "__client_id": client_id,
                "_uid": uid,
                "C3VK": c3vk,
            }
            self.c3vk_source = "cookies" if cookies.get("C3VK") else "fallback"
            self.state = "done"
            self.message = "登录成功, 已提取 Cookies"

    def _set(self, msg: str) -> None:
        with self._lock:
            self.message = msg
            if self.state not in ("need_2fa",):
                # need_2fa 阶段不要覆盖
                pass

    def _fail(self, err: str) -> None:
        with self._lock:
            self.state = "failed"
            self.error = err
            self.message = f"失败: {err}"


# ----------------------------------------------------------------------
#  全局单例: 会话管理器
# ----------------------------------------------------------------------


class LoginSessionManager:
    """管理所有进行中的 LoginSession。带 TTL 自动清理。"""

    def __init__(self) -> None:
        self._sessions: Dict[str, LoginSession] = {}
        self._lock = threading.Lock()

    def create(self, username: str, password: str) -> LoginSession:
        sid = uuid.uuid4().hex
        sess = LoginSession(
            session_id=sid,
            username=username,
            password=password,
        )
        with self._lock:
            self._sessions[sid] = sess
        self._gc()
        return sess

    def get(self, session_id: str) -> Optional[LoginSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def remove(self, session_id: str) -> None:
        with self._lock:
            sess = self._sessions.pop(session_id, None)
        if sess:
            sess.close()

    def _gc(self) -> None:
        """清理过期 session"""
        with self._lock:
            expired = [sid for sid, s in self._sessions.items() if s.is_expired()]
        for sid in expired:
            self.remove(sid)

    def get_or_create_status(self, session_id: Optional[str]) -> Optional[dict]:
        if not session_id:
            return None
        sess = self.get(session_id)
        if not sess:
            return None
        if sess.is_expired():
            self.remove(session_id)
            return None
        return sess.to_dict()


# 全局单例
_MANAGER: Optional[LoginSessionManager] = None
_MGR_LOCK = threading.Lock()


def get_manager() -> LoginSessionManager:
    global _MANAGER
    with _MGR_LOCK:
        if _MANAGER is None:
            _MANAGER = LoginSessionManager()
        return _MANAGER


# ----------------------------------------------------------------------
#  ddddocr 单例 (启动慢, 别每次都 new)
# ----------------------------------------------------------------------

_OCR = None
_OCR_LOCK = threading.Lock()


def _get_ocr():
    global _OCR
    with _OCR_LOCK:
        if _OCR is None:
            import ddddocr  # type: ignore
            _OCR = ddddocr.DdddOcr(show_ad=False)
        return _OCR
