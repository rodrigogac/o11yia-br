"""
O11yIA BR - Servidor Central de Métricas de IA
Receptor OTLP + API REST para coleta de métricas do Copilot

Recebe dados de:
- VSCode (via OTel nativo)
- IntelliJ Plugin (via HTTP POST)
- Chrome Extension (via HTTP POST)
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn


# ============================================================
# CONFIGURAÇÃO
# ============================================================

DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/metrics.db")

# Custos em créditos (baseado na documentação GitHub Jun/2026)
CREDIT_COSTS = {
    "gpt-4o": {"input": 0.00025, "output": 0.001},  # por token
    "gpt-4o-mini": {"input": 0.000015, "output": 0.00006},
    "claude-sonnet-4": {"input": 0.0003, "output": 0.0015},
    "o3-mini": {"input": 0.00011, "output": 0.00044},
    "default": {"input": 0.0002, "output": 0.0008}
}

# Pool de créditos
CREDITS_PER_USER_PROMO = 7000  # Jun-Ago 2026
CREDITS_PER_USER_NORMAL = 3900  # Set 2026+
TEAM_SIZE = 18


# ============================================================
# MODELOS PYDANTIC
# ============================================================

class TokenMetric(BaseModel):
    """Métrica de tokens enviada pelos plugins"""
    user_id: str
    source: str  # vscode, intellij, browser
    model: str
    input_tokens: int
    output_tokens: int
    timestamp: Optional[str] = None
    session_id: Optional[str] = None
    context: Optional[str] = None  # chat, completion, inline


class UserSummary(BaseModel):
    """Resumo de uso por usuário"""
    user_id: str
    total_credits: float
    total_input_tokens: int
    total_output_tokens: int
    by_source: dict
    by_model: dict
    last_activity: str


# ============================================================
# DATABASE
# ============================================================

def init_db():
    """Inicializa o banco SQLite"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            source TEXT NOT NULL,
            model TEXT NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            credits_used REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            session_id TEXT,
            context TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            display_name TEXT,
            team TEXT DEFAULT 'default',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_metrics_user 
        ON metrics(user_id, timestamp)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_metrics_date 
        ON metrics(date(timestamp))
    """)
    
    conn.commit()
    conn.close()


def calculate_credits(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calcula créditos baseado no modelo e tokens"""
    costs = CREDIT_COSTS.get(model.lower(), CREDIT_COSTS["default"])
    return (input_tokens * costs["input"]) + (output_tokens * costs["output"])


def save_metric(metric: TokenMetric) -> dict:
    """Salva métrica no banco"""
    credits = calculate_credits(metric.model, metric.input_tokens, metric.output_tokens)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Upsert do usuário
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id) VALUES (?)
    """, (metric.user_id,))
    
    # Inserir métrica
    cursor.execute("""
        INSERT INTO metrics 
        (user_id, source, model, input_tokens, output_tokens, credits_used, timestamp, session_id, context)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        metric.user_id,
        metric.source,
        metric.model,
        metric.input_tokens,
        metric.output_tokens,
        credits,
        metric.timestamp or datetime.utcnow().isoformat(),
        metric.session_id,
        metric.context
    ))
    
    conn.commit()
    conn.close()
    
    return {"credits_used": credits, "id": cursor.lastrowid}


