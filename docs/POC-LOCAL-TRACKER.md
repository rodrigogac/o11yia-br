# POC v2: Tracker LOCAL de AI Credits do Copilot

**Cenário:** Time de 18 pessoas (devs, PO, estagiários) usando Copilot em:
- VSCode
- IntelliJ/JetBrains
- Browser (github.com)

**Problema:** API do GitHub tem delay de 2 dias e não mostra uso real-time por pessoa.

**Solução:** Coleta LOCAL em cada máquina + envio para servidor central.

---

## 1. Arquitetura da Solução LOCAL

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     MÁQUINA DO DESENVOLVEDOR                              │
│                                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                  │
│  │   VSCode    │    │  IntelliJ   │    │   Browser   │                  │
│  │  + Copilot  │    │  + Copilot  │    │  github.com │                  │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                  │
│         │                  │                  │                          │
│         ▼                  ▼                  ▼                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                  │
│  │  OTEL/Logs  │    │  IDEA Logs  │    │  Extension  │                  │
│  │  (nativo!)  │    │  (parsear)  │    │  (Chrome)   │                  │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                  │
│         │                  │                  │                          │
│         └──────────────────┼──────────────────┘                          │
│                            │                                             │
│                   ┌────────▼────────┐                                    │
│                   │  LOCAL AGENT    │  ◄── App Electron/Tauri           │
│                   │  (consolida     │      ou daemon Python              │
│                   │   e envia)      │                                    │
│                   └────────┬────────┘                                    │
│                            │                                             │
└────────────────────────────┼─────────────────────────────────────────────┘
                             │
                             │ HTTP POST (intranet)
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│                     SERVIDOR CENTRAL (SETID)                              │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────┐             │
│  │                    COLLECTOR API                         │             │
│  │  POST /usage { user, source, model, tokens, timestamp }  │             │
│  └───────────────────────────┬─────────────────────────────┘             │
│                              │                                            │
│                   ┌──────────▼──────────┐                                │
│                   │  Database (SQLite)  │                                │
│                   └──────────┬──────────┘                                │
│                              │                                            │
│                   ┌──────────▼──────────┐                                │
│                   │  Dashboard Streamlit │                               │
│                   │  + Alertas Telegram  │                               │
│                   └─────────────────────┘                                │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Coleta por Plataforma

### 2.1 VSCode — OpenTelemetry NATIVO (Melhor opção!)

**Descoberta importante:** VSCode Copilot Chat já exporta OpenTelemetry nativamente!

**Configuração (settings.json do VSCode):**
```json
{
  "github.copilot.chat.otel.enabled": true,
  "github.copilot.chat.otel.exporterType": "otlp-http",
  "github.copilot.chat.otel.otlpEndpoint": "http://servidor-setid:4318",
  "github.copilot.chat.otel.captureContent": false
}
```

**Dados exportados automaticamente:**
| Métrica | Descrição |
|---------|-----------|
| `gen_ai.client.token.usage` | Input/output tokens por request |
| `invoke_agent` | Tempo total de sessão |
| `chat` | Cada chamada LLM individual |
| `execute_tool` | Ferramentas usadas |

**Atributos disponíveis:**
- `gen_ai.request.model` — Qual modelo (gpt-4o, claude, etc)
- `gen_ai.usage.input_tokens` — Tokens de entrada
- `gen_ai.usage.output_tokens` — Tokens de saída
- `gen_ai.agent.name` — Nome do agente

**Alternativa: Usar extensão pronta**

Já existe extensão que faz isso: `winter0729.github-copilot-token-tracker`
- Dashboard local com uso diário/mensal
- Persistente entre restarts
- Custo estimado por modelo

### 2.2 IntelliJ/JetBrains — Logs + Plugin

**Plugin existente:** `GitHub Copilot Premium Quota Monitor`
- Mostra quota restante
- Monitora uso premium

**Logs nativos (onde ficam):**
- Windows: `%APPDATA%\JetBrains\<IDE>\log\idea.log`
- Mac: `~/Library/Logs/JetBrains/<IDE>/idea.log`
- Linux: `~/.cache/JetBrains/<IDE>/log/idea.log`

**Parser para extrair uso:**
```python
import re
from pathlib import Path

def parse_idea_copilot_logs(log_path: str):
    """Extrai eventos do Copilot dos logs do IntelliJ"""
    pattern = r"Copilot.*tokens?.*(\d+)"
    
    with open(log_path) as f:
        for line in f:
            if "copilot" in line.lower():
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    yield {
                        "timestamp": extract_timestamp(line),
                        "tokens": int(match.group(1)),
                        "raw": line
                    }
```

