# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest (`main`) | Yes |

## Reporting a Vulnerability

**Please do NOT open a public GitHub Issue for security vulnerabilities.**

If you discover a security issue in lulzVM, please report it privately by:

1. Opening a [GitHub Security Advisory](https://github.com/Bobbydelhi/lulzvm/security/advisories/new)
2. Or emailing the maintainer directly (see GitHub profile)

Include in your report:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

We aim to respond within **72 hours** and release a patch within **7 days** for confirmed critical issues.

---

## Security Design Notes

lulzVM intentionally has **no authentication layer** — it is designed for deployment inside trusted private networks (home labs, isolated VLANs, private data centers).

**If you expose lulzVM on a public IP:**
- Put it behind a reverse proxy (e.g. Nginx or Caddy) with HTTP Basic Auth or OAuth2
- Use a firewall to restrict port 8006 to trusted IPs only
- Consider running it in a dedicated VLAN isolated from production traffic