def get_team_summary(days: int = 30) -> dict:
    """Retorna resumo do time"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    # Total do time
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT user_id) as active_users,
            SUM(input_tokens) as total_input,
            SUM(output_tokens) as total_output,
            SUM(credits_used) as total_credits
        FROM metrics 
        WHERE timestamp >= ?
    """, (since,))
    
    row = cursor.fetchone()
    
    # Por usuário
    cursor.execute("""
        SELECT 
            user_id,
            SUM(credits_used) as credits,
            SUM(input_tokens) as input_tokens,
            SUM(output_tokens) as output_tokens,
            MAX(timestamp) as last_activity
        FROM metrics 
        WHERE timestamp >= ?
        GROUP BY user_id
        ORDER BY credits DESC
    """, (since,))
    
    users = []
    for r in cursor.fetchall():
        users.append({
            "user_id": r[0],
            "credits": round(r[1], 2),
            "input_tokens": r[2],
            "output_tokens": r[3],
            "last_activity": r[4]
        })
    
    # Por fonte
    cursor.execute("""
        SELECT source, SUM(credits_used) as credits
        FROM metrics 
        WHERE timestamp >= ?
        GROUP BY source
    """, (since,))
    
    by_source = {r[0]: round(r[1], 2) for r in cursor.fetchall()}
    
    # Por modelo
    cursor.execute("""
        SELECT model, SUM(credits_used) as credits
        FROM metrics 
        WHERE timestamp >= ?
        GROUP BY model
        ORDER BY credits DESC
        LIMIT 10
    """, (since,))
    
    by_model = {r[0]: round(r[1], 2) for r in cursor.fetchall()}
    
    conn.close()
    
    # Calcular pool
    is_promo = datetime.utcnow().month in [6, 7, 8] and datetime.utcnow().year == 2026
    credits_per_user = CREDITS_PER_USER_PROMO if is_promo else CREDITS_PER_USER_NORMAL
    total_pool = credits_per_user * TEAM_SIZE
    used = row[3] or 0
    
    return {
        "period": "promo" if is_promo else "normal",
        "pool": {
            "total": total_pool,
            "used": round(used, 2),
            "remaining": round(total_pool - used, 2),
            "percent_used": round((used / total_pool) * 100, 1) if total_pool > 0 else 0
        },
        "stats": {
            "active_users": row[0] or 0,
            "total_input_tokens": row[1] or 0,
            "total_output_tokens": row[2] or 0,
            "total_credits": round(row[3] or 0, 2)
        },
        "users": users,
        "by_source": by_source,
        "by_model": by_model,
        "days": days
    }


