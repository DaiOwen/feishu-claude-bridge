# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-06-14

### Added
- Core bridge service with Feishu WebSocket long-connection mode
- Dual-mode operation: Chat (default) and Task (`/run` prefix)
- Auto-whitelist: first user who messages the bot is automatically locked in
- User whitelist support via `FEISHU_ALLOWED_USERS` environment variable
- `/help` and `/status` commands for runtime guidance
- Windows one-click launcher (`start_bridge.bat`)
- Claude Code CLI auto-detection (PATH + common install locations)
- Automatic WebSocket reconnection with exponential backoff
- Task output directory (`feishu-tasks/<timestamp>/`) for `/run` mode
- Comprehensive README with step-by-step Feishu app setup guide
- Technical architecture documentation in `docs/architecture.md`
- Security policy (`SECURITY.md`)
- MIT License
