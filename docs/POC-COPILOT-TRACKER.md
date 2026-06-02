# POC: Tracker de AI Credits do GitHub Copilot para Times

**Data:** 2026-05-30
**Cenário:** Órgão público (SETID/TCU) com 18 pessoas usando Copilot Enterprise
**Problema:** Gestor precisa medir uso por time/pessoa de forma fácil e dinâmica

---

## 1. O Problema Real

### 1.1 Contexto da Mudança (1º Junho 2026)

**Antes:** Taxa fixa por usuário, uso ilimitado
**Depois:** Pool de créditos compartilhado por time

| Plano | Créditos/usuário/mês | Pool total (18 pessoas) |
|-------|---------------------|------------------------|
| Enterprise (promo) | 7.000 | 126.000 créditos |
| Enterprise (normal) | 3.900 | 70.200 créditos |

**1 AI Credit = $0.01 USD**

### 1.2 O que Consome Créditos

| Feature | Consome? | Observação |
|---------|----------|------------|
| Code completions | ❌ NÃO | Ilimitado |
| Next edit suggestions | ❌ NÃO | Ilimitado |
| Copilot Chat | ✅ SIM | Varia por modelo |
| Copilot CLI | ✅ SIM | |
| Copilot Agents | ✅ SIM | Alto consumo |
| Copilot Spaces | ✅ SIM | |

### 1.3 Dor do Gestor

O GitHub oferece:
- Pool compartilhado no nível da organização
- API de métricas agregadas
- Dashboard enterprise

**O que NÃO oferece nativamente:**
- Visão em tempo real por pessoa
- Alertas quando indivíduo está gastando muito
- Projeção "vai estourar em X dias"
- Dashboard simples para o gestor não-técnico

---

## 2. Arquitetura da Solução

### 2.1 Três Camadas de Coleta

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAMADA 1: COLETA LOCAL                        │
│  (Extensão VSCode na máquina de cada dev)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│   │  Dev 1       │  │  Dev 2       │  │  Dev N       │          │
│   │  VSCode +    │  │  VSCode +    │  │  VSCode +    │          │
│   │  Extension   │  │  Extension   │  │  Extension   │          │
│   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│          │                 │                 │                   │
│          └─────────────────┼─────────────────┘                   │
│                            │                                     │
│                            ▼                                     │
│              ┌─────────────────────────┐                         │
│              │  Collector Service      │  ◄── Intranet/VPN      │
│              │  (Node.js ou Python)    │                         │
│              └───────────┬─────────────┘                         │
│                          │                                       │
└──────────────────────────┼───────────────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────────────┐
│                    CAMADA 2: API GITHUB                          │
├──────────────────────────┼───────────────────────────────────────┤
│                          │                                       │
│              ┌───────────▼─────────────┐                         │
│              │  GitHub REST API        │                         │
│              │  /copilot/metrics       │                         │
│              └───────────┬─────────────┘                         │
│                          │                                       │
│   Endpoints usados:                                              │
│   • GET /orgs/{org}/copilot/metrics/reports/users-1-day          │
│   • GET /enterprises/{ent}/copilot/metrics/reports/user-teams    │
│   • GET /orgs/{org}/copilot/billing/seats                        │
│                          │                                       │
└──────────────────────────┼───────────────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────────────┐
│                    CAMADA 3: DASHBOARD                           │
├──────────────────────────┼───────────────────────────────────────┤
│                          │                                       │
│              ┌───────────▼─────────────┐                         │
│              │  Database (SQLite/PG)   │                         │
│              └───────────┬─────────────┘                         │
│                          │                                       │
│              ┌───────────▼─────────────┐                         │
│              │  Dashboard Web          │                         │
│              │  (Next.js ou Streamlit) │                         │
│              └─────────────────────────┘                         │
│                                                                  │
│   Features:                                                      │
│   • Uso por pessoa/time em tempo real                            │
│   • Projeção de esgotamento                                      │
│   • Alertas via email/Teams/Telegram                             │
│   • Export para planilha                                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Opções de Implementação

#### Opção A: Extensão VSCode Local (Mais Granular)

**Prós:**
- Dados em tempo real
- Vê CADA interação do dev
- Funciona offline (sync depois)

**Contras:**
- Precisa instalar em cada máquina
- Privacidade (dev vê que está sendo monitorado)
- Manutenção de extensão

