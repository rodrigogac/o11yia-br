# O11yIA BR Roadmap

O11yIA BR is an early-stage open-source project. This roadmap explains the intended direction and phases of development.

---

## Phase 1: Core Observability (Current)

Establish a stable, functional observability foundation.

- [x] FastAPI backend scaffold
- [ ] Stable metrics ingestion schema
- [ ] Implement `/v1/metrics` and `/v1/metrics/batch` endpoints
- [ ] SQLite storage for usage events
- [ ] Build initial Streamlit dashboard
- [ ] Add basic filters: user, project, source, model
- [ ] Health check and monitoring endpoints
- [ ] Local Docker-based deployment
- [ ] API documentation (endpoint contracts)

**Expected outcome**: Teams can send metrics and see basic usage dashboards locally.

---

## Phase 2: Collectors & Multi-source Support

Connect AI coding tools to the platform.

### VSCode

- [ ] Native OpenTelemetry integration (validate native `github.copilot.chat.otel.*` settings)
- [ ] Fallback VSCode extension (`@o11yia` chat participant)
- [ ] Token counting (measured via `model.countTokens`, estimated as fallback)
- [ ] Batch queue and sync (30s flush)
- [ ] Configuration UI and validation
- [ ] Privacy controls (disable/enable collection)

### Chrome

- [ ] Chrome extension for AI tool usage tracking
- [ ] Background message queue
- [ ] Batch send (30s flush)
- [ ] Privacy manifest and permissions
- [ ] Installation and configuration guide

### IntelliJ

- [ ] IntelliJ plugin scaffold (Gradle-based)
- [ ] Service integration for Copilot events
- [ ] Token tracking
- [ ] Settings and configuration panel
- [ ] Build and packaging (`.jar`/`.zip` distribution)

### General collector features

- [ ] Local configuration (API key, server URL, team/user ID)
- [ ] Offline buffering (queue events when offline)
- [ ] Privacy controls (toggle collection on/off)
- [ ] Status indicators (connected, syncing, failed)
- [ ] Test/validation commands (send test metric)

**Expected outcome**: Metrics flow from multiple IDE sources into a single dashboard.

---

## Phase 3: Governance & Cost Management

Enable teams to control and audit AI tool usage.

- [ ] Budget thresholds (per team, per project)
- [ ] Alert system (warnings, critical alerts)
- [ ] Usage anomaly detection (statistical or ML-based)
- [ ] Cost reports (usage breakdown, trends over time)
- [ ] Team/project-level analytics and drill-down
- [ ] Exportable reports (CSV, PDF)
- [ ] Usage forecasting (trends, budget depletion prediction)
- [ ] Audit logs (who did what, when, and with what result)

**Expected outcome**: Organizations can govern and forecast AI tool costs and usage.

---

## Phase 4: Security & Privacy Assurance

Build trust in the platform's privacy and security model.

- [ ] Security code review (internal and community)
- [ ] Threat model documentation
- [ ] Publish "no source code" guarantee with evidence
- [ ] Publish "no prompt content" guarantee with evidence
- [ ] Secret detection safeguards (redaction in logs, alerts)
- [ ] Access control (role-based, multi-tenant)
- [ ] Encryption in transit (TLS/HTTPS)
- [ ] Encryption at rest (database encryption)
- [ ] Data retention policies (archival, deletion)
- [ ] Compliance documentation (LGPD, GDPR, SOC 2 readiness)
- [ ] Security policy and vulnerability reporting guide
- [ ] Dependency scanning and supply chain security

**Expected outcome**: Organizations can confidently deploy O11yIA BR knowing data is safe and private.

---

## Phase 5: Open Source Maturity

Establish best practices for an open-source project.

- [ ] Contributing guide ([CONTRIBUTING.md](CONTRIBUTING.md))
- [ ] Issue templates (bug, feature, collector request)
- [ ] Pull request template
- [ ] Community code of conduct
- [ ] Automated tests (unit, integration, API)
- [ ] CI/CD pipeline (GitHub Actions, linting, coverage)
- [ ] Release workflow and versioning (semantic versioning, CHANGELOG)
- [ ] Example datasets for local testing
- [ ] Demo environment (with sample data)
- [ ] Documentation site (MkDocs, GitHub Pages, or similar)
- [ ] Onboarding guide for contributors
- [ ] Architecture decision records (ADRs)

**Expected outcome**: O11yIA BR becomes easier to understand, contribute to, and deploy.

---

## Phase 6: Advanced Features (Future)

Extend functionality based on community needs.

- [ ] Multi-tenant deployments
- [ ] Custom metrics and aggregations
- [ ] Webhook integrations (Slack, Teams, webhooks for alerts)
- [ ] Pluggable collector framework (SDK for new collectors)
- [ ] Integration with GitHub billing APIs (if available)
- [ ] Integration with cloud platforms (AWS, GCP, Azure for cost correlation)
- [ ] Advanced anomaly detection (isolation forests, autoencoders)
- [ ] Real-time streaming (WebSocket dashboards)
- [ ] GraphQL API (in addition to REST)
- [ ] Mobile app or responsive dashboard improvements
- [ ] Internationalization (i18n) support

---

## Codex for OSS Integration

If accepted into the **Codex for OSS** program, O11yIA BR will use Codex, Codex Security, and API credits for:

- [ ] Automated code review of collector implementations
- [ ] Security scanning of FastAPI backend and dependencies
- [ ] Test generation for edge cases and error scenarios
- [ ] Documentation generation (API docs, guides, examples)
- [ ] Issue triage and categorization automation
- [ ] Release notes generation from commits/PRs
- [ ] Privacy threat model development
- [ ] Anomaly detection prototype and validation

See linked GitHub issue for task details.

---

## Timeline

- **Phase 1 (Core)**: Ongoing (Jun–Jul 2026)
- **Phase 2 (Collectors)**: Jul–Aug 2026
- **Phase 3 (Governance)**: Aug–Sep 2026
- **Phase 4 (Security)**: Sep–Oct 2026
- **Phase 5 (Maturity)**: Oct–Dec 2026
- **Phase 6 (Advanced)**: 2027 onwards

---

## How to contribute

- Volunteer for any phase task by opening an issue.
- Suggest new phases or features via discussions.
- Report blockers or dependencies.
- Review and test pre-release versions.

---

**Last updated**: June 2026