# Feishu Claude Bridge 🦅 ↔ 🤖

**在手机上用飞书操控你的电脑，让 Claude Code 随时执行你的想法。**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)

---

## 这是什么

一个轻量级桥接服务，把飞书机器人变成你的 **Claude Code 手机遥控器**。

```
你躺在床上 / 在地铁上 / 在星巴克
   │
   │  飞书发一条消息:
   │  "帮我写个爬虫抓取今天的新闻标题"
   │
   ▼
手机飞书 ──▶ 飞书服务器 ──WebSocket──▶ 你的电脑
                                          │
                                          │ claude -p "帮我写个..."
                                          ▼
手机飞书 ◀── 飞书服务器 ◀── 回复 ◀───  代码 + 解释
```

**你得到的不只是一个聊天机器人** —— 你远程操控的是运行在你电脑上的完整 Claude Code，它有文件系统、能写代码、能用浏览器、能操作你的工具。

---

## 为什么不用 MCP / ngrok / 公网服务器？

| 传统方案 | 痛点 | 本方案 |
|----------|------|--------|
| HTTP + ngrok 穿透 | URL 总变，不稳定，免费版限速 | WebSocket 长连接，电脑主动连飞书 |
| 公网服务器 | 要花钱，要运维 | 零成本，本地跑 |
| SSH 终端 | 手机打字累，无会话历史 | 飞书聊天界面，舒适 |

**一句话：电脑开机挂个脚本，全世界都能用飞书唤醒它。**

---

## 核心原理

### 通信模式：飞书「长连接」而非 HTTP 推送

飞书开放平台支持两种接收消息的方式：

| 方式 | 原理 | 是否需要公网 |
|------|------|-------------|
| HTTP 回调 | 飞书 POST 消息到你的 URL | **需要** |
| WebSocket 长连接 | 你主动连飞书，保持 TCP 隧道 | **不需要** ✅ |

本方案使用 WebSocket 长连接模式：

```
┌─────────────┐      WebSocket (你主动连飞书，不是飞书连你)
│  你的电脑    │ ──────────────────────────────▶ ┌──────────────┐
│  bridge.py  │ ◄────────────────────────────── │ 飞书 WS 网关  │
│              │     消息事件通过这条隧道推送过来    └──────┬───────┘
│  claude -p  │                                         │
│  处理消息    │                                    ┌────┴───────┐
│              │                                    │ 手机飞书    │
│  飞书 API    │ ────────── HTTP POST ──────────▶  └────────────┘
│  回复消息    │
└─────────────┘
```

1. `bridge.py` 用飞书 SDK 主动向飞书 WebSocket 网关发起连接
2. 连接建立后，维持一条全双工 TCP 隧道
3. 用户在手机飞书给机器人发消息 → 飞书服务器通过这条隧道推送事件
4. `bridge.py` 收到后调 `claude -p` 处理
5. 结果通过飞书 HTTP API 回复给用户

### 技术栈

```
bridge.py
├── lark-oapi SDK  ── 飞书 WebSocket 长连接 + 事件分发
├── subprocess     ── 调 claude -p (Claude Code CLI 管道模式)
├── requests       ── 飞书 REST API (发回复, 获取 token)
└── asyncio        ── 异步事件循环 (SDK 内部使用)
```

---

## 快速开始

### 前置条件

- Python 3.10+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) 已安装 (`claude` 命令可用)
- 飞书账号

### 第 1 步：创建飞书应用

