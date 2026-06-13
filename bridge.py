"""
Feishu <-> Claude Code Bridge (WebSocket Long Connection Mode)
===============================================================
Control your PC's Claude Code from your phone via Feishu.

Two modes:
  Chat mode  (default)   - Phone asks, Claude answers, reply in Feishu.
                           Shared: both PC user and phone user talk to the
                           same Claude Code. Quick Q&A, code snippets, ideas.

  Task mode  (/run)      - Phone dispatches a task, PC executes it silently,
                           saves output to files. The PC works independently.
                           Code generation, file processing, report writing.

Usage:
  export FEISHU_APP_ID=cli_xxx
  export FEISHU_APP_SECRET=your_secret
  python bridge.py
"""

import json
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests
from lark_oapi.ws import Client
from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
from lark_oapi.api.im.v1.model.p2_im_message_receive_v1 import P2ImMessageReceiveV1

# ====== Configuration ======

APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
ENCRYPT_KEY = os.environ.get("FEISHU_ENCRYPT_KEY", "")
VERIFICATION_TOKEN = os.environ.get("FEISHU_VERIFICATION_TOKEN", "")

# User whitelist: comma-separated Feishu open_ids.
# If set, ONLY these users can use the bot. If empty, all enterprise
# members can message the bot (default for enterprise self-built apps).
# Find your open_id from bridge.log: look for "Reply sent -> open_id:ou_xxx..."
ALLOWED_USERS = os.environ.get("FEISHU_ALLOWED_USERS", "").split(",") if os.environ.get("FEISHU_ALLOWED_USERS") else []

# Working directory for Claude Code
WORK_DIR = os.environ.get("CLAUDE_WORK_DIR", str(Path.home()))

# Directory where task outputs are saved
TASK_OUTPUT_DIR = Path(WORK_DIR) / "feishu-tasks"

# Timeout in seconds: chat = short, task = long
CHAT_TIMEOUT = 300   # 5 min
TASK_TIMEOUT = 900   # 15 min

# Log file
LOG_FILE = Path(__file__).parent / "bridge.log"


def find_claude() -> str:
    """Find claude CLI path. Checks env var first, then PATH."""
    explicit = os.environ.get("CLAUDE_PATH")
    if explicit and Path(explicit).exists():
        return explicit
    candidates = [shutil.which("claude"), shutil.which("claude.cmd")]
    for c in candidates:
        if c:
            return c
    raise FileNotFoundError(
        "claude CLI not found. Install Claude Code or set CLAUDE_PATH env var."
    )


CLAUDE_PATH: str = ""


def log(msg: str):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("ascii", errors="replace").decode("ascii"))
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_tenant_access_token() -> str:
    resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Failed to get tenant access token: {data}")
    return data["tenant_access_token"]


def send_reply(open_id: str, text: str):
    """Send a text message back to the user via Feishu REST API."""
    token = get_tenant_access_token()
    content = json.dumps({"text": text}, ensure_ascii=False)
    resp = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages",
        params={"receive_id_type": "open_id"},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "receive_id": open_id,
            "msg_type": "text",
            "content": content,
        },
        timeout=15,
    )
    data = resp.json()
    if data.get("code") != 0:
        log(f"Reply failed: {data}")
        if data.get("code") == 230002:  # Message too long
            send_reply(open_id, text[:5000] + "\n\n... (truncated)")


def call_claude_chat(prompt: str) -> str:
    """
    Chat mode: quick question → answer in Feishu.

    PC and phone share the same Claude Code. The phone asks a question,
    Claude answers, and the reply appears in Feishu. Good for:
    - "帮我解释一下这个错误是什么意思"
    - "这段代码有什么问题"
    - "给我一个 Python 读取 CSV 的例子"
    """
    log(f"[CHAT] {prompt[:80]}...")
    try:
        safe_prompt = prompt.replace('"', "'")
        result = subprocess.run(
            f'"{CLAUDE_PATH}" -p "{safe_prompt}"',
            capture_output=True,
            text=True,
            cwd=WORK_DIR,
            timeout=CHAT_TIMEOUT,
            encoding="utf-8",
            shell=True,
        )
        out = result.stdout.strip()
        if out:
            log(f"[CHAT] Reply: {len(out)} chars")
            return out
        err = result.stderr.strip()
        if err:
            log(f"[CHAT] stderr: {err[:200]}")
            return f"[Claude] {err[:800]}"
        return "[Claude] (no output)"
    except subprocess.TimeoutExpired:
        log("[CHAT] Timeout")
        return "Chat mode timed out (5 min). For longer tasks, use /run prefix."
    except Exception as e:
        log(f"[CHAT] Error: {e}")
        return f"[ERR] {e}"


