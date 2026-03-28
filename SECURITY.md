# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public GitHub issue
2. Email the maintainers directly (or use GitHub's private vulnerability reporting)
3. Include steps to reproduce and the potential impact

We will acknowledge receipt within 48 hours and aim to release a fix within 7 days for critical issues.

## Scope

- API endpoint security
- Secret/credential exposure
- Injection vulnerabilities (SQL, XSS, command injection)
- Authentication/authorization bypasses

## Best Practices for Contributors

- Never commit secrets or API keys — use environment variables
- Keep dependencies updated
- Validate and sanitize all user input at API boundaries