**Extensões existentes que podemos usar/adaptar:**
1. `emagin8.copilot-usage` - Já faz tracking de tokens
2. `ethanhubin/copilot-usage-tracker` - Open source
3. `JaydipChangani.copilot-tracker` - Simples, 430 installs

#### Opção B: API GitHub Oficial (Mais Simples)

**Prós:**
- Sem instalação local
- Dados oficiais do GitHub
- Já disponível (changelog 14/Mai/2026: team-level metrics)

**Contras:**
- Delay de 2 dias úteis nos dados
- Menos granular (não vê cada prompt)
- Depende de telemetria habilitada

#### Opção C: Híbrido (Recomendado)

- **API GitHub** para dados oficiais e histórico
- **Extensão leve** para alertas em tempo real

---

## 3. POC Técnica: Script de Coleta via API

### 3.1 Pré-requisitos

```bash
# Token GitHub com permissões:
# - read:org
# - manage_billing:copilot
# - copilot (se usar GitHub App)

export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
export GITHUB_ORG="setid-tcu"  # ou nome da org
```

### 3.2 Script Python: Coletor de Métricas

```python
#!/usr/bin/env python3
"""
copilot_metrics_collector.py
Coleta métricas de uso do Copilot por usuário e time
"""

import os
import json
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class UserUsage:
    username: str
    team: str
    date: str
    chat_requests: int
    chat_tokens_input: int
    chat_tokens_output: int
    agent_sessions: int
    agent_tokens: int
    estimated_credits: float

class CopilotMetricsCollector:
    def __init__(self, token: str, org: str):
        self.token = token
        self.org = org
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10"
        }
    
    def get_users_usage(self, date: str = None) -> List[Dict]:
        """
        Busca uso por usuário para uma data específica
        Endpoint: GET /orgs/{org}/copilot/metrics/reports/users-1-day
        """
        if date is None:
            # Dados de 2 dias atrás (delay padrão)
            date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        
        url = f"{self.base_url}/orgs/{self.org}/copilot/metrics/reports/users-1-day"
        params = {"date": date}
        
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            # Retorna link para download do report
            report_url = response.json().get("download_url")
            if report_url:
                return self._download_report(report_url)
        
        return []
    
    def get_user_teams_mapping(self) -> Dict[str, List[str]]:
        """
        Busca mapeamento usuário -> times
        Endpoint: GET /orgs/{org}/copilot/metrics/reports/user-teams
        """
        url = f"{self.base_url}/orgs/{self.org}/copilot/metrics/reports/user-teams"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            report_url = response.json().get("download_url")
            if report_url:
                data = self._download_report(report_url)
                # Mapeia username -> [team1, team2, ...]
                return {
                    row["username"]: row.get("teams", [])
                    for row in data
                }
        
        return {}
    
    def get_billing_seats(self) -> List[Dict]:
        """
        Lista todos os seats ativos
        Endpoint: GET /orgs/{org}/copilot/billing/seats
        """
        url = f"{self.base_url}/orgs/{self.org}/copilot/billing/seats"
        
        all_seats = []
        page = 1
        
        while True:
            response = requests.get(
                url, 
                headers=self.headers, 
                params={"per_page": 100, "page": page}
            )
            
            if response.status_code != 200:
                break
            
            data = response.json()
            seats = data.get("seats", [])
            
            if not seats:
                break
            
            all_seats.extend(seats)
            page += 1
        
        return all_seats
    
    def _download_report(self, url: str) -> List[Dict]:
        """Baixa e parseia report NDJSON"""
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            lines = response.text.strip().split("\n")
            return [json.loads(line) for line in lines if line]
        
        return []
    
    def calculate_credits(self, tokens_input: int, tokens_output: int, 
                          model: str = "gpt-4o") -> float:
        """
        Estima AI Credits consumidos
        Baseado em: https://docs.github.com/copilot/reference/copilot-billing/models-and-pricing
        """
        # Pricing aproximado por modelo (credits per 1M tokens)
        MODEL_PRICING = {
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "claude-sonnet": {"input": 3.00, "output": 15.00},
            "claude-haiku": {"input": 0.25, "output": 1.25},
            "o1": {"input": 15.00, "output": 60.00},
        }
        
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4o"])
        
        input_cost = (tokens_input / 1_000_000) * pricing["input"] * 100  # cents -> credits
        output_cost = (tokens_output / 1_000_000) * pricing["output"] * 100
        
        return round(input_cost + output_cost, 2)
    
    def generate_team_report(self, days: int = 7) -> Dict:
        """
        Gera relatório agregado por time
        """
        # Coleta user-teams mapping
        user_teams = self.get_user_teams_mapping()
        
        # Coleta uso dos últimos N dias
        team_usage = {}
        
        for i in range(2, days + 2):  # Começa em 2 dias atrás
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_usage = self.get_users_usage(date)
            
            for user_data in daily_usage:
                username = user_data.get("username")
                teams = user_teams.get(username, ["sem-time"])
                
                for team in teams:
                    if team not in team_usage:
                        team_usage[team] = {
                            "total_credits": 0,
                            "users": {},
                            "daily": {}
                        }
                    
                    # Agrega por usuário
                    if username not in team_usage[team]["users"]:
                        team_usage[team]["users"][username] = 0
                    
                    # Calcula créditos (estimativa)
                    credits = self.calculate_credits(
                        user_data.get("chat_tokens_input", 0),
                        user_data.get("chat_tokens_output", 0)
                    )
                    
                    team_usage[team]["users"][username] += credits
                    team_usage[team]["total_credits"] += credits
                    
                    # Agrega por dia
                    if date not in team_usage[team]["daily"]:
                        team_usage[team]["daily"][date] = 0
                    team_usage[team]["daily"][date] += credits
        
        return team_usage


def main():
    token = os.environ.get("GITHUB_TOKEN")
    org = os.environ.get("GITHUB_ORG", "setid-tcu")
    
    if not token:
        print("Erro: GITHUB_TOKEN não definido")
        return
    
    collector = CopilotMetricsCollector(token, org)
    
    print(f"📊 Coletando métricas do Copilot para {org}...")
    print("=" * 60)
    
    # Lista seats ativos
    seats = collector.get_billing_seats()
    print(f"\n👥 Seats ativos: {len(seats)}")
    
    # Gera relatório por time
    report = collector.generate_team_report(days=7)
    
    print("\n📈 USO POR TIME (últimos 7 dias):")
    print("-" * 60)
    
    for team, data in sorted(report.items(), key=lambda x: x[1]["total_credits"], reverse=True):
        print(f"\n🏷️  {team}")
        print(f"   Total: {data['total_credits']:.0f} créditos")
        print(f"   Usuários: {len(data['users'])}")
        
        # Top 3 usuários
        top_users = sorted(data["users"].items(), key=lambda x: x[1], reverse=True)[:3]
        for username, credits in top_users:
            print(f"      • {username}: {credits:.0f} créditos")
    
    # Projeção
    total_used = sum(d["total_credits"] for d in report.values())
    daily_avg = total_used / 7
    pool_total = len(seats) * 7000  # Enterprise promo
    days_to_exhaust = (pool_total - total_used) / daily_avg if daily_avg > 0 else float('inf')
    
    print("\n" + "=" * 60)
    print("📉 PROJEÇÃO:")
    print(f"   Pool total: {pool_total:,.0f} créditos")
    print(f"   Usado (7d): {total_used:,.0f} créditos ({100*total_used/pool_total:.1f}%)")
    print(f"   Média diária: {daily_avg:,.0f} créditos")
    print(f"   Esgota em: ~{days_to_exhaust:.0f} dias")


if __name__ == "__main__":
    main()
```

