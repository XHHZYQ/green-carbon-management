"""校验种子订阅「立即执行」不再触发外键错误（临时校验脚本）。"""
import json
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"


def call(method, path, data=None, token=""):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(data).encode() if data else None, method=method
    )
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return {"http_error": exc.code, "body": exc.read().decode()[:400]}
    except Exception as exc:  # noqa: BLE001
        return {"err": str(exc)}


def main():
    token = ""
    for _ in range(20):
        r = call("POST", "/auth/login", {"username": "admin", "password": "admin123"})
        token = (r.get("data") or {}).get("access_token", "")
        if token:
            break
        time.sleep(1)
    print("token ok:", bool(token))

    r = call("GET", "/reports/subscriptions?page=1&page_size=20", token=token)
    subs = (r.get("data") or {}).get("items") or []
    print("订阅数:", len(subs))
    for s in subs:
        rr = call("POST", f"/reports/subscriptions/{s['id']}/run", {}, token=token)
        print(f"  执行「{s['subscribe_name']}」channel_ids={s.get('channel_ids')} ->", rr.get("code"), rr.get("data") or rr.get("message"))


if __name__ == "__main__":
    main()
