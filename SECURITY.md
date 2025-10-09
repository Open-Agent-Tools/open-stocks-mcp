# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Currently supported versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

We take the security of Open Stocks MCP seriously. If you discover a security vulnerability, please follow these steps:

### Where to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of these methods:

1. **GitHub Security Advisories** (Preferred)
   - Navigate to the [Security Advisories](https://github.com/Open-Agent-Tools/open-stocks-mcp/security/advisories) page
   - Click "Report a vulnerability"
   - Fill out the form with details about the vulnerability

2. **Direct Email**
   - If you prefer email, contact the maintainers directly
   - Include "SECURITY" in the subject line
   - Provide detailed information about the vulnerability

### What to Include

When reporting a vulnerability, please include:

- **Description**: Clear description of the vulnerability
- **Impact**: What can an attacker accomplish?
- **Reproduction**: Step-by-step instructions to reproduce the issue
- **Version**: Which version(s) are affected
- **Proof of Concept**: Code, screenshots, or other evidence (if available)
- **Suggested Fix**: If you have ideas for how to fix it (optional)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt within 48 hours
- **Assessment**: We will assess the vulnerability and determine severity
- **Updates**: We will keep you informed of progress toward a fix
- **Disclosure**: We will coordinate with you on public disclosure timing
- **Credit**: We will credit you in the security advisory (unless you prefer to remain anonymous)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Release**: Depends on severity and complexity
  - Critical: Within 7 days
  - High: Within 14 days
  - Medium: Within 30 days
  - Low: Next regular release

## Security Best Practices

When using Open Stocks MCP:

### API Keys and Authentication

- **Environment Variables**: Store all API keys and secrets in environment variables
- **Never Commit**: Never commit `.env` files or credentials to version control
- **Rotate Regularly**: Rotate API keys and passwords regularly
- **Broker Credentials**: Securely store Robinhood, Schwab, and other broker credentials
- **OAuth Tokens**: Handle OAuth tokens securely, use refresh tokens appropriately

### Network Security

- **HTTPS Only**: Always use HTTPS for API connections
- **Certificate Validation**: Verify SSL/TLS certificates
- **Rate Limiting**: Implement rate limiting to prevent abuse
- **Input Validation**: Validate all inputs to MCP tools

### Data Protection

- **Sensitive Data**: Never log sensitive data (passwords, API keys, account numbers)
- **Personal Information**: Handle PII in compliance with regulations
- **Financial Data**: Secure storage and transmission of financial information

## Security Updates

Security updates will be released as:

1. **Patch Releases**: For backward-compatible security fixes (0.1.x)
2. **GitHub Security Advisories**: Public disclosure after fix is available
3. **Release Notes**: Detailed information in CHANGELOG.md
4. **CVE**: We will request CVE numbers for significant vulnerabilities

## Contact

For questions about this security policy or other security-related matters:

- Open a discussion in [GitHub Discussions](https://github.com/Open-Agent-Tools/open-stocks-mcp/discussions) (for general questions)
- Use GitHub Security Advisories for vulnerability reports
- Check existing [Security Advisories](https://github.com/Open-Agent-Tools/open-stocks-mcp/security/advisories) for known issues

## Attribution

This security policy is based on best practices from the open source community and recommendations from the GitHub Security Lab.