### 3.3 Extensão VSCode Simplificada

Para coleta em tempo real, criar extensão que:

1. **Intercepta requisições** do Copilot (via proxy local)
2. **Conta tokens** por interação
3. **Envia para servidor** interno via HTTP POST

```typescript
// extension.ts (esqueleto)
import * as vscode from 'vscode';

const COLLECTOR_URL = "http://interno.setid.tcu.gov.br:8080/copilot-usage";

interface UsageEvent {
    user: string;
    timestamp: string;
    feature: "chat" | "agent" | "cli";
    model: string;
    tokens_input: number;
    tokens_output: number;
    estimated_credits: number;
}

export function activate(context: vscode.ExtensionContext) {
    // Lê logs do Copilot do diretório local
    // ~/.config/github-copilot/versions.json contém sessões
    
    // Monitora mudanças e envia para collector
    const watcher = vscode.workspace.createFileSystemWatcher(
        "**/.copilot/**/*.json"
    );
    
    watcher.onDidChange(async (uri) => {
        const content = await vscode.workspace.fs.readFile(uri);
        const data = JSON.parse(content.toString());
        
        // Extrai métricas e envia
        const event: UsageEvent = {
            user: vscode.env.machineId, // ou username configurado
            timestamp: new Date().toISOString(),
            feature: "chat",
            model: data.model || "gpt-4o",
            tokens_input: data.prompt_tokens || 0,
            tokens_output: data.completion_tokens || 0,
            estimated_credits: calculateCredits(data)
        };
        
        // Envia para collector (fire and forget)
        fetch(COLLECTOR_URL, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(event)
        }).catch(() => {}); // Ignora erros de rede
    });
    
    // Status bar com uso atual
    const statusBar = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right, 100
    );
    statusBar.text = "$(pulse) Copilot: 0 créditos";
    statusBar.show();
    
    context.subscriptions.push(watcher, statusBar);
}

function calculateCredits(data: any): number {
    // Pricing simplificado
    const inputCost = (data.prompt_tokens || 0) * 0.0000025;
    const outputCost = (data.completion_tokens || 0) * 0.00001;
    return Math.round((inputCost + outputCost) * 100); // cents -> credits
}
```