def call_claude_task(prompt: str) -> str:
    """
    Task mode: phone dispatches a job → PC executes → saves output to files.

    The PC works independently. Claude Code has full access to the file
    system, can write code, process data, generate reports. Results are
    saved to WORK_DIR/feishu-tasks/<timestamp>/. The phone gets a summary +
    file paths.

    Use when:
    - "/run 写一个爬虫抓取今天的热搜并保存到 hot.csv"
    - "/run 把 data/ 下所有 CSV 合并成一个大表，画趋势图"
    - "/run 检查 src/ 下所有 Python 文件的类型错误"

    The PC does the heavy lifting while you do other things.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_dir = TASK_OUTPUT_DIR / timestamp
    task_dir.mkdir(parents=True, exist_ok=True)

    log(f"[TASK] {prompt[:80]}... -> {task_dir}")

    # Build a prompt that tells Claude to save its work
    full_prompt = (
        f"{prompt}\n\n"
        f"Important: Save all generated files, code, and output to this directory: {task_dir}\n"
        f"After finishing, output a brief summary of what was done and list all created files."
    )

    try:
        safe_prompt = full_prompt.replace('"', "'")
        result = subprocess.run(
            f'"{CLAUDE_PATH}" -p "{safe_prompt}"',
            capture_output=True,
            text=True,
            cwd=WORK_DIR,
            timeout=TASK_TIMEOUT,
            encoding="utf-8",
            shell=True,
        )

        # Save the raw Claude output
        log_file = task_dir / "claude_output.txt"
        log_file.write_text(result.stdout + "\n\n--- stderr ---\n" + result.stderr,
                            encoding="utf-8")

        # List files actually created
        created_files = []
        for f in task_dir.rglob("*"):
            if f.is_file():
                created_files.append(str(f.relative_to(task_dir)))

        # Build summary for Feishu reply
        summary = result.stdout.strip()
        if not summary:
            summary = result.stderr.strip() or "(no output)"

        # Truncate long summaries for the chat reply
        if len(summary) > 2000:
            summary = summary[:2000] + "\n\n... (full output saved)"

        if created_files:
            file_list = "\n".join(f"  - {f}" for f in created_files)
            summary += f"\n\n---\nSaved files ({task_dir}):\n{file_list}"

        log(f"[TASK] Done: {len(created_files)} files -> {task_dir}")
        return summary

    except subprocess.TimeoutExpired:
        log("[TASK] Timeout")
        return (
            f"Task timed out (15 min). Try breaking it into smaller steps.\n"
            f"Partial output may be in: {task_dir}"
        )
    except Exception as e:
        log(f"[TASK] Error: {e}")
        return f"[ERR] {e}"


def route_message(user_text: str) -> tuple[str, str]:
    """
    Route a message to the appropriate handler based on content.

    Returns (mode, reply_text).

    Modes:
      - "chat"  : normal question-answer, quick response
      - "task"  : PC executes independently, saves files
      - "help"  : show available commands
      - "status": show bridge status
    """
    text = user_text.strip()

    # -- Task mode: /run or /task prefix --
    if text.lower().startswith("/run ") or text.lower().startswith("/task "):
        task_prompt = text.split(" ", 1)[1].strip()
        if not task_prompt:
            return ("help", "Usage: /run <your task>\nExample: /run write a script to analyze data.csv")
        return ("task", call_claude_task(task_prompt))

    # -- Help --
    if text.lower() in ("/help", "/?", "help", "帮助", "使用帮助"):
        return ("help", HELP_TEXT)

    # -- Status --
    if text.lower() in ("/status", "/state", "状态", "运行状态"):
        return ("status", get_status())

    # -- Default: Chat mode --
    return ("chat", call_claude_chat(text))


HELP_TEXT = """
Feishu Claude Bridge - 使用说明

