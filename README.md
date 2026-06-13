<p align="center">
  <h1 align="center">🦅 飞书 Claude 桥接</h1>
  <p align="center">
    <strong>躺在手机上用飞书操控电脑上的 Claude Code，随时把想法变成现实。</strong>
    <br>
    不要公网 IP、不要服务器、不花一分钱，一个 Python 脚本搞定。
  </p>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
  <a href="#"><img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg" alt="Platform"></a>
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/version-1.0.0-green.svg" alt="Version"></a>
</p>

---

## 这是什么

你躺在床上，灵光一闪。抓起手机，打开飞书，给机器人发：

```
/run 写一个爬虫抓取今天的热搜，按热度排序保存为 CSV
```

几分钟后，手机响了：

```
完成。已创建:
  - feishu-tasks/20240614_103000/crawler.py  (爬虫脚本)
  - feishu-tasks/20240614_103000/hot.csv     (50 条数据)
```

**你的电脑替你干了活，而你全程没下床。**

这不止是一个聊天机器人。它直连你电脑上的 **Claude Code**——拥有完整文件系统、项目上下文、MCP 工具和持久记忆。

---

## 解决了什么问题

| 你想做的事 | 没有它 | 有了它 |
|---|---|---|
| 手机问 Claude 一个问题 | 打开电脑 → 等开机 → 打字 | 飞书发消息 → 几秒回复 |
| 通勤路上写段代码 | 忍着，到公司再说 | `/run` 下发任务，到了就有 |
| 处理数据、生成报表 | SSH + 终端 + 折腾 | 一条飞书消息 |
| 随时记录想法并落地 | 录音备忘，忘了 | 跟 Claude 聊，结果自动保存 |

**核心原理**：Claude Code 有个管道模式（`claude -p`），飞书有 WebSocket 长连接。把它们接起来，你的手机就变成了 Claude Code 遥控器。

---

## 5 分钟部署

### 你需要

- Python 3.10+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code/overview) 已装好
- 飞书账号（免费）

### 第 1 步：克隆安装

```bash
git clone https://github.com/DaiOwen/feishu-claude-bridge.git
cd feishu-claude-bridge
pip install -r requirements.txt
```

### 第 2 步：创建飞书应用（3 分钟）