### 2.3 Browser (github.com) — Extension Chrome/Edge

**Abordagem:** Interceptar requests para `api.github.com/copilot`

**Manifest v3 (Chrome Extension):**
```json
{
  "manifest_version": 3,
  "name": "Copilot Usage Tracker - SETID",
  "version": "1.0",
  "permissions": [
    "webRequest",
    "storage"
  ],
  "host_permissions": [
    "https://api.github.com/*",
    "https://copilot-proxy.githubusercontent.com/*"
  ],
  "background": {
    "service_worker": "background.js"
  }
}
```

**Background script (intercepta requests):**
```javascript
// background.js
const COLLECTOR_URL = "http://servidor-setid:8080/usage";

// Monitora requests para API do Copilot
chrome.webRequest.onCompleted.addListener(
  async (details) => {
    if (details.url.includes("copilot") && details.method === "POST") {
      // Extrai response headers com token usage
      const tokenHeader = details.responseHeaders?.find(
        h => h.name.toLowerCase() === "x-copilot-tokens"
      );
      
      if (tokenHeader) {
        const usage = JSON.parse(tokenHeader.value);
        
        // Envia para collector
        await fetch(COLLECTOR_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user: await getGitHubUser(),
            source: "browser",
            timestamp: new Date().toISOString(),
            model: usage.model,
            tokens_input: usage.input_tokens,
            tokens_output: usage.output_tokens
          })
        });
      }
    }
  },
  { urls: ["https://api.github.com/*", "https://copilot-proxy.githubusercontent.com/*"] },
  ["responseHeaders"]
);

async function getGitHubUser() {
  // Busca username logado
  const response = await fetch("https://api.github.com/user");
  const data = await response.json();
  return data.login;
}
```

---

## 3. Agente Local Consolidador

Pequeno app que roda em background na máquina do dev.

### 3.1 Opção A: Daemon Python (Simples)

```python
#!/usr/bin/env python3
"""
copilot_local_agent.py
Daemon que coleta uso do Copilot de múltiplas fontes e envia para servidor central.
"""

import os
import json
import time
import sqlite3
import requests
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuração
COLLECTOR_URL = os.environ.get("COPILOT_COLLECTOR_URL", "http://servidor-setid:8080/usage")
USERNAME = os.environ.get("COPILOT_USERNAME", os.environ.get("USER", "unknown"))
TEAM = os.environ.get("COPILOT_TEAM", "sem-time")
SYNC_INTERVAL = 60  # segundos

# Paths dos logs do Copilot por plataforma
VSCODE_OTEL_DB = Path.home() / ".vscode" / "copilot-traces.db"
IDEA_LOG = Path.home() / ".cache" / "JetBrains" / "IntelliJIdea2024.2" / "log" / "idea.log"

class UsageCollector:
    def __init__(self):
        self.pending_events = []
        self.local_db = sqlite3.connect(":memory:")
        self._init_db()
    
    def _init_db(self):
        self.local_db.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                source TEXT,
                model TEXT,
                tokens_input INTEGER,
                tokens_output INTEGER,
                synced INTEGER DEFAULT 0
            )
        """)
    
    def collect_vscode_otel(self):
        """Coleta do banco SQLite exportado pelo OTel do VSCode"""
        if not VSCODE_OTEL_DB.exists():
            return
        
        try:
            conn = sqlite3.connect(str(VSCODE_OTEL_DB))
            cursor = conn.cursor()
            
            # Busca spans de chat com token usage
            cursor.execute("""
                SELECT 
                    timestamp,
                    json_extract(attributes, '$.gen_ai.request.model') as model,
                    json_extract(attributes, '$.gen_ai.usage.input_tokens') as input_tokens,
                    json_extract(attributes, '$.gen_ai.usage.output_tokens') as output_tokens
                FROM spans
                WHERE name = 'chat'
                AND timestamp > datetime('now', '-1 hour')
            """)
            
            for row in cursor.fetchall():
                self.pending_events.append({
                    "timestamp": row[0],
                    "source": "vscode",
                    "model": row[1] or "gpt-4o",
                    "tokens_input": row[2] or 0,
                    "tokens_output": row[3] or 0
                })
            
            conn.close()
        except Exception as e:
            print(f"Erro ao coletar VSCode: {e}")
    
    def collect_intellij_logs(self):
        """Parseia logs do IntelliJ"""
        if not IDEA_LOG.exists():
            return
        
        # Implementar parser de logs
        # ...
    
    def sync_to_server(self):
        """Envia eventos pendentes para servidor central"""
        if not self.pending_events:
            return
        
        payload = {
            "user": USERNAME,
            "team": TEAM,
            "events": self.pending_events
        }
        
        try:
            response = requests.post(
                COLLECTOR_URL,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✓ Sincronizado {len(self.pending_events)} eventos")
                self.pending_events = []
            else:
                print(f"✗ Erro ao sincronizar: {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            print(f"✗ Falha de conexão: {e}")
            # Mantém eventos para próxima tentativa
    
    def run(self):
        """Loop principal"""
        print(f"🚀 Copilot Usage Agent iniciado")
        print(f"   User: {USERNAME}")
        print(f"   Team: {TEAM}")
        print(f"   Collector: {COLLECTOR_URL}")
        
        while True:
            self.collect_vscode_otel()
            self.collect_intellij_logs()
            self.sync_to_server()
            time.sleep(SYNC_INTERVAL)


if __name__ == "__main__":
    collector = UsageCollector()
    collector.run()
```

