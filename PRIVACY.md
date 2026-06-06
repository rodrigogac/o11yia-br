# Privacy Model

O11yIA BR is designed as a **privacy-first observability tool** for AI-assisted development. This document explains what data is collected, what is not, and why.

---

## Design Principle

O11yIA BR collects **only the minimum metadata required** for:

- **Observability**: Understanding AI tool usage patterns and trends.
- **Cost governance**: Tracking token/credit consumption by team, project, and user.
- **Responsible AI adoption**: Monitoring for anomalies, waste, or risk.

All other data is explicitly **not** collected or transmitted.

---

## Data We Intend to Collect

O11yIA BR may collect the following **aggregated, non-sensitive metadata**:

| Field | Source | Purpose | Example |
|-------|--------|---------|----------|
| **Tool/source** | Collector | Identify which IDE or tool sent the metric | `vscode`, `chrome`, `intellij` |
| **Event timestamp** | Collector | Track when usage occurred (for analytics, trends) | `2026-06-06T14:30:45Z` |
| **User identifier** | Organization config | Attribute usage to individuals (team billing, audits) | `user@example.com`, user UUID |
| **Team identifier** | Organization config | Attribute usage to teams/squads (budget tracking) | `backend-team`, `squad-123` |
| **Project identifier** | Organization config | Attribute usage to projects (cost allocation) | `project-x`, Git repo name |
| **Model name** | API / Copilot | Track which LLMs are used | `gpt-4o`, `claude-3`, `gpt-4-turbo` |
| **Token usage metrics** | API / Copilot | Measure consumption (cost calculation, trends) | `input_tokens: 150, output_tokens: 500` |
| **Aggregated cost** | Backend calculation | Compute spend (budget tracking, reports) | `$2.50 per request` |
| **Error or status metadata** | API / Collector | Track failures, retries, and health | `status: success`, `error_code: auth_failed` |
| **Context type** | Collector | Understand usage patterns (chat vs. inline completions) | `chat`, `completion`, `snippet` |
| **Session ID** | Collector | Group related events (optional, for correlation) | `session-abc123` |

---

## Data We Do NOT Collect

O11yIA BR is **explicitly designed NOT to collect**:

| Data Type | Why not | Risk if collected |
|-----------|---------|-------------------|
| **Source code** | No business need; violates privacy | IP theft, compliance violations, developer surveillance |
| **Prompt content** | No business need; privacy-critical | Reveals developer intent, company secrets, personal info |
| **Generated code content** | No business need; similar risks | IP exposure, audit trail of what was built |
| **Secrets or credentials** | No business need; security risk | Account compromise, credential theft |
| **Private files** | No business need; privacy violation | File names reveal projects, architecture, secrets |
| **Full browser history** | No business need; extreme privacy violation | Reveals all sites visited, personal activity |
| **Keystrokes** | No business need; extreme surveillance | Captures everything typed, passwords, messages |
| **Screenshots or recordings** | No business need; extreme surveillance | Visual capture of code, conversations, personal info |
| **Personal messages or comms** | No business need; privacy violation | Slack messages, emails, chat logs |
| **System information** | Generally not needed; edge case: IP can reveal location | Reveals developer device type, OS, software stack |

**Collectors are hardcoded to reject any payload containing prohibited fields.**

---

## Implementation Guarantees

### VSCode Collectors

**Native OTel mode** (`github.copilot.chat.otel.*` settings):
- Setting `github.copilot.chat.otel.captureContent` is **always `false`** (no prompt/code capture).
- Only `gen_ai.usage.*` metrics (token counts) and `gen_ai.request.model` are forwarded.

**Fallback extension** (`plugins/vscode-extension/`):
- No access to source code via VS Code APIs.
- Captures tokens via public `model.countTokens()` API only.
- No keystroke or clipboard interception.
- Status bar shows tokens sent (transparency).

### Chrome Extension

- Cannot intercept HTTPS traffic or read encrypted content.
- Cannot access cookies, localStorage, or sensitive storage.
- Manifest explicitly declares no access to browsing history.
- Collects only UI-level events (e.g., "user opened Chrome extension").

### IntelliJ Plugin

- Uses official Copilot APIs only (no code parsing or introspection).
- Collects only token usage and model names.
- No file system access beyond project configuration.

### Backend (`server/`)

- Validates all incoming metrics; rejects payloads with prohibited fields.
- Logs only metadata (no storage of code, prompts, or raw content).
- Implements rate limiting and access controls.

---

## Privacy by Default

- **Local deployment**: O11yIA BR runs on your infrastructure by default. Data never leaves your network.
- **No cloud sync**: No telemetry is sent to third-party servers without explicit configuration.
- **No profiling**: No behavioral tracking or correlation of users across sessions.
- **Configurable retention**: Deployments can set data TTLs and archival policies.

---

## Data Retention & Deletion

**Default retention** (configurable):
- Usage metrics: 90 days (configurable)
- Aggregated reports: indefinite (no personal data)
- Logs: 30 days

**Deletion on request**: Organizations can request data deletion for specific users or time ranges via admin APIs.

---

## Future Work (Planned)

- [ ] Configurable anonymization (hash user IDs, remove IP addresses)
- [ ] Team-level aggregation only (never expose individual user data in dashboards)
- [ ] Local-only deployment mode (no backend API exposure)
- [ ] Data retention controls (UI for TTL, archival, deletion policies)
- [ ] Redaction safeguards (detect and strip accidental secrets in error logs)
- [ ] Privacy impact assessment (for new features)
- [ ] Privacy threat model documentation (detailed risk analysis)
- [ ] Community privacy review (open review, feedback, validation)

---

## Compliance

O11yIA BR is designed with compliance in mind:

- **LGPD** (Brazil): Collects only aggregated usage data; aligns with data minimization principles.
- **GDPR** (EU): Supports data portability, retention limits, and deletion on request.
- **SOC 2 readiness**: Local deployment, audit logs, encryption, access controls.

---

## Reporting Privacy Issues

If you discover a privacy concern (unexpected data collection, undocumented telemetry, etc.):

1. **Do not open a public issue.** Privacy issues can be sensitive.
2. Contact the maintainer privately: [@rodrigogac](https://github.com/rodrigogac)
3. Provide details: what data was collected, under what conditions, and why it's concerning.

---

## Questions?

For privacy questions or feedback:
- Open a [GitHub issue](https://github.com/rodrigogac/o11yia-br/issues) (public concerns only)
- Contact [@rodrigogac](https://github.com/rodrigogac) privately (sensitive concerns)
- See [CONTRIBUTING.md](CONTRIBUTING.md) for more ways to engage

---

**Last updated**: June 2026