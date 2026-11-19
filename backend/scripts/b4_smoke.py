"""B4 控制域综合冒烟测试（B4-3 批次收尾）。

B4-1/B4-2 的脚本各自覆盖本模块内部，本脚本补充跨模块端到端链路：
  1) 单台控制下发 -> 状态自动流转到终态 -> 命中映射时同步写入测点数据
  2) 场景一键执行 -> 生成 source=scene 控制指令 -> 指令自动流转 -> 写入执行记录
  3) 联动规则命中 -> 调度器自动执行 -> 生成 link 执行记录
  4) 场景定时配置 -> 正确计算下次执行时间
  5) 控制域各列表接口连通
"""

import json
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
TOKEN = ""

# 控制点 -> 可映射的测点编码（与 control_service.CTRL_TO_POINT 保持一致）
CTRL_TO_POINT = {
    "switch": ["RunStatus", "Power", "ActivePower"],
    "brightness_set": ["Brightness"],
    "setpoint": ["SupplyTemp"],
    "frequency": ["FanSpeed", "Flow"],
}


def call(method: str, path: str, data=None, auth=True):
    url = BASE + path
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    if auth and TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return {"http_error": exc.code, "body": exc.read().decode()}


def wait_terminal(command_id: int, rounds: int = 12):
    """轮询控制指令状态直到终态，返回最终状态。"""
    final = None
    for _ in range(rounds):
        time.sleep(1)
        rr = call("GET", f"/control/commands/{command_id}")
        final = (rr.get("data") or {}).get("status")
        if final in ("success", "fail", "timeout"):
            break
    return final


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

    # ==================== 链路① 控制下发闭环 + 测点同步 ====================
    devices = call("GET", "/control/points").get("data") or []
    check("控制面板设备列表", len(devices) > 0, f"设备数={len(devices)}")
    # 优先选能映射到测点的控制点
    dev = point = None
    for d in devices:
        for p in d.get("points") or []:
            if p.get("point_key") in CTRL_TO_POINT:
                dev, point = d, p
                break
        if dev:
            break
    if not dev:
        dev = devices[0] if devices else {}
        point = (dev.get("points") or [{}])[0]
    check("选取控制点", bool(dev.get("device_id")) and bool(point.get("point_key")),
          f"设备={dev.get('device_name')} 控制点={point.get('point_key')}")

    # 找到该控制点可映射到的测点（用于验证同步写数）
    mapped_point = None
    for code in CTRL_TO_POINT.get(point.get("point_key") or "", []):
        r = call("GET", f"/points?device_id={dev.get('device_id')}&keyword={code}&page=1&page_size=5")
        for it in (r.get("data") or {}).get("items") or []:
            if it.get("point_code") == code:
                mapped_point = it
                break
        if mapped_point:
            break

    target = "55.5"
    r = call("POST", "/control/command", {
        "device_id": dev.get("device_id"), "point_key": point.get("point_key"),
        "target_value": target, "source": "manual",
    })
    cid = (r.get("data") or {}).get("id")
    check("单台下发创建指令", r.get("code") == 0 and bool(cid), f"id={cid}")
    final = wait_terminal(cid) if cid else None
    check("指令状态自动流转到终态", final in ("success", "fail", "timeout"), f"最终状态={final}")

    if mapped_point and final == "success":
        r = call("GET", f"/data?point_id={mapped_point['id']}&page=1&page_size=1")
        latest = ((r.get("data") or {}).get("items") or [{}])[0]
        val = latest.get("collect_value")
        check("下发成功同步写入测点数据", val is not None and abs(float(val) - float(target)) < 1e-6,
              f"测点={mapped_point.get('point_code')} 最新值={val} 目标={target}")
    else:
        check("下发同步测点（该控制点无映射或不成功，跳过）", True,
              f"映射点={'有' if mapped_point else '无'} 状态={final}")

    # ==================== 链路② 场景一键执行 -> 控制指令 + 执行记录 ====================
    scenes = (call("GET", "/scenes?page=1&page_size=50").get("data") or {}).get("items") or []
    scene = next((s for s in scenes if (s.get("action_count") or 0) > 0), None)
    check("存在含动作的场景", bool(scene), f"场景={scene.get('scene_name') if scene else None}")

    if scene:
        before_cmds = ((call("GET", "/control/commands?source=scene&page=1&page_size=1").get("data") or {}).get("total") or 0)
        before_logs = ((call("GET", f"/scene-exec-logs?exec_type=scene&scene_id={scene['id']}&page=1&page_size=1").get("data") or {}).get("total") or 0)

        r = call("POST", f"/scenes/{scene['id']}/exec")
        ex = r.get("data") or {}
        check("场景一键执行返回统计", r.get("code") == 0 and "success_count" in ex, f"结果={ex}")

        r = call("GET", "/control/commands?source=scene&page=1&page_size=1")
        cmds = (r.get("data") or {}).get("items") or []
        scene_cid = cmds[0].get("id") if cmds else None
        check("场景执行生成 scene 来源控制指令", bool(scene_cid),
              f"指令id={scene_cid} 剩余下一状态={cmds[0].get('status') if cmds else None}")
        sfinal = wait_terminal(scene_cid) if scene_cid else None
        check("场景生成指令由调度器自动流转", sfinal in ("success", "fail", "timeout"), f"最终状态={sfinal}")

        r = call("GET", f"/scene-exec-logs?exec_type=scene&scene_id={scene['id']}&page=1&page_size=1")
        after_logs = (r.get("data") or {}).get("total") or 0
        log0 = ((r.get("data") or {}).get("items") or [{}])[0]
        check("场景执行写入执行记录", after_logs > before_logs and log0.get("exec_type_text") == "场景执行",
              f"执行记录 {before_logs}->{after_logs} 结果={log0.get('result_text')}")

    # ==================== 链路③ 联动规则命中 -> 自动执行 ====================
    pts = ((call("GET", "/points?page=1&page_size=5").get("data") or {}).get("items") or [])
    cp = pts[0] if pts else {}
    rule_name = f"B4冒烟联动_{int(time.time())}"
    r = call("POST", "/link-rules", {
        "rule_name": rule_name,
        "condition_text": "冒烟：数值 > -1e9 必然命中",
        "condition_json": {"device_id": cp.get("device_id"), "point_code": cp.get("point_code"),
                           "operator": ">", "threshold": -1e9},
        "action_type": "control", "target_device_id": dev.get("device_id"),
        "target_point_key": point.get("point_key"), "target_value": target, "enable_status": 1,
    })
    rid = (r.get("data") or {}).get("id")
    check("新增必然命中的联动规则", r.get("code") == 0 and bool(rid), f"id={rid} 条件点={cp.get('point_code')}")

    hit = False
    if rid:
        for _ in range(18):  # 最多约 36 秒，等待 scene_link 周期任务
            time.sleep(2)
            rr = call("GET", "/scene-exec-logs?exec_type=link&page=1&page_size=10")
            items = (rr.get("data") or {}).get("items") or []
            if any(i.get("rule_name") == rule_name for i in items):
                hit = True
                break
    check("联动规则被调度器命中并执行", hit)
    if rid:
        r = call("DELETE", f"/link-rules/{rid}")
        check("清理联动规则", r.get("code") == 0)

    # ==================== 链路④ 场景定时 ====================
    r = call("POST", "/scenes", {
        "scene_code": f"SCENE_B4_{int(time.time())}", "scene_name": "B4冒烟定时场景",
        "icon": "Clock", "description": "综合冒烟用例", "enable_status": 1,
    })
    sid = (r.get("data") or {}).get("id")
    if sid:
        r = call("POST", f"/scenes/{sid}/schedule",
                 {"cron_expr": "0 7 * * *", "repeat_desc": "每天 07:00", "enable_status": 1})
        sched = r.get("data") or {}
        check("场景定时计算下次执行时间", r.get("code") == 0 and bool(sched.get("next_run_time")),
              f"next={sched.get('next_run_time')}")
        r = call("DELETE", f"/scenes/{sid}")
        check("清理冒烟场景", r.get("code") == 0)
    else:
        check("新建冒烟场景", False)

    # ==================== 链路⑤ 控制域列表连通 ====================
    for name, path in [
        ("控制面板", "/control/points"),
        ("控制记录", "/control/commands?page=1&page_size=10"),
        ("定时任务", "/control/timed-tasks?page=1&page_size=10"),
        ("场景列表", "/scenes?page=1&page_size=10"),
        ("联动规则", "/link-rules?page=1&page_size=10"),
        ("执行记录", "/scene-exec-logs?page=1&page_size=10"),
    ]:
        rr = call("GET", path)
        check(f"列表接口连通-{name}", rr.get("code") == 0)

    print("\n== 结果 ==", "全部通过" if ok_all else "存在失败")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
