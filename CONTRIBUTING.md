# Contributing to O11yIA BR

Thank you for your interest in contributing to O11yIA BR!

O11yIA BR is an early-stage, open-source project focused on observability and governance for AI-assisted development teams. We welcome all kinds of contributions.

---

## Ways to contribute

- **Improve documentation** — fix typos, expand guides, add examples.
- **Suggest metrics** — propose new usage metrics or aggregation strategies.
- **Build collectors** — create or improve collectors for VSCode, Chrome, IntelliJ, or other tools.
- **Improve backend** — add features to the FastAPI backend, improve performance, optimize queries.
- **Improve dashboard** — enhance the Streamlit UI, add visualizations, improve usability.
- **Add tests** — write unit tests, integration tests, or end-to-end tests.
- **Report bugs** — open issues with clear reproduction steps.
- **Security review** — review privacy and security assumptions, suggest improvements.
- **Suggest integrations** — propose integrations with other tools or platforms.

---

## Core contribution principles

Before you start coding, understand O11yIA BR's core principles:

### 1. Privacy is non-negotiable

- **Do not collect source code.**
- **Do not collect prompts or generated code.**
- **Do not collect secrets, credentials, or private files.**
- Prefer **aggregated metrics over individual events**.
- Every new telemetry field **must be explicitly justified and documented**.
- See [PRIVACY.md](PRIVACY.md) for the complete privacy model.

### 2. Transparency in telemetry

- All collected fields must be documented in code and in [PRIVACY.md](PRIVACY.md).
- If a new feature collects data, **update PRIVACY.md** in the same PR.
- Collectors should have **clear configuration** for what is collected.

### 3. Honesty in claims

- Do not claim features that don't exist yet.
- Mark work-in-progress as "planned" or "experimental".
- Test locally before opening a PR.
- Report test results honestly (pass/fail/unclear).

---

## Before opening a PR

1. **Check the [ROADMAP.md](ROADMAP.md)** — is your feature already planned?
2. **Open an issue first** (if not already open) — discuss the change before writing code.
3. **Review [PRIVACY.md](PRIVACY.md) and [SECURITY.md](SECURITY.md)** — understand the constraints.
4. **Run tests locally** — make sure nothing breaks.

---

## Pull request workflow

### Step 1: Fork and branch

```bash
git clone https://github.com/rodrigogac/o11yia-br.git
cd o11yia-br
git checkout -b feature/your-feature-name
```

### Step 2: Make your changes

- Follow the existing code style.
- Add tests for new functionality.
- Update documentation (README, docstrings, etc.).
- Update [PRIVACY.md](PRIVACY.md) if new data is collected.

### Step 3: Test locally

**Backend tests:**
```bash
cd server
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -v
```

**Docker test:**
```bash
docker compose up --build
# Test manually or run integration tests
docker compose down
```

**Collectors:**
- VSCode extension: Press F5 in Extension Development Host, test functionality.
- Chrome extension: Load unpacked in `chrome://extensions/`, test.
- IntelliJ: Build and install locally, test.

### Step 4: Open a PR

Use the [pull request template](.github/pull_request_template.md):

- **Summary**: What changed and why?
- **Privacy impact**: Does this collect any new data?
- **Security impact**: Does this affect authentication, storage, or telemetry?
- **Checklist**: Confirm you didn't add source-code collection, prompts collection, or secret collection.

### Step 5: Review and merge

- Address feedback from maintainers.
- Be prepared to refine privacy/security aspects.
- Once approved, your PR will be merged.

---

## Issue templates

We provide templates to streamline issue creation:

- **Bug report** (`.github/ISSUE_TEMPLATE/bug_report.md`)
- **Feature request** (`.github/ISSUE_TEMPLATE/feature_request.md`)
- **Collector request** (`.github/ISSUE_TEMPLATE/collector_request.md`)

Use the appropriate template when opening an issue.

---

## Code style and standards

### Python (FastAPI backend)

- Use **PEP 8** style.
- Type hints are required.
- Docstrings for public functions.
- Format with `black` (if available).
- Linting with `pylint` or `ruff` (if available).

### TypeScript/JavaScript (VSCode extension, Chrome)

- Use **ESLint** configuration (if provided).
- Prefer `const` over `let`, and `let` over `var`.
- Add JSDoc comments for public functions.
- Test in actual VS Code and Chrome environments.

### Gradle/Kotlin (IntelliJ plugin)

- Follow **Kotlin conventions**.
- Use IDE plugin SDK conventions.
- Test in actual IntelliJ IDEA environment.

---

## Testing expectations

**New features should include tests:**

- Unit tests for business logic (calculations, aggregations).
- Integration tests for API endpoints.
- End-to-end tests for collector → backend → dashboard flow.

**Test coverage target**: 70%+ for critical paths.

If you're unsure how to test something, ask in the PR or issue.

---

## Documentation

**Every new feature should include:**

- Docstring/inline comments explaining **what** it does and **why**.
- README or guide update (if user-facing).
- [PRIVACY.md](PRIVACY.md) update (if new data is collected).
- Example or screenshot (if UI-related).

**Good documentation makes contributions more likely to be merged.**

---

## Security and privacy checklist

Before submitting a PR, confirm:

- [ ] No source code collection added.
- [ ] No prompt or generated code collection added.
- [ ] No secret/credential collection added.
- [ ] New fields are documented in code.
- [ ] [PRIVACY.md](PRIVACY.md) is updated if needed.
- [ ] [SECURITY.md](SECURITY.md) is updated if needed.
- [ ] No API keys, credentials, or sensitive values hardcoded.
- [ ] All external dependencies are from trusted sources.

---

## Community guidelines

- Be respectful and constructive.
- Assume good intent.
- Provide constructive feedback.
- Help others if you can.
- Report concerns to the maintainer privately if needed.

---

## Getting help

- **Questions about a feature?** Open an issue.
- **Need help setting up?** Check README and see if there's a guide.
- **Stuck on implementation?** Ask in a draft PR or discussion.
- **Privacy/security concern?** Contact [@rodrigogac](https://github.com/rodrigogac) privately.

---

## Recognition

Contributors are recognized in:

- Git commit history (with your name/email).
- Release notes for significant contributions.
- [CONTRIBUTORS.md](CONTRIBUTORS.md) (planned).

---

## Thank you!

Every contribution helps O11yIA BR grow. We appreciate your time and effort, whether it's a small fix, a major feature, or thoughtful feedback.

Happy coding! 🚀

---

**Last updated**: June 2026