---

## 4. Dashboard para o Gestor

### 4.1 MVP com Streamlit (Rápido de Implementar)

```python
#!/usr/bin/env python3
"""
dashboard.py - Dashboard Streamlit para gestores
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Copilot Usage - SETID", layout="wide")

st.title("📊 Dashboard de Uso do GitHub Copilot")
st.caption("Monitoramento de AI Credits por time")

# Sidebar: filtros
st.sidebar.header("Filtros")
team_filter = st.sidebar.multiselect(
    "Times",
    ["Backend", "Frontend", "DevOps", "QA", "Estagiários"],
    default=["Backend", "Frontend"]
)

date_range = st.sidebar.date_input(
    "Período",
    value=(datetime.now() - timedelta(days=7), datetime.now()),
    max_value=datetime.now()
)

# Métricas principais
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Pool Total",
        value="126.000",
        help="18 usuários × 7.000 créditos (promo)"
    )

with col2:
    st.metric(
        label="Usado (mês)",
        value="45.230",
        delta="-12% vs semana passada",
        delta_color="inverse"
    )

with col3:
    st.metric(
        label="Dias Restantes",
        value="23",
        delta="⚠️ Risco médio" if True else "✅ OK"
    )

with col4:
    st.metric(
        label="Média/Usuário/Dia",
        value="142",
        help="Créditos consumidos por dia por pessoa"
    )

st.divider()

# Gráfico de uso por time
st.subheader("Uso por Time")

# Dados mock (substituir por API real)
df_teams = pd.DataFrame({
    "Time": ["Backend", "Frontend", "DevOps", "QA", "Estagiários"],
    "Créditos": [18500, 12300, 8200, 4100, 2130],
    "Pessoas": [6, 5, 3, 2, 2]
})
df_teams["Média/Pessoa"] = df_teams["Créditos"] / df_teams["Pessoas"]

fig = px.bar(
    df_teams, 
    x="Time", 
    y="Créditos",
    color="Média/Pessoa",
    color_continuous_scale="RdYlGn_r",
    text_auto=True
)
st.plotly_chart(fig, use_container_width=True)

# Tabela de usuários
st.subheader("Top Consumidores")

df_users = pd.DataFrame({
    "Usuário": ["joao.silva", "maria.santos", "pedro.costa", "ana.lima", "carlos.dev"],
    "Time": ["Backend", "Backend", "Frontend", "DevOps", "Backend"],
    "Créditos (7d)": [4200, 3800, 3100, 2900, 2700],
    "% do Pool": [3.3, 3.0, 2.5, 2.3, 2.1],
    "Trend": ["↑ +15%", "→ 0%", "↓ -8%", "↑ +22%", "→ +2%"]
})

st.dataframe(
    df_users,
    column_config={
        "% do Pool": st.column_config.ProgressColumn(
            format="%.1f%%",
            min_value=0,
            max_value=10
        )
    },
    hide_index=True,
    use_container_width=True
)

# Alertas
st.subheader("⚠️ Alertas")

alerts = [
    {"level": "warning", "msg": "Time DevOps usou 85% do budget projetado"},
    {"level": "info", "msg": "joao.silva está 22% acima da média do time"},
    {"level": "success", "msg": "Consumo geral 12% menor que semana passada"},
]

for alert in alerts:
    if alert["level"] == "warning":
        st.warning(alert["msg"])
    elif alert["level"] == "info":
        st.info(alert["msg"])
    else:
        st.success(alert["msg"])

# Export
st.divider()
st.download_button(
    label="📥 Exportar CSV",
    data=df_users.to_csv(index=False),
    file_name=f"copilot_usage_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv"
)
```

