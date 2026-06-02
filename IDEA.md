# O11yIA BR — Observabilidade para Gateways de Inferência AI

**Data:** 2026-05-30
**Status:** Pesquisa / Ideação
**Categoria:** SaaS B2B
**Mercado-alvo:** Times de engenharia brasileiros usando LLMs em produção

---

## 1. Contexto de Mercado

### 1.1 Tendência Macro: Explosion de AI Gateways
O mercado de gateways de inferência explodiu em 2025-2026:
- **Pioneer:** >999% growth (dados OpenRouter)
- **opengateway:** +100%, #4 global, 98.7B tokens processados
- Juntos representam ~12% do volume do top 20

### 1.2 Players Atuais (Gateways)
| Gateway | Foco Principal | Ponto Forte | Fraqueza |
|---------|---------------|-------------|----------|
| **LiteLLM** | Open-source proxy | 100+ providers | Sem guardrails nativos |
| **Portkey** | Managed control plane | Semantic caching, guardrails | Pricing por volume, vendor lock-in |
| **Kong AI** | Enterprise security | OAuth 2.0, mTLS | Alto overhead operacional |
| **Helicone** | Performance (Rust) | 8ms P50 latency | RBAC/governance imaturos |
| **Bifrost** | Performance (Go) | 11µs overhead @ 5K RPS | Menos providers (20+) |
| **FloTorch** | Agentic workflows | Stack completo, no-code | Complexidade |

### 1.3 Players de Observabilidade AI
| Plataforma | Foco | Limitação |
|-----------|------|-----------|
| **Arize AI** | RAG debugging, drift | Não roteia tráfego |
| **Datadog LLM** | Full-stack APM | Generalista, não AI-first |
| **LangSmith** | LangChain ecosystem | Lock-in LangChain |
| **WhyLabs** | Data quality, bias | MLOps tradicional |
| **Maxim AI** | Evaluation + O11y | Acoplado ao Bifrost |

### 1.4 Adoção no Brasil
- **67% das empresas** posicionam AI como prioridade estratégica (2025)
- **72% ainda em estágio inicial** de adoção
- **R$ 23 bilhões** em investimento governo até 2029
- **14% aumento produtividade** em empresas com IA generativa
- ANPD publicou **Portaria nº 5/2024** sobre IA e dados pessoais

---

## 2. Gap Identificado

### 2.1 O Problema Central
> **"Com a multiplicação de gateways de inferência, times de engenharia não têm ferramentas para monitorar, auditar e otimizar o tráfego entre MÚLTIPLOS gateways e modelos."**

### 2.2 Desafio Específico: Medir Inferência por Time
Dentro de uma organização, o tráfego de tokens passa pela rede de formas dispersas:
- Diferentes times usam diferentes gateways
- Cada gateway tem seu próprio dashboard (se tiver)
- Dados de uso fragmentados entre providers
- Sem visão consolidada de custos por departamento
- Impossível responder: "Quanto o time de Marketing gastou em LLM esse mês?"

### 2.3 Limitações das Soluções Atuais

**Gateways (Bifrost, LiteLLM, Portkey):**
- Focam em SER o gateway, não em observar MÚLTIPLOS gateways
- Attribution limitada ao próprio tráfego
- Não agregam dados de concorrentes

**Observabilidade tradicional (Datadog, New Relic):**
- Generalistas — AI é um add-on
- Não entendem semântica de tokens
- Não fazem cost attribution por team/projeto
- Pricing enterprise inviável para startups BR

**Observabilidade AI-native (Arize, WhyLabs):**
- Focados em qualidade de modelo (drift, bias)
- Não são control plane de custos
- Não integram com múltiplos gateways

---

## 3. Proposta: O11yIA BR

### 3.1 Posicionamento
> **"Datadog/New Relic dos gateways de IA — observabilidade pura, agnóstico de gateway"**

### 3.2 Diferenciais

| Dimensão | Portkey | Helicone | O11yIA BR |
|----------|---------|----------|-----------|
| Foco | Gateway + governance | Gateway + logging | **O11y pura** |
| Multi-gateway | ❌ | ❌ | ✅ |
| Cost attribution | Por virtual key | Por request | **Por team/projeto/feature** |
| LGPD | ❓ | ❓ | **Nativo** |
| Mercado BR | Global | Global | **BR-first** |

### 3.3 Features Propostas

**Tier 1: Dashboards de Custo**
- Custo por modelo, agente, feature, time
- Breakdown: input/output/reasoning tokens
- Comparativo histórico (trend)
- Multi-provider consolidado (OpenAI + Anthropic + Bedrock)