### 3.2 Opção B: App Electron/Tauri (Com UI)

Para dar feedback visual ao dev:

```
┌─────────────────────────────────────┐
│  🤖 Copilot Tracker - SETID         │
├─────────────────────────────────────┤
│                                     │
│  Hoje: 142 créditos                 │
│  ████████████░░░░░░░░ 35%           │
│                                     │
│  Semana: 891 créditos               │
│  Média time: 756 créditos           │
│                                     │
│  Status: ✅ Sincronizado            │
│                                     │
└─────────────────────────────────────┘
```

---

## 4. Servidor Collector Central

### 4.1 API (FastAPI)

```python
#!/usr/bin/env python3
"""
collector_server.py
Servidor central que recebe uso de todos os agentes locais.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import sqlite3

app = FastAPI(title="Copilot Usage Collector - SETID")

# Database
DB_PATH = "copilot_usage.db"

class UsageEvent(BaseModel):
    timestamp: str
    source: str  # vscode, intellij, browser
    model: str
    tokens_input: int
    tokens_output: int

class UsagePayload(BaseModel):
    user: str
    team: str
    events: List[UsageEvent]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT NOT NULL,
            team TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            source TEXT NOT NULL,
            model TEXT NOT NULL,
            tokens_input INTEGER,
            tokens_output INTEGER,
            estimated_credits REAL,
            received_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user ON usage(user)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_team ON usage(team)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON usage(timestamp)")
    conn.commit()
    conn.close()

def calculate_credits(tokens_in: int, tokens_out: int, model: str) -> float:
    """Calcula AI Credits estimados"""
    pricing = {
        "gpt-4o": {"in": 2.50, "out": 10.00},
        "gpt-4o-mini": {"in": 0.15, "out": 0.60},
        "claude-sonnet-4": {"in": 3.00, "out": 15.00},
        "o1": {"in": 15.00, "out": 60.00},
    }
    
    p = pricing.get(model, pricing["gpt-4o"])
    cost_in = (tokens_in / 1_000_000) * p["in"] * 100
    cost_out = (tokens_out / 1_000_000) * p["out"] * 100
    
    return round(cost_in + cost_out, 2)

@app.on_event("startup")
def startup():
    init_db()

@app.post("/usage")
async def receive_usage(payload: UsagePayload):
    """Recebe eventos de uso de um agente local"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for event in payload.events:
        credits = calculate_credits(
            event.tokens_input,
            event.tokens_output,
            event.model
        )
        
        cursor.execute("""
            INSERT INTO usage (user, team, timestamp, source, model, 
                             tokens_input, tokens_output, estimated_credits)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.user,
            payload.team,
            event.timestamp,
            event.source,
            event.model,
            event.tokens_input,
            event.tokens_output,
            credits
        ))
    
    conn.commit()
    conn.close()
    
    return {"status": "ok", "events_received": len(payload.events)}

@app.get("/stats/team/{team}")
async def get_team_stats(team: str, days: int = 7):
    """Estatísticas por time"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            user,
            SUM(estimated_credits) as total_credits,
            SUM(tokens_input) as total_input,
            SUM(tokens_output) as total_output,
            COUNT(*) as request_count
        FROM usage
        WHERE team = ?
        AND timestamp > datetime('now', ?)
        GROUP BY user
        ORDER BY total_credits DESC
    """, (team, f"-{days} days"))
    
    users = []
    total = 0
    
    for row in cursor.fetchall():
        users.append({
            "user": row[0],
            "credits": row[1],
            "tokens_input": row[2],
            "tokens_output": row[3],
            "requests": row[4]
        })
        total += row[1]
    
    conn.close()
    
    return {
        "team": team,
        "period_days": days,
        "total_credits": total,
        "users": users
    }

@app.get("/stats/user/{user}")
async def get_user_stats(user: str, days: int = 7):
    """Estatísticas por usuário"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            date(timestamp) as day,
            source,
            model,
            SUM(estimated_credits) as credits,
            SUM(tokens_input + tokens_output) as tokens
        FROM usage
        WHERE user = ?
        AND timestamp > datetime('now', ?)
        GROUP BY date(timestamp), source, model
        ORDER BY day DESC
    """, (user, f"-{days} days"))
    
    daily = []
    for row in cursor.fetchall():
        daily.append({
            "date": row[0],
            "source": row[1],
            "model": row[2],
            "credits": row[3],
            "tokens": row[4]
        })
    
    conn.close()
    
    return {"user": user, "daily": daily}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

---

## 5. Cobertura por Plataforma

| Plataforma | Método de Coleta | Esforço | Precisão |
|------------|-----------------|---------|----------|
| **VSCode** | OTel nativo | ⭐ Baixo | 100% |
| **IntelliJ** | Plugin + logs | ⭐⭐ Médio | ~90% |
| **Browser** | Chrome Extension | ⭐⭐ Médio | ~95% |
| **CLI** | Logs / OTel | ⭐ Baixo | 100% |

### VSCode: Melhor cobertura
O Copilot Chat no VSCode já exporta OpenTelemetry com:
- Token usage por request
- Modelo usado
- Tempo de resposta
- Tool calls (agents)

**Configuração centralizada via GPO/MDM:**
```json
// Política para todas as máquinas
{
  "github.copilot.chat.otel.enabled": true,
  "github.copilot.chat.otel.otlpEndpoint": "http://collector.setid.intranet:4318"
}
```

---

## 6. Plano de Implementação

### Fase 1: VSCode Only (1 semana)
1. Subir collector OTEL (Aspire Dashboard ou Jaeger)
2. Distribuir settings.json via GPO
3. Dashboard básico Streamlit
4. **Cobertura:** ~70% do uso (VSCode é majoritário)

### Fase 2: IntelliJ (Semana 2)
1. Desenvolver plugin simples
2. Ou: parser de logs com daemon
3. Integrar com collector

### Fase 3: Browser (Semana 3)
1. Extension Chrome/Edge
2. Distribuir via política de extensões
3. Integrar com collector

### Fase 4: Dashboard Final (Semana 4)
1. UI para gestor
2. Alertas por threshold
3. Export para relatórios

---

## 7. Privacidade e Compliance

**O que NÃO coletamos:**
- Conteúdo dos prompts (código)
- Conteúdo das respostas
- Dados pessoais além de username

**O que coletamos:**
- Username (para atribuição)
- Timestamps
- Modelo usado
- Quantidade de tokens
- Origem (vscode/intellij/browser)

**Transparência:**
- Agente local mostra ao dev seu próprio uso
- Dev pode ver dashboard individual
- Comunicar previamente ao time

---

## 8. Alternativa: Usar Extensão Existente

Se não quiser desenvolver, já existem extensões prontas:

### VSCode
- `winter0729.github-copilot-token-tracker` — Dashboard completo, custo estimado
- `emagin8.copilot-usage` — Global dashboard, comparativo de workspaces

### IntelliJ
- `GitHub Copilot Premium Quota Monitor` — Mostra quota restante

**Problema:** Essas extensões não enviam para servidor central. Seriam úteis para cada dev ver seu próprio uso, mas gestor não teria visão consolidada.

---

## Próximos Passos Imediatos

1. [ ] Validar se VSCode é majoritário no time (vs IntelliJ)
2. [ ] Subir Aspire Dashboard ou Jaeger local para teste
3. [ ] Configurar `github.copilot.chat.otel.enabled` em uma máquina
4. [ ] Ver traces aparecendo no dashboard
5. [ ] Decidir: extensão existente vs desenvolvimento próprio
