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

## Automated Security

This project uses several layers of automated security scanning:

| Tool | What it does | Runs in |
|------|-------------|---------|
| **Dependabot** | Auto-creates PRs for vulnerable dependencies (Python, npm, GitHub Actions) | GitHub (weekly) |
| **`uv audit`** | Scans Python dependencies against the OSV vulnerability database | CI + `make security` |
| **Bandit** | Python static analysis — catches SQL injection, hardcoded secrets, shell injection | CI + `make security` |
| **`npm audit`** | Scans Node dependencies against the GitHub Advisory Database | CI + `make security` |

Run all security checks locally:

```bash
make security
```

## Best Practices for Contributors

- Never commit secrets or API keys — use environment variables
- Keep dependencies updated
- Validate and sanitize all user input at API boundaries