**Tier 2: Anomaly Detection**
- Alerta de spike de latência
- Detecção de "runaway agents" (loops recursivos)
- Budget enforcement com soft/hard limits
- Rate limiting por consumer

**Tier 3: Otimização**
- Recomendação automática de modelos mais baratos
- "Este prompt poderia usar Claude Haiku em vez de Opus (-85% custo)"
- Semantic similarity para detectar duplicação

**Tier 4: Compliance LGPD**
- Scanner de PII em prompts/responses
- Relatórios de quais dados sensíveis trafegaram
- Audit trail completo
- Alerta quando dados de CPF/RG/saúde passam pelo gateway

### 3.4 Arquitetura Conceitual

```
┌─────────────────────────────────────────────────────────────┐
│                    Aplicações do Cliente                     │
└────────────────┬──────────────┬──────────────┬──────────────┘
                 │              │              │
                 ▼              ▼              ▼
         ┌───────────┐  ┌───────────┐  ┌───────────┐
         │  LiteLLM  │  │  Portkey  │  │  Bifrost  │
         └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
               │              │              │
               └──────────────┼──────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   O11yIA Agent    │ ◄── Sidecar/Proxy
                    │   (coleta logs)   │     ou SDK leve
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │   O11yIA Cloud    │
                    │  ┌─────────────┐  │
                    │  │ Ingest API  │  │
                    │  └──────┬──────┘  │
                    │         ▼         │
                    │  ┌─────────────┐  │
                    │  │ TimeSeries  │  │
                    │  │  (ClickHouse) │ │
                    │  └──────┬──────┘  │
                    │         ▼         │
                    │  ┌─────────────┐  │
                    │  │ Dashboards  │  │
                    │  │   Alertas   │  │
                    │  │   LGPD      │  │
                    │  └─────────────┘  │
                    └───────────────────┘
```

### 3.5 Integração: Como Capturar Dados?

**Opção A: SDK Leve (mais invasivo)**
```python
from o11yia import track

@track(team="marketing", feature="chatbot")
def generate_response(prompt):
    return openai.chat.completions.create(...)
```

**Opção B: Proxy Sidecar (menos invasivo)**
- Deploy como sidecar que intercepta HTTP
- Zero code change no cliente
- Mais overhead de rede

**Opção C: Export via OTLP (ideal)**
- Gateways que suportam OpenTelemetry exportam traces
- O11yIA consome como backend OTLP
- Arize/Phoenix já fazem isso

---

## 4. Análise de Viabilidade

### 4.1 Pontos a Favor
- **Timing:** Explosão de gateways cria fragmentação → demanda por consolidação
- **Brasil:** 72% ainda em estágio inicial → capturar early adopters
- **LGPD:** Regulamentação específica (Portaria 5/2024) cria necessidade
- **Pricing:** Mercado global caro; BR-first com preço em BRL
- **Open-source:** Bifrost/Helicone são OSS → integração fácil

### 4.2 Riscos e Desafios
- **Gateways podem expandir O11y:** Bifrost+Maxim já fazem isso
- **Datadog pode lançar feature:** Já têm LLM monitoring beta
- **Adoção de SDK:** Times resistem a instrumentação extra
- **Fragmentação de protocolos:** Cada gateway exporta diferente

### 4.3 Moat Potencial
1. **BR-first compliance:** Scanner LGPD nativo (CPF, RG, dados de saúde)
2. **Multi-gateway from day 1:** Posicionamento único
3. **Pricing em BRL:** Competitivo para startups BR
4. **Comunidade local:** Integrações com ecossistema BR

---

## 5. Próximos Passos

- [ ] Validar demanda: Entrevistar 5-10 eng managers BR usando LLMs
- [ ] Mapear integrações: Quais gateways têm export OTLP/logs?
- [ ] MVP scope: Começar com LiteLLM (mais popular OSS)
- [ ] Estudo LGPD: Quais dados AI são "sensíveis" segundo Portaria 5/2024
- [ ] Competitor deep-dive: Testar Helicone/Portkey free tiers
- [ ] Pricing research: Quanto times BR pagam por observabilidade?

---

## 6. Referências

- FloTorch LLM Gateway Comparison 2026
- Maxim AI - Tracking LLM Token Usage
- Braintrust - 7 Best AI Observability Platforms 2025
- Galileo - 6 Best LLM Monitoring Solutions Enterprise
- ANPD - Portaria nº 5/2024 (IA e dados pessoais)
- Pesquisa Pipefy - Adoção IA Brasil 2025
