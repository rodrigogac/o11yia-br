"""
O11yIA BR - Collector central de métricas de IA (multi-fonte / multi-gateway)

Coleta uso de tokens de IA de clientes locais (extensão VSCode, plugin IntelliJ,
extensão Chrome) e de gateways de inferência via OTLP. NÃO usa a API oficial do
GitHub Copilot.

Camadas:
- main.py   -> app FastAPI + rotas
- db.py     -> acesso a dados (SQLite, isolado p/ futura migração a Postgres)
- pricing.py-> tabela de preços / cálculo de créditos (fonte única da verdade)
- auth.py   -> dependências de autenticação (X-API-Key / X-Admin-Key)
- models.py -> modelos Pydantic
- otlp.py   -> parsing OTLP (JSON e protobuf)
"""

import os
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, Request, Depends, Response
from fastapi.middleware.cors import CORSMiddleware

import db
from models import (
    TokenMetric,
    TeamCreate,
    TeamUpdate,
    UserUpdate,
    PoolConfig,
)
from auth import require_api_key, require_admin_key
import otlp

logging.basicConfig(level=os.getenv("O11YIA_LOG_LEVEL", "INFO"))
logger = logging.getLogger("o11yia")


def _cors_origins() -> List[str]:
    raw = os.getenv("O11YIA_CORS_ORIGINS", "http://localhost:8501")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins or ["http://localhost:8501"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(
    title="O11yIA BR - AI Token Metrics Collector",
    description="Collector multi-fonte/multi-gateway de uso de tokens de IA.",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS: origens configuráveis; nunca "*" com credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["X-API-Key", "X-Admin-Key", "Content-Type", "Authorization"],
)


# ============================================================
# PÚBLICO
# ============================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": db.utcnow_iso()}


# ============================================================
# INGESTÃO (X-API-Key)
# ============================================================

@app.post("/v1/metrics", dependencies=[Depends(require_api_key)])
async def receive_metric(metric: TokenMetric):
    result = db.save_metric(metric)
    return {
        "success": True,
        "metric_id": result["id"],
        "credits_used": result["credits_used"],
    }


@app.post("/v1/metrics/batch", dependencies=[Depends(require_api_key)])
async def receive_metrics_batch(metrics: List[TokenMetric]):
    total_credits = 0.0
    count = 0
    for metric in metrics:
        result = db.save_metric(metric)
        total_credits += result["credits_used"]
        count += 1
    return {
        "success": True,
        "count": count,
        "total_credits": round(total_credits, 4),
    }


@app.post("/v1/traces", dependencies=[Depends(require_api_key)])
async def receive_otel_traces(request: Request):
    """
    Receptor OTLP. Aceita application/json (OTLP/JSON) e
    application/x-protobuf (OTLP/protobuf).
    """
    content_type = request.headers.get("content-type", "").lower()
    try:
        if "protobuf" in content_type:
            body = await request.body()
            metrics = otlp.parse_otlp_protobuf(body)
        else:
            # default: JSON (OTLP/JSON)
            data = await request.json()
            metrics = otlp.parse_otlp_json(data)
    except Exception as e:  # noqa: BLE001
        logger.exception("Falha ao parsear OTLP")
        raise HTTPException(status_code=400, detail=f"OTLP parse error: {e}")

    extracted = 0
    for m in metrics:
        db.save_metric(m)
        extracted += 1

    # Resposta OTLP de sucesso (partialSuccess vazio = tudo aceito).
    if "protobuf" in content_type:
        try:
            from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
                ExportTraceServiceResponse,
            )
            resp = ExportTraceServiceResponse()
            return Response(
                content=resp.SerializeToString(),
                media_type="application/x-protobuf",
                headers={"X-Metrics-Extracted": str(extracted)},
            )
        except Exception:  # noqa: BLE001
            pass

    return {"success": True, "metrics_extracted": extracted, "partialSuccess": {}}


# ============================================================
# QUERY (X-API-Key)
# ============================================================

@app.get("/v1/team/summary", dependencies=[Depends(require_api_key)])
async def team_summary(days: int = 30):
    return db.get_team_summary(days)


