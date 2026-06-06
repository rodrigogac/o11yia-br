# Security Policy

O11yIA BR is an observability platform for AI-assisted development. Security and privacy are core concerns.

---

## Security goals

O11yIA BR is designed with these security and privacy goals:

✅ **Avoid collecting source code** — minimal risk of code exposure.  
✅ **Avoid collecting prompts or generated code** — minimal risk of intent/design exposure.  
✅ **Avoid collecting secrets or credentials** — reduce credential compromise risk.  
✅ **Minimize telemetry** — less data = less risk if compromised.  
✅ **Make collected fields explicit** — document what's collected and why.  
✅ **Support local/self-hosted deployment** — data stays on your infrastructure.  
✅ **Validate all inputs** — reject payloads with prohibited fields.  
✅ **Audit access and changes** — track who accessed what, when.  

---

## Reporting a vulnerability

**Do not open a public issue for security vulnerabilities.** Public disclosure can put users at risk.

**Instead:**

1. **Contact the maintainer privately:**
   - GitHub: [@rodrigogac](https://github.com/rodrigogac)
   - Email (if available): check GitHub profile

2. **Include:**
   - A clear description of the vulnerability.
   - Steps to reproduce (if applicable).
   - Impact assessment (who is affected, how severely).
   - A suggested fix (if you have one).

3. **Expect:**
   - Acknowledgment within 48 hours.
   - Updates on the fix timeline.
   - Credit in the fix commit (if desired).

---

## Current security posture

O11yIA BR is **early-stage** and **under active development**. Security features are being built progressively.

### ✅ Implemented

- API key authentication (`X-API-Key`, `X-Admin-Key` headers).
- Input validation (payload schema checks).
- CORS configuration (configurable allowed origins).
- Local deployment option (data stays on-premises).
- No remote analytics or telemetry to third parties (by default).
- Prohibited field detection (rejects code, prompts, secrets).

### ⚠️ Planned / Under review

- End-to-end encryption for collector → backend transmission.
- Database encryption at rest.
- Role-based access control (RBAC).
- Audit logging (comprehensive audit trail).
- Dependency scanning and supply chain security.
- Regular security reviews (internal and community).
- Threat model documentation.

---

## Security considerations for deployers

### Authentication

- **Always set strong API keys** in production. Avoid `dev-key-1`, `dev-key-2`.
- **Use environment variables** for secrets (never hardcode).
- **Rotate API keys periodically**.
- **Use separate keys for different environments** (dev, staging, prod).

### Network

- **Deploy behind a firewall** if handling sensitive data.
- **Use HTTPS in production** (TLS 1.2+).
- **Restrict CORS origins** to trusted domains only.
- **Disable public health checks** if needed (`/health` endpoint is public by default).

### Data storage

- **Keep SQLite database on encrypted storage** (if self-hosted).
- **Set appropriate file permissions** (read/write for app only).
- **Back up data regularly** and test recovery.
- **Implement data retention policies** (delete old metrics periodically).

### Collector deployment

- **VSCode extension**: Install only from trusted sources. Verify package signature if available.
- **Chrome extension**: Review permissions before installing.
- **IntelliJ plugin**: Install only from official sources.

---

## Areas for future security review

These items are planned for future security review and hardening:

- [ ] **API authentication** — rate limiting, IP whitelisting, token expiration.
- [ ] **Collector permissions** — minimal privilege principle for extensions.
- [ ] **Data minimization** — audit that only necessary fields are collected.
- [ ] **Secret redaction** — detect and redact accidental secrets in logs/errors.
- [ ] **Dashboard access control** — role-based access to views and data.
- [ ] **Storage encryption** — at-rest encryption for sensitive deployments.
- [ ] **Multi-tenant isolation** — secure separation if supporting multiple organizations.
- [ ] **Dependency scanning** — automated checks for vulnerable dependencies.
- [ ] **Supply chain security** — verification of third-party code, signed releases.
- [ ] **Incident response** — documented response plan for security incidents.
- [ ] **Penetration testing** — external security audit (after MVP).
- [ ] **Web Application Firewall (WAF)** considerations for cloud deployments.

---

## Privacy-first design (related to security)

Security and privacy are linked. Key privacy principles that inform security design:

- **No source code collection** (enforced by collector validation).
- **No prompt content collection** (enforced by setting defaults).
- **Aggregated metrics only** (per [PRIVACY.md](PRIVACY.md)).
- **User transparency** (users know what data is collected).
- **Data minimization** (collect only what's needed).

See [PRIVACY.md](PRIVACY.md) for the complete privacy model.

---

## Dependency security

O11yIA BR uses open-source dependencies. Security best practices:

- **Keep dependencies up to date** — run `pip install --upgrade` or `npm update` regularly.
- **Review critical updates** — read changelogs for breaking changes or security fixes.
- **Use lock files** — commit `requirements.txt` (Python) or `package-lock.json` (Node) for reproducible builds.
- **Scan for vulnerabilities** — use `pip-audit`, `npm audit`, or similar tools.

---

## Responsible disclosure

If you discover a non-vulnerability issue (missing docs, suboptimal code, etc.), feel free to:

- Open a public issue.
- Submit a PR with a fix.
- Mention it in a discussion.

---

## Security best practices for contributors

If you're contributing to O11yIA BR:

1. **No hardcoded secrets** — use environment variables or configuration files.
2. **Validate all inputs** — reject unexpected or malformed data.
3. **Log carefully** — avoid logging sensitive data (tokens, API keys, user input).
4. **Use HTTPS** — if adding external integrations, use secure connections.
5. **Test edge cases** — what if data is malicious? What if collectors go offline?
6. **Document security trade-offs** — explain why you chose security approach X over Y.

---

## Questions?

- **General security question?** Open an issue.
- **Security vulnerability?** Contact [@rodrigogac](https://github.com/rodrigogac) privately.
- **Privacy concern?** See [PRIVACY.md](PRIVACY.md) or contact privately.

---

**Last updated**: June 2026