1. 打开 [飞书开放平台](https://open.feishu.cn)
2. 创建 **企业自建应用**
3. 添加「**机器人**」能力
4. 权限管理 → 开通:
   - `im:message:send_as_bot` (发送消息)
   - `im:message:read` (读取消息)
5. 事件与回调 → 启用事件订阅 → 选择 **「使用长连接接收事件」**
6. 订阅事件 `im.message.receive_v1` (接收消息)
7. 版本管理与发布 → 创建版本 → **发布**

### 第 2 步：获取凭据

飞书开放平台 → 你的应用 → **凭据与基础信息**:
- 复制 **App ID** (`cli_xxx...`)
- 复制 **App Secret**

### 第 3 步：安装运行

```bash
# 克隆
git clone https://github.com/YOUR_USERNAME/feishu-claude-bridge.git
cd feishu-claude-bridge

# 安装依赖
pip install -r requirements.txt

# 配置凭据（二选一）
# 方式 A: 环境变量
export FEISHU_APP_ID="cli_xxxxxxxx"
export FEISHU_APP_SECRET="your_secret"

# 方式 B: 直接编辑 bridge.py 第 19-20 行
# APP_ID = "cli_xxxxxxxx"
# APP_SECRET = "your_secret"

# 启动
python bridge.py
```

看到 `connected to wss://msg-frontier.feishu.cn/ws/v2?...` 就是成功了。

### 第 4 步：在手机飞书测试

打开手机飞书 → 搜索你的应用名称 → 发消息：

```
帮我写一个 Python 脚本，把所有 markdown 文件合并成一个 PDF
```

---

## 配置选项

所有配置都在 `bridge.py` 顶部：

```python
APP_ID              # 飞书应用 ID
APP_SECRET          # 飞书应用密钥
ENCRYPT_KEY         # 加密密钥（如未开启加密则留空）
VERIFICATION_TOKEN  # 验证 Token（如未配置则留空）
WORK_DIR            # Claude Code 工作目录，默认用户主目录
CLAUDE_PATH         # claude 命令路径，默认用 PATH 中的
```

CLI 模式的 Claude Code 行为由你的正常 Claude Code 配置决定（`~/.claude/settings.json`），包括模型选择、权限等。

---

## 开机自启

### Windows

创建 `C:\Users\你的用户名\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\bridge.bat`:

```bat
@echo off
set FEISHU_APP_ID=cli_xxxxxxxx
set FEISHU_APP_SECRET=your_secret
start /min python C:\path\to\feishu-claude-bridge\bridge.py
```

### macOS / Linux

```bash
# 编辑 crontab
crontab -e

# 添加一行
@reboot cd /path/to/feishu-claude-bridge && FEISHU_APP_ID=xxx FEISHU_APP_SECRET=yyy python bridge.py &
```

---

## 安全须知

- **App Secret 是敏感信息**，不要提交到公开仓库（已加入 `.gitignore`）
- 飞书自建应用只在你自己的企业内可用，外部用户搜不到
- 所有消息经过飞书服务器中转，飞书本身有企业级安全认证
- 建议在 `bridge.py` 中加一个白名单：只回复特定用户的消息
- WebSocket 连接使用 TLS 加密

---

## 项目结构

```
feishu-claude-bridge/
├── README.md              # 本文件
├── bridge.py              # 核心桥接脚本
├── requirements.txt       # Python 依赖
├── setup.bat              # Windows 一键启动
├── .gitignore             # 忽略敏感文件
├── .env.example           # 环境变量示例
├── LICENSE                # MIT 协议
└── docs/
    └── architecture.md    # 技术架构详解
```

---

## 常见问题

<details>
<summary><b>收不到消息？</b></summary>

1. 确认应用已**发布**（版本管理与发布 → 创建版本 → 发布）
2. 确认事件订阅已开启，且选择「长连接」模式
3. 确认 `im.message.receive_v1` 事件已添加
4. 检查 `im:message:read` 权限是否开通
</details>

<details>
<summary><b>回复失败？</b></summary>

- 检查 `im:message:send_as_bot` 权限
- 查看 `bridge.log` 日志文件
</details>

<details>
<summary><b>Claude Code 处理很慢？</b></summary>

- 复杂问题需要几十秒到几分钟
- 默认超时 5 分钟，可修改 `bridge.py` 中 `timeout=300`
</details>

<details>
<summary><b>WebSocket 断连了？</b></summary>

SDK 自带自动重连机制，无需手动处理。
</details>

---

## License

MIT © 2024
