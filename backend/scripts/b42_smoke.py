"""B4-2 场景与联动域冒烟测试。"""

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

    # 场景列表
    r = call("GET", "/scenes?page=1&page_size=10")
    page = r.get("data") or {}
    items = page.get("items") or []
    check("场景列表", r.get("code") == 0 and page.get("total", 0) > 0, f"总数={page.get('total')}")
    first = items[0] if items else {}
    check("场景含动作数/定时信息", "action_count" in first and "cron_expr" in first, f"scene={first.get('scene_name')} 动作数={first.get('action_count')}")

    # 场景详情
    if first.get("id"):
        r = call("GET", f"/scenes/{first['id']}")
        d = r.get("data") or {}
        check("场景详情含动作列表", r.get("code") == 0 and "actions" in d, f"动作数={len(d.get('actions') or [])}")

    # 控制点（用于构造动作）
    r = call("GET", "/control/points")
    devices = r.get("data") or []
    dev = devices[0] if devices else {}
    point = (dev.get("points") or [{}])[0]
    target = "1" if point.get("point_type") == "enum" else str(point.get("value_max") or 50)

    # 场景 CRUD
    r = call("POST", "/scenes", {
        "scene_code": f"SCENE_SMOKE_{int(time.time())}", "scene_name": "冒烟测试场景", "icon": "MagicStick",
        "description": "冒烟用例", "enable_status": 1,
    })
    sid = (r.get("data") or {}).get("id")
    check("新建场景", r.get("code") == 0 and bool(sid), f"id={sid}")

    if sid:
        r = call("PUT", f"/scenes/{sid}", {"scene_name": "冒烟测试场景-改"})
        check("编辑场景", r.get("code") == 0 and (r.get("data") or {}).get("scene_name") == "冒烟测试场景-改")

        # 场景动作
        r = call("POST", f"/scenes/{sid}/actions", {
            "device_id": dev.get("device_id"), "point_key": point.get("point_key"),
            "target_value": target, "delay_sec": 0, "sort_no": 0,
        })
        aid = (r.get("data") or {}).get("id")
        check("新增场景动作", r.get("code") == 0 and bool(aid), f"id={aid}")

        r = call("GET", f"/scenes/{sid}/actions")
        check("场景动作列表", r.get("code") == 0 and len(r.get("data") or []) == 1)

        if aid:
            r = call("PUT", f"/scenes/actions/{aid}", {"target_value": target})
            check("编辑场景动作", r.get("code") == 0)
            r = call("DELETE", f"/scenes/actions/{aid}")
            check("删除场景动作", r.get("code") == 0)

        # 一键执行
        r = call("POST", f"/scenes/{sid}/exec")
        ex = r.get("data") or {}
        check("一键执行场景", r.get("code") == 0 and "success_count" in ex, f"结果={ex}")

        # 定时配置
        r = call("POST", f"/scenes/{sid}/schedule", {"cron_expr": "0 9 * * 1-5", "repeat_desc": "工作日 09:00", "enable_status": 1})
        check("配置场景定时", r.get("code") == 0 and bool((r.get("data") or {}).get("next_run_time")))

        # 启停
        r = call("PUT", f"/scenes/{sid}/enable", {"enable_status": 0})
        check("启停场景", r.get("code") == 0 and (r.get("data") or {}).get("enable_status") == 0)

        r = call("DELETE", f"/scenes/{sid}")
        check("删除场景", r.get("code") == 0)

    # 联动规则
    r = call("GET", "/link-rules?page=1&page_size=10")
    page = r.get("data") or {}
    rules = page.get("items") or []
    check("联动规则列表", r.get("code") == 0 and page.get("total", 0) > 0, f"总数={page.get('total')}")
    rule0 = rules[0] if rules else {}
    check("规则含条件/目标描述", bool(rule0.get("condition_text")), f"规则={rule0.get('rule_name')}")

    r = call("POST", "/link-rules", {
        "rule_name": "冒烟联动规则", "condition_text": "温度 > 30",
        "condition_json": {"device_id": dev.get("device_id"), "point_code": "CO2", "operator": ">", "threshold": 2000},
        "action_type": "control", "target_device_id": dev.get("device_id"),
        "target_point_key": point.get("point_key"), "target_value": target, "enable_status": 1,
    })
    rid = (r.get("data") or {}).get("id")
    check("新增联动规则", r.get("code") == 0 and bool(rid), f"id={rid}")
    if rid:
        r = call("PUT", f"/link-rules/{rid}", {"rule_name": "冒烟联动规则-改"})
        check("编辑联动规则", r.get("code") == 0 and (r.get("data") or {}).get("rule_name") == "冒烟联动规则-改")
        r = call("PUT", f"/link-rules/{rid}/enable", {"enable_status": 0})
        check("启停联动规则", r.get("code") == 0 and (r.get("data") or {}).get("enable_status") == 0)
        r = call("DELETE", f"/link-rules/{rid}")
        check("删除联动规则", r.get("code") == 0)

    # 执行记录
    r = call("GET", "/scene-exec-logs?page=1&page_size=10")
    page = r.get("data") or {}
    logs = page.get("items") or []
    check("执行记录列表", r.get("code") == 0 and page.get("total", 0) > 0, f"总数={page.get('total')}")
    log0 = logs[0] if logs else {}
    check("记录含执行类型/结果文本", bool(log0.get("exec_type_text")) and bool(log0.get("result_text")),
          f"类型={log0.get('exec_type_text')} 结果={log0.get('result_text')}")

    r = call("GET", "/scene-exec-logs?exec_type=link&page=1&page_size=10")
    check("执行记录按类型筛选", r.get("code") == 0)

    print("\n== 结果 ==", "全部通过" if ok_all else "存在失败")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
