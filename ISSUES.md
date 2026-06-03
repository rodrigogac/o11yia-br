# O11yIA BR — Issues, Diário e Próximos Passos

> Documento de acompanhamento do desenvolvimento do **tracker de tokens de IA** (PoC do SaaS multi-gateway).
> Última atualização: **2026-06-02**.

---

## 📔 Diário de desenvolvimento

### 2026-06-02 — Reposicionamento e construção do tracker v2
O projeto foi reposicionado: deixou de ser apenas um "tracker de Copilot" para ser a **PoC de um SaaS multi-gateway de observabilidade de tokens de IA**, com foco imediato em entregar o produto tracker para a equipe. Decisão-chave: **capturar tokens SEM usar a API oficial do GitHub Copilot** (que tem delay de ~2 dias e não dá visão real-time por pessoa). A captura é local, na máquina do dev, por 3 fontes (VSCode, IntelliJ, Browser), enviando para um backend central.

O trabalho foi executado por **5 agentes em paralelo** (worktrees isolados), todos seguindo um **contrato de API compartilhado** (auth por `X-API-Key`/`X-Admin-Key`; schema com team/project; pricing único = 1 crédito US$ 0,01; endpoints `/v1/metrics`, `/v1/metrics/batch`, `/v1/traces` OTLP, `/v1/team/summary`, `/v1/teams`, `/v1/users`, `/v1/alerts`, `/v1/admin/*`).

**Marco validado:** captura **ponta a ponta com dado real** comprovada — extensão VSCode (`@o11yia`) → backend autenticado → painel, sem usar a API do Copilot.

---

## ✅ Issues concluídas (por agente)

### Agente 1 — Backend collector v2 (`server/`)
- [x] Autenticação `X-API-Key` (ingestão/consulta) e `X-Admin-Key` (admin); modo `O11YIA_AUTH_DISABLED` para dev.
- [x] Schema multi-fonte/multi-gateway com `team`, `project`, `gateway`, `reasoning_tokens`, `cost_usd` (camada isolada em `db.py`, pronta para migrar a Postgres).
- [x] Pricing como fonte única (`pricing.py`), match por prefixo case-insensitive.
- [x] Receptor **OTLP real** (JSON **e** protobuf via `opentelemetry-proto`) extraindo `gen_ai.usage.*`.
- [x] Endpoints admin (CRUD times/budgets, usuários, config do pool).
- [x] Bugs corrigidos: CORS (`*`+credentials), `lastrowid` após close, `datetime.utcnow()`, concorrência SQLite (WAL+lock+retry).
- [x] **13 testes pytest** passando.

### Agente 2 — Painel de administração (`dashboard/`)
- [x] 5 páginas: Visão Geral, Por Time, Por Projeto, Detalhe de Usuário, Administração (CRUD).
- [x] Projeção de esgotamento corrigida; auto-refresh não-bloqueante (`st_autorefresh`).
- [x] Tratamento de erros de auth (401/403) e estados vazios amigáveis.

### Agente 3 — Cliente de captura VSCode (`plugins/vscode-extension/`, `plugins/vscode-config/`)
- [x] **Confirmado** que o OTel nativo do Copilot existe (VS Code 1.119, mai/2026); guias e exemplos de validação.
- [x] Extensão VSCode própria (Chat Participant `@o11yia`, `model.countTokens`, fila/batch, status bar, comandos).
- [x] Build esbuild OK; **`.vsix` gerado** (`o11yia-vscode-0.1.0.vsix`) e **testado pelo usuário com dado real**.

### Agente 4 — Extensão Chrome (`plugins/chrome-extension/`)
- [x] Auth `X-API-Key` em todas as chamadas; config `apiKey`/`team`/`project`; botão "Testar Conexão".
- [x] **Ícones PNG** (16/48/128) criados — extensão agora carrega.
- [x] Teste real contra o backend: 401 sem key, `success:true` com key.

### Agente 5 — Plugin IntelliJ (`plugins/intellij-plugin/`)
- [x] Setting de API key (campo senha) + `team`/`project`; header `X-API-Key` nas chamadas OkHttp.
- [x] Wrapper Gradle 8.5 criado; **`./gradlew buildPlugin` → BUILD SUCCESSFUL** (.zip ~4,45 MB).
- [x] Teste curl do contrato OK.

