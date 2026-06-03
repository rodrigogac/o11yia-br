# O11yIA BR - Copilot Metrics Tracker

Sistema de observabilidade para monitoramento de créditos do GitHub Copilot em times de desenvolvimento.

## 📋 Componentes

```
o11yia-br/
├── server/           # API FastAPI (collector multi-fonte + OTLP + admin)
├── dashboard/        # Painel de administração Streamlit (multi-página)
├── plugins/
│   ├── vscode-extension/   # Extensão VSCode própria (captura + envio)
│   ├── vscode-config/      # Validação + config do OTel nativo do Copilot
│   ├── chrome-extension/   # Extensão para browser
│   └── intellij-plugin/    # Plugin IntelliJ IDEA
└── deploy/           # Scripts de instalação
```

## 🚀 Deploy Rápido

### 1. Servidor Central

```bash
cd ~/projetosdocker/o11yia-br
docker compose up -d
```

Acesse:
- **API**: http://localhost:8080
- **Dashboard**: http://localhost:8501

### 2. Captura no VSCode

Há dois caminhos (veja detalhes em `plugins/vscode-config/README.md`):

- **OTel nativo do Copilot** (VS Code 1.119+, mai/2026): settings `github.copilot.chat.otel.*` exportam `gen_ai.usage.*`. Foca no **modo Agente** — exporta OTLP padrão para `:4318` (pode exigir um OpenTelemetry Collector encaminhando para `/v1/traces`). Exemplos em `plugins/vscode-config/`.
- **Extensão própria** (`plugins/vscode-extension/`): fallback que captura via Chat Participant `@o11yia`, conta tokens (`model.countTokens`) e envia direto para o backend com `X-API-Key`.

```bash
cd plugins/vscode-extension
npm install && npm run build      # bundle via esbuild
# F5 abre o Extension Development Host, ou: npx vsce package  → .vsix
```

Configure em Settings: `o11yia.serverUrl`, `o11yia.userId`, `o11yia.apiKey`, `o11yia.team`.
Comando **"O11yIA: Send Test Metric"** valida o pipeline ponta a ponta sem depender do Copilot.

### 3. Extensão Chrome

1. Abra `chrome://extensions`
2. Ative "Modo desenvolvedor"
3. Clique "Carregar sem compactação"
4. Selecione a pasta `plugins/chrome-extension`
5. Configure o servidor e usuário nas opções

### 4. Plugin IntelliJ

```bash
cd plugins/intellij-plugin
./gradlew buildPlugin
# O .zip estará em build/distributions/
```

Instale via: `Settings > Plugins > Install from disk`

## 📊 Pool de Créditos (Jun/2026)

| Período | Créditos/Usuário | Time (18 pessoas) |
|---------|------------------|-------------------|
| Promocional (Jun-Ago) | 7.000 | 126.000 |
| Normal (Set+) | 3.900 | 70.200 |

## 🔐 Autenticação

A API exige chaves, configuradas por variáveis de ambiente no serviço `api`:

- `O11YIA_API_KEYS` — chaves de ingestão/consulta (separadas por vírgula). Header: `X-API-Key`.
- `O11YIA_ADMIN_KEY` — chave de administração. Header: `X-Admin-Key`.
- `O11YIA_CORS_ORIGINS` — origens liberadas no CORS (default `http://localhost:8501`).
- `O11YIA_AUTH_DISABLED=true` — desliga a autenticação (apenas dev/PoC local).

`GET /health` é público. Sem nenhuma chave configurada, a API opera em modo aberto e registra um aviso.

## 🔧 API Endpoints

```
GET  /health              # Health check (público)

# Ingestão e consulta — exigem X-API-Key
POST /v1/metrics          # Enviar uma métrica
POST /v1/metrics/batch    # Enviar múltiplas métricas
POST /v1/traces           # Receptor OTLP (JSON e protobuf)
GET  /v1/team/summary     # Resumo do time (+ by_team, by_project)
GET  /v1/teams            # Times com budget e % usado
GET  /v1/users/{id}       # Detalhe de um usuário
GET  /v1/alerts           # Alertas ativos

# Administração — exigem X-Admin-Key
GET|POST|PUT|DELETE /v1/admin/teams[/{name}]   # CRUD de times/budgets
GET|PUT             /v1/admin/users[/{id}]     # Atribuir time/nome
GET|PUT             /v1/admin/config           # Pool, datas promo, team_size
```

## 📦 Payload de Métrica

```bash
curl -X POST http://localhost:8080/v1/metrics \
  -H "X-API-Key: SUA_CHAVE" -H "Content-Type: application/json" \
  -d '{
    "user_id": "usuario@empresa.gov.br",
    "source": "vscode",
    "model": "gpt-4o",
    "input_tokens": 150,
    "output_tokens": 500,
    "team": "backend",
    "project": "projeto-x",
    "context": "chat"
  }'
```

## 🧪 Testes

```bash
pip install -r server/requirements.txt -r server/requirements-dev.txt
python -m pytest server/ -q
```

## 🛡️ Segurança

- Acesso à API protegido por chave (`X-API-Key` / `X-Admin-Key`)
- Dados ficam no servidor interno (não sai da rede)
- Sem coleta de conteúdo de código/prompts
- Apenas métricas agregadas (tokens/modelo/fonte/time/projeto)
- Compatível com LGPD (dados de uso, não pessoais)

## 📈 Alertas

| Nível | Condição |
|-------|----------|
| 🔴 Critical | Pool > 90% usado |
| 🟡 Warning | Pool > 80% usado |
| ℹ️ Info | Usuário 2x acima da média |

## 🔄 Sincronização

- **VSCode**: OTel nativo (tempo real) ou extensão própria (batch 30s)
- **Chrome**: Batch a cada 30 segundos
- **IntelliJ**: Batch a cada 30 segundos + logs

---

Desenvolvido para SETID/TCU - Jun/2026
