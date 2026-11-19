"""B7 报表记录 report_type 过滤分页一致性校验（临时校验脚本）。"""
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
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return {"http_error": exc.code, "body": exc.read().decode()[:300]}
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
    for rt in ["daily", "monthly", "yearly", "custom"]:
        r = call("GET", f"/reports/records?page=1&page_size=50&report_type={rt}", token=token)
        data = r.get("data") or {}
        print(f"report_type={rt}: total={data.get('total')} items={len(data.get('items') or [])}")


if __name__ == "__main__":
    main()