@app.get("/v1/teams", dependencies=[Depends(require_api_key)])
async def teams(days: int = 30):
    return {"teams": db.list_teams(days), "days": days}


@app.get("/v1/users/{user_id}", dependencies=[Depends(require_api_key)])
async def user_detail(user_id: str, days: int = 30):
    return db.get_user_detail(user_id, days)


@app.get("/v1/alerts", dependencies=[Depends(require_api_key)])
async def check_alerts(days: int = 30):
    summary = db.get_team_summary(days)
    teams = db.list_teams(days)
    alerts = []

    # Pool global
    pct = summary["pool"]["percent_used"]
    if pct >= 80:
        alerts.append({
            "level": "critical" if pct >= 90 else "warning",
            "type": "pool_low",
            "scope": "global",
            "message": f"Pool global de créditos em {pct}%",
            "remaining": summary["pool"]["remaining"],
        })

    # Por time (usa thresholds do próprio time)
    for t in teams:
        if t["budget_credits"] <= 0:
            continue
        tp = t["percent_used"]
        warn = t.get("alert_warning_pct", 80)
        crit = t.get("alert_critical_pct", 90)
        if tp >= crit:
            level = "critical"
        elif tp >= warn:
            level = "warning"
        else:
            continue
        alerts.append({
            "level": level,
            "type": "team_budget",
            "scope": "team",
            "team": t["name"],
            "message": f"Time {t['name']} usou {tp}% do budget",
            "percent_used": tp,
        })

    # Usuários 2x acima da média
    active = summary["stats"]["active_users"] or 0
    avg = summary["stats"]["total_credits"] / active if active else 0
    for u in summary["users"]:
        if avg > 0 and u["credits"] > avg * 2:
            alerts.append({
                "level": "info",
                "type": "high_usage",
                "scope": "user",
                "user_id": u["user_id"],
                "message": f"Usuário {u['user_id']} com consumo 2x acima da média",
                "credits": u["credits"],
            })

    return {"alerts": alerts, "checked_at": db.utcnow_iso()}


# ============================================================
# ADMIN (X-Admin-Key)
# ============================================================

@app.get("/v1/admin/teams", dependencies=[Depends(require_admin_key)])
async def admin_list_teams():
    return {"teams": db.admin_list_teams()}


@app.post("/v1/admin/teams", dependencies=[Depends(require_admin_key)])
async def admin_create_team(team: TeamCreate):
    created = db.admin_create_team(
        team.name, team.budget_credits, team.alert_warning_pct, team.alert_critical_pct
    )
    return {"success": True, "team": created}


@app.put("/v1/admin/teams/{name}", dependencies=[Depends(require_admin_key)])
async def admin_update_team(name: str, updates: TeamUpdate):
    result = db.admin_update_team(name, updates.model_dump())
    if result is None:
        raise HTTPException(status_code=404, detail=f"Time '{name}' não encontrado")
    return {"success": True, "team": result}


@app.delete("/v1/admin/teams/{name}", dependencies=[Depends(require_admin_key)])
async def admin_delete_team(name: str):
    ok = db.admin_delete_team(name)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Time '{name}' não encontrado")
    return {"success": True, "deleted": name}


@app.get("/v1/admin/users", dependencies=[Depends(require_admin_key)])
async def admin_list_users():
    return {"users": db.admin_list_users()}


@app.put("/v1/admin/users/{user_id}", dependencies=[Depends(require_admin_key)])
async def admin_update_user(user_id: str, updates: UserUpdate):
    result = db.admin_update_user(user_id, team=updates.team, display_name=updates.display_name)
    return {"success": True, "user": result}


@app.get("/v1/admin/config", dependencies=[Depends(require_admin_key)])
async def admin_get_config():
    return {"config": db.get_config()}


@app.put("/v1/admin/config", dependencies=[Depends(require_admin_key)])
async def admin_update_config(config: PoolConfig):
    updated = db.update_config(config.model_dump())
    return {"success": True, "config": updated}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
