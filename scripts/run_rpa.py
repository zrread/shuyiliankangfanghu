"""
后台执行上海访护 RPA 程序，结果写入持久化文件。

本脚本采用异步模式：启动 exe 后立即退出，不阻塞等待执行完毕。
  1. 启动时写入 status=running（含 PID）到结果文件
  2. 以 DETACHED_PROCESS 启动 exe，立即退出

结果最终状态由 get_result.py 在查询时通过 PID 检测自动完成。

结果文件路径：C:\RPA\rpa_result.json
"""

import json
import subprocess
import sys
from datetime import datetime

EXE_PATH = r"C:\RPA\上海访护生成\上海访护生成.exe"
LOG_PATH = r"C:\RPA\rpa.log"
RESULT_PATH = r"C:\RPA\rpa_result.json"


def write_result(data):
    """将结果写入持久化 JSON 文件"""
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    started_at = now()

    # 写入"运行中"状态，Agent 启动后可立即确认任务已提交
    write_result({
        "status": "running",
        "started_at": started_at,
        "finished_at": None,
        "exit_code": None,
        "log_lines": None,
        "message": "RPA 程序正在执行中...",
    })
    print(f"[{started_at}] RPA 任务已启动，结果将写入 {RESULT_PATH}")
    sys.stdout.flush()

    # 执行 exe，不设超时，等待自然结束
    # 使用 DETACHED_PROCESS 脱离父进程组，避免父进程被杀时 exe 因管道断裂而退出
    try:
        proc = subprocess.Popen(
            [EXE_PATH, "--headless"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        pid = proc.pid
    except Exception as e:
        write_result({
            "status": "error",
            "started_at": started_at,
            "finished_at": now(),
            "pid": None,
            "exit_code": None,
            "log_lines": None,
            "message": f"启动 RPA 程序异常: {e}",
        })
        sys.exit(1)

    write_result({
        "status": "running",
        "started_at": started_at,
        "finished_at": None,
        "pid": pid,
        "exit_code": None,
        "log_lines": None,
        "message": f"RPA 程序已启动（PID: {pid}），正在后台执行...",
    })
    print(f"[{started_at}] RPA 进程已启动，PID={pid}，结果将写入 {RESULT_PATH}")
    sys.exit(0)


if __name__ == "__main__":
    main()
