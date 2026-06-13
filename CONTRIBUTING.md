# Contributing to Feishu Claude Bridge

Thanks for your interest in contributing!

## How to Contribute

### Reporting Bugs

1. Check [existing issues](https://github.com/DaiOwen/feishu-claude-bridge/issues) first
2. Use the Bug Report template
3. Include: OS, Python version, Claude Code version, error messages, steps to reproduce

### Suggesting Features

1. Use the Feature Request template
2. Describe the problem you're solving
3. Explain how the feature would work

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Test thoroughly
5. Commit with descriptive messages
6. Push and open a PR against `main`

### Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/feishu-claude-bridge.git
cd feishu-claude-bridge
pip install -r requirements.txt

# Create a test Feishu app (see README)
# Set environment variables
export FEISHU_APP_ID=cli_test_xxx
export FEISHU_APP_SECRET=test_secret

# Run
python bridge.py
```

### Code Style

- Python 3.10+ compatible
- Follow PEP 8
- Type hints appreciated but not required
- Docstrings for public functions
- Keep `bridge.py` under 500 lines

### Testing

Before submitting a PR:
1. Verify the bridge starts without errors
2. Test message receiving (send a message from Feishu)
3. Test both Chat mode and `/run` mode
4. Test `/help` and `/status` commands
5. Check that logs are clean (no unexpected errors)

## Project Structure

```
feishu-claude-bridge/
├── bridge.py              # Main script — start here
├── requirements.txt       # Python dependencies
├── start_bridge.bat       # Windows launcher (gitignored, has creds)
├── start_bridge.example.bat  # Example launcher template
├── setup.bat              # Quick setup script
├── .env.example           # Environment variables template
├── README.md              # User-facing documentation
├── CHANGELOG.md           # Release history
├── SECURITY.md            # Security policy
├── LICENSE                # MIT License
├── docs/
│   ├── architecture.md    # Technical deep dive
│   └── FAQ.md             # Frequently asked questions
└── .github/
    ├── ISSUE_TEMPLATE/
    │   ├── bug_report.md
    │   └── feature_request.md
    └── PULL_REQUEST_TEMPLATE.md
```

## Recognition

All contributors will be listed in the README. Significant contributions may be mentioned in release notes.
