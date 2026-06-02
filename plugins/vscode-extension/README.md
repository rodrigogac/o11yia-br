# O11yIA BR — Extensão VSCode (Copilot Token Tracker)

Extensão VSCode que captura uso de tokens do **GitHub Copilot Chat** e envia ao
backend **O11yIA BR**. É o **fallback** da estratégia "OTel nativo → cliente próprio"
(ver [`../vscode-config/`](../vscode-config/)). Funciona **sem** usar a API oficial do
GitHub Copilot e **sem** depender do OTel nativo.

## Como ela captura

A extensão registra um **Chat Participant** (`@o11yia`) usando a **Chat Participant
API** e a **Language Model API** (`vscode.lm`) — ambas APIs **públicas** do VSCode,
disponíveis para qualquer extensão. Quando você conversa com `@o11yia`, a pergunta é
encaminhada a um modelo do Copilot via `model.sendRequest(...)` e a extensão
contabiliza os tokens.

### Medido vs estimado (transparência)

| Quando | input_tokens | output_tokens |
|--------|--------------|---------------|
| `model.countTokens(...)` disponível e bem-sucedido | **medido** (tokenizer do modelo) | **medido** |
| Falha/indisponível | **estimado** (~4 chars/token) | **estimado** |

Cada resposta do `@o11yia` mostra no rodapé se foi `medido` ou `estimado`.

> **Limitação honesta:** o Copilot **não expõe** contagem de tokens das suas próprias
> interações (chat lateral, completions inline) a outras extensões. Por isso a captura
> automática só ocorre para o que passa pelo participant `@o11yia`. Para uso fora do
> participant, a alternativa é o **OTel nativo** (ver `../vscode-config/`).

## Configuração (Settings)

| Setting | Default | Descrição |
|---------|---------|-----------|
| `o11yia.enabled` | `true` | Liga/desliga captura e envio |
| `o11yia.serverUrl` | `http://localhost:8080` | URL base do backend (sem barra final) |
| `o11yia.userId` | `""` | E-mail do usuário (fallback: login da máquina) |
| `o11yia.apiKey` | `""` | Enviada no header `X-API-Key` |
| `o11yia.team` | `""` | Time/squad (opcional) |

## Status bar

Item à direita mostra **tokens consumidos na sessão**, **pendentes na fila** e o
**status de sync** (ícone muda: nuvem = sem sync ainda, upload = OK, aviso = falha).
Clique abre `O11yIA: Show Status`.

## Comandos (Ctrl+Shift+P)

- **O11yIA: Sync Now** — força flush da fila para `/v1/metrics/batch`.
- **O11yIA: Send Test Metric** — envia uma métrica de teste para `/v1/metrics`
  (valida a PoC ponta a ponta **sem depender do Copilot**).
- **O11yIA: Show Status** — mostra config, health do backend e stats da sessão.

## Envio / contrato

- POST imediato: `${serverUrl}/v1/metrics` (métrica única — usado no Send Test Metric e requeue).
- Batch a cada 30s: `${serverUrl}/v1/metrics/batch` (array de métricas).
- Header obrigatório: `X-API-Key: <o11yia.apiKey>`.
- Fila em memória + **requeue em falha** (espelha `plugins/chrome-extension/background.js`).

Payload (TokenMetric):
```json
{
  "user_id": "fulano@empresa.gov.br",
  "source": "vscode",
  "model": "gpt-4o",
  "input_tokens": 150,
  "output_tokens": 500,
  "team": "backend",
  "session_id": "vscode-...",
  "context": "chat",
  "timestamp": "ISO-8601"
}
```

## Build

```powershell
npm install
npm run build      # bundle com esbuild -> out/extension.js
npm run compile    # checagem de tipos (tsc --noEmit), opcional
```

## Rodar em modo dev (Extension Development Host)

1. Abra a pasta `plugins/vscode-extension/` no VSCode.
2. `npm install` (uma vez).
3. Pressione **F5** (ou use `npm run watch` em paralelo para rebuild automático).
4. Na janela "Extension Development Host", abra a view de Chat e digite
   `@o11yia <sua pergunta>`.
5. Rode `O11yIA: Send Test Metric` para validar o backend sem o Copilot.

## Empacotar e instalar via .vsix

```powershell
npm install -g @vscode/vsce   # se ainda não tiver o vsce
npm run package               # gera o11yia-vscode-0.1.0.vsix
code --install-extension o11yia-vscode-0.1.0.vsix
```

## Teste ponta a ponta (sugerido)

1. Suba o backend O11yIA (`docker-compose up` na raiz do projeto).
2. Configure `o11yia.serverUrl`, `o11yia.userId`, `o11yia.apiKey`, `o11yia.team`.
3. Rode **O11yIA: Send Test Metric** → mensagem de sucesso e a métrica deve aparecer
   no dashboard.
4. Use `@o11yia olá` no Chat → tokens aparecem na status bar; após 30s (ou
   **Sync Now**) são enviados em batch.
