"""B3-1 阶段接口冒烟测试：区域 -> 设备台账 -> 接入向导/导入/接入记录 -> 测点与数据。"""

import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
TOKEN = ""


def call(method: str, path: str, data=None, auth=True):
    url = BASE + path
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    if auth and TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return {"http_error": exc.code, "body": exc.read().decode()}


def main():
    global TOKEN
    ok_all = True

    def check(name, cond, extra=""):
        nonlocal ok_all
        ok_all = ok_all and cond
        print(f"[{'PASS' if cond else 'FAIL'}] {name} {extra}")

    r = call("POST", "/auth/login", {"username": "admin", "password": "admin123"}, auth=False)
    TOKEN = r.get("data", {}).get("access_token", "")
    check("登录", bool(TOKEN))

    # 区域
    r = call("GET", "/areas/tree")
    check("区域树", r.get("code") == 0, f"根节点={len(r.get('data') or [])}")

    # 设备台账
    r = call("GET", "/devices?page=1&page_size=5")
    check("设备台账", r.get("code") == 0, f"total={r.get('data', {}).get('total')}")

    # 接入向导
    r = call("GET", "/devices/wizard/types")
    check("向导-设备类型", r.get("code") == 0, f"数量={len(r.get('data') or [])}")

    r = call("GET", "/devices/wizard/protocols")
    protocols = r.get("data") or []
    check("向导-协议", r.get("code") == 0, f"数量={len(protocols)}")
    proto_id = protocols[0]["id"] if protocols else None

    if proto_id:
        r = call("GET", f"/devices/wizard/params?protocol_id={proto_id}")
        check("向导-协议参数", r.get("code") == 0, f"数量={len(r.get('data') or [])}")
        r = call("POST", "/devices/test-connection",
                 {"protocol_id": proto_id, "params": {"ip": "192.168.1.10", "port": 502}})
        check("测试连接", r.get("code") == 0 and r["data"].get("success") is True, r.get("data"))

    # 导入模板
    req = urllib.request.Request(BASE + "/devices/import/template")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
        check("导入模板下载", raw[:2] == b"PK", f"bytes={len(raw)}")
    except urllib.error.HTTPError as exc:
        check("导入模板下载", False, f"http={exc.code}")

    # 接入记录
    r = call("GET", "/devices/access-logs?page=1&page_size=5")
    check("接入记录", r.get("code") == 0, f"total={r.get('data', {}).get('total')}")

    # 设备接入（新增）
    r = call("GET", "/devices/wizard/types")
    types = r.get("data") or []
    type_id = types[0]["id"] if types else None
    payload = {
        "device_code": "SMOKE-B31-001",
        "device_name": "冒烟测试设备",
        "device_type_id": type_id,
        "protocol_id": proto_id,
        "install_location": "测试机房",
        "params": {"ip": "192.168.1.10", "port": 502},
        "enable_online": True,
    }
    r = call("POST", "/devices", payload)
    new_id = r.get("data", {}).get("id") if r.get("code") == 0 else None
    check("新增设备并上线", r.get("code") == 0, r.get("message", r))

    if new_id:
        r = call("GET", f"/devices/{new_id}")
        check("设备详情", r.get("code") == 0 and r["data"]["device_code"] == "SMOKE-B31-001")

        r = call("PUT", f"/devices/{new_id}/online-status", {"online": False})
        check("设备下线", r.get("code") == 0 and r["data"]["online_status"] == "offline", r.get("message", r))

        # 测点
        r = call("POST", "/points", {"device_id": new_id, "point_code": "P1", "point_name": "冒烟测点", "unit": "kWh"})
        point_id = r.get("data", {}).get("id") if r.get("code") == 0 else None
        check("新增测点", r.get("code") == 0, r.get("message", r))
        if point_id:
            r = call("PUT", f"/points/{point_id}", {"point_name": "冒烟测点-改"})
            check("编辑测点", r.get("code") == 0, r.get("message", r))
            r = call("DELETE", f"/points/{point_id}")
            check("删除测点", r.get("code") == 0, r.get("message", r))

        # 采集任务
        r = call("POST", "/collect-tasks", {"device_id": new_id, "task_name": "冒烟任务", "period_sec": 30})
        task_id = r.get("data", {}).get("id") if r.get("code") == 0 else None
        check("新增采集任务", r.get("code") == 0, r.get("message", r))
        if task_id:
            r = call("PUT", f"/collect-tasks/{task_id}", {"task_name": "冒烟任务-改", "period_sec": 60})
            check("编辑采集任务", r.get("code") == 0, r.get("message", r))

        r = call("DELETE", f"/devices/{new_id}")
        check("删除设备（级联）", r.get("code") == 0, r.get("message", r))

    # 其它列表
    r = call("GET", "/points?page=1&page_size=5")
    check("测点列表", r.get("code") == 0, f"total={r.get('data', {}).get('total')}")
    r = call("GET", "/point-templates?page=1&page_size=5")
    check("测点模板列表", r.get("code") == 0, f"total={r.get('data', {}).get('total')}")
    r = call("GET", "/collect-tasks?page=1&page_size=5")
    check("采集任务列表", r.get("code") == 0, f"total={r.get('data', {}).get('total')}")
    r = call("GET", "/data?page=1&page_size=5")
    check("历史数据查询", r.get("code") == 0, f"total={r.get('data', {}).get('total')}")

    print("\n结果:", "全部通过" if ok_all else "存在失败项")


if __name__ == "__main__":
    main()
