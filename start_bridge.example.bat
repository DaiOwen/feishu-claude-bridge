@echo off
chcp 65001 >nul
title Feishu Claude Bridge

REM Replace with your own credentials from https://open.feishu.cn
set FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
set FEISHU_APP_SECRET=your_secret_here

cd /d C:\path\to\feishu-claude-bridge

echo Starting Feishu Claude Bridge...
echo Chat: send any message | Task: /run <task> | Help: /help
echo.

python bridge.py

pause
