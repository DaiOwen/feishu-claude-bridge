# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |

## Reporting a Vulnerability

**Do not open a public issue.** Instead, please:

1. Email the project maintainer directly
2. Provide a detailed description of the vulnerability
3. Include steps to reproduce if possible
4. Allow reasonable time for a fix before public disclosure

## Security Design

This project follows these security principles:

- **No credentials in code**: All secrets via environment variables
- **Auto-whitelist**: First user is locked in by default
- **Enterprise isolation**: Feishu self-built apps are only visible within your enterprise
- **No external dependencies beyond Feishu SDK**: Minimal attack surface
- **.gitignore**: Prevents accidental credential commits

## Known Limitations

- App credentials are stored in `start_bridge.bat` (local file). Keep this file private.
- The bridge has the same system permissions as the user running it.
- Feishu WebSocket uses TLS — ensure your system trusts Feishu's certificates.