### Coordenação
- [x] Merge dos 5 branches no `integration/tracker-v2` (sem conflitos — caminhos disjuntos).
- [x] Fix de integração: dashboard desembrulhando listas de `/v1/teams` e `/v1/admin/*`.
- [x] `.gitignore` raiz; pins relaxados (pandas/pydantic) para wheels no Python 3.13.
- [x] README atualizado.

---

## 🐞 Issues abertas / limitações conhecidas

### Captura
- [ ] **VSCode é opt-in (`@o11yia`)**: a extensão só mede o que é enviado ao participant. O VS Code não expõe tokens do uso first-party do Copilot (chat normal/inline) a terceiros. Captura automática depende do OTel nativo.
- [ ] **OTel nativo não validado na máquina real**: setting `serviceName` da doc interna não existe; recurso foca no **modo Agente**; `otlpEndpoint` espera OTLP padrão (porta 4318, exporter anexa `/v1/traces`). **Wrinkle de auth:** o exporter do Copilot pode não enviar o header `X-API-Key` — exigirá um OpenTelemetry Collector injetando a chave, ou liberar a rota `/v1/traces`.
- [ ] **Chrome**: contagem de tokens é heurística (MV3 `webRequest` não expõe corpo da resposta); ícones são placeholders (trocar pela arte oficial).
- [ ] **IntelliJ**: captura por parsing de `idea.log` é heurística e depende do que o Copilot loga; build exige JDK 17+.

### Backend / dados
- [ ] SQLite com lock de escrita único — ok para PoC, **migrar a Postgres** para escala (SaaS multi-gateway).
- [ ] Gestão de chaves via env (`O11YIA_API_KEYS`) — falta UI/rotação de chaves por time.
- [ ] **Pricing é aproximação** — calibrar com o billing real de AI Credits do GitHub.
- [ ] `team_size` ainda fixo (18) na Visão Geral do painel — conectar ao `/v1/admin/config`.

### Qualidade
- [ ] Sem testes automatizados para dashboard, extensão VSCode, Chrome e IntelliJ (só backend tem).
- [ ] Sem CI.

---

## 🧭 Próximos passos (sugestão de ordem)

1. **Validar o OTel nativo do Copilot** ponta a ponta (collector OTLP injetando `X-API-Key` → `/v1/traces`), provando captura **automática** no modo Agente.
2. **Calibrar o pricing** com o billing real do GitHub (1 AI credit = US$ 0,01) por modelo.
3. **Distribuição**: publicar a extensão VSCode (.vsix interno) e distribuir settings via GPO/MDM; carregar a extensão Chrome por política; empacotar o plugin IntelliJ.
4. **Conectar `team_size`/datas promo** do painel ao `/v1/admin/config`.
5. **Migrar SQLite → Postgres** e adicionar gestão de chaves por time.
6. **Ingestão de gateways** (LiteLLM/Portkey/Bifrost via OTLP) — passo rumo à visão multi-gateway da `IDEA.md`.
7. **Compliance LGPD** (Tier 4 da IDEA): scanner de PII em prompts/respostas, audit trail.
8. **Testes + CI** para painel e plugins.

---

## 🔧 Como rodar (referência rápida)

```bash
# Backend (porta 8080)
cd server
DATABASE_PATH=./metrics.db O11YIA_API_KEYS=dev-key-1 O11YIA_ADMIN_KEY=admin-key-1 \
  python -m uvicorn main:app --port 8080
python -m pytest server/ -q     # 13 testes

# Painel (porta 8501)
cd dashboard
API_URL=http://localhost:8080 O11YIA_API_KEY=dev-key-1 O11YIA_ADMIN_KEY=admin-key-1 \
  streamlit run app.py

# Extensão VSCode
cd plugins/vscode-extension && npm install && npm run build
npx @vscode/vsce package --allow-missing-repository --skip-license   # gera .vsix

# Plugin IntelliJ
cd plugins/intellij-plugin && ./gradlew buildPlugin   # .zip em build/distributions/
```

Chaves de teste atuais: ingestão `dev-key-1`, admin `admin-key-1`.
