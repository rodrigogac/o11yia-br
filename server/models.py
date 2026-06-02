"""
O11yIA BR - Modelos Pydantic (contrato de API).
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class TokenMetric(BaseModel):
    """Métrica de tokens enviada por plugins/clients ou extraída de OTLP."""
    user_id: str
    source: str  # vscode, intellij, browser, gateway, vscode-otel, ...
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    team: Optional[str] = None
    project: Optional[str] = None
    gateway: Optional[str] = None
    reasoning_tokens: int = 0
    timestamp: Optional[str] = None
    session_id: Optional[str] = None
    context: Optional[str] = None  # chat, completion, inline, span name...
    request_id: Optional[str] = None


# ----------------------------------------------------------------------------
# Admin: Teams
# ----------------------------------------------------------------------------

class TeamCreate(BaseModel):
    name: str
    budget_credits: float = 0.0
    alert_warning_pct: int = 80
    alert_critical_pct: int = 90


class TeamUpdate(BaseModel):
    budget_credits: Optional[float] = None
    alert_warning_pct: Optional[int] = None
    alert_critical_pct: Optional[int] = None


# ----------------------------------------------------------------------------
# Admin: Users
# ----------------------------------------------------------------------------

class UserUpdate(BaseModel):
    team: Optional[str] = None
    display_name: Optional[str] = None


# ----------------------------------------------------------------------------
# Admin: Config (parâmetros do pool)
# ----------------------------------------------------------------------------

class PoolConfig(BaseModel):
    credits_per_user_promo: Optional[float] = None
    credits_per_user_normal: Optional[float] = None
    team_size: Optional[int] = None
    promo_start: Optional[str] = None  # YYYY-MM-DD
    promo_end: Optional[str] = None    # YYYY-MM-DD
