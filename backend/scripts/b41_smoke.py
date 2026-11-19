"""B4-1 设备控制域冒烟测试。"""

import json
import time
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
        with urllib.request.urlopen(req, timeout=15) as resp:
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

    # 控制面板
    r = call("GET", "/control/points")
    devices = r.get("data") or []
    check("控制面板设备列表", r.get("code") == 0 and len(devices) > 0, f"设备数={len(devices)}")
    dev = devices[0] if devices else {}
    point = (dev.get("points") or [{}])[0]
    check("设备含控制点", bool(dev.get("points")), f"设备={dev.get('device_name')} 控制点={len(dev.get('points') or [])}")
    check("控制点当前值字段", "current_value" in point, f"key={point.get('point_key')}")

    # 单设备下发
    target = "1" if point.get("point_type") == "enum" else str(point.get("value_max") or 60)
    r = call("POST", "/control/command", {
        "device_id": dev.get("device_id"),
        "point_key": point.get("point_key"),
        "target_value": target,
        "source": "manual",
    })
    cmd = r.get("data") or {}
    cid = cmd.get("id")
    check("下发指令创建", r.get("code") == 0 and bool(cid), f"id={cid} 状态={cmd.get('status')}")
    check("初始状态待下发", cmd.get("status") == "pending", f"status={cmd.get('status')}")

    # 轮询状态流转
    final = None
    for _ in range(12):
        time.sleep(1)
        rr = call("GET", f"/control/commands/{cid}")
        final = (rr.get("data") or {}).get("status")
        if final in ("success", "fail", "timeout"):
            break
    check("状态异步流转到终态", final in ("success", "fail", "timeout"), f"最终状态={final}")

    # 控制记录列表
    r = call("GET", "/control/commands?page=1&page_size=10")
    page = r.get("data") or {}
    check("控制记录列表", r.get("code") == 0 and page.get("total", 0) > 0, f"总数={page.get('total')}")
    check("记录含设备名", bool((page.get("items") or [{}])[0].get("device_name")))

    # 批量下发
    items = [
        {"device_id": d.get("device_id"), "point_key": (d.get("points") or [{}])[0].get("point_key"),
         "target_value": "1" if (d.get("points") or [{}])[0].get("point_type") == "enum" else "50"}
        for d in devices[:3]
    ]
    r = call("POST", "/control/batch", {"items": items})
    check("批量下发", r.get("code") == 0 and (r.get("data") or {}).get("count") == len(items),
          f"count={(r.get('data') or {}).get('count')}")

    # 定时任务 CRUD
    r = call("GET", "/control/timed-tasks?page=1&page_size=10")
    tasks = (r.get("data") or {}).get("items") or []
    check("定时任务列表", r.get("code") == 0 and len(tasks) > 0, f"数量={(r.get('data') or {}).get('total')}")

    payload = {
        "task_name": "冒烟测试任务",
        "device_id": dev.get("device_id"),
        "point_key": point.get("point_key"),
        "target_value": target,
        "cron_expr": "0 8 * * *",
        "repeat_desc": "每天 08:00",
        "enable_status": 1,
    }
    r = call("POST", "/control/timed-tasks", payload)
    tid = (r.get("data") or {}).get("id")
    check("新增定时任务", r.get("code") == 0 and bool(tid), f"id={tid}")
    check("定时任务计算下次执行", bool((r.get("data") or {}).get("next_run_time")), f"next={(r.get('data') or {}).get('next_run_time')}")

    if tid:
        r = call("PUT", f"/control/timed-tasks/{tid}", {"task_name": "冒烟测试任务-改", "enable_status": 0})
        d = r.get("data") or {}
        check("编辑定时任务", r.get("code") == 0 and d.get("task_name") == "冒烟测试任务-改" and d.get("next_run_time") is None)
        r = call("DELETE", f"/control/timed-tasks/{tid}")
        check("删除定时任务", r.get("code") == 0)

    print("\n== 结果 ==", "全部通过" if ok_all else "存在失败")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
