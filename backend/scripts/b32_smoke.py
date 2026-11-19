"""B3-2 实时监控域冒烟测试。"""

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

    # 实时测点值
    r = call("GET", "/monitor/realtime")
    devices = r.get("data") or []
    check("实时数据列表", r.get("code") == 0 and len(devices) > 0, f"设备数={len(devices)}")
    first = devices[0] if devices else {}
    check("实时测点含值", bool(first.get("points")), f"设备={first.get('device_name')} 测点={len(first.get('points') or [])}")

    # 按设备过滤
    did = first.get("device_id")
    r = call("GET", f"/monitor/realtime?device_id={did}")
    check("实时数据按设备过滤", len(r.get("data") or []) == 1)

    # 实时曲线
    pid = (first.get("points") or [{}])[0].get("point_id")
    r = call("GET", f"/monitor/curve?point_id={pid}&hours=1")
    curve = r.get("data") or []
    check("实时曲线", r.get("code") == 0 and len(curve) > 5, f"点数={len(curve)}")

    # 组态图列表
    r = call("GET", "/monitor/topology?topo_type=topology&page_size=20")
    topos = (r.get("data") or {}).get("items") or []
    check("组态图列表", r.get("code") == 0 and len(topos) >= 2, f"数量={len(topos)}")

    # 组态图详情
    if topos:
        tid = topos[0]["id"]
        r = call("GET", f"/monitor/topology/{tid}")
        d = r.get("data") or {}
        nodes = d.get("nodes") or []
        check("组态图详情", r.get("code") == 0 and len(nodes) > 0, f"节点={len(nodes)}")
        check("节点含实时值", nodes[0].get("value") is not None if nodes else False,
              f"value={nodes[0].get('value') if nodes else None}")

    # 平面图列表
    r = call("GET", "/monitor/topology?topo_type=plan&page_size=20")
    plans = (r.get("data") or {}).get("items") or []
    check("平面图列表", r.get("code") == 0 and len(plans) >= 2, f"数量={len(plans)}")

    # 新建 -> 更新 -> 删除
    payload = {
        "topo_code": "TOPO_TEST_SMOKE",
        "topo_name": "冒烟测试组态",
        "topo_type": "topology",
        "remark": "smoke",
        "nodes": [
            {"node_key": "n1", "node_type": "device", "device_id": did, "point_id": pid,
             "pos_x": 60, "pos_y": 60, "width": 160, "height": 80, "style_json": {"color": "#2f7cf6"}},
            {"node_key": "n2", "node_type": "device", "device_id": did, "point_id": pid,
             "pos_x": 260, "pos_y": 60, "width": 160, "height": 80},
        ],
    }
    r = call("POST", "/monitor/topology", payload)
    new_id = (r.get("data") or {}).get("id")
    check("新建组态图", r.get("code") == 0 and bool(new_id), f"id={new_id}")

    if new_id:
        r = call("PUT", f"/monitor/topology/{new_id}", {"topo_name": "冒烟测试组态-改", "nodes": payload["nodes"][:1]})
        d = r.get("data") or {}
        check("保存组态图", r.get("code") == 0 and d.get("topo_name") == "冒烟测试组态-改" and len(d.get("nodes") or []) == 1)

        r = call("DELETE", f"/monitor/topology/{new_id}")
        check("删除组态图", r.get("code") == 0)
        r = call("GET", f"/monitor/topology/{new_id}")
        check("删除后不存在", r.get("code") not in (0,), f"code={r.get('code')}")

    print("\n== 结果 ==", "全部通过" if ok_all else "存在失败")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