def get_user_detail(user_id: str, days: int = 30) -> dict:
    """Detalhe de um usuário específico"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    # Métricas do usuário
    cursor.execute("""
        SELECT 
            SUM(input_tokens),
            SUM(output_tokens),
            SUM(credits_used),
            COUNT(*),
            MAX(timestamp)
        FROM metrics 
        WHERE user_id = ? AND timestamp >= ?
    """, (user_id, since))
    
    row = cursor.fetchone()
    
    # Por dia
    cursor.execute("""
        SELECT 
            date(timestamp) as day,
            SUM(credits_used) as credits
        FROM metrics 
        WHERE user_id = ? AND timestamp >= ?
        GROUP BY date(timestamp)
        ORDER BY day
    """, (user_id, since))
    
    daily = {r[0]: round(r[1], 2) for r in cursor.fetchall()}
    
    # Por fonte
    cursor.execute("""
        SELECT source, SUM(credits_used)
        FROM metrics 
        WHERE user_id = ? AND timestamp >= ?
        GROUP BY source
    """, (user_id, since))
    
    by_source = {r[0]: round(r[1], 2) for r in cursor.fetchall()}
    
    conn.close()
    
    return {
        "user_id": user_id,
        "total_input_tokens": row[0] or 0,
        "total_output_tokens": row[1] or 0,
        "total_credits": round(row[2] or 0, 2),
        "request_count": row[3] or 0,
        "last_activity": row[4],
        "daily": daily,
        "by_source": by_source
    }


# ============================================================
# FASTAPI APP
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="O11yIA BR - Copilot Metrics Collector",
    description="Servidor central para coleta de métricas de uso do GitHub Copilot",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/v1/metrics")
async def receive_metric(metric: TokenMetric):
    """
    Recebe métrica de qualquer plugin (VSCode config, IntelliJ, Chrome)
    """
    result = save_metric(metric)
    return {
        "success": True,
        "credits_used": result["credits_used"],
        "metric_id": result["id"]
    }


@app.post("/v1/metrics/batch")
async def receive_metrics_batch(metrics: list[TokenMetric]):
    """
    Recebe múltiplas métricas de uma vez (para sync em lote)
    """
    results = []
    total_credits = 0
    
    for metric in metrics:
        result = save_metric(metric)
        results.append(result)
        total_credits += result["credits_used"]
    
    return {
        "success": True,
        "count": len(results),
        "total_credits": round(total_credits, 2)
    }


@app.get("/v1/team/summary")
async def team_summary(days: int = 30):
    """
    Dashboard do time - consumo geral do pool
    """
    return get_team_summary(days)


@app.get("/v1/users/{user_id}")
async def user_detail(user_id: str, days: int = 30):
    """
    Detalhe de consumo de um usuário
    """
    return get_user_detail(user_id, days)


@app.get("/v1/alerts")
async def check_alerts():
    """
    Verifica alertas de consumo
    """
    summary = get_team_summary(30)
    alerts = []
    
    # Alerta de pool baixo
    if summary["pool"]["percent_used"] > 80:
        alerts.append({
            "level": "critical" if summary["pool"]["percent_used"] > 90 else "warning",
            "type": "pool_low",
            "message": f"Pool de créditos em {summary['pool']['percent_used']}%",
            "remaining": summary["pool"]["remaining"]
        })
    
    # Alerta de usuários com alto consumo
    avg_credits = summary["stats"]["total_credits"] / max(summary["stats"]["active_users"], 1)
    for user in summary["users"]:
        if user["credits"] > avg_credits * 2:
            alerts.append({
                "level": "info",
                "type": "high_usage",
                "message": f"Usuário {user['user_id']} com consumo 2x acima da média",
                "credits": user["credits"]
            })
    
    return {"alerts": alerts, "checked_at": datetime.utcnow().isoformat()}


# ============================================================
# ENDPOINT OTLP (para VSCode nativo)
# ============================================================

@app.post("/v1/traces")
async def receive_otel_traces(request: Request):
    """
    Recebe traces OTLP do VSCode (formato protobuf ou JSON)
    Extrai métricas de tokens dos spans do Copilot
    """
    content_type = request.headers.get("content-type", "")
    
    try:
        if "json" in content_type:
            data = await request.json()
            # Processar spans OTLP JSON
            metrics_extracted = process_otel_json(data)
            return {"success": True, "metrics_extracted": metrics_extracted}
        else:
            # Protobuf - aceitar mas logar para análise
            body = await request.body()
            # TODO: Parsear protobuf quando tivermos exemplos reais
            return {"success": True, "note": "protobuf received, parsing pending"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def process_otel_json(data: dict) -> int:
    """
    Extrai métricas de tokens de traces OTLP JSON
    """
    count = 0
    
    # Estrutura OTLP: resourceSpans -> scopeSpans -> spans
    for resource_span in data.get("resourceSpans", []):
        # Extrair user_id do resource
        user_id = "unknown"
        for attr in resource_span.get("resource", {}).get("attributes", []):
            if attr.get("key") == "user.id":
                user_id = attr.get("value", {}).get("stringValue", "unknown")
        
        for scope_span in resource_span.get("scopeSpans", []):
            for span in scope_span.get("spans", []):
                # Procurar atributos de tokens
                attrs = {
                    a["key"]: a.get("value", {}).get("intValue") or a.get("value", {}).get("stringValue")
                    for a in span.get("attributes", [])
                }
                
                if "llm.usage.prompt_tokens" in attrs or "gen_ai.usage.input_tokens" in attrs:
                    metric = TokenMetric(
                        user_id=user_id,
                        source="vscode-otel",
                        model=attrs.get("llm.request.model", attrs.get("gen_ai.request.model", "unknown")),
                        input_tokens=int(attrs.get("llm.usage.prompt_tokens", attrs.get("gen_ai.usage.input_tokens", 0))),
                        output_tokens=int(attrs.get("llm.usage.completion_tokens", attrs.get("gen_ai.usage.output_tokens", 0))),
                        context=span.get("name", "")
                    )
                    save_metric(metric)
                    count += 1
    
    return count


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True
    )
