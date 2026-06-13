"""
Feishu <-> Claude Code Bridge (WebSocket Long Connection Mode)
===============================================================
Control your PC's Claude Code from your phone via Feishu.

No ngrok, no public IP, no server costs — just a Python script.

Usage:
  export FEISHU_APP_ID=cli_xxx
  export FEISHU_APP_SECRET=your_secret
  python bridge.py

Architecture:
  Phone Feishu -> Feishu Server -> WebSocket push -> bridge.py -> claude -p -> Reply
"""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import requests
from lark_oapi.ws import Client
from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
from lark_oapi.api.im.v1.model.p2_im_message_receive_v1 import P2ImMessageReceiveV1

# ====== Configuration ======

# Feishu App credentials (set via environment variables)
APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")

# Encrypt Key & Verification Token (leave empty if not configured)
ENCRYPT_KEY = os.environ.get("FEISHU_ENCRYPT_KEY", "")
VERIFICATION_TOKEN = os.environ.get("FEISHU_VERIFICATION_TOKEN", "")

# Working directory for Claude Code (defaults to user home)
WORK_DIR = os.environ.get("CLAUDE_WORK_DIR", str(Path.home()))

# Log file (alongside this script)
LOG_FILE = Path(__file__).parent / "bridge.log"


def find_claude() -> str:
    """Find claude CLI path. Checks env var first, then PATH."""
    # Check explicit path from environment
    explicit = os.environ.get("CLAUDE_PATH")
    if explicit and Path(explicit).exists():
        return explicit

    # Check common install locations
    candidates = [
        shutil.which("claude"),                    # PATH
        shutil.which("claude.cmd"),                # Windows
    ]
    for c in candidates:
        if c:
            return c

    raise FileNotFoundError(
        "claude CLI not found. Install Claude Code or set CLAUDE_PATH env var."
    )


CLAUDE_PATH: str = ""
""""Path to claude CLI, auto-detected at startup."""


def log(msg: str):
    """Write timestamped message to log file and console."""
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("ascii", errors="replace").decode("ascii"))
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_tenant_access_token() -> str:
    """Obtain Feishu tenant_access_token (valid 2 hours)."""
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
    else:
        log(f"Reply sent -> open_id:{open_id[:8]}...")


def call_claude(prompt: str) -> str:
    """Process a user prompt through Claude Code CLI pipe mode.

    Uses `claude -p` which reads the prompt as an argument and writes
    the response to stdout. This mode inherits the full Claude Code
    environment: model choice, MCP tools, file system access, project
    context, and conversation memory.
    """
    log(f"[PROCESS] {prompt[:80]}...")
    try:
        # shell=True is needed on Windows where claude is a .cmd script
        safe_prompt = prompt.replace('"', "'")
        result = subprocess.run(
            f'"{CLAUDE_PATH}" -p "{safe_prompt}"',
            capture_output=True,
            text=True,
            cwd=WORK_DIR,
            timeout=300,  # 5-minute timeout
            encoding="utf-8",
            shell=True,
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        if out:
            log(f"[OK] Reply: {len(out)} chars")
            return out
        if err:
            log(f"[WARN] stderr: {err[:200]}")
            return f"[Claude] {err[:800]}"
        return "[Claude] (no output)"
    except subprocess.TimeoutExpired:
        log("[TIMEOUT] Claude exceeded 5 minutes")
        return "[TIMEOUT] Processing took more than 5 minutes. Please simplify your question."
    except Exception as e:
        log(f"[ERR] {e}")
        return f"[ERR] {e}"


def on_im_message_receive(event: P2ImMessageReceiveV1):
    """Feishu event callback: fires when the bot receives a message.

    This is the core handler registered with the Feishu SDK's event
    dispatcher. It extracts the text content, calls Claude Code, and
    sends the response back.
    """
    try:
        evt = event.event
        if evt is None:
            return

        msg = evt.message
        if msg is None or msg.message_type != "text":
            return

        # Feishu sends message content as a JSON string: {"text": "..."}
        try:
            content = json.loads(msg.content)
            user_text = content.get("text", "").strip()
        except (json.JSONDecodeError, AttributeError):
            return

        if not user_text:
            return

        # Extract sender identity for reply routing
        sender = evt.sender
        open_id = sender.sender_id.open_id if sender and sender.sender_id else ""
        if not open_id:
            log("[WARN] Cannot determine sender open_id")
            return

        log(f"[RECV] {user_text[:80]}...")

        reply = call_claude(user_text)
        send_reply(open_id, reply)

    except Exception as e:
        log(f"[ERR] Message handler: {e}")


def main():
    global CLAUDE_PATH

    print("=" * 60)
    print("  Feishu <-> Claude Code Bridge")
    print("  Mode: WebSocket Long Connection (no public IP needed)")
    print("=" * 60)
    print()

    # Validate credentials
    if not APP_ID or not APP_SECRET:
        print("[ERROR] Missing credentials. Set environment variables:")
        print("  export FEISHU_APP_ID=cli_xxx")
        print("  export FEISHU_APP_SECRET=your_secret")
        print()
        print("Or edit bridge.py directly.")
        return

    # Find claude CLI
    try:
        CLAUDE_PATH = find_claude()
        log(f"[INIT] Claude CLI found at: {CLAUDE_PATH}")
    except FileNotFoundError as e:
        log(f"[FATAL] {e}")
        print(f"[ERROR] {e}")
        return

    # Build Feishu event handler: route im.message.receive_v1 to our callback
    handler = (
        EventDispatcherHandler.builder(
            encrypt_key=ENCRYPT_KEY,
            verification_token=VERIFICATION_TOKEN,
        )
        .register_p2_im_message_receive_v1(on_im_message_receive)
        .build()
    )

    # Create WebSocket client (auto-reconnect enabled by default)
    client = Client(
        app_id=APP_ID,
        app_secret=APP_SECRET,
        event_handler=handler,
    )

    log("[START] Bridge starting, waiting for Feishu messages...")
    log(f"[INIT] Working directory: {WORK_DIR}")
    print()
    print("[OK] Service started!")
    print("     Find your bot in Feishu mobile app and send a message.")
    print("     Press Ctrl+C to stop.")
    print()

    try:
        client.start()  # Blocks until interrupted
    except KeyboardInterrupt:
        log("[STOP] User stopped service")
        print("\nBye.")
    except Exception as e:
        log(f"[FATAL] Service crashed: {e}")
        raise


if __name__ == "__main__":
    main()