1. 打开 [飞书开放平台](https://open.feishu.cn) → 创建「**企业自建应用**」
2. 添加「**机器人**」能力
3. 权限管理 → 开通 `im:message:send_as_bot` 和 `im:message:read`
4. 事件订阅 → 启用 → 选「**使用长连接接收事件**」→ 添加 `im.message.receive_v1`
5. 发布应用（版本管理与发布 → 创建版本 → 发布）

### 第 3 步：拿到凭据

飞书开放平台 → 你的应用 → **凭据与基础信息**：
- 复制 **App ID**（`cli_` 开头）
- 点击眼睛图标，复制 **App Secret**

### 第 4 步：启动

**Windows**（双击就行）:
```
把 start_bridge.example.bat 复制一份改名为 start_bridge.bat，
填上你的 App ID 和 App Secret，双击运行。
```

**macOS / Linux**（终端）:
```bash
export FEISHU_APP_ID="cli_xxxxxxxx"
export FEISHU_APP_SECRET="你的密钥"
python bridge.py
```

### 第 5 步：测试

手机飞书 → 搜索你的应用名 → 发：

```
你好，你是谁？
```

几秒内收到回复，搞定。

---

## 两种模式

### 💬 聊天模式（默认）

每条消息 Claude Code 处理后直接回复到飞书。适合问答、讨论、要代码片段。

```
你:  "Python 怎么高效读取 10GB 的 CSV 文件？"
机器人: [解释分块读取，推荐 polars，给出代码示例]
```

- **超时**：5 分钟
- **场景**：问答、代码审查、头脑风暴
- **电脑行为**：快速处理并回复

### ⚙️ 任务模式（`/run`）

手机下发任务，电脑独立执行，产出文件保存到本地目录。适合写脚本、处理数据、生成报告。

```
你:  "/run 把 data/ 下所有 CSV 合并去重，画趋势图，写分析报告"
机器人: "完成。feishu-tasks/20240614_143022/ 下创建了:
        - merged.csv (12万行)
        - trend.png (趋势图)
        - report.md (分析报告)
        - merge_and_analyze.py (脚本)"
```

- **超时**：15 分钟
- **场景**：写脚本、数据处理、报表生成
- **电脑行为**：独立执行，产出存到 `~/feishu-tasks/<时间戳>/`

### 命令一览

| 命令 | 作用 |
|------|------|
| `/help` | 显示使用说明和示例 |
| `/status` | 查看桥接状态、任务历史 |
| 其他任意文字 | 聊天模式 |

---

## 架构原理

```
┌─────────────────────────────────────────────────────────┐
│                      你的手机                            │
│  飞书 App: "/run 写个数据分析脚本"                        │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTPS
                      ▼
┌─────────────────────────────────────────────────────────┐
│                  飞书服务器集群                           │
│  IM 服务 → 事件引擎 → WebSocket 网关                     │
│  (wss://msg-frontier.feishu.cn/ws/v2)                  │
└─────────────────────┬───────────────────────────────────┘
                      │ WSS 加密隧道 (TLS 1.3，全双工)
                      │ 你的电脑主动连飞书，飞书把消息推回来
                      ▼
┌─────────────────────────────────────────────────────────┐
│                     你的电脑 💻                          │
│                                                         │
│  bridge.py                                              │
│  ├── lark-oapi SDK (WebSocket 客户端)                   │
│  ├── 事件分发: im.message.receive_v1                    │
│  ├── 消息路由: 聊天 or /run                              │
│  └── subprocess: claude -p "..."                        │
│                                                         │
│  Claude Code CLI                                        │
│  ├── 完整文件系统访问                                    │
│  ├── 项目上下文 & 记忆                                   │
│  ├── 所有 MCP 工具                                      │
│  └── 自定义指令 (CLAUDE.md)                              │
└─────────────────────────────────────────────────────────┘
```

**为什么不需要公网 IP**：传统的 webhook 是服务器主动调你（需要公网地址），而我们是你的电脑主动连飞书，保持长连接。飞书有消息就推过来。就像你打电话给飞书说「有事跟我说，我在线」，而不是让飞书满世界找你。

深入技术细节见 [docs/architecture.md](docs/architecture.md)。

---

## 配置说明

所有设置都是环境变量，在 `start_bridge.bat` 或终端里设：

| 变量 | 必须 | 默认值 | 说明 |
|------|------|--------|------|
| `FEISHU_APP_ID` | ✅ | — | 飞书开放平台获取 |
| `FEISHU_APP_SECRET` | ✅ | — | 飞书开放平台获取 |
| `FEISHU_ALLOWED_USERS` | — | (自动) | 多个 open_id 用逗号分隔。留空则自动白名单第一个用户 |
| `FEISHU_AUTO_WHITELIST` | — | `1` | 设为 `0` 关闭自动白名单 |
| `CLAUDE_PATH` | — | (自动检测) | `claude` 可执行文件路径 |
| `CLAUDE_WORK_DIR` | — | `$HOME` | Claude Code 工作目录 |
| `FEISHU_ENCRYPT_KEY` | — | (空) | 飞书配置了加密才需要 |
| `FEISHU_VERIFICATION_TOKEN` | — | (空) | 仅 HTTP 回调模式需要 |

---

## 安全保障

- **自动白名单**：第一个发消息的人自动锁定为唯一用户，无需手动配置
- **企业隔离**：飞书企业自建应用仅你的企业内可见
- **凭据无泄漏**：密钥用环境变量传递，含凭据的 `start_bridge.bat` 已 gitignore
- **传输加密**：所有通信走 TLS 1.3 加密

详见 [SECURITY.md](SECURITY.md)。

---

## 开机自启

### Windows

双击 `start_bridge.bat` 即可在独立窗口运行。开机自启：

1. `Win+R` → 输入 `shell:startup`
2. 把 `start_bridge.bat` **快捷方式**拖进去
3. 右键快捷方式 → 属性 → 运行方式：最小化

### macOS

```bash
# 编辑 ~/Library/LaunchAgents/com.feishu.bridge.plist
# 模板见 docs/architecture.md
launchctl load ~/Library/LaunchAgents/com.feishu.bridge.plist
```

### Linux

```bash
crontab -e
# 添加:
@reboot cd /path/to/feishu-claude-bridge && \
  FEISHU_APP_ID=xxx FEISHU_APP_SECRET=yyy python bridge.py &
```

---

## 常见问题

<details>
<summary><b>收不到消息怎么办？</b></summary>

1. 确认应用已**发布**（版本管理与发布 → 已发布）
2. 事件订阅是否选的「长连接」模式
3. `im.message.receive_v1` 事件是否已添加
4. `im:message:read` 权限是否已开通
</details>

<details>
<summary><b>多人能用吗？</b></summary>

可以。设 `FEISHU_ALLOWED_USERS=ou_xxx,ou_yyy` 白名单多个用户。留空则第一个发消息的人自动锁定。
</details>

<details>
<summary><b>Claude Code 有记忆吗？</b></summary>

管道模式每次调用是独立的，但 Claude Code 会维护项目上下文。需要多轮对话的话，在消息中包含关键上下文。
</details>

<details>
<summary><b>WebSocket 断连了？</b></summary>

SDK 自动重连，有指数退避机制。短暂断连你感知不到。
</details>

<details>
<summary><b>Lark（国际版飞书）能用吗？</b></summary>

能。代码中修改飞书 API 域名为 `open.larksuite.com` 即可。
</details>

更多见 [docs/FAQ.md](docs/FAQ.md)。

---

## 项目结构

```
feishu-claude-bridge/
├── bridge.py                          # 核心脚本（~300 行）
├── requirements.txt                   # Python 依赖
├── setup.bat                          # 一键安装
├── start_bridge.example.bat           # 启动模板（填好凭据就能用）
├── .env.example                       # 环境变量模板
├── README.md                          # 👈 本文件
├── CHANGELOG.md                       # 更新日志
├── CONTRIBUTING.md                    # 贡献指南
├── SECURITY.md                        # 安全策略
├── LICENSE                            # MIT 开源协议
├── docs/
│   ├── architecture.md                # 技术架构详解
│   └── FAQ.md                         # 常见问题
└── .github/
    ├── ISSUE_TEMPLATE/
    │   ├── bug_report.md              # Bug 提交模板
    │   └── feature_request.md         # 功能建议模板
    └── PULL_REQUEST_TEMPLATE.md       # PR 模板
```

---

## 参与贡献

欢迎提 Issue 和 PR！先看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解规范。

---

## 开源协议

MIT © 2024 — 详见 [LICENSE](LICENSE)

---

<p align="center">
  <sub>用 🦅 飞书 + 🤖 Claude Code 打造</sub>
</p>
