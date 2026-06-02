# O11yIA BR - Copilot Metrics Tracker

Sistema de observabilidade para monitoramento de créditos do GitHub Copilot em times de desenvolvimento.

## 📋 Componentes

```
o11yia-br/
├── server/           # API FastAPI (receptor de métricas)
├── dashboard/        # Dashboard Streamlit
├── plugins/
│   ├── chrome-extension/   # Extensão para browser
│   ├── intellij-plugin/    # Plugin IntelliJ IDEA
│   └── vscode-config/      # Configuração OTel para VSCode
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

### 2. Configurar VSCode (OTel nativo)

```bash
# Linux/Mac
export O11YIA_SERVER="http://servidor:8080"
export O11YIA_USER="seu.email@empresa.gov.br"
./deploy/configure-vscode.sh

# Windows (PowerShell)
.\deploy\Configure-VSCode.ps1 -ServerUrl "http://servidor:8080" -UserEmail "seu.email@empresa.gov.br"
```

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

## 🔧 API Endpoints

```
GET  /health              # Health check
POST /v1/metrics          # Enviar uma métrica
POST /v1/metrics/batch    # Enviar múltiplas métricas
GET  /v1/team/summary     # Dashboard do time
GET  /v1/users/{id}       # Detalhe de um usuário
GET  /v1/alerts           # Alertas ativos
POST /v1/traces           # Receptor OTLP (VSCode)
```

## 📦 Payload de Métrica

```json
{
  "user_id": "usuario@empresa.gov.br",
  "source": "vscode",
  "model": "gpt-4o",
  "input_tokens": 150,
  "output_tokens": 500,
  "context": "chat"
}
```

## 🛡️ Segurança

- Dados ficam no servidor interno (não sai da rede)
- Sem coleta de conteúdo de código/prompts
- Apenas métricas agregadas (tokens/modelo/fonte)
- Compatível com LGPD (dados de uso, não pessoais)

## 📈 Alertas

| Nível | Condição |
|-------|----------|
| 🔴 Critical | Pool > 90% usado |
| 🟡 Warning | Pool > 80% usado |
| ℹ️ Info | Usuário 2x acima da média |

## 🔄 Sincronização

- **VSCode**: Automático via OTel (tempo real)
- **Chrome**: Batch a cada 30 segundos
- **IntelliJ**: Batch a cada 30 segundos + logs

---

Desenvolvido para SETID/TCU - Jun/2026
