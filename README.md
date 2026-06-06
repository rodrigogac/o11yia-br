# O11yIA BR — Copilot Metrics Tracker

[![Open Source](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Early Stage](https://img.shields.io/badge/status-early%20stage-orange.svg)](#current-status)
[![AI Governance](https://img.shields.io/badge/focus-AI%20Governance-blue.svg)](#why-this-matters)
[![Observability](https://img.shields.io/badge/category-Observability-brightgreen.svg)](#what-o11yia-br-does)

**English** | [Português](#português)

O11yIA BR is an open-source observability and governance platform for AI-assisted development teams. It helps organizations **monitor token usage, credit consumption, model adoption, project/team costs, and usage anomalies** across tools such as GitHub Copilot, VSCode, Chrome and IntelliJ collectors, **without collecting source code or user prompts**.

---

## Why this matters

AI-powered coding tools like GitHub Copilot are growing rapidly across development teams. Yet most organizations still lack visibility into:

- **Cost and consumption**: How many tokens are being used? Which teams or projects consume the most?
- **Budget governance**: What happens when credit pools are depleted? Are there anomalies or waste?
- **Model adoption**: Which LLMs are actually being used in practice?
- **Usage patterns**: Which developers, teams, and projects rely on AI assistance?
- **Compliance and audits**: Can organizations prove what data was collected (and what wasn't)?

O11yIA BR addresses these gaps by providing **aggregated, privacy-first metrics** designed specifically for AI-assisted development governance.

---

## What O11yIA BR does

✅ **Tracks AI coding usage metrics** — tokens, models, sources, teams, and projects.  
✅ **Aggregates by user, team, project, and model** — no individual prompts, no code snippets.  
✅ **Identifies consumption trends** — spot unusual spikes, patterns, or budget risks.  
✅ **Enables cost governance** — set budgets, track spend, generate reports.  
✅ **Provides a dashboard** — real-time visibility via Streamlit analytics.  
✅ **Plans multiple collectors** — VSCode (native OTel + fallback extension), Chrome, IntelliJ.  

---

## What it does NOT collect

**This is a privacy-first project.** O11yIA BR is explicitly **designed NOT to collect**:

❌ Source code  
❌ Prompt content  
❌ Generated code content  
❌ Secrets or credentials  
❌ Private files  
❌ Full browser history  
❌ Keystrokes  
❌ Screenshots or screen recordings  
❌ Personal messages  

O11yIA BR collects **only metadata and aggregated metrics** intended for cost governance, observability, and responsible AI adoption.

---

## Architecture

```
┌─────────────────────────────────────────┐
│  Collectors (VSCode, Chrome, IntelliJ)  │
└─────────────┬───────────────────────────┘
              │ HTTP / OpenTelemetry
              ▼
┌─────────────────────────────────────────┐
│      FastAPI Backend                    │
│  • Metrics ingestion endpoints          │
│  • OTLP trace receiver                  │
│  • Admin APIs (teams, budgets, config)  │
└─────────────┬───────────────────────────┘
              │ SQLite / Storage
              ▼
┌─────────────────────────────────────────┐
│      Metrics Storage                    │
│  • Aggregated usage events              │
│  • Cost tracking                        │
│  • Alerts and anomalies                 │
└─────────────┬───────────────────────────┘
              │ REST API
              ▼
┌─────────────────────────────────────────┐
│   Streamlit Dashboard                   │
│  • Analytics and visualizations         │
│  • Reports and governance               │
│  • Budget and cost views                │
└─────────────────────────────────────────┘
```

**Key components:**

- **FastAPI backend** (`server/`) — RESTful metrics API, OTLP ingestion, admin endpoints.
- **Streamlit dashboard** (`dashboard/`) — real-time analytics, filtering, reports.
- **Collectors/extensions** (`plugins/`) — VSCode (OTel + fallback), Chrome, IntelliJ.
- **Docker-based local deployment** (`docker-compose.yml`) — easy local development and testing.

---

## Current status

**This project is currently early-stage and under active development.**

- Core APIs, collectors, and dashboards are functional for local development and testing.
- Architecture may change as the project evolves.
- Not yet production-hardened; use for evaluation, prototyping, and contribution.

See the [ROADMAP](#roadmap) for planned features and phases.

---

## Quick start

### Prerequisites

- Docker and Docker Compose (recommended)  
- OR: Python 3.10+, Node.js 18+, Java 11+ (for manual setup)

### Option 1: Docker Compose (recommended)

```bash
git clone https://github.com/rodrigogac/o11yia-br.git
cd o11yia-br
docker compose up --build
```

- **API**: http://localhost:8080
- **Dashboard**: http://localhost:8501
- **Health check**: `curl http://localhost:8080/health`

### Option 2: Manual Python setup (backend only)

```bash
git clone https://github.com/rodrigogac/o11yia-br.git
cd o11yia-br

# Backend API
cd server
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8080
```

### Option 3: VSCode extension (development)

```bash
cd plugins/vscode-extension
npm install
npm run build
# Press F5 to launch Extension Development Host
```

For detailed collector setup, see:
- VSCode: `plugins/vscode-config/README.md` (native OTel) and `plugins/vscode-extension/README.md` (fallback)
- Chrome: `plugins/chrome-extension/` (local setup)
- IntelliJ: `plugins/intellij-plugin/` (Gradle-based build)

---

## API overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check (public) |
| `POST` | `/v1/metrics` | Send a single metric |
| `POST` | `/v1/metrics/batch` | Send multiple metrics |
| `POST` | `/v1/traces` | OpenTelemetry receiver (OTLP) |
| `GET` | `/v1/team/summary` | Team usage summary |
| `GET` | `/v1/teams` | All teams with budgets |
| `GET` | `/v1/users/{id}` | User-level metrics |

All endpoints except `/health` require `X-API-Key` header. Admin endpoints require `X-Admin-Key`.

Example:
```bash
curl -X POST http://localhost:8080/v1/metrics \
  -H "X-API-Key: dev-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user@example.com",
    "source": "vscode",
    "model": "gpt-4o",
    "input_tokens": 150,
    "output_tokens": 500,
    "team": "backend",
    "project": "project-x",
    "context": "chat"
  }'
```

---

## Use cases

- **Engineering managers** monitoring AI tool adoption and cost across teams.
- **Open-source maintainers** understanding AI-assisted contribution workflows.
- **Startups** controlling AI coding tool expenses and budgets.
- **Teams** auditing AI adoption across projects and time periods.
- **Organizations** detecting unusual usage spikes, anomalies, or budget risks.
- **Compliance officers** verifying that only safe metadata is collected (no code, no prompts).

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for detailed phases and timelines.

### Immediate priorities

- [ ] Stable FastAPI ingestion API
- [ ] Streamlit dashboard improvements (multi-page, filters, export)
- [ ] VSCode collector (native OTel + fallback extension)
- [ ] Chrome collector
- [ ] IntelliJ collector
- [ ] Budget alerts and thresholds
- [ ] Anomaly detection
- [ ] Privacy and security documentation
- [ ] Automated tests and CI/CD
- [ ] Security review and threat model
- [ ] Release workflow and versioning

---

## Privacy model

See [PRIVACY.md](PRIVACY.md) for the complete privacy policy.

**In short:**

- We collect **metadata only**: source, timestamp, user/team ID, project, model name, token counts, costs.
- We **never** collect source code, prompts, generated code, secrets, or keystrokes.
- Deployments are local/self-hosted by default — data stays on your infrastructure.
- All telemetry fields are explicitly documented.

---

## Codex for OSS usage plan

If accepted into the **Codex for OSS** program, O11yIA BR would use **Codex**, **Codex Security**, and **API credits** to accelerate:

- **Automated code review** — improve FastAPI backend and collectors for security, performance.
- **Test generation** — add tests for ingestion APIs, dashboard logic, edge cases.
- **Security analysis** — review telemetry model, threat model, secret redaction safeguards.
- **Documentation** — improve guides, API docs, contributor onboarding, privacy docs.
- **Issue triage and release automation** — automated labeling, release notes, changelog generation.
- **Anomaly detection prototype** — develop and test AI-powered usage pattern analysis.

See [GitHub Issue](https://github.com/rodrigogac/o11yia-br/issues) section for the full plan.

---

## Contributing

We welcome contributions! Before you start:

1. **Open an issue** — suggest a collector, report a bug, propose a feature, or discuss privacy/security concerns.
2. **Review [CONTRIBUTING.md](CONTRIBUTING.md)** — contributor guidelines and principles.
3. **Check [SECURITY.md](SECURITY.md)** — security policies and how to report vulnerabilities.
4. **Understand the privacy model** — see [PRIVACY.md](PRIVACY.md); any new telemetry field must be documented.

### Ways to contribute

- Improve documentation.
- Suggest new metrics or aggregation strategies.
- Build or improve collectors (VSCode, Chrome, IntelliJ, others).
- Improve the FastAPI backend or Streamlit dashboard.
- Add tests, fix bugs, or review code.
- Review privacy and security assumptions.
- Suggest integrations or use cases.

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## Maintainer

**Rodrigo Silva** — [@rodrigogac](https://github.com/rodrigogac)

Questions? Open an issue or reach out.

---

## Português

**O11yIA BR** é uma plataforma open source de observabilidade e governança para times que usam IA no desenvolvimento. O objetivo é monitorar consumo de tokens, créditos, modelos, custos por projeto/time e anomalias de uso em ferramentas como GitHub Copilot, VSCode, Chrome e IntelliJ, **sem coletar código-fonte nem prompts dos usuários**.

### Por que importa

Ferramentas de IA para programação estão crescendo rapidamente, mas equipes ainda têm pouca visibilidade sobre consumo, custos, uso por projeto, riscos de orçamento, governança e segurança.

### O que coleta

✅ Tokens, modelos, fontes (VSCode, Chrome, IntelliJ)  
✅ Agregação por usuário, time, projeto  
✅ Tendências de consumo e anomalias  
✅ Governança de orçamento  
✅ Dashboard em tempo real  

### O que NÃO coleta

❌ Código-fonte  
❌ Conteúdo de prompts  
❌ Código gerado  
❌ Segredos ou credenciais  
❌ Arquivos privados  
❌ Teclados, screenshots, histórico completo  

### Como começar

```bash
git clone https://github.com/rodrigogac/o11yia-br.git
cd o11yia-br
docker compose up --build
```

- **API**: http://localhost:8080
- **Dashboard**: http://localhost:8501

### Contribuir

Veja [CONTRIBUTING.md](CONTRIBUTING.md), [PRIVACY.md](PRIVACY.md) e [SECURITY.md](SECURITY.md).

---

**Last updated**: June 2026
