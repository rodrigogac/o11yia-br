#!/usr/bin/env python3
"""
copilot_metrics_poc.py
POC: Coleta de métricas do GitHub Copilot por usuário/time

Uso:
    export GITHUB_TOKEN="ghp_xxxx"
    export GITHUB_ORG="setid-tcu"
    python copilot_metrics_poc.py

Requer: requests, python-dateutil
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import sqlite3

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_ORG = os.environ.get("GITHUB_ORG", "sua-org")
DB_PATH = "copilot_usage.db"

# Pricing por modelo (AI Credits per 1M tokens)
# Fonte: https://docs.github.com/copilot/reference/copilot-billing/models-and-pricing
MODEL_PRICING = {
    "gpt-4o": {"input": 250, "output": 1000},        # $2.50/$10 per 1M
    "gpt-4o-mini": {"input": 15, "output": 60},      # $0.15/$0.60 per 1M
    "claude-sonnet-4": {"input": 300, "output": 1500},
    "claude-haiku": {"input": 25, "output": 125},
    "o1": {"input": 1500, "output": 6000},
    "o1-mini": {"input": 300, "output": 1200},
    "default": {"input": 250, "output": 1000},       # fallback
}

# Planos e créditos mensais
PLAN_CREDITS = {
    "business": 1900,
    "enterprise": 3900,
    "business_promo": 3000,    # Jun-Ago 2026
    "enterprise_promo": 7000,  # Jun-Ago 2026
}


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class UserUsage:
    username: str
    date: str
    feature: str  # chat, agent, cli
    model: str
    tokens_input: int
    tokens_output: int
    estimated_credits: float
    teams: List[str]


@dataclass
class TeamSummary:
    team: str
    total_credits: float
    user_count: int
    avg_per_user: float
    top_user: str
    top_user_credits: float


# ============================================================================
# GITHUB API CLIENT
# ============================================================================

class CopilotMetricsClient:
    """Cliente para API de métricas do Copilot"""
    
    def __init__(self, token: str, org: str):
        self.token = token
        self.org = org
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10"
        }
    
    def _get(self, endpoint: str, params: dict = None) -> requests.Response:
        """GET request com headers padrão"""
        url = f"{self.base_url}{endpoint}"
        return requests.get(url, headers=self.headers, params=params)
    
    def _download_ndjson(self, url: str) -> List[Dict]:
        """Baixa e parseia report NDJSON"""
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            return []
        
        lines = response.text.strip().split("\n")
        return [json.loads(line) for line in lines if line.strip()]
    
    def get_billing_info(self) -> Dict:
        """
        Informações de billing da org
        GET /orgs/{org}/copilot/billing
        """
        response = self._get(f"/orgs/{self.org}/copilot/billing")
        if response.status_code == 200:
            return response.json()
        return {}
    
    def get_seats(self) -> List[Dict]:
        """
        Lista seats ativos
        GET /orgs/{org}/copilot/billing/seats
        """
        all_seats = []
        page = 1
        
        while True:
            response = self._get(
                f"/orgs/{self.org}/copilot/billing/seats",
                params={"per_page": 100, "page": page}
            )
            
            if response.status_code != 200:
                print(f"Erro ao buscar seats: {response.status_code}")
                print(response.text)
                break
            
            data = response.json()
            seats = data.get("seats", [])
            
            if not seats:
                break
            
            all_seats.extend(seats)
            page += 1
        
        return all_seats
    
    def get_user_teams_mapping(self) -> Dict[str, List[str]]:
        """
        Mapeamento usuário -> times
        GET /orgs/{org}/copilot/metrics/reports/user-teams
        """
        response = self._get(f"/orgs/{self.org}/copilot/metrics/reports/user-teams")
        
        if response.status_code != 200:
            print(f"Erro ao buscar user-teams: {response.status_code}")
            return {}
        
        data = response.json()
        download_url = data.get("download_url")
        
        if not download_url:
            return {}
        
        rows = self._download_ndjson(download_url)
        return {
            row["username"]: row.get("teams", ["sem-time"])
            for row in rows
        }
    
    def get_users_usage_day(self, date: str) -> List[Dict]:
        """
        Uso por usuário em um dia específico
        GET /orgs/{org}/copilot/metrics/reports/users-1-day?date=YYYY-MM-DD
        
        Nota: dados disponíveis com 2 dias de delay
        """
        response = self._get(
            f"/orgs/{self.org}/copilot/metrics/reports/users-1-day",
            params={"date": date}
        )
        
        if response.status_code != 200:
            print(f"Erro ao buscar usage para {date}: {response.status_code}")
            return []
        
        data = response.json()
        download_url = data.get("download_url")
        
        if not download_url:
            return []
        
        return self._download_ndjson(download_url)
    
    def get_org_metrics(self) -> Dict:
        """
        Métricas agregadas da org (últimos 28 dias)
        GET /orgs/{org}/copilot/metrics
        """
        response = self._get(f"/orgs/{self.org}/copilot/metrics")
        
        if response.status_code == 200:
            return response.json()
        return {}


# ============================================================================
# CÁLCULO DE CRÉDITOS
# ============================================================================

def calculate_credits(tokens_input: int, tokens_output: int, model: str = "gpt-4o") -> float:
    """
    Calcula AI Credits estimados baseado em tokens e modelo
    
    1 AI Credit = $0.01 USD
    """
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
    
    # Créditos = (tokens / 1M) * (preço em cents)
    input_credits = (tokens_input / 1_000_000) * pricing["input"]
    output_credits = (tokens_output / 1_000_000) * pricing["output"]
    
    return round(input_credits + output_credits, 2)


def estimate_daily_avg(usage_data: List[Dict], days: int) -> float:
    """Calcula média diária de créditos"""
    total = sum(
        calculate_credits(
            u.get("chat_tokens_input", 0) + u.get("agent_tokens_input", 0),
            u.get("chat_tokens_output", 0) + u.get("agent_tokens_output", 0),
            u.get("model", "gpt-4o")
        )
        for u in usage_data
    )
    return total / days if days > 0 else 0


# ============================================================================
# DATABASE (SQLite)
# ============================================================================

def init_db(db_path: str = DB_PATH):
    """Inicializa banco SQLite"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            date TEXT NOT NULL,
            feature TEXT,
            model TEXT,
            tokens_input INTEGER,
            tokens_output INTEGER,
            estimated_credits REAL,
            teams TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(username, date, feature, model)
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_usage_date ON usage(date)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_usage_username ON usage(username)
    """)
    
    conn.commit()
    return conn


def save_usage(conn: sqlite3.Connection, usage: UserUsage):
    """Salva registro de uso no banco"""
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO usage 
        (username, date, feature, model, tokens_input, tokens_output, estimated_credits, teams)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        usage.username,
        usage.date,
        usage.feature,
        usage.model,
        usage.tokens_input,
        usage.tokens_output,
        usage.estimated_credits,
        json.dumps(usage.teams)
    ))
    
    conn.commit()


def get_team_summary(conn: sqlite3.Connection, days: int = 7) -> List[TeamSummary]:
    """Gera resumo por time dos últimos N dias"""
    cursor = conn.cursor()
    
    min_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    # Query para agregar por time
    cursor.execute("""
        SELECT 
            json_each.value as team,
            SUM(estimated_credits) as total_credits,
            COUNT(DISTINCT username) as user_count,
            username,
            MAX(estimated_credits) as max_credits
        FROM usage, json_each(teams)
        WHERE date >= ?
        GROUP BY json_each.value
        ORDER BY total_credits DESC
    """, (min_date,))
    
    results = []
    for row in cursor.fetchall():
        team, total, user_count, top_user, top_credits = row
        results.append(TeamSummary(
            team=team,
            total_credits=total,
            user_count=user_count,
            avg_per_user=total / user_count if user_count > 0 else 0,
            top_user=top_user,
            top_user_credits=top_credits
        ))
    
    return results


# ============================================================================
# RELATÓRIOS
# ============================================================================

def print_report(client: CopilotMetricsClient, conn: sqlite3.Connection):
    """Imprime relatório formatado"""
    
    print("\n" + "=" * 70)
    print("📊 RELATÓRIO DE USO DO GITHUB COPILOT")
    print("=" * 70)
    
    # Info da org
    billing = client.get_billing_info()
    seats = client.get_seats()
    
    plan = billing.get("plan_type", "enterprise")
    is_promo = datetime.now() < datetime(2026, 9, 1)
    credits_per_user = PLAN_CREDITS.get(f"{plan}_promo" if is_promo else plan, 3900)
    total_pool = len(seats) * credits_per_user
    
    print(f"\n🏢 Organização: {client.org}")
    print(f"📋 Plano: {plan.upper()} {'(período promocional)' if is_promo else ''}")
    print(f"👥 Seats ativos: {len(seats)}")
    print(f"💰 Pool total: {total_pool:,} créditos/mês")
    print(f"   ({credits_per_user:,} por usuário)")
    
    # Resumo por time
    print("\n" + "-" * 70)
    print("📈 USO POR TIME (últimos 7 dias)")
    print("-" * 70)
    
    summaries = get_team_summary(conn, days=7)
    
    for s in summaries:
        pct = (s.total_credits / total_pool * 100) if total_pool > 0 else 0
        bar = "█" * int(pct / 2) + "░" * (50 - int(pct / 2))
        
        print(f"\n🏷️  {s.team}")
        print(f"   Total: {s.total_credits:,.0f} créditos ({pct:.1f}% do pool)")
        print(f"   [{bar}]")
        print(f"   Usuários: {s.user_count} | Média: {s.avg_per_user:,.0f}/usuário")
        print(f"   Top: {s.top_user} ({s.top_user_credits:,.0f} créditos)")
    
    # Projeção
    total_used_7d = sum(s.total_credits for s in summaries)
    daily_avg = total_used_7d / 7
    days_in_month = 30
    projected_monthly = daily_avg * days_in_month
    
    print("\n" + "-" * 70)
    print("📉 PROJEÇÃO MENSAL")
    print("-" * 70)
    
    print(f"   Média diária: {daily_avg:,.0f} créditos")
    print(f"   Projeção mensal: {projected_monthly:,.0f} créditos")
    
    if projected_monthly > total_pool:
        overage = projected_monthly - total_pool
        overage_cost = overage * 0.01  # 1 credit = $0.01
        print(f"   ⚠️  RISCO: Projeção {overage:,.0f} créditos ACIMA do pool!")
        print(f"   💸 Custo extra estimado: ${overage_cost:,.2f} USD")
    else:
        remaining = total_pool - projected_monthly
        print(f"   ✅ Projeção dentro do pool ({remaining:,.0f} créditos de margem)")
    
    # Dias restantes
    used_this_month = total_used_7d  # simplificação
    remaining_credits = total_pool - used_this_month
    days_to_exhaust = remaining_credits / daily_avg if daily_avg > 0 else float('inf')
    
    print(f"\n   Créditos restantes: {remaining_credits:,.0f}")
    print(f"   Esgota em: ~{days_to_exhaust:.0f} dias (ritmo atual)")
    
    print("\n" + "=" * 70)


# ============================================================================
# MAIN
# ============================================================================

def main():
    # Validação
    if not GITHUB_TOKEN:
        print("❌ Erro: GITHUB_TOKEN não definido")
        print("   export GITHUB_TOKEN='ghp_xxxx'")
        sys.exit(1)
    
    print(f"🔧 Conectando à org: {GITHUB_ORG}")
    
    # Inicializa cliente e banco
    client = CopilotMetricsClient(GITHUB_TOKEN, GITHUB_ORG)
    conn = init_db()
    
    # Busca mapeamento user -> teams
    print("📥 Buscando mapeamento de times...")
    user_teams = client.get_user_teams_mapping()
    print(f"   {len(user_teams)} usuários mapeados")
    
    # Coleta uso dos últimos 7 dias (começa em D-2 por causa do delay)
    print("📥 Coletando métricas de uso...")
    
    for i in range(2, 9):  # D-2 até D-8
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        print(f"   {date}...", end=" ")
        
        daily_data = client.get_users_usage_day(date)
        
        for row in daily_data:
            username = row.get("username", "unknown")
            teams = user_teams.get(username, ["sem-time"])
            
            # Chat usage
            if row.get("chat_requests", 0) > 0:
                usage = UserUsage(
                    username=username,
                    date=date,
                    feature="chat",
                    model=row.get("chat_model", "gpt-4o"),
                    tokens_input=row.get("chat_tokens_input", 0),
                    tokens_output=row.get("chat_tokens_output", 0),
                    estimated_credits=calculate_credits(
                        row.get("chat_tokens_input", 0),
                        row.get("chat_tokens_output", 0),
                        row.get("chat_model", "gpt-4o")
                    ),
                    teams=teams
                )
                save_usage(conn, usage)
            
            # Agent usage
            if row.get("agent_sessions", 0) > 0:
                usage = UserUsage(
                    username=username,
                    date=date,
                    feature="agent",
                    model=row.get("agent_model", "gpt-4o"),
                    tokens_input=row.get("agent_tokens_input", 0),
                    tokens_output=row.get("agent_tokens_output", 0),
                    estimated_credits=calculate_credits(
                        row.get("agent_tokens_input", 0),
                        row.get("agent_tokens_output", 0),
                        row.get("agent_model", "gpt-4o")
                    ),
                    teams=teams
                )
                save_usage(conn, usage)
        
        print(f"{len(daily_data)} registros")
    
    # Gera relatório
    print_report(client, conn)
    
    conn.close()


if __name__ == "__main__":
    main()
