# O11yIA BR — Validação do OTel nativo do Copilot Chat (VSCode)

Este diretório contém o **passo a passo de validação** da estratégia
**"OTel nativo → fallback cliente próprio"** para captura de uso de tokens
do GitHub Copilot Chat no VSCode.

> **TL;DR honesto:** As settings `github.copilot.chat.otel.*` **EXISTEM e são reais**
> (introduzidas no VS Code **1.119**, maio/2026 — ver "Resultado da pesquisa" abaixo).
> Elas exportam traces/métricas OTLP seguindo as **GenAI Semantic Conventions**,
> incluindo `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens`.
> **PORÉM** existem 3 ressalvas importantes que precisam de validação em máquina real
> (ver seção 6) antes de adotar como fonte única:
> 1. O recurso só cobre o **modo Agente** do Copilot Chat (não há garantia de que
>    completions inline / chat simples gerem spans com tokens).
> 2. O endpoint precisa ser um **coletor OTLP padrão** (`:4318` HTTP), **não** o
>    endpoint `/v1/traces` do backend O11yIA diretamente — a menos que o backend
>    implemente o protocolo OTLP. Veja seção 5.
> 3. A disponibilidade depende da versão instalada do VSCode/extensão Copilot Chat.
>
> Se a validação falhar, o **fallback é a extensão própria** em
> [`../vscode-extension/`](../vscode-extension/), que funciona independentemente.

---

## 1. Resultado da pesquisa: as settings OTel existem? (jun/2026)

**SIM, existem.** A pesquisa na web confirmou que o GitHub Copilot Chat para VSCode
ganhou exportação OpenTelemetry nativa no **VS Code 1.119 (release de maio/2026)**.

### Settings confirmadas (nomes EXATOS, da documentação oficial)

| Setting | Tipo | Default | Função |
|---------|------|---------|--------|
| `github.copilot.chat.otel.enabled` | boolean | `false` | Habilita emissão OTel |
| `github.copilot.chat.otel.exporterType` | string | `"otlp-http"` | `otlp-http`, `otlp-grpc`, `console` ou `file` |
| `github.copilot.chat.otel.otlpEndpoint` | string | `"http://localhost:4318"` | URL do coletor OTLP |
| `github.copilot.chat.otel.captureContent` | boolean | `false` | Captura prompt/resposta completos (privacidade!) |
| `github.copilot.chat.otel.maxAttributeSizeChars` | integer | `0` | Limite de truncamento (0 = desabilitado) |
| `github.copilot.chat.otel.outfile` | string | `""` | Caminho para saída JSON-lines |
| `github.copilot.chat.otel.dbSpanExporter.enabled` | boolean | `false` | Persiste spans em SQLite local |

Variáveis de ambiente equivalentes (têm precedência sobre as settings):
`COPILOT_OTEL_ENABLED`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `COPILOT_OTEL_ENDPOINT`,
`COPILOT_OTEL_PROTOCOL`, `COPILOT_OTEL_CAPTURE_CONTENT`.

### Atributos GenAI exportados (token usage)

Seguem as **OpenTelemetry GenAI Semantic Conventions**:

- Span `invoke_agent`: `gen_ai.operation.name`, `gen_ai.provider.name`,
  `gen_ai.agent.name`, `gen_ai.conversation.id`,
  `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`
- Span `chat`: `gen_ai.request.model`, `gen_ai.response.model`,
  `gen_ai.response.finish_reasons`, `gen_ai.usage.cache_read.input_tokens`
- Span `execute_tool`: `gen_ai.tool.name`, `gen_ai.tool.type`, `gen_ai.tool.call.id`
- Métrica `gen_ai.client.token.usage`: histograma de tokens, filtrável por
  `gen_ai.token.type` (input/output).

### Portas OTLP

- HTTP/protobuf (default): **`http://localhost:4318`** (exporter anexa `/v1/traces`).
- gRPC: **`http://localhost:4317`** (use `exporterType: "otlp-grpc"`).

### ⚠️ Divergência com a doc interna

O `docs/POC-LOCAL-TRACKER.md` (seção 2.1) e o `deploy/configure-vscode.sh` afirmavam
que o OTel "já existia" e apontavam o endpoint para `http://SERVIDOR:8080/v1/traces`.
A pesquisa confirma que **o recurso de fato existe** (a doc interna estava certa no
conceito), **mas**:

- A doc interna citava `github.copilot.chat.otel.exporterType: "otlp-http"` e
  `github.copilot.chat.otel.serviceName` — `exporterType` existe e está correto;
  **`serviceName` NÃO aparece** na lista oficial de settings. Não use `serviceName`.
