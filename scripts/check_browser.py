"""
检查浏览器前置条件：先通过 urllib 探测 CDP 端口确认 Chrome 已运行，
再通过 DrissionPage 检查标签页和登录状态。

检查项：
  1. Chrome 是否以远程调试模式运行（端口 5333）
  2. 是否存在「易照护服务平台」标签页
  3. 该标签页是否已登录（页面包含已登录态的特征元素）
  4. 必需文件是否存在（exe 程序、回访情况表、妙阖护士护理员信息）

输出 JSON 格式结果，exit code 含义：
  0 = 全部通过
  1 = 检查未通过（具体原因见 message 字段）
"""

import json
import os
import sys
import urllib.request
import urllib.error

CDP_PORT = 5333
CDP_URL = f"http://localhost:{CDP_PORT}/json"
USER_DATA_PATH = r"C://RPA//Chrome//User Data"
TAB_TITLE = "易照护服务平台"
LOGIN_INDICATOR = "tag:h1@@class=sidebar-title@@text():易照护平台"
LOGIN_OUT_INDICATOR = "tag:button@@text():重新登录"
REQUIRED_FILES = [
    {
        "path": r"C:\RPA\上海访护生成\上海访护生成.exe",
        "name": "上海访护生成.exe",
        "description": "RPA 自动化程序",
        "uploadable": False,
    },
    {
        "path": r"C:\RPA\回访\回访情况表.xlsx",
        "name": "回访情况表.xlsx",
        "description": "回访情况数据表，包含需要生成访视记录的回访数据",
        "uploadable": True,
    },
    {
        "path": r"C:\RPA\回访\妙阖护士护理员信息.xlsx",
        "name": "妙阖护士护理员信息.xlsx",
        "description": "护士护理员信息表，包含护士和护理员的基本信息",
        "uploadable": True,
    },
]


def build_result(chrome_running=False, tab_found=False, logged_in=None,
                 files_ok=False, tab_title="", tab_url="", message="",
                 missing_files=None):
    return {
        "chrome_running": chrome_running,
        "tab_found": tab_found,
        "logged_in": logged_in,
        "files_ok": files_ok,
        "tab_title": tab_title,
        "tab_url": tab_url,
        "message": message,
        "missing_files": missing_files or [],
    }


def output_and_exit(result, code):
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(code)


def main():
    # ── 检查 1：通过 urllib 探测 CDP 端口，确认 Chrome 已在运行 ──
    try:
        resp = urllib.request.urlopen(CDP_URL, timeout=1)
        tabs_json = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, ConnectionRefusedError, OSError):
        output_and_exit(build_result(
            message=(
                f"Chrome 未以远程调试模式运行，或端口 {CDP_PORT} 不可达。\n"
                "请确认 Chrome 已通过以下参数启动：\n"
                f'  --remote-debugging-port={CDP_PORT}\n'
                f'  --user-data-dir="{USER_DATA_PATH}"\n'
                "  --remote-allow-origins=*"
            )
        ), 1)

    # 在 CDP 返回的标签页列表中预检是否存在目标标签页
    has_target = any(
        TAB_TITLE in t.get("title", "")
        for t in tabs_json if t.get("type") == "page"
    )
    if not has_target:
        output_and_exit(build_result(
            chrome_running=True,
            message=f"未找到标题包含「{TAB_TITLE}」的标签页，请在 Chrome 中打开易照护服务平台。"
        ), 1)

    # ── 检查 2 & 3：通过 DrissionPage 连接已运行的 Chrome，检查标签页和登录状态 ──
    from DrissionPage import ChromiumOptions, Chromium

    co = ChromiumOptions().set_paths(local_port=CDP_PORT, user_data_path=USER_DATA_PATH)
    try:
        browser = Chromium(addr_or_opts=co)
    except Exception as e:
        output_and_exit(build_result(
            chrome_running=True,
            message=f"DrissionPage 连接 Chrome 失败：{e}"
        ), 1)

    try:
        tab = browser.get_tab(title=TAB_TITLE)
    except Exception:
        tab = None

    if not tab:
        output_and_exit(build_result(
            chrome_running=True,
            message=f"未找到标题为「{TAB_TITLE}」的标签页，请在 Chrome 中打开易照护服务平台。"
        ), 1)

    tab_title = tab.title
    tab_url = tab.url

    # ── 检查 3：检测登录状态 ──
    h = tab.ele(LOGIN_INDICATOR, timeout=0.5)
    h_out = tab.ele(LOGIN_OUT_INDICATOR, timeout=0.5)
    logged_in = bool(h) and not bool(h_out)

    if not logged_in:
        output_and_exit(build_result(
            chrome_running=True, tab_found=True,
            logged_in=False, tab_title=tab_title, tab_url=tab_url,
            message="易照护服务平台未登录（未检测到已登录特征元素），请先完成登录。"
        ), 1)
        
    # ── 检查 4：检查必需文件是否存在，区分可上传文件与系统文件 ──
    missing = []
    for f in REQUIRED_FILES:
        if not os.path.isfile(f["path"]):
            missing.append({
                "path": f["path"],
                "name": f["name"],
                "description": f["description"],
                "uploadable": f["uploadable"],
            })
    if missing:
        uploadable = [f for f in missing if f["uploadable"]]
        non_uploadable = [f for f in missing if not f["uploadable"]]
        parts = []
        if uploadable:
            names = "、".join(f"「{f['name']}」" for f in uploadable)
            parts.append(f"以下数据文件缺失，请上传：{names}")
        if non_uploadable:
            names = "、".join(f"「{f['name']}」" for f in non_uploadable)
            parts.append(f"以下系统文件缺失，请联系管理员部署：{names}")
        output_and_exit(build_result(
            chrome_running=True, tab_found=True,
            logged_in=True, tab_title=tab_title, tab_url=tab_url,
            message="；".join(parts),
            missing_files=missing,
        ), 1)

    # ── 全部通过 ──
    output_and_exit(build_result(
        chrome_running=True, tab_found=True,
        logged_in=True, files_ok=True, tab_title=tab_title, tab_url=tab_url,
        message="前置检查全部通过：Chrome 已运行、易照护标签页已打开、平台已登录、必需文件齐全。"
    ), 0)


if __name__ == "__main__":
    main()
