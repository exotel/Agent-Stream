# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT** open a public GitHub issue
2. Email the security team with details
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Security Best Practices

### API Keys

- **Never** commit API keys to the repository
- Use environment variables (`.env` file)
- Rotate keys regularly
- Use separate keys for development and production

```bash
# .env (never commit this file)
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...
EXOTEL_API_KEY=...
```

### WebSocket Security

- Use WSS (WebSocket Secure) in production
- Validate incoming connections
- Implement rate limiting
- Set appropriate timeouts

### Docker Security

- Run containers as non-root user
- Don't expose unnecessary ports
- Use secrets management for API keys
- Keep base images updated

### Audio Data

- Don't log raw audio data
- Don't store call recordings without consent
- Encrypt data in transit (TLS/SSL)
- Follow data retention policies

## Dependencies

- Regularly update dependencies: `npm audit`
- Review new dependencies before adding
- Use lockfiles (`package-lock.json`)

## Checklist for Deployment

- [ ] API keys stored in environment variables
- [ ] WSS enabled (not WS)
- [ ] Rate limiting configured
- [ ] Logging configured (no sensitive data)
- [ ] Health checks enabled
- [ ] Error handling doesn't expose internals
- [ ] Docker running as non-root
- [ ] Dependencies up to date

