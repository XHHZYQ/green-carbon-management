"""诊断：验证测点数值随时间变化。"""

import json
import time
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"


def get(path, token=None):
    req = urllib.request.Request(BASE + path)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def login():
    body = json.dumps({"username": "admin", "password": "admin123"}).encode()
    req = urllib.request.Request(BASE + "/auth/login", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())["data"]["access_token"]


def sample(token):
    dev = get("/monitor/realtime?limit=1", token)["data"][0]
    p = dev["points"][0]
    return f'{dev["device_name"]} / {p["point_name"]} = {p["value"]}{p.get("unit") or ""}'


token = login()
a = sample(token)
print("T0   :", a)
time.sleep(22)
b = sample(token)
print("T+22s:", b)
print("结论 :", "数值已变化" if a != b else "数值未变化（异常）")
