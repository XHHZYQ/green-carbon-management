"""B6 批次综合冒烟测试（消息通知 / 告警工单 / 节能定额）。

覆盖三条跨模块端到端链路 + 各模块列表接口连通：
  1) 超定额 -> 预警 -> 站内通知
  2) 告警确认 -> 转工单 -> 指派 -> 处理 -> 完成
  3) 发送通知 -> 生成站内消息与发送记录 -> 标记已读
用法：先启动后端服务，再执行
    uv run python scripts/b6_smoke.py
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

BASE = "http://127.0.0.1:8000/api/v1"
TOKEN = ""


def q(value) -> str:
    """URL 编码查询参数（支持中文）。"""
    return urllib.parse.quote(str(value))


def call(method: str, path: str, data=None, auth=True):
    url = BASE + path
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    if auth and TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return {"http_error": exc.code, "body": exc.read().decode()}


def data_of(resp: dict) -> dict:
    return resp.get("data") or {}


def total_of(resp: dict) -> int:
    return data_of(resp).get("total") or 0


def items_of(resp: dict) -> list:
    return data_of(resp).get("items") or []


def main():
    global TOKEN
    ok_all = True

    def check(name, cond, extra=""):
        nonlocal ok_all
        ok_all = ok_all and cond
        print(f"[{'PASS' if cond else 'FAIL'}] {name} {extra}")

    r = call("POST", "/auth/login", {"username": "admin", "password": "admin123"}, auth=False)
    TOKEN = data_of(r).get("access_token", "")
    check("登录", bool(TOKEN))

    # ==================== 链路① 超定额 -> 预警 -> 通知 ====================
    r = call("GET", f"/notify/messages?page=1&page_size=1&keyword={q('定额')}")
    notify_before = total_of(r)
    r = call("POST", "/quota/monitors/refresh", {})
    refresh = data_of(r)
    check("刷新定额监控接口连通", r.get("code") == 0, f"结果={refresh}")

    r = call("GET", "/quota/monitors?page=1&page_size=5&warn_status=exceed")
    exceed_total = total_of(r)
    exceed_row = items_of(r)[0] if items_of(r) else {}
    check("存在超定额监控记录", exceed_total > 0,
          f"超限数={exceed_total} 样例={exceed_row.get('quota_name')} 完成率={exceed_row.get('complete_rate')}")

    r = call("GET", f"/notify/messages?page=1&page_size=1&keyword={q('定额')}")
    notify_after = total_of(r)
    check("超定额产生站内通知", notify_after >= 1, f"定额相关消息 {notify_before} -> {notify_after}")

    # ==================== 链路② 告警 -> 工单闭环 ====================
    r = call("GET", "/alarm/infos?page=1&page_size=5&status=pending")
    alarms = items_of(r)
    alarm = alarms[0] if alarms else {}
    check("存在待确认告警", bool(alarm.get("id")), f"告警={alarm.get('alarm_no')} 设备={alarm.get('device_name')}")

    if alarm.get("id"):
        aid = alarm["id"]
        r = call("PUT", f"/alarm/infos/{aid}/confirm", {"remark": "B6冒烟确认"})
        check("确认告警", r.get("code") == 0 and data_of(r).get("status") == "confirmed")
        r = call("GET", f"/alarm/infos/{aid}")
        check("确认后状态回读", (data_of(r).get("status") == "confirmed"))

        r = call("POST", f"/alarm/infos/{aid}/work-order")
        wo = data_of(r)
        wo_id = wo.get("id")
        check("告警转工单", r.get("code") == 0 and bool(wo_id), f"工单号={wo.get('order_no')}")

        if wo_id:
            # 从用户列表取一位运营/管理员作为指派对象
            r = call("GET", "/system/users?page=1&page_size=20")
            users = items_of(r)
            ops = next((u for u in users if u.get("username") in ("ops", "energy_admin", "admin")), {})
            r = call("PUT", f"/wo/work-orders/{wo_id}/assign", {"assignee_id": ops.get("id") or 1})
            check("指派工单", r.get("code") == 0 and data_of(r).get("status") == "processing",
                  f"指派给={ops.get('username')}")
            r = call("PUT", f"/wo/work-orders/{wo_id}/handle", {"handle_result": "B6冒烟：现场已处理"})
            check("处理工单", r.get("code") == 0)
            r = call("PUT", f"/wo/work-orders/{wo_id}/finish", {"handle_result": "B6冒烟：处理完成"})
            check("完成工单", r.get("code") == 0 and data_of(r).get("status") == "finished")
            r = call("GET", f"/wo/work-orders/{wo_id}")
            got = data_of(r)
            check("工单详情回读-来源为alarm", got.get("source") == "alarm" and bool(got.get("finish_time")),
                  f"来源={got.get('source')} 完成时间={got.get('finish_time')}")

    # ==================== 链路③ 发送通知 -> 消息 + 发送记录 -> 已读 ====================
    r = call("GET", "/system/users?page=1&page_size=20")
    users = items_of(r)
    admin = next((u for u in users if u.get("username") == "admin"), {})
    r = call("GET", "/notify/channels?page=1&page_size=20")
    channels = items_of(r)
    ch_ids = [c["id"] for c in channels[:2]]

    title = f"B6冒烟通知_{int(time.time())}"
    r = call("POST", "/notify/messages", {
        "title": title, "content": "B6 冒烟测试通知内容",
        "msg_type": "internal", "level": "info",
        "receiver_ids": [admin.get("id") or 1], "channel_ids": ch_ids,
    })
    res = data_of(r)
    check("发送通知生成消息与发送记录", r.get("code") == 0 and (res.get("message_count") or 0) >= 1
          and (res.get("log_count") or 0) >= 1, f"结果={res}")

    r = call("GET", f"/notify/messages?page=1&page_size=10&keyword={q(title)}")
    check("站内消息可按标题检索到", total_of(r) >= 1)

    r = call("PUT", "/notify/messages/read-all")
    check("全部标记已读", r.get("code") == 0)
    r = call("GET", "/notify/messages/unread-count")
    check("未读数为 0", data_of(r).get("count") == 0, f"未读={data_of(r).get('count')}")

    # ==================== 链路④ 定额考核生成 ====================
    period = datetime.now().strftime("%Y-%m")
    r = call("POST", "/quota/assess/generate", {"period_value": period})
    check("生成定额考核", r.get("code") == 0 and (data_of(r).get("count") or 0) > 0,
          f"周期={period} 结果={data_of(r)}")
    r = call("GET", "/quota/assess?page=1&page_size=5")
    check("考核列表有数据", total_of(r) > 0, f"总数={total_of(r)}")
    r = call("GET", "/quota/report")
    rep = data_of(r)
    check("考核报表返回统计", bool(rep.get("cards")) and bool(rep.get("grade_ratio")),
          f"卡片={rep.get('cards')}")

    # ==================== 链路⑤ 各模块列表接口连通 ====================
    for name, path in [
        ("通知渠道", "/notify/channels?page=1&page_size=10"),
        ("通知模板", "/notify/templates?page=1&page_size=10"),
        ("通知规则", "/notify/rules?page=1&page_size=10"),
        ("发送记录", "/notify/send-logs?page=1&page_size=10"),
        ("告警规则", "/alarm/rules?page=1&page_size=10"),
        ("告警列表", "/alarm/infos?page=1&page_size=10"),
        ("告警统计", "/alarm/statistics"),
        ("工单列表", "/wo/work-orders?page=1&page_size=10"),
        ("定额列表", "/quota/quotas?page=1&page_size=10"),
        ("定额树", "/quota/tree"),
        ("定额监控", "/quota/monitors?page=1&page_size=10"),
        ("考核报表", "/quota/report"),
    ]:
        rr = call("GET", path)
        check(f"列表接口连通-{name}", rr.get("code") == 0)

    print("\n== 结果 ==", "全部通过" if ok_all else "存在失败")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