### 4.2 Alertas Automáticos

```python
# alerts.py - Sistema de alertas via Telegram/Email

from typing import List
import requests

TELEGRAM_BOT_TOKEN = "xxx"
TELEGRAM_CHAT_ID = "-100xxx"  # Grupo do time

def check_alerts(team_usage: dict, pool_total: int) -> List[str]:
    """Verifica condições de alerta"""
    alerts = []
    
    for team, data in team_usage.items():
        # Alerta se time usa mais de 50% do pool proporcional
        team_size = len(data["users"])
        team_budget = (team_size / 18) * pool_total
        
        if data["total_credits"] > team_budget * 0.5:
            alerts.append(
                f"⚠️ {team}: {data['total_credits']:.0f} créditos "
                f"({100*data['total_credits']/team_budget:.0f}% do budget)"
            )
        
        # Alerta por usuário outlier
        avg_user = data["total_credits"] / team_size if team_size > 0 else 0
        for user, credits in data["users"].items():
            if credits > avg_user * 2:
                alerts.append(
                    f"📊 {user} ({team}): {credits:.0f} créditos "
                    f"(2x acima da média do time)"
                )
    
    return alerts

def send_telegram_alert(message: str):
    """Envia alerta para Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    })
```

---

## 5. Plano de Implementação

### Fase 1: MVP (1 semana)

| Dia | Entrega |
|-----|---------|
| 1 | Setup: criar PAT GitHub, testar API |
| 2 | Script Python de coleta funcionando |
| 3 | Banco SQLite + carga histórica |
| 4 | Dashboard Streamlit básico |
| 5 | Deploy interno + acesso gestor |

### Fase 2: Alertas (Semana 2)

- Integração Telegram/Teams
- Cron de coleta diária
- Alertas de threshold

### Fase 3: Extensão VSCode (Semana 3-4)

- Extensão local para dados real-time
- Sync com servidor central
- Status bar para cada dev

---

## 6. Custos e Recursos

### Infraestrutura

| Item | Custo | Nota |
|------|-------|------|
| Servidor interno | R$ 0 | Usar VM existente |
| GitHub API | Grátis | Limites generosos |
| Streamlit Cloud | Grátis | Tier free |
| Extensão VSCode | Grátis | Distribuição interna |

### Esforço

| Perfil | Horas |
|--------|-------|
| Dev Python | 20h |
| Dev TypeScript (extensão) | 16h |
| Testes | 8h |
| Deploy | 4h |
| **Total** | **48h** |

---

## 7. Próximos Passos Imediatos

1. [ ] Obter PAT GitHub com permissões corretas
2. [ ] Testar endpoint `/orgs/{org}/copilot/metrics/reports/users-1-day`
3. [ ] Mapear times no GitHub (já existem?)
4. [ ] Definir thresholds de alerta com gestor
5. [ ] Escolher stack: Streamlit vs Next.js

---

## Referências

- [GitHub Docs: Usage-based billing](https://docs.github.com/copilot/concepts/billing/usage-based-billing-for-organizations-and-enterprises)
- [GitHub Changelog: Team-level metrics API (14/Mai/2026)](https://github.blog/changelog/2026-05-14-team-level-copilot-usage-metrics-now-available-via-api)
- [GitHub REST API: Copilot Metrics](https://docs.github.com/rest/copilot/copilot-usage-metrics)
- [Copilot Usage Extension (VSCode)](https://marketplace.visualstudio.com/items?itemName=emagin8.copilot-usage)
