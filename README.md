# Feishu Claude Bridge 🦅 ↔ 🤖

**在手机上用飞书操控你的电脑，让 Claude Code 随时执行你的想法。**

> 躺在床上想到一个点子 → 打开手机飞书 → 给机器人发消息 → Claude Code 在电脑上干活 → 结果回复到飞书

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)

---

## 目录

- [效果演示](#效果演示)
- [原理（一句话版）](#原理一句话版)
- [为什么不用别的方案](#为什么不用别的方案)
- [完整部署教程（手把手）](#完整部署教程手把手)
  - [Step 1：安装依赖](#step-1安装依赖)
  - [Step 2：创建飞书应用](#step-2创建飞书应用)
  - [Step 3：配置应用权限](#step-3配置应用权限)
  - [Step 4：开启事件订阅](#step-4开启事件订阅)
  - [Step 5：获取 App ID 和 App Secret](#step-5获取-app-id-和-app-secret)
  - [Step 6：发布应用](#step-6发布应用)
  - [Step 7：配置凭据并启动桥接](#step-7配置凭据并启动桥接)
  - [Step 8：手机飞书测试](#step-8手机飞书测试)
- [环境变量说明](#环境变量说明)
- [开机自启](#开机自启)
- [项目结构](#项目结构)
- [技术架构](#技术架构)
- [常见问题](#常见问题)

---

## 效果演示

```
手机飞书对话:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

你: 帮我写一个 Python 脚本，读取 data.csv，
    把销售额按月份汇总画成柱状图

机器人: [几秒后回复]
    这是脚本：
    
    import pandas as pd
    import matplotlib.pyplot as plt
    
    df = pd.read_csv('data.csv')
    monthly = df.groupby('month')['sales'].sum()
    
    plt.figure(figsize=(10, 6))
    monthly.plot(kind='bar')
    plt.title('Monthly Sales Summary')
    plt.tight_layout()
    plt.savefig('sales_chart.png')
    print('Chart saved as sales_chart.png')
    
    运行方式：python sales_chart.py

你: 改一下，饼图更好看，颜色用暖色调

机器人: [理解了上下文，知道在说刚才的脚本]
    已修改，将柱状图改为饼图...
    
    ```python
    ...
    plt.pie(monthly.values, labels=monthly.index,
            autopct='%1.1f%%', colors=['#FF6B6B','#FFA07A',
            '#FFD700','#FF8C69','#FF7F50'])
    ...
    ```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 原理（一句话版）

```
你的手机 ──发消息──▶ 飞书服务器 ──WebSocket──▶ 你电脑上的 bridge.py
                                                    │
                                         claude -p "你的问题"
                                                    │
你的手机 ◀──回复── 飞书服务器 ◀─── HTTP ─── 结果输出
```

- 电脑**主动连**飞书，不需要公网 IP
- 消息通过 WebSocket 长连接推送过来
- 调用 `claude -p` 处理（有完整文件系统 + 工具 + 记忆）
- 结果通过飞书 API 回复到手机

---

## 为什么不用别的方案

| 方案 | 问题 |
|------|------|
| SSH + Termius | 手机打字累，没有富文本，没有会话历史 |
| ngrok 内网穿透 | 免费版 URL 每次变，不稳定，有限速 |
| 云服务器中转 | 要花钱，要运维 |
| ChatGPT 网页版 | 没有文件系统，不能执行代码，没有上下文记忆 |
| 微信机器人 | 有封号风险，接口不官方 |

**本方案：免费、稳定、官方的飞书 API + Claude Code 完整能力。**

---

## 完整部署教程（手把手）

### 前置条件

- **Python 3.10+**（[下载](https://www.python.org/downloads/)）
- **Claude Code CLI** 已安装（[安装指南](https://docs.anthropic.com/en/docs/claude-code/overview)），终端输 `claude` 能进交互界面
- **飞书账号**（就是用飞书的手机号）
- **电脑保持开机**（桥接服务运行在电脑上）

---

### Step 1：安装依赖

```bash
# 克隆项目
git clone https://github.com/DaiOwen/feishu-claude-bridge.git
cd feishu-claude-bridge

# 安装 Python 依赖
pip install -r requirements.txt
```

---

### Step 2：创建飞书应用

> 飞书开放平台的界面偶尔会改版，但核心流程不变。如果按钮位置和描述不完全一致，找相似的关键词即可。

**2.1 登录飞书开放平台**

浏览器打开 https://open.feishu.cn ，用你的飞书账号登录。

**2.2 创建应用**

点击「创建应用」按钮：

![Step 2.2](https://img.shields.io/badge/操作-点击「创建应用」-blue)

1. 选择 **「企业自建应用」**（不是「应用商店应用」）
2. 填写：
   - **应用名称**：随便取，比如 `Claude 助手` 或 `我的电脑管家`
   - **应用描述**：随便写，比如 "手机远程操控电脑上的 Claude Code"
3. 点击「创建」

**2.3 添加机器人能力**

进入应用详情页后：

1. 左侧菜单找到「应用能力」（或叫「添加应用能力」）
2. 点击「**机器人**」→ 开启
3. 系统会提示配置机器人基本信息，直接用默认的就行

---

### Step 3：配置应用权限

> 这一步告诉飞书：我的机器人可以收发消息。

**3.1 进入权限管理**

左侧菜单 →「权限管理」

**3.2 搜索并开通两个权限**

| 权限名称 | 用途 | 操作 |
|----------|------|------|
| `im:message:send_as_bot` | 机器人发消息 | 搜索 → 点击开通 |
| `im:message:read` | 读取用户消息 | 搜索 → 点击开通 |

> **注意**：搜索时只输入关键词如 `im:message` 就能看到。找到后点击右侧的「开通权限」按钮。

开通后页面会显示这两条权限记录。

> **关于审核**：企业自建应用开通权限后，首次发布时需要管理员审核。如果你是企业管理员，自己就能审批通过。

---

### Step 4：开启事件订阅

> 这一步告诉飞书：有新消息时，通过 WebSocket 推送到我的电脑。

**4.1 进入事件订阅页面**

左侧菜单 →「事件与回调」→「事件订阅」

**4.2 启用事件订阅**

1. 打开「启用事件订阅」开关（右上角或顶部）
2. **订阅方式**选择「**使用长连接接收事件**」（默认就是，不用改）

   > ⚠️ 不要选「使用 HTTP 回调地址」！那个需要公网 IP。

3. 下方「事件」区域，点击「**添加事件**」按钮
4. 搜索框中输入 `im.message.receive_v1`
5. 勾选搜到的结果，点击确认添加

添加成功后，事件列表里会显示：

```
im.message.receive_v1   接收消息   已启用
```

4. 点击页面底部的「**保存**」按钮

---

### Step 5：获取 App ID 和 App Secret

> 这是飞书应用的"用户名"和"密码"，桥接脚本需要它们。

1. 左侧菜单 →「**凭据与基础信息**」
2. 你会看到：

```
App ID:     cli_a21xxxxxxxxxxxxxxxx
App Secret: ●●●●●●●●●●●●●●●●●●●●
```

3. 点击 App Secret 旁边的小眼睛图标 👁️ 显示完整值
4. **复制这两个值，保存好，后面要用**

---

### Step 6：发布应用

> 不发布的话，只有你自己在开发者后台能看到这个应用，手机上搜不到。

1. 左侧菜单 →「**版本管理与发布**」
2. 点击「**创建版本**」
3. 填写：
   - **版本号**：`1.0.0`
   - **更新说明**：`初始版本，实现消息收发`
4. 点击「保存」
5. 回到版本列表，找到刚创建的版本，点击「**申请发布**」或「发布」
6. 如果提示需要审批，联系你的飞书管理员通过一下（如果是你自己创建的企业，你就是管理员，自己去管理后台审批）

> 发布成功后，应用状态变为「已发布」。

---

### Step 7：配置凭据并启动桥接

**7.1 设置环境变量**

在终端（PowerShell 或 CMD）中执行：

```powershell
# PowerShell
$env:FEISHU_APP_ID="cli_你的AppID"
$env:FEISHU_APP_SECRET="你的AppSecret"
```

```bash
# Git Bash / Linux / macOS
export FEISHU_APP_ID="cli_你的AppID"
export FEISHU_APP_SECRET="你的AppSecret"
```

> 也可以直接编辑 `bridge.py` 第 22-23 行，把凭据写进去。但用环境变量更安全（不会不小心提交到 GitHub）。

**7.2 启动桥接**

```bash
cd feishu-claude-bridge
python bridge.py
```

**7.3 看到以下输出表示成功：**

```
============================================================
  Feishu <-> Claude Code Bridge
  Mode: WebSocket Long Connection (no public IP needed)
============================================================

[2026-06-14 01:06:47] [INIT] Claude CLI found at: D:\...\claude
[2026-06-14 01:06:47] [START] Bridge starting, waiting for Feishu messages...
[2026-06-14 01:06:47] [INIT] Working directory: C:\Users\你的用户名

[OK] Service started!
     Find your bot in Feishu mobile app and send a message.
     Press Ctrl+C to stop.

[Lark] [INFO] connected to wss://msg-frontier.feishu.cn/ws/v2?... [conn_id=...]
```

**关键行**：`connected to wss://msg-frontier.feishu.cn/...` — 说明 WebSocket 连接成功。

---

### Step 8：手机飞书测试

1. 打开**手机飞书 App**
2. 顶部搜索框输入你的应用名称（Step 2 填的那个名字，比如 "Claude 助手"）
3. 搜索结果显示「机器人」分类下会有你的应用
4. 点进去，发第一条消息：

```
1 + 1 等于几？
```

5. 等几秒，Claude Code 处理后回复到你的飞书

**如果收到回复，恭喜 🎉 部署完成！**

如果没收到回复，看 [常见问题](#常见问题)。

---

## 环境变量说明

| 变量 | 必需 | 说明 | 示例 |
|------|------|------|------|
| `FEISHU_APP_ID` | ✅ | 飞书应用 ID | `cli_aaa731b19xxx` |
| `FEISHU_APP_SECRET` | ✅ | 飞书应用密钥 | `5T2WV3tOxxx` |
| `FEISHU_ENCRYPT_KEY` | ❌ | 加密密钥（如果你在飞书配置了加密才需要） | 留空即可 |
| `FEISHU_VERIFICATION_TOKEN` | ❌ | 验证 Token（HTTP 模式需要，长连接不需要） | 留空即可 |
| `CLAUDE_PATH` | ❌ | Claude CLI 路径 | 自动检测，如果检测不到再设 |
| `CLAUDE_WORK_DIR` | ❌ | Claude Code 工作目录 | 默认用户主目录 |

---

## 开机自启

### Windows

创建文件 `C:\Users\你的用户名\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\feishu-bridge.bat`：

```bat
@echo off
set FEISHU_APP_ID=cli_你的AppID
set FEISHU_APP_SECRET=你的AppSecret
cd C:\path\to\feishu-claude-bridge
start /min python bridge.py
```

> 保存后，下次开机自动在后台启动。`start /min` 表示最小化窗口。

### macOS

```bash
# 创建 LaunchAgent 配置
cat > ~/Library/LaunchAgents/com.feishu.bridge.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.feishu.bridge</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/feishu-claude-bridge/bridge.py</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>FEISHU_APP_ID</key>
        <string>cli_你的AppID</string>
        <key>FEISHU_APP_SECRET</key>
        <string>你的AppSecret</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

# 加载
launchctl load ~/Library/LaunchAgents/com.feishu.bridge.plist
```

---

## 项目结构

```
feishu-claude-bridge/
├── README.md              # 👈 你正在看的这个文件
├── bridge.py              # 核心桥接脚本（~200 行）
├── requirements.txt       # Python 依赖（lark-oapi + requests）
├── setup.bat              # Windows 一键启动脚本
├── .env.example           # 环境变量配置示例
├── .gitignore             # Git 忽略规则（排除日志和密钥）
├── LICENSE                # MIT 开源协议
└── docs/
    └── architecture.md    # 技术架构详解（开发者看）
```

---

## 技术架构

### 通信流程

```
┌─────────────────────────────────────────────────────────┐
│                     手机飞书 App                          │
│  用户发消息: "帮我写个爬虫脚本"                             │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTPS POST
                      ▼
┌─────────────────────────────────────────────────────────┐
│                  飞书服务器集群                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │
│  │ IM 服务   │─▶│ 事件引擎  │─▶│ WebSocket 网关        │   │
│  │ 收消息    │  │ 匹配订阅  │  │ wss://msg-frontier   │   │
│  │          │  │          │  │ .feishu.cn/ws/v2     │   │
│  └──────────┘  └──────────┘  └──────────┬───────────┘   │
└──────────────────────────────────────────┼───────────────┘
                                           │ WSS 隧道 (TLS 1.3)
                                           │ 长连接，全双工
                                           ▼
┌──────────────────────────────────────────────────────────┐
│                     你的电脑 💻                            │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ bridge.py                                          │  │
│  │                                                    │  │
│  │  ① 收到 WebSocket 事件: im.message.receive_v1      │  │
│  │  ② 提取文本内容: "帮我写个爬虫脚本"                   │  │
│  │  ③ subprocess.run("claude -p '帮我写个爬虫脚本'")    │  │
│  │  ④ Claude Code: 写代码、读文件、执行命令...          │  │
│  │  ⑤ 获取 stdout 输出                                │  │
│  │  ⑥ POST /im/v1/messages → 回复到飞书               │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Claude Code CLI                                     │  │
│  │ • 完整文件系统访问      • 项目上下文感知              │  │
│  │ • 所有 Claude 工具     • 跨消息对话记忆              │  │
│  │ • 你的 MCP 工具        • 自定义指令 (CLAUDE.md)      │  │
│  └───────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### 为什么不需要公网 IP

传统方案（HTTP 回调）：

```
飞书服务器 ──HTTP POST──▶ 你的电脑
                ❌ 飞书找不到你的电脑（你在内网）
```

本方案（WebSocket 长连接）：

```
你的电脑 ──WebSocket──▶ 飞书服务器
                ✅ 你主动连飞书，飞书把消息推回来
```

就像你的电脑说：「飞书，我在这儿等着，有消息告诉我。」飞书说：「好，你等着。」——然后保持连接，有消息就推。

### 技术栈

```
bridge.py (Python)
├── lark-oapi SDK   →  飞书 WebSocket 长连接 + 事件分发
├── subprocess      →  调用 claude -p（管道模式）
├── requests        →  飞书 REST API（发回复、获取 token）
└── asyncio         →  异步事件循环（SDK 内部）
```

---

## 常见问题

### 收不到消息

<details>
<summary><b>点击展开排查步骤</b></summary>

1. **确认应用已发布**
   - 飞书开放平台 → 你的应用 → 版本管理与发布 → 状态是「已发布」？
   - 如果不是，点击「创建版本」→ 填写信息 → 申请发布

2. **确认事件订阅已开启**
   - 飞书开放平台 → 你的应用 → 事件与回调 → 事件订阅
   - 开关是打开的吗？
   - 订阅方式是不是「长连接」？
   - `im.message.receive_v1` 在事件列表中吗？

3. **确认权限已开通**
   - 飞书开放平台 → 你的应用 → 权限管理
   - `im:message:read` 状态是「已开通」？
   - `im:message:send_as_bot` 状态是「已开通」？

4. **确认桥接服务在运行**
   - 看终端有没有 `connected to wss://...` 这行
   - 看 `bridge.log` 有没有异常

5. **确认搜索方式**
   - 飞书手机 App 搜索应用名称
   - 在「机器人」分类下找
   - 如果搜不到，先搜一次然后在「聊天」列表里找历史记录
</details>

### 回复很慢或超时

<details>
<summary><b>点击展开</b></summary>

- Claude Code 处理复杂问题需要时间，尤其是涉及代码生成、文件操作时
- 默认超时 5 分钟，可修改 `bridge.py` 中的 `timeout=300`
- 如果频繁超时，把大问题拆成小问题发送
</details>

### WebSocket 断连了

<details>
<summary><b>点击展开</b></summary>

SDK 内置自动重连机制，无需手动处理。断连后会自动重试，重连间隔默认 120 秒。

日志中有 `reconnecting` 字样说明在重连中。
</details>

### 如何限制只有我能使用

<details>
<summary><b>点击展开</b></summary>

飞书企业自建应用默认只有你企业内的人能搜到。如果企业内有多人，可以在 `bridge.py` 的 `on_im_message_receive` 函数中加一个白名单：

```python
ALLOWED_USERS = {"ou_7d5c7..."}  # 你的 open_id

def on_im_message_receive(event):
    sender = event.event.sender
    open_id = sender.sender_id.open_id
    if open_id not in ALLOWED_USERS:
        return  # 忽略其他人的消息
```

你的 open_id 可以从日志中找到（`Reply sent -> open_id:ou_7d5c7...`）。
</details>

### 如何卸载

```bash
# 停止桥接服务
# 在运行 bridge.py 的终端按 Ctrl+C

# 飞书开放平台 → 你的应用 → 删除应用
# 删除项目文件夹
rm -rf feishu-claude-bridge
```

---

## License

MIT © 2024
