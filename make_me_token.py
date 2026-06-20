"""make_me_token.py - 生成 /me/<uid>?t=... 签名 token

生产 docker-compose.yml 没设 ME_TOKEN_SECRET,用的就是源码里那个 fallback:
  _ME_TOKEN_SECRET = "luogu-ai-me-token-CHANGE-ME-IN-PROD-9b4e7d2a"
所以这里直接用这个 secret 算,跟线上 web_app.py 一致。

用法:
    python make_me_token.py 1752947
    python make_me_token.py 1752947 1752948 123456
"""
import hmac, hashlib, sys

SECRET = "luogu-ai-me-token-CHANGE-ME-IN-PROD-9b4e7d2a"
BASE = "https://oi.aijiangti.cn"

def sign(uid: str) -> str:
    msg = uid.encode("utf-8")
    secret = SECRET.encode("utf-8")
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()[:24]

if __name__ == "__main__":
    uids = sys.argv[1:] or ["1752947"]
    for uid in uids:
        t = sign(uid)
        url = f"{BASE}/me/{uid}?t={t}"
        print(f"uid={uid}  token={t}")
        print(f"  → {url}")
