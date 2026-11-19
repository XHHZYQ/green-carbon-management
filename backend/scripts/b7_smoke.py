"""B7 批次综合冒烟测试（报表中心 / 数据驾驶舱）。

覆盖两条主线：
  1) 数据驾驶舱 8 个聚合接口连通 + 关键字段非空
  2) 报表中心端到端：模板 -> 生成 -> 记录 -> 导出(Excel/PDF) -> 订阅 -> 立即执行(推送)
用法：先启动后端服务，再执行
    uv run python scripts/b7_smoke.py
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request

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


def call_raw(method: str, path: str):
    """下载二进制内容，返回 (bytes, content_type)。"""
    url = BASE + path
    req = urllib.request.Request(url, method=method)
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read(), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        return exc.read(), f"HTTP_{exc.code}"


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

    # ==================== 一、数据驾驶舱 ====================
    r = call("GET", "/dashboard/overview")
    ov = data_of(r)
    check("驾驶舱-指标卡", r.get("code") == 0 and "device_total" in ov,
          f"设备={ov.get('device_total')} 在线率={ov.get('online_rate')}% 月能耗={ov.get('month_energy')}")

    r = call("GET", "/dashboard/energy-trend?days=7")
    tr = data_of(r)
    check("驾驶舱-能耗趋势", r.get("code") == 0 and len(tr.get("dates") or []) == 7,
          f"点数={len(tr.get('dates') or [])}")

    r = call("GET", "/dashboard/energy-item-ratio")
    ratio = data_of(r)
    check("驾驶舱-分项占比", r.get("code") == 0 and isinstance(ratio, list),
          f"分项数={len(ratio)}")

    r = call("GET", "/dashboard/area-rank?limit=8")
    rank = data_of(r)
    check("驾驶舱-区域排名", r.get("code") == 0 and isinstance(rank, list) and len(rank) > 0,
          f"区域数={len(rank)} top1={rank[0] if rank else '-'}")

    r = call("GET", "/dashboard/carbon-overview")
    co = data_of(r)
    check("驾驶舱-碳排总览", r.get("code") == 0 and "trend" in co,
          f"年度={co.get('year')} 总量={co.get('total')}")

    r = call("GET", "/dashboard/device-status")
    ds = data_of(r)
    check("驾驶舱-设备状态", r.get("code") == 0 and isinstance(ds.get("online"), list),
          f"在线分布={ds.get('online')}")

    r = call("GET", "/dashboard/latest-alarms?limit=10")
    alarms = data_of(r)
    check("驾驶舱-最新告警", r.get("code") == 0 and isinstance(alarms, list),
          f"告警数={len(alarms)}")

    r = call("GET", "/dashboard/fee-quota")
    fq = data_of(r)
    check("驾驶舱-费用定额", r.get("code") == 0 and "month_fee" in fq,
          f"本月费用={fq.get('month_fee')} 环比={fq.get('fee_mom')}%")

    # ==================== 二、报表中心 ====================
    r = call("GET", "/reports/templates")
    templates = data_of(r)
    check("报表-模板列表", r.get("code") == 0 and isinstance(templates, list) and len(templates) > 0,
          f"模板数={len(templates)}")
    tpl = templates[0] if templates else {}
    tpl_id = tpl.get("id")

    # 生成报表（按模板）
    r = call("POST", "/reports/generate", {
        "template_id": tpl_id, "report_type": "monthly", "file_type": "excel",
    })
    gen = data_of(r)
    gen_id = gen.get("id")
    check("报表-按模板生成", r.get("code") == 0 and bool(gen_id),
          f"名称={gen.get('report_name')} 状态={gen.get('gen_status')}")
    check("报表-生成返回聚合内容", isinstance(gen.get("content"), dict)
          and "summary" in (gen.get("content") or {}),
          f"汇总={(gen.get('content') or {}).get('summary')}")

    # 自定义报表
    r = call("POST", "/reports/custom", {
        "report_name": f"B7冒烟自定义报表_{int(time.time())}",
        "data_source": "energy", "dimension": "area",
    })
    cus = data_of(r)
    check("报表-自定义生成", r.get("code") == 0 and bool(cus.get("id")),
          f"名称={cus.get('report_name')}")

    # 记录列表
    r = call("GET", f"/reports/records?page=1&page_size=10&report_name={q('B7冒烟')}")
    check("报表-记录列表", r.get("code") == 0 and total_of(r) >= 1, f"总数={total_of(r)}")

    # 导出 Excel / PDF
    if gen_id:
        raw, ctype = call_raw("GET", f"/reports/records/{gen_id}/export?file_type=excel")
        check("报表-导出Excel", len(raw) > 500 and ctype.startswith("application/vnd.openxml"),
              f"字节={len(raw)} 类型={ctype}")
        raw, ctype = call_raw("GET", f"/reports/records/{gen_id}/export?file_type=pdf")
        check("报表-导出PDF", raw[:4] == b"%PDF" and ctype.startswith("application/pdf"),
              f"字节={len(raw)} 类型={ctype}")

    # 订阅列表
    r = call("GET", "/reports/subscriptions?page=1&page_size=10")
    subs = items_of(r)
    check("报表-订阅列表", r.get("code") == 0 and total_of(r) >= 1, f"总数={total_of(r)}")

    # 新增订阅 -> 立即执行 -> 校验推送
    r = call("GET", "/system/users?page=1&page_size=20")
    users = items_of(r)
    admin = next((u for u in users if u.get("username") == "admin"), {})
    r = call("GET", "/notify/channels?page=1&page_size=20")
    channels = items_of(r)
    ch_ids = [c["id"] for c in channels[:2]]

    sub_name = f"B7冒烟订阅_{int(time.time())}"
    r = call("POST", "/reports/subscriptions", {
        "template_id": tpl_id, "subscribe_name": sub_name, "cron_expr": "0 0 8 * * ?",
        "receivers": str(admin.get("id") or 1),
        "channel_ids": ",".join(str(c) for c in ch_ids),
        "enable_status": 1,
    })
    sub = data_of(r)
    sub_id = sub.get("id")
    check("报表-新增订阅", r.get("code") == 0 and bool(sub_id), f"名称={sub.get('subscribe_name')}")

    if sub_id:
        r = call("POST", f"/reports/subscriptions/{sub_id}/run", {})
        run = data_of(r)
        check("报表-立即执行订阅", r.get("code") == 0 and (run.get("receiver_count") or 0) >= 1,
              f"结果={run}")
        # 校验站内消息是否生成
        r = call("GET", f"/notify/messages?page=1&page_size=5&keyword={q('报表订阅')}")
        check("报表-订阅推送站内消息", total_of(r) >= 1, f"消息数={total_of(r)}")
        # 清理冒烟订阅
        rr = call("DELETE", f"/reports/subscriptions/{sub_id}")
        check("报表-删除订阅", rr.get("code") == 0)

    # ==================== 三、列表接口连通 ====================
    for name, path in [
        ("驾驶舱指标卡", "/dashboard/overview"),
        ("报表模板", "/reports/templates"),
        ("报表记录", "/reports/records?page=1&page_size=10"),
        ("报表订阅", "/reports/subscriptions?page=1&page_size=10"),
    ]:
        rr = call("GET", path)
        check(f"接口连通-{name}", rr.get("code") == 0)

    print("\n== 结果 ==", "全部通过" if ok_all else "存在失败")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
