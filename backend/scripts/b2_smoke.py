"""B2 阶段接口冒烟测试：登录 -> 基础配置 CRUD -> 系统管理 -> 操作日志。"""

import json
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

    r = call("GET", "/config/dict-types?page=1&page_size=5")
    check("字典类型列表", r.get("code") == 0 and r["data"]["total"] > 0, f"total={r.get('data', {}).get('total')}")

    r = call("POST", "/config/dict-types", {"type_code": "smoke_test", "type_name": "冒烟测试", "status": 1})
    check("新增字典类型", r.get("code") == 0, r.get("message", r))
    new_id = r.get("data", {}).get("id") if r.get("code") == 0 else None

    if new_id:
        r = call("PUT", f"/config/dict-types/{new_id}", {"type_name": "冒烟测试-改"})
        check("编辑字典类型", r.get("code") == 0 and r["data"]["type_name"] == "冒烟测试-改",
              r.get("message", r))
        r = call("DELETE", f"/config/dict-types/{new_id}")
        check("删除字典类型", r.get("code") == 0, r.get("message", r))

    r = call("GET", "/config/carbon-factors?page=1&page_size=5")
    check("碳因子列表", r.get("code") == 0, f"total={r.get('data', {}).get('total')}")
    r = call("GET", "/config/device-types?page=1&page_size=5")
    check("设备类型列表", r.get("code") == 0, f"total={r.get('data', {}).get('total')}")
    r = call("GET", "/config/system-params")
    check("系统参数列表", r.get("code") == 0, f"total={len(r.get('data') or [])}")

    r = call("GET", "/system/users?page=1&page_size=5")
    check("用户列表", r.get("code") == 0 and r["data"]["total"] > 0,
          f"total={r.get('data', {}).get('total')}")

    r = call("GET", "/system/roles?page=1&page_size=5")
    check("角色列表", r.get("code") == 0, f"total={r.get('data', {}).get('total')}")

    r = call("GET", "/system/menus")
    check("权限菜单树", r.get("code") == 0 and len(r.get("data") or []) > 0)

    r = call("GET", "/system/oper-logs?page=1&page_size=5")
    check("操作日志（应含本脚本写操作）", r.get("code") == 0 and r["data"]["total"] > 0,
          f"total={r.get('data', {}).get('total')}")

    r = call("GET", "/system/login-logs?page=1&page_size=5")
    check("登录日志", r.get("code") == 0, f"total={r.get('data', {}).get('total')}")

    r = call("GET", "/system/profile")
    check("个人信息", r.get("code") == 0 and r["data"].get("username") == "admin")

    print("\n结果:", "全部通过" if ok_all else "存在失败项")


if __name__ == "__main__":
    main()