- Apontar o `otlpEndpoint` direto para `:8080/v1/traces` do O11yIA **só funciona se
  o backend O11yIA aceitar OTLP**. Caso contrário, é preciso um **coletor OTLP no
  meio** que traduza/encaminhe (seção 5).

### Fontes

- Monitor agent usage with OpenTelemetry — docs oficiais VS Code:
  https://code.visualstudio.com/docs/copilot/guides/monitoring-agents
- vscode-copilot-chat — agent_monitoring.md:
  https://github.com/microsoft/vscode-copilot-chat/blob/main/docs/monitoring/agent_monitoring.md
- VS Code 1.119 release notes:
  https://code.visualstudio.com/updates/v1_119
- Visual Studio Magazine — "VS Code 1.119 Adds ... OpenTelemetry Tracing":
  https://visualstudiomagazine.com/articles/2026/05/07/vs-code-1-119-adds-agent-browser-sharing-opentelemetry-tracing.aspx
- Meta issue — Agent Observability based on OpenTelemetry (microsoft/vscode#293225):
  https://github.com/microsoft/vscode/issues/293225
- OpenTelemetry GenAI Semantic Conventions:
  https://opentelemetry.io/blog/2026/genai-observability/

---

## 2. Pré-requisitos da validação

- VSCode **1.119 ou superior** (confira em `Help > About` / `Code > Sobre`).
- Extensão **GitHub Copilot Chat** instalada e logada com licença ativa.
- Docker disponível (para subir o coletor OTLP local), OU use o exporter `console`
  (seção 4, opção rápida sem container).

---

## 3. Passo 1 — Inspecionar se as settings do Copilot Chat existem nesta máquina

Antes de configurar, **confirme que as chaves existem na sua versão**:

1. Abra o VSCode.
2. `Ctrl+Shift+P` → **Preferences: Open Settings (UI)**.
3. Na barra de busca digite: `copilot.chat.otel`
   - **Se aparecerem** as opções (Enabled, Otlp Endpoint, Exporter Type...):
     a versão suporta OTel nativo. ✅
   - **Se NÃO aparecer nada**: sua versão do Copilot Chat é antiga ou removeu o
     recurso. Atualize VSCode + extensão. Se ainda assim não aparecer → vá direto ao
     **fallback** (extensão própria, seção 7). ❌
4. Alternativa por linha de comando (lista todas as settings registradas que casam):
   - `Ctrl+Shift+P` → **Developer: Show Running Extensions** confirma o Copilot Chat ativo.
   - Para ver o schema completo de settings registradas, abra o
     **settings.json** e comece a digitar `"github.copilot.chat.otel.` — o
     autocomplete só sugere chaves que **realmente existem** no schema da sua versão.
     Se o autocomplete não sugerir nada, as chaves não existem.

> Critério deste passo: se o autocomplete/Settings UI **não reconhece**
> `github.copilot.chat.otel.enabled`, pare aqui e use o fallback.

---

## 4. Passo 2 — Subir um coletor OTLP local para ver os traces

Você precisa de "olhos" no que o Copilot exporta. Três opções, da mais simples à mais real.

### Opção A (mais rápida, sem container): exporter `console`

Aponta a saída para o próprio Output do VSCode / arquivo. Use o
[`settings.example.console.json`](./settings.example.console.json):

```jsonc
{
  "github.copilot.chat.otel.enabled": true,
  "github.copilot.chat.otel.exporterType": "file",
  "github.copilot.chat.otel.outfile": "C:\\temp\\copilot-otel.jsonl"
}
```

Depois de usar o Copilot (modo Agente), abra `C:\temp\copilot-otel.jsonl` e procure
por linhas com `gen_ai.usage.input_tokens`. Se aparecerem → **funciona**.

### Opção B: Aspire Dashboard (UI bonita, recomendado)

```powershell
docker run --rm -it -p 18888:18888 -p 4318:18890 `
  mcr.microsoft.com/dotnet/aspire-dashboard:latest
```

Abra `http://localhost:18888` (o terminal mostra um token de login na primeira vez).
Use [`settings.example.json`](./settings.example.json) apontando para `http://localhost:4318`.

### Opção C: OpenTelemetry Collector (mais próximo de produção)

Suba o Collector com a config de exemplo deste diretório
([`otel-collector-config.yaml`](./otel-collector-config.yaml)), que recebe OTLP e
imprime no log (`debug` exporter) — útil para confirmar a chegada dos traces:

```powershell
docker run --rm -it -p 4317:4317 -p 4318:4318 `
  -v "${PWD}/otel-collector-config.yaml:/etc/otelcol/config.yaml" `
  otel/opentelemetry-collector:latest
```

Você verá os spans `invoke_agent` / `chat` no log do container, com os atributos
`gen_ai.usage.*`. Em produção esse collector encaminharia para o backend O11yIA
(seção 5).

### Opção D: Jaeger

```powershell
docker run --rm -it -p 16686:16686 -p 4318:4318 jaegertracing/jaeger:latest
```
Abra `http://localhost:16686`.

---

## 5. Passo 3 — Apontar para o backend O11yIA

O arquivo [`settings.example.o11yia.json`](./settings.example.o11yia.json) aponta o
endpoint para o backend O11yIA:

```jsonc
{
  "github.copilot.chat.otel.enabled": true,
  "github.copilot.chat.otel.exporterType": "otlp-http",
  "github.copilot.chat.otel.otlpEndpoint": "http://SERVIDOR:8080"
}
```

> **IMPORTANTE / honestidade técnica:** o exporter HTTP do OpenTelemetry **anexa
> automaticamente `/v1/traces`** ao `otlpEndpoint`. Portanto:
> - Configure `otlpEndpoint` como **`http://SERVIDOR:8080`** (base), e o Copilot
>   enviará para `http://SERVIDOR:8080/v1/traces` (que é o endpoint que a doc interna
>   mencionava). **Não inclua `/v1/traces` manualmente**, ou viraria
>   `.../v1/traces/v1/traces`.
> - Isso **só funciona se o backend O11yIA implementar ingestão OTLP** nesse caminho.
>   O backend O11yIA da PoC expõe `/v1/metrics` (JSON próprio), **não** OTLP. Logo,
>   na prática você precisa de um **OTel Collector no meio** (Opção C) configurado
>   para receber OTLP do Copilot e re-exportar/transformar para o formato do O11yIA,
>   OU validar com o backend se ele aceita OTLP nativo.
> - Para a **PoC**, recomenda-se: validar a chegada dos traces num collector local
>   (seções 4B/4C) e, em paralelo, usar a **extensão própria** (fallback) que fala
>   o protocolo JSON do O11yIA diretamente.

---

## 6. Critério claro: FUNCIONOU vs NÃO FUNCIONOU

### ✅ FUNCIONOU se TODOS forem verdadeiros:

1. As settings `github.copilot.chat.otel.*` aparecem no autocomplete/Settings UI.
2. Após habilitar e **usar o Copilot Chat em modo Agente**, chegam spans no coletor.
3. Os spans contêm `gen_ai.usage.input_tokens` e `gen_ai.usage.output_tokens` com
   valores > 0 e `gen_ai.request.model` preenchido.

### ❌ NÃO FUNCIONOU se QUALQUER um ocorrer:

- As settings não existem na versão instalada.
- Nenhum span chega ao coletor depois de usar o Copilot.
- Spans chegam **mas sem** os atributos `gen_ai.usage.*` (sem contagem de tokens).
- Só funciona no modo Agente e o time usa majoritariamente completions inline /
  chat simples (cobertura insuficiente para a PoC).

### O que reportar (template)

```
Máquina: <SO / versão>
VSCode: <versão>  | Copilot Chat: <versão>
Settings otel.* visíveis no autocomplete? (sim/não)
Coletor usado: (console/aspire/collector/jaeger)
Spans chegaram? (sim/não)  | Tipos: (invoke_agent/chat/execute_tool)
gen_ai.usage.input_tokens presente? (sim/não, exemplo de valor)
gen_ai.usage.output_tokens presente? (sim/não, exemplo de valor)
Cobriu completions inline / chat simples? (sim/não)
Conclusão: FUNCIONOU / NÃO FUNCIONOU
Observações:
```

---

## 7. Fallback (se NÃO funcionou)

Se a validação falhar (ou a cobertura for insuficiente), use a **extensão VSCode
própria** em [`../vscode-extension/`](../vscode-extension/). Ela:

- Não depende do OTel nativo nem da API oficial do GitHub Copilot.
- Captura via **Chat Participant API** (`@o11yia`) e/ou **Language Model API**
  (`vscode.lm`), estimando/contando tokens.
- Envia direto para `POST /v1/metrics` e `/v1/metrics/batch` do backend O11yIA
  (protocolo JSON da PoC), com fila + flush em batch.

Veja o README da extensão para build (`npm install && npm run build`), F5 e `vsce package`.
