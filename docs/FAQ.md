# Frequently Asked Questions

## Setup

### Q: I created a Feishu app but can't find it in the mobile app.
**A:** You need to **publish** the app first. Go to Feishu Open Platform → Your App → Version Management & Release → Create Version → Publish. After publishing, search the app name in Feishu mobile.

### Q: The bridge says "app_id is invalid" (error 1000040346).
**A:** Double-check that you copied the App ID correctly from Feishu Open Platform → Credentials & Basic Info. The App ID should start with `cli_`.

### Q: I enabled event subscription but `im.message.receive_v1` doesn't appear.
**A:** Make sure you've added the **Bot** capability first (App Capabilities → Bot). The IM message events are only available after enabling the bot.

### Q: Do I need to configure an HTTP callback URL?
**A:** No! Choose **"Use long connection to receive events"** (WebSocket mode), not the HTTP callback option. That's the whole point of this project — no public URL needed.

## Usage

### Q: What's the difference between Chat mode and Task mode?
**A:** See [README - Two Modes](#). In short:
- **Chat mode** (default): Quick Q&A, reply goes to Feishu. 5 min timeout.
- **Task mode** (`/run`): PC executes independently, saves files to disk. 15 min timeout.

### Q: Can multiple people use the bot?
**A:** By default, the **first person** who messages the bot is auto-whitelisted. You can allow multiple users by setting `FEISHU_ALLOWED_USERS=ou_id1,ou_id2` in `start_bridge.bat`.

### Q: How do I limit Claude Code's access for phone-initiated tasks?
**A:** Claude Code inherits your normal configuration. Add a `.claudeignore` file to exclude sensitive directories. Keep Claude Code permissions at the `default` level so destructive operations require confirmation.

### Q: The bridge crashes when my PC sleeps.
**A:** Yes — the bridge requires the PC to be awake and connected to the internet. Configure your PC to not sleep, or use Wake-on-LAN.

## Security

### Q: Is my App Secret safe?
**A:** The App Secret is stored only in your local `start_bridge.bat` file (which is gitignored). It is never transmitted except directly to Feishu's API over TLS. We recommend regenerating your App Secret periodically via the Feishu Open Platform.

### Q: Can people outside my company message my bot?
**A:** No. Feishu enterprise self-built apps are only visible to members of your Feishu enterprise organization.

### Q: What if I accidentally committed my credentials?
**A:** Immediately:
1. Regenerate App Secret on Feishu Open Platform
2. Use `git filter-branch` or delete and recreate the repo
3. Update your local `start_bridge.bat` with the new secret

## Troubleshooting

### Q: Messages are received but replies fail.
**A:** Check that `im:message:send_as_bot` permission is granted AND the app is published. Permission changes require re-publishing.

### Q: The bridge shows "processor not found" errors.
**A:** These are harmless. They mean Feishu sent events we don't handle (like `message_read_v1` read receipts). Only `im.message.receive_v1` matters for our use case.

### Q: Claude Code times out frequently.
**A:** Complex tasks take time. For chat mode (5 min timeout), simplify your question. For task mode (15 min timeout), break large tasks into smaller `/run` commands. You can increase timeouts by editing `CHAT_TIMEOUT` and `TASK_TIMEOUT` in `bridge.py`.

### Q: The WebSocket disconnects occasionally.
**A:** This is normal. The Feishu SDK has built-in auto-reconnect with exponential backoff. You'll see `reconnecting` in the logs — it recovers automatically.
