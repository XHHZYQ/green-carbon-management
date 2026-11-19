"""B5 能耗 / 电价与费用 / 碳排放 综合冒烟测试。

覆盖：
  1) 能耗域：总览 / 区域·分项·设备分析 / 分项占比 / 峰谷 / 排名 / 成本 / 导出
  2) 电价域：方案列表 / 时段列表 / 方案增改删 / 时段增改删 / 调整历史
  3) 费用域：分时·按月·按区域统计 / 环比同比分时对比 / 报表 / 导出
  4) 碳排域：总览 / 执行核算 / 排放明细 / 报告列表 / 生成报告 / 报告导出 / 减排对比

登录：admin / admin123
"""

import json
import urllib.error
import urllib.request
from datetime import date, timedelta

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
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return {"http_error": exc.code, "body": exc.read().decode()}


def fetch_raw(path: str):
    """请求导出接口，返回 (状态码, 内容类型, 字节数)。"""
    req = urllib.request.Request(BASE + path, method="GET")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read()
            return resp.status, resp.headers.get("Content-Type", ""), len(content)
    except urllib.error.HTTPError as exc:
        return exc.code, "", len(exc.read())


def _add_months(d: date, n: int) -> date:
    y, m = d.year, d.month + n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return date(y, m, 1)


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
    if not TOKEN:
        print("\n== 结果 == 登录失败，终止")
        return 1

    # ==================== 一、能耗域 ====================
    d = call("GET", "/energy/overview").get("data") or {}
    cards = d.get("cards") or {}
    check("能耗总览-卡片", cards.get("month_energy") is not None and cards.get("month_fee") is not None,
          f"本月能耗={cards.get('month_energy')} 本月费用={cards.get('month_fee')} 本月碳排={cards.get('month_carbon')}")
    check("能耗总览-趋势", len((d.get("trend") or {}).get("dates") or []) > 0,
          f"趋势点数={len((d.get('trend') or {}).get('dates') or [])}")
    check("能耗总览-类型构成", len(d.get("type_ratio") or []) > 0, f"类型数={len(d.get('type_ratio') or [])}")
    check("能耗总览-区域排名", len(d.get("area_rank") or []) > 0, f"区域数={len(d.get('area_rank') or [])}")

    for dim in ("area", "item", "device"):
        rr = call("GET", f"/energy/analysis?dim={dim}")
        rows = rr.get("data") or []
        check(f"能耗分析-{dim}", rr.get("code") == 0 and len(rows) > 0,
              f"条数={len(rows)} 首行={rows[0].get('name') if rows else None}")

    rr = call("GET", "/energy/item-ratio")
    check("分项计量占比", rr.get("code") == 0 and len(rr.get("data") or []) > 0, f"条数={len(rr.get('data') or [])}")

    rr = call("GET", "/energy/peak-valley")
    pv_rows = rr.get("data") or []
    check("峰谷用电分析", rr.get("code") == 0 and len(pv_rows) == 4,
          " ".join(f"{x.get('period_name')}={x.get('usage')}" for x in pv_rows))

    rr = call("GET", "/energy/rank?dim=device&limit=5")
    ranks = rr.get("data") or []
    check("能耗排名-设备", rr.get("code") == 0 and len(ranks) > 0 and ranks[0].get("rank") == 1,
          f"条数={len(ranks)} 第一={ranks[0].get('name') if ranks else None}")

    rr = call("GET", "/energy/cost?months=6")
    cost = rr.get("data") or {}
    check("能耗成本", rr.get("code") == 0 and len((cost.get("trend") or {}).get("months") or []) > 0
          and len(cost.get("period_fee") or []) == 4,
          f"月份数={len((cost.get('trend') or {}).get('months') or [])}")

    status, ctype, size = fetch_raw("/energy/export")
    check("能耗数据导出", status == 200 and "spreadsheet" in ctype and size > 1000,
          f"status={status} size={size}")

    # ==================== 二、电价域 ====================
    rr = call("GET", "/price/plans")
    plans = rr.get("data") or []
    check("电价方案列表", rr.get("code") == 0 and len(plans) >= 5,
          f"条数={len(plans)} 首行={plans[0].get('plan_name') if plans else None}")

    ele_plan = next((p for p in plans if (p.get("energy_type_name") == "电力")), None) or (plans[0] if plans else {})
    plan_id = ele_plan.get("id")
    rr = call("GET", f"/price/plans/{plan_id}/periods")
    periods = rr.get("data") or []
    check("时段划分列表", rr.get("code") == 0 and len(periods) > 0,
          f"方案={ele_plan.get('plan_name')} 时段数={len(periods)}")

    rr = call("GET", f"/price/plans/{plan_id}/history")
    check("电价调整历史", rr.get("code") == 0, f"条数={len(rr.get('data') or [])}")

    # 新增 -> 编辑 -> 增时段 -> 改时段 -> 删方案
    rr = call("POST", "/price/plans", {
        "plan_code": f"EP_TEST_{date.today():%Y%m%d}", "plan_name": "B5冒烟测试方案",
        "energy_type_id": ele_plan.get("energy_type_id"), "effective_date": f"{date.today():%Y-%m-%d}",
        "expire_date": None, "status": 1,
    })
    test_pid = (rr.get("data") or {}).get("id")
    check("新增电价方案", rr.get("code") == 0 and bool(test_pid), f"id={test_pid}")

    if test_pid:
        rr = call("PUT", f"/price/plans/{test_pid}", {"plan_name": "B5冒烟测试方案-已改"})
        check("编辑电价方案", rr.get("code") == 0 and (rr.get("data") or {}).get("plan_name") == "B5冒烟测试方案-已改")

        rr = call("POST", f"/price/plans/{test_pid}/periods", {
            "period_type": "peak", "start_time": "09:00", "end_time": "12:00",
            "day_type": "workday", "price": "1.0500", "sort_no": 1,
        })
        test_period_id = (rr.get("data") or {}).get("id")
        check("新增时段划分", rr.get("code") == 0 and bool(test_period_id), f"id={test_period_id}")

        if test_period_id:
            rr = call("PUT", f"/price/periods/{test_period_id}", {"price": "1.1000"})
            check("编辑时段划分", rr.get("code") == 0 and float((rr.get("data") or {}).get("price") or 0) == 1.1,
                  f"新价={(rr.get('data') or {}).get('price')}")
            rr = call("GET", f"/price/plans/{test_pid}/history")
            check("时段改价写入调整历史", rr.get("code") == 0 and len(rr.get("data") or []) > 0,
                  f"历史条数={len(rr.get('data') or [])}")
            rr = call("DELETE", f"/price/periods/{test_period_id}")
            check("删除时段划分", rr.get("code") == 0)

        rr = call("DELETE", f"/price/plans/{test_pid}")
        check("删除电价方案", rr.get("code") == 0)

    # ==================== 三、费用域 ====================
    for dim, expect in (("period", 4), ("month", None), ("area", None)):
        rr = call("GET", f"/fee/stat?dim={dim}")
        data = rr.get("data") or {}
        items = data.get("items") or []
        cond = rr.get("code") == 0 and len(items) > 0 and (data.get("summary") or {}).get("total_fee", 0) > 0
        if expect:
            cond = cond and len(items) == expect
        check(f"费用统计-{dim}", cond,
              f"条数={len(items)} 总费用={(data.get('summary') or {}).get('total_fee')}")

    rr = call("GET", "/fee/compare")
    cmp = rr.get("data") or {}
    check("费用对比（环比/同比/分时）",
          rr.get("code") == 0 and (cmp.get("current") or {}).get("fee") is not None
          and len(cmp.get("period_compare") or []) == 4,
          f"本月={((cmp.get('current') or {}).get('fee'))} 环比={((cmp.get('mom') or {}).get('rate'))}%")

    rr = call("GET", "/fee/report")
    rp = rr.get("data") or {}
    check("费用报表", rr.get("code") == 0 and len(rp.get("rows") or []) > 0,
          f"年份={rp.get('year')} 月份数={len(rp.get('rows') or [])} 总费用={(rp.get('summary') or {}).get('total_fee')}")

    status, ctype, size = fetch_raw("/fee/export")
    check("费用报表导出", status == 200 and "spreadsheet" in ctype and size > 500, f"status={status} size={size}")

    # ==================== 四、碳排域 ====================
    rr = call("GET", "/carbon/overview")
    ov = rr.get("data") or {}
    ocards = ov.get("cards") or {}
    check("碳排总览-卡片", rr.get("code") == 0 and ocards.get("total") is not None,
          f"年度={ocards.get('year')} 总排放={ocards.get('total')} 范围二={ocards.get('scope2')}")
    check("碳排总览-构成与趋势", len(ov.get("type_ratio") or []) > 0
          and len((ov.get("trend") or {}).get("months") or []) > 0,
          f"能源类型数={len(ov.get('type_ratio') or [])}")

    rr = call("POST", "/carbon/calc", {"period_type": "month"})
    check("执行碳排放核算", rr.get("code") == 0 and (rr.get("data") or {}).get("inserted", 0) > 0,
          f"写入={(rr.get('data') or {}).get('inserted')}")

    rr = call("GET", "/carbon/emissions?page=1&page_size=10")
    em = rr.get("data") or {}
    check("碳排放明细分页", rr.get("code") == 0 and (em.get("total") or 0) > 0 and len(em.get("items") or []) > 0,
          f"总数={em.get('total')} 本页={len(em.get('items') or [])}")

    rr = call("GET", "/carbon/reports?page=1&page_size=10")
    reps = rr.get("data") or {}
    check("碳报告列表", rr.get("code") == 0 and (reps.get("total") or 0) >= 3,
          f"总数={reps.get('total')}")

    today = date.today()
    start = _add_months(today.replace(day=1), -2)
    end = _add_months(today.replace(day=1), 0) - timedelta(days=1)
    rr = call("POST", "/carbon/reports", {
        "report_name": f"B5冒烟碳报告_{today:%Y%m%d}",
        "report_type": "monthly",
        "period_start": start.strftime("%Y-%m-%d"),
        "period_end": end.strftime("%Y-%m-%d"),
    })
    new_report_id = (rr.get("data") or {}).get("id")
    check("生成碳报告", rr.get("code") == 0 and bool(new_report_id),
          f"id={new_report_id} 总排放={(rr.get('data') or {}).get('total_emission')}")

    if new_report_id:
        status, ctype, size = fetch_raw(f"/carbon/reports/{new_report_id}/export")
        check("碳报告导出", status == 200 and "spreadsheet" in ctype and size > 500, f"status={status} size={size}")

    rr = call("GET", "/carbon/reduction-compare")
    rc = rr.get("data") or {}
    check("减排对比", rr.get("code") == 0 and rc.get("current_total") is not None
          and rc.get("pv_reduction") is not None,
          f"本年={rc.get('current_total')} 光伏减排={rc.get('pv_reduction')} 同比={rc.get('yoy_rate')}%")

    print("\n== 结果 ==", "全部通过" if ok_all else "存在失败")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
