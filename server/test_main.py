"""
Testes do backend O11yIA BR.

Cada teste roda contra um banco SQLite temporário isolado e recarrega os módulos
para que DATABASE_PATH e as envs de auth sejam aplicados.

Rodar:
    python -m pytest server/ -q
"""

import os
import importlib
import tempfile

import pytest
from fastapi.testclient import TestClient


API_KEY = "test-api-key"
ADMIN_KEY = "test-admin-key"


def _make_client(env_overrides=None):
    """Cria um TestClient com banco temporário e envs configuráveis."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()

    env = {
        "DATABASE_PATH": tmp.name,
        "O11YIA_API_KEYS": API_KEY,
        "O11YIA_ADMIN_KEY": ADMIN_KEY,
        "O11YIA_AUTH_DISABLED": "false",
        "O11YIA_CORS_ORIGINS": "http://localhost:8501",
    }
    if env_overrides:
        env.update(env_overrides)
    for k, v in env.items():
        os.environ[k] = v

    # Recarrega módulos na ordem de dependência.
    import pricing, db, auth, otlp, models, main
    importlib.reload(pricing)
    importlib.reload(models)
    importlib.reload(db)
    importlib.reload(auth)
    importlib.reload(otlp)
    importlib.reload(main)

    client = TestClient(main.app)
    return client, tmp.name


@pytest.fixture
def client():
    c, path = _make_client()
    with c:
        yield c
    try:
        os.remove(path)
    except OSError:
        pass


def _hdr():
    return {"X-API-Key": API_KEY}


def _admin_hdr():
    return {"X-Admin-Key": ADMIN_KEY}


# ----------------------------------------------------------------------------
# Health
# ----------------------------------------------------------------------------

def test_health_public(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


# ----------------------------------------------------------------------------
# Auth
# ----------------------------------------------------------------------------

def test_metrics_requires_api_key(client):
    r = client.post("/v1/metrics", json={
        "user_id": "u1", "source": "vscode", "model": "gpt-4o",
        "input_tokens": 1000, "output_tokens": 500,
    })
    assert r.status_code == 401


def test_metrics_with_api_key(client):
    r = client.post("/v1/metrics", headers=_hdr(), json={
        "user_id": "u1", "source": "vscode", "model": "gpt-4o",
        "input_tokens": 1000, "output_tokens": 500,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["metric_id"] >= 1


def test_auth_disabled_mode():
    c, path = _make_client({"O11YIA_AUTH_DISABLED": "true"})
    with c:
        r = c.post("/v1/metrics", json={
            "user_id": "u1", "source": "vscode", "model": "gpt-4o",
            "input_tokens": 100, "output_tokens": 100,
        })
        assert r.status_code == 200
    os.remove(path)


def test_admin_requires_admin_key(client):
    r = client.get("/v1/admin/teams")
    assert r.status_code == 401
    # X-API-Key não vale para admin
    r2 = client.get("/v1/admin/teams", headers=_hdr())
    assert r2.status_code == 401


# ----------------------------------------------------------------------------
# Pricing / créditos
# ----------------------------------------------------------------------------

def test_metrics_credit_calculation(client):
    # gpt-4o: 250 créditos/1M input, 1000/1M output
    # 1_000_000 input + 1_000_000 output = 250 + 1000 = 1250 créditos
    r = client.post("/v1/metrics", headers=_hdr(), json={
        "user_id": "calc", "source": "gateway", "model": "gpt-4o-2024-08-06",
        "input_tokens": 1_000_000, "output_tokens": 1_000_000,
    })
    assert r.status_code == 200
    assert r.json()["credits_used"] == pytest.approx(1250.0)


def test_pricing_prefix_and_default():
    import pricing
    importlib.reload(pricing)
    # prefixo -> gpt-4o-mini (mais específico que gpt-4o)
    assert pricing.calculate_credits("gpt-4o-mini-2024", 1_000_000, 0) == pytest.approx(15.0)
    # modelo desconhecido -> default 200/800
    assert pricing.calculate_credits("modelo-zzz", 1_000_000, 1_000_000) == pytest.approx(1000.0)
    # cost_usd = credits * 0.01
    assert pricing.calculate_cost_usd("gpt-4o", 1_000_000, 0) == pytest.approx(2.5)


# ----------------------------------------------------------------------------
# Batch
# ----------------------------------------------------------------------------

def test_metrics_batch(client):
    payload = [
        {"user_id": "b1", "source": "vscode", "model": "gpt-4o-mini",
         "input_tokens": 1_000_000, "output_tokens": 0},
        {"user_id": "b2", "source": "vscode", "model": "gpt-4o-mini",
         "input_tokens": 1_000_000, "output_tokens": 0},
    ]
    r = client.post("/v1/metrics/batch", headers=_hdr(), json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert body["total_credits"] == pytest.approx(30.0)  # 15 + 15


# ----------------------------------------------------------------------------
# OTLP/JSON
# ----------------------------------------------------------------------------

def test_otlp_json_extraction(client):
    otlp_payload = {
        "resourceSpans": [{
            "resource": {"attributes": [
                {"key": "user.id", "value": {"stringValue": "otel-user"}},
                {"key": "service.name", "value": {"stringValue": "copilot-gw"}},
            ]},
            "scopeSpans": [{
                "spans": [{
                    "name": "chat.completion",
                    "attributes": [
                        {"key": "gen_ai.request.model", "value": {"stringValue": "gpt-4o"}},
                        {"key": "gen_ai.usage.input_tokens", "value": {"intValue": "1000000"}},
                        {"key": "gen_ai.usage.output_tokens", "value": {"intValue": "0"}},
                    ],
                }]
            }],
        }]
    }
    r = client.post("/v1/traces", headers=_hdr(), json=otlp_payload)
    assert r.status_code == 200
    assert r.json()["metrics_extracted"] == 1

    # confirma que entrou no summary do usuário
    d = client.get("/v1/users/otel-user", headers=_hdr())
    assert d.status_code == 200
    assert d.json()["total_input_tokens"] == 1_000_000


def test_otlp_json_legacy_attrs(client):
    payload = {
        "resourceSpans": [{
            "resource": {"attributes": [
                {"key": "service.name", "value": {"stringValue": "copilot-legacy@x.com"}},
            ]},
            "scopeSpans": [{
                "spans": [{
                    "name": "llm",
                    "attributes": [
                        {"key": "llm.request.model", "value": {"stringValue": "claude-haiku"}},
                        {"key": "llm.usage.prompt_tokens", "value": {"intValue": "100"}},
                        {"key": "llm.usage.completion_tokens", "value": {"intValue": "50"}},
                    ],
                }]
            }],
        }]
    }
    r = client.post("/v1/traces", headers=_hdr(), json=payload)
    assert r.status_code == 200
    assert r.json()["metrics_extracted"] == 1
    # derivou user de service.name "copilot-legacy@x.com"
    d = client.get("/v1/users/legacy@x.com", headers=_hdr())
    assert d.json()["request_count"] == 1


# ----------------------------------------------------------------------------
# Summary + by_team
# ----------------------------------------------------------------------------

def test_summary_with_by_team(client):
    # cria time com budget
    client.post("/v1/admin/teams", headers=_admin_hdr(),
                json={"name": "alpha", "budget_credits": 1000})
    # métrica com team
    client.post("/v1/metrics", headers=_hdr(), json={
        "user_id": "ua", "team": "alpha", "project": "projx",
        "source": "vscode", "model": "gpt-4o",
        "input_tokens": 1_000_000, "output_tokens": 1_000_000,  # 1250 créditos
    })

    r = client.get("/v1/team/summary", headers=_hdr())
    assert r.status_code == 200
    body = r.json()
    assert "by_team" in body
    assert "by_project" in body
    alpha = next(t for t in body["by_team"] if t["team"] == "alpha")
    assert alpha["budget"] == 1000
    assert alpha["credits"] == pytest.approx(1250.0)
    assert alpha["active_users"] == 1
    assert "projx" in body["by_project"]


# ----------------------------------------------------------------------------
# Admin endpoints
# ----------------------------------------------------------------------------

def test_admin_team_crud(client):
    # create
    r = client.post("/v1/admin/teams", headers=_admin_hdr(),
                    json={"name": "beta", "budget_credits": 500, "alert_warning_pct": 70})
    assert r.status_code == 200
    assert r.json()["team"]["budget_credits"] == 500
    assert r.json()["team"]["alert_warning_pct"] == 70

    # list
    r = client.get("/v1/admin/teams", headers=_admin_hdr())
    names = [t["name"] for t in r.json()["teams"]]
    assert "beta" in names

    # update
    r = client.put("/v1/admin/teams/beta", headers=_admin_hdr(),
                   json={"budget_credits": 999})
    assert r.status_code == 200
    assert r.json()["team"]["budget_credits"] == 999

    # delete
    r = client.delete("/v1/admin/teams/beta", headers=_admin_hdr())
    assert r.status_code == 200

    # update inexistente -> 404
    r = client.put("/v1/admin/teams/naoexiste", headers=_admin_hdr(),
                   json={"budget_credits": 1})
    assert r.status_code == 404


def test_admin_user_and_config(client):
    client.post("/v1/metrics", headers=_hdr(), json={
        "user_id": "cfguser", "source": "vscode", "model": "gpt-4o",
        "input_tokens": 10, "output_tokens": 10,
    })
    r = client.put("/v1/admin/users/cfguser", headers=_admin_hdr(),
                   json={"team": "gamma", "display_name": "Fulano"})
    assert r.status_code == 200
    assert r.json()["user"]["team"] == "gamma"

    r = client.put("/v1/admin/config", headers=_admin_hdr(),
                   json={"team_size": 25})
    assert r.status_code == 200
    assert r.json()["config"]["team_size"] == 25
