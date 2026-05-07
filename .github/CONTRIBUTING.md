# Contributing to lulzVM

First of all — **thank you** for taking the time to contribute! lulzVM is an open-source project built by the community. Every bug fix, improvement, translation or new feature makes the platform stronger for everyone.

> *"Feel free to modify whatever you want. Together we can build something really powerful."*

---

## Ways to Contribute

- **Bug reports** — Open an Issue describing what happened and how to reproduce it
- **Feature requests** — Open an Issue with the `enhancement` label
- **Code contributions** — Fork -> Branch -> PR (see workflow below)
- **Translations** — Add a new language to `static/app.js` i18n strings
- **Documentation** — Improve this README or add wiki pages

---

## Pull Request Workflow

1. **Fork** the repository on GitHub
2. **Clone** your fork locally: `git clone https://github.com/Bobbydelhi/lulzvm.git`
3. **Create a branch**: `git checkout -b fix/my-bugfix` or `feature/my-feature`
4. Make your changes and **test them locally** with `docker-compose up --build`
5. **Push** to your fork and **open a Pull Request** against `main`

### PR Checklist

- [ ] I tested my changes with `docker-compose up --build`
- [ ] My code does not introduce hardcoded credentials, personal data or external telemetry
- [ ] I did not add any backdoors, obfuscated code or malicious dependencies
- [ ] I described clearly what this PR does in the description

---

## Code Review & Safety

All Pull Requests are **reviewed by maintainers before merging**. This protects all users who clone the repository — nobody will ever get malicious code through a `git pull` without it being caught in review first.

**We never merge PRs that:**
- Add obfuscated or minified code without a clear explanation
- Pull in new npm/pip dependencies without justification
- Execute shell commands not related to VM/container management
- Contain any form of data exfiltration or tracking

---

## Code Style

- Python: follow PEP 8, use type hints, document public functions
- JavaScript: vanilla ES2020+, no external frameworks
- Keep files focused — one router per resource, one manager per domain

---

## Community Standards

Be respectful. We welcome contributors of all skill levels. See our [Code of Conduct](CODE_OF_CONDUCT.md).