两种模式：

1. 聊天模式（默认）
   直接发消息，Claude 回答后回复到飞书。
   适合：问问题、要代码片段、讨论想法
   示例： "这段代码有什么问题？"
        "Python 里怎么读取 Excel？"

2. 任务模式 /run
   电脑独立执行任务，产出文件保存到本地。
   适合：写脚本、处理数据、生成报告
   示例： "/run 写一个爬虫抓取今日热搜并存为 hot.csv"
        "/run 把 data/ 下所有 CSV 合并画趋势图"

3. 其他命令
   /help   - 显示此帮助
   /status - 查看桥接运行状态
"""


def get_status() -> str:
    """Return a one-line status summary."""
    task_count = 0
    if TASK_OUTPUT_DIR.exists():
        task_count = len(list(TASK_OUTPUT_DIR.iterdir()))
    return (
        f"Bridge: Running\n"
        f"Work dir: {WORK_DIR}\n"
        f"Task history: {task_count} completed\n"
        f"Chat timeout: {CHAT_TIMEOUT // 60} min | Task timeout: {TASK_TIMEOUT // 60} min"
    )


def on_im_message_receive(event: P2ImMessageReceiveV1):
    """Feishu event callback: fires when the bot receives a message."""
    try:
        evt = event.event
        if evt is None:
            return

        msg = evt.message
        if msg is None or msg.message_type != "text":
            return

        try:
            content = json.loads(msg.content)
            user_text = content.get("text", "").strip()
        except (json.JSONDecodeError, AttributeError):
            return

        if not user_text:
            return

        sender = evt.sender
        open_id = sender.sender_id.open_id if sender and sender.sender_id else ""
        if not open_id:
            return

        # Whitelist check
        if ALLOWED_USERS and open_id not in ALLOWED_USERS:
            log(f"[BLOCK] Unauthorized open_id: {open_id}")
            send_reply(open_id, "Sorry, you are not authorized to use this bot.")
            return

        log(f"[RECV] {user_text[:80]}...")

        mode, reply = route_message(user_text)
        log(f"[DISPATCH] mode={mode}")
        send_reply(open_id, reply)

    except Exception as e:
        log(f"[ERR] Message handler: {e}")


def main():
    global CLAUDE_PATH

    print("=" * 60)
    print("  Feishu <-> Claude Code Bridge")
    print("  Chat (default) + Task (/run) dual-mode")
    print("=" * 60)
    print()

    if not APP_ID or not APP_SECRET:
        print("[ERROR] Missing credentials:")
        print("  export FEISHU_APP_ID=cli_xxx")
        print("  export FEISHU_APP_SECRET=your_secret")
        return

    try:
        CLAUDE_PATH = find_claude()
        log(f"[INIT] Claude: {CLAUDE_PATH}")
    except FileNotFoundError as e:
        log(f"[FATAL] {e}")
        return

    # Ensure task output directory exists
    TASK_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    handler = (
        EventDispatcherHandler.builder(
            encrypt_key=ENCRYPT_KEY,
            verification_token=VERIFICATION_TOKEN,
        )
        .register_p2_im_message_receive_v1(on_im_message_receive)
        .build()
    )

    client = Client(
        app_id=APP_ID,
        app_secret=APP_SECRET,
        event_handler=handler,
    )

    log("[START] Bridge starting (chat + task modes)...")
    log(f"[INIT] Work dir: {WORK_DIR}")
    log(f"[INIT] Task output: {TASK_OUTPUT_DIR}")
    print()
    print("[OK] Service started! Two modes available:")
    print("     Chat   - Just type your question")
    print("     Task   - Prefix with /run <task>")
    print("     /help  - Show usage guide")
    print("     Press Ctrl+C to stop.")
    print()

    try:
        client.start()
    except KeyboardInterrupt:
        log("[STOP] User stopped service")
        print("\nBye.")
    except Exception as e:
        log(f"[FATAL] {e}")
        raise


if __name__ == "__main__":
    main()
