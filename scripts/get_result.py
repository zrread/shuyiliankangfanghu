"""
查询上海访护 RPA 任务的执行结果。

读取 C:\RPA\rpa_result.json，输出当前任务状态。

查询逻辑：
  - status=running  → 通过 PID 检测进程是否存活：
      存活   → 直接返回 running 状态，不读日志
      已结束 → 将状态切换为 finished，写回文件，返回（不读日志）
  - status=finished → 若 log_lines 为空则读取 rpa.log 并写回，再展示结果
  - 其他状态        → 直接输出

输出 JSON 格式结果，exit code 含义：
  0 = 任务已完成（成功或失败，结果在 JSON 中）
  1 = 任务仍在运行中或结果文件不存在
"""

import ctypes
import json
import os
import sys
from datetime import datetime

RESULT_PATH = r"C:\RPA\rpa_result.json"
LOG_PATH = r"C:\RPA\rpa.log"


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_pid_running(pid):
    """通过 Windows API 检查 PID 进程是否仍在运行"""
    STILL_ACTIVE = 259
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    exit_code = ctypes.c_ulong(0)
    kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
    kernel32.CloseHandle(handle)
    return exit_code.value == STILL_ACTIVE


def read_log_tail(path, lines=2):
    """读取日志文件最后 N 行"""
    if not os.path.isfile(path):
        return None, "日志文件不存在"
    try:
        with open(path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        if not all_lines:
            return None, "日志文件为空"
        tail = [line.rstrip("\n\r") for line in all_lines[-lines:]]
        return tail, None
    except Exception as e:
        return None, f"读取日志文件异常: {e}"


def write_result(data):
    """将结果写回持久化 JSON 文件"""
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_feishu_card_summary(log_lines):
    """从日志行中提取飞书卡片 JSON 并转换为纯文本摘要"""
    if not log_lines:
        return None
    for line in log_lines:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            card = json.loads(line)
        except json.JSONDecodeError:
            continue
        parts = []
        header = card.get("header", {})
        title_content = header.get("title", {}).get("content", "")
        if title_content:
            parts.append(title_content)
        for elem in card.get("elements", []):
            if elem.get("tag") == "div":
                text_content = elem.get("text", {}).get("content", "")
                if text_content:
                    parts.append(text_content)
        if parts:
            return "\n\n".join(parts)
    return None


def main():
    try:
        with open(RESULT_PATH, "r", encoding="utf-8") as f:
            result = json.load(f)
    except FileNotFoundError:
        print(json.dumps({
            "status": "no_task",
            "message": "未找到任务结果文件，可能尚未执行过 RPA 任务。",
        }, ensure_ascii=False, indent=2))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "message": f"读取结果文件异常: {e}",
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    # ── 阶段一：running 状态只做 PID 存活检查，不读日志 ──
    if result.get("status") == "running":
        pid = result.get("pid")
        if pid and not is_pid_running(int(pid)):
            # 进程已结束，切换状态为 finished，不读日志
            result.update({
                "status": "finished",
                "finished_at": now(),
                "message": "RPA 程序执行完成，请再次查询以获取详细结果。",
            })
            write_result(result)
        # 无论是否刚切换，均直接返回当前状态，不读日志

    # ── 阶段二：finished 状态下补充读取日志（仅当 log_lines 尚未填充时）──
    elif result.get("status") == "finished" and not result.get("log_lines"):
        tail, err = read_log_tail(LOG_PATH)
        if err:
            result.update({
                "status": "warning",
                "message": f"RPA 程序已完成，但{err}。",
            })
        else:
            result["log_lines"] = tail
            result["message"] = "RPA 程序执行完成。"
        write_result(result)

    result["card_summary"] = extract_feishu_card_summary(result.get("log_lines"))
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("status") == "running":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
