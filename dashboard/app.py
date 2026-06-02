"""
O11yIA BR - Painel de Administração
Streamlit Dashboard para gestão e monitoramento de uso de tokens de IA.

Consome a API FastAPI do O11yIA BR conforme contrato documentado.
Configurável via env: API_URL, O11YIA_API_KEY, O11YIA_ADMIN_KEY
"""

import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except Exception:
    HAS_AUTOREFRESH = False


# ============================================================
# CONFIGURAÇÃO DA PÁGINA + TEMA DARK
# ============================================================

st.set_page_config(
    page_title="O11yIA BR - Painel de Administração",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .stApp {
        background-color: #1a1a2e;
    }
    .metric-card {
        background: #252542;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    .big-number {
        font-size: 48px;
        font-weight: 700;
        color: #4ecdc4;
    }
    .warning-text { color: #f9c74f; }
    .danger-text { color: #ff6b6b; }
    .success-text { color: #4ecdc4; }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Paleta de cores reutilizável
COLOR_OK = "#4ecdc4"
COLOR_WARN = "#f9c74f"
COLOR_CRIT = "#ff6b6b"
PAPER_BG = "#1a1a2e"
PLOT_BG = "#252542"


# ============================================================
# SIDEBAR - CONFIGURAÇÃO
# ============================================================

st.sidebar.title("⚡ O11yIA BR")
st.sidebar.caption("Painel de Administração")

API_URL = st.sidebar.text_input(
    "URL do Servidor",
    value=os.getenv("API_URL", "http://localhost:8080"),
).rstrip("/")

API_KEY = st.sidebar.text_input(
    "API Key (X-API-Key)",
    value=os.getenv("O11YIA_API_KEY", ""),
    type="password",
    help="Usada nas chamadas de leitura/consulta.",
)

ADMIN_KEY = st.sidebar.text_input(
    "Admin Key (X-Admin-Key)",
    value=os.getenv("O11YIA_ADMIN_KEY", ""),
    type="password",
    help="Se preenchida, habilita a aba de Administração.",
)

period = st.sidebar.selectbox(
    "Período",
    options=[7, 30, 90],
    format_func=lambda x: f"Últimos {x} dias",
    index=1,
)

auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=False)

if auto_refresh:
    if HAS_AUTOREFRESH:
        st_autorefresh(interval=30_000, key="o11yia_autorefresh")
    else:
        st.sidebar.warning(
            "Componente `streamlit-autorefresh` não instalado. "
            "Instale-o (já incluso no requirements.txt) para auto-refresh não bloqueante."
        )

ADMIN_ENABLED = bool(ADMIN_KEY.strip())


# ============================================================
# CAMADA HTTP CENTRALIZADA
# ============================================================

class ApiError(Exception):
    """Erro de chamada à API com mensagem amigável."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.message = message
        self.status = status


def _headers(admin: bool = False) -> dict:
    headers = {"Accept": "application/json"}
    if admin:
        if ADMIN_KEY:
            headers["X-Admin-Key"] = ADMIN_KEY
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    return headers


def api_request(
    method: str,
    path: str,
    *,
    admin: bool = False,
    params: dict | None = None,
    json: dict | None = None,
    timeout: int = 10,
):
    """
    Chamada HTTP centralizada que injeta headers de auth e trata erros.

    Levanta ApiError com mensagem amigável em caso de falha de conexão,
    timeout ou status de erro (incluindo 401/403).
    Retorna o corpo JSON decodificado em caso de sucesso.
    """
    url = f"{API_URL}{path}"
    try:
        response = requests.request(
            method,
            url,
            params=params,
            json=json,
            headers=_headers(admin=admin),
            timeout=timeout,
        )
    except requests.exceptions.Timeout:
        raise ApiError("Tempo de conexão esgotado ao contatar a API.")
    except requests.exceptions.ConnectionError:
        raise ApiError(f"Não foi possível conectar à API em {API_URL}.")
    except requests.exceptions.RequestException as exc:
        raise ApiError(f"Erro de rede: {exc}")

    if response.status_code in (401, 403):
        raise ApiError(
            "API key inválida ou sem permissão (verifique X-API-Key / X-Admin-Key).",
            status=response.status_code,
        )

    if not response.ok:
        detail = ""
        try:
            body = response.json()
            detail = body.get("detail") or body.get("message") or ""
        except Exception:
            detail = response.text[:200]
        raise ApiError(
            f"A API retornou erro {response.status_code}. {detail}".strip(),
            status=response.status_code,
        )

    if response.status_code == 204 or not response.content:
        return {}
    try:
        return response.json()
    except ValueError:
        raise ApiError("A API retornou uma resposta inválida (não-JSON).")


# --- Wrappers de leitura (com cache) ---------------------------------------

@st.cache_data(ttl=30, show_spinner=False)
def fetch_team_summary(api_url: str, api_key: str, days: int):
    return api_request("GET", "/v1/team/summary", params={"days": days})


@st.cache_data(ttl=30, show_spinner=False)
def fetch_alerts(api_url: str, api_key: str):
    return api_request("GET", "/v1/alerts")


@st.cache_data(ttl=30, show_spinner=False)
def fetch_teams(api_url: str, api_key: str):
    resp = api_request("GET", "/v1/teams")
    if isinstance(resp, dict):
        return resp.get("teams", [])
    return resp or []


@st.cache_data(ttl=30, show_spinner=False)
def fetch_user_detail(api_url: str, api_key: str, user_id: str, days: int):
    return api_request("GET", f"/v1/users/{user_id}", params={"days": days})


# --- Wrappers admin (sem cache - sempre fresco) ----------------------------

def admin_list_teams():
    resp = api_request("GET", "/v1/admin/teams", admin=True)
    if isinstance(resp, dict):
        return resp.get("teams", [])
    return resp or []


def admin_create_team(payload: dict):
    return api_request("POST", "/v1/admin/teams", admin=True, json=payload)


def admin_update_team(name: str, payload: dict):
    return api_request("PUT", f"/v1/admin/teams/{name}", admin=True, json=payload)


def admin_delete_team(name: str):
    return api_request("DELETE", f"/v1/admin/teams/{name}", admin=True)


def admin_list_users():
    resp = api_request("GET", "/v1/admin/users", admin=True)
    if isinstance(resp, dict):
        return resp.get("users", [])
    return resp or []


def admin_update_user(user_id: str, payload: dict):
    return api_request("PUT", f"/v1/admin/users/{user_id}", admin=True, json=payload)


def admin_get_config():
    return api_request("GET", "/v1/admin/config", admin=True)


def admin_update_config(payload: dict):
    return api_request("PUT", "/v1/admin/config", admin=True, json=payload)


# ============================================================
# HELPERS DE FORMATAÇÃO / NORMALIZAÇÃO
# ============================================================

def safe_num(value, default=0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def dict_to_rows(d: dict, key_name: str, value_name: str = "credits"):
    """Converte {chave: valor} em lista de dicts para DataFrame."""
    if not d:
        return []
    return [{key_name: k, value_name: safe_num(v)} for k, v in d.items()]


def fmt_dt(value):
    if not value:
        return "—"
    try:
        return pd.to_datetime(value).strftime("%d/%m %H:%M")
    except Exception:
        return str(value)


# ============================================================
# COMPONENTES DE VISUALIZAÇÃO (tema dark)
# ============================================================

def render_pool_gauge(data):
    pool = data.get("pool", {}) or {}
    total = safe_num(pool.get("total"), 1) or 1
    used = safe_num(pool.get("used"))
    percent = safe_num(pool.get("percent_used"))

    if percent > 90:
        color = COLOR_CRIT
    elif percent > 70:
        color = COLOR_WARN
    else:
        color = COLOR_OK

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=used,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Créditos Utilizados", "font": {"color": "#eee", "size": 20}},
            delta={
                "reference": total * 0.7,
                "increasing": {"color": COLOR_CRIT},
                "decreasing": {"color": COLOR_OK},
            },
            number={"suffix": f" / {total:,.0f}", "font": {"color": "#eee", "size": 24}},
            gauge={
                "axis": {"range": [0, total], "tickcolor": "#666"},
                "bar": {"color": color},
                "bgcolor": PLOT_BG,
                "borderwidth": 0,
                "steps": [
                    {"range": [0, total * 0.7], "color": "#1a3a2e"},
                    {"range": [total * 0.7, total * 0.9], "color": "#3a3a1e"},
                    {"range": [total * 0.9, total], "color": "#3a1a1e"},
                ],
                "threshold": {
                    "line": {"color": COLOR_CRIT, "width": 4},
                    "thickness": 0.75,
                    "value": total * 0.9,
                },
            },
        )
    )
    fig.update_layout(
        paper_bgcolor=PAPER_BG,
        font={"color": "#eee"},
        height=300,
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


def render_users_ranking(users):
    if not users:
        return None
    df = pd.DataFrame(users)
    if "credits" not in df.columns or "user_id" not in df.columns:
        return None
    df["user_short"] = df["user_id"].apply(
        lambda x: x.split("@")[0] if isinstance(x, str) and "@" in x else str(x)[:15]
    )
    fig = px.bar(
        df.sort_values("credits", ascending=False).head(10),
        x="credits",
        y="user_short",
        orientation="h",
        color="credits",
        color_continuous_scale=[COLOR_OK, COLOR_WARN, COLOR_CRIT],
        labels={"credits": "Créditos", "user_short": "Usuário"},
    )
    fig.update_layout(
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font={"color": "#eee"},
        height=400,
        showlegend=False,
        yaxis={"categoryorder": "total ascending"},
    )
    return fig


def render_source_distribution(by_source):
    rows = dict_to_rows(by_source, "source")
    if not rows:
        return None
    df = pd.DataFrame(rows)
    colors = {
        "vscode": "#007ACC",
        "vscode-otel": "#0078D7",
        "intellij": "#FE315D",
        "browser": "#F1502F",
        "default": COLOR_OK,
    }
    fig = px.pie(
        df,
        values="credits",
        names="source",
        color="source",
        color_discrete_map=colors,
        hole=0.4,
    )
    fig.update_layout(
        paper_bgcolor=PAPER_BG,
        font={"color": "#eee"},
        height=300,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
    )
    return fig


def render_model_distribution(by_model):
    rows = dict_to_rows(by_model, "model")
    if not rows:
        return None
    df = pd.DataFrame(rows)
    fig = px.bar(
        df,
        x="model",
        y="credits",
        color="credits",
        color_continuous_scale=[COLOR_OK, "#44a08d"],
        labels={"credits": "Créditos", "model": "Modelo"},
    )
    fig.update_layout(
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font={"color": "#eee"},
        height=300,
        showlegend=False,
    )
    return fig


def render_alerts(alerts):
    for alert in alerts:
        level = alert.get("level", "info")
        icon = "🔴" if level == "critical" else "🟡" if level == "warning" else "ℹ️"
        message = alert.get("message", "")
        if level == "critical":
            st.error(f"{icon} {message}")
        elif level == "warning":
            st.warning(f"{icon} {message}")
        else:
            st.info(f"{icon} {message}")


# ============================================================
# PÁGINA 1 — VISÃO GERAL (MONITORAMENTO)
# ============================================================

def page_overview(data, alerts_data, team_size):
    is_promo = data.get("period") == "promo"
    period_label = (
        "🎁 Período Promocional (7.000 cr/user)"
        if is_promo
        else "📊 Período Normal (3.900 cr/user)"
    )
    st.markdown(f"### {period_label}")

    alerts = (alerts_data or {}).get("alerts", []) or []
    if alerts:
        with st.expander(f"⚠️ {len(alerts)} Alerta(s) Ativo(s)", expanded=True):
            render_alerts(alerts)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(render_pool_gauge(data), use_container_width=True)

    with col2:
        stats = data.get("stats", {}) or {}
        pool = data.get("pool", {}) or {}

        used = safe_num(pool.get("used"))
        remaining = safe_num(pool.get("remaining"))

        st.metric(
            "Créditos Restantes",
            f"{remaining:,.0f}",
            delta=f"-{used:,.0f} usados",
        )
        st.metric(
            "Usuários Ativos",
            f"{int(safe_num(stats.get('active_users')))} / {team_size}",
        )
        total_tokens = safe_num(stats.get("total_input_tokens")) + safe_num(
            stats.get("total_output_tokens")
        )
        st.metric("Total de Tokens", f"{int(total_tokens):,}")

        # --- BUG CORRIGIDO: projeção de esgotamento ---
        # A janela de consulta (em dias) é a base correta para a taxa diária média,
        # não o "tempo decorrido". Tratamos divisão por zero.
        window_days = safe_num(data.get("days"), period) or period
        daily_rate = used / window_days if window_days else 0.0
        if daily_rate <= 0:
            st.info("Sem consumo na janela: projeção indisponível.")
        else:
            days_remaining = remaining / daily_rate
            label = (
                f"(projeção pela média dos últimos {int(window_days)} dias: "
                f"{daily_rate:,.0f} cr/dia)"
            )
            if days_remaining < 30:
                st.warning(f"⏱️ Pool acaba em ~{int(days_remaining)} dias {label}")
            else:
                st.success(f"✓ Pool dura ~{int(days_remaining)} dias {label}")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏆 Ranking de Consumo")
        fig = render_users_ranking(data.get("users", []))
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum usuário com atividade.")

    with col2:
        st.subheader("📊 Distribuição por Fonte")
        fig = render_source_distribution(data.get("by_source", {}))
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados por fonte.")

    st.divider()

    st.subheader("🤖 Consumo por Modelo")
    fig = render_model_distribution(data.get("by_model", {}))
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados por modelo.")

    st.divider()

    st.subheader("📋 Detalhes por Usuário")
    users = data.get("users", []) or []
    if users:
        df = pd.DataFrame(users)
        if "last_activity" in df.columns:
            df["last_activity"] = df["last_activity"].apply(fmt_dt)
        df = df.rename(
            columns={
                "user_id": "Usuário",
                "credits": "Créditos",
                "input_tokens": "Input Tokens",
                "output_tokens": "Output Tokens",
                "last_activity": "Última Atividade",
            }
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum usuário com atividade.")


# ============================================================
# PÁGINA 2 — POR TIME
# ============================================================

def page_teams(data):
    st.markdown("### 👥 Consumo por Time")

    by_team = data.get("by_team", []) or []
    teams_list = []
    try:
        teams_list = fetch_teams(API_URL, API_KEY) or []
    except ApiError as exc:
        st.warning(f"Não foi possível carregar /v1/teams: {exc.message}")

    # Normaliza /v1/teams (name, budget_credits, used, percent_used, active_users)
    # para o mesmo shape de by_team (team, credits, budget, percent_used, active_users).
    normalized = []
    seen = set()
    for t in by_team:
        normalized.append(
            {
                "team": t.get("team"),
                "credits": safe_num(t.get("credits")),
                "budget": safe_num(t.get("budget")),
                "percent_used": safe_num(t.get("percent_used")),
                "active_users": int(safe_num(t.get("active_users"))),
            }
        )
        seen.add(t.get("team"))

    for t in teams_list:
        name = t.get("name")
        if name in seen:
            continue
        normalized.append(
            {
                "team": name,
                "credits": safe_num(t.get("used")),
                "budget": safe_num(t.get("budget_credits")),
                "percent_used": safe_num(t.get("percent_used")),
                "active_users": int(safe_num(t.get("active_users"))),
            }
        )

    if not normalized:
        st.info("Nenhum time configurado ou sem dados de consumo por time.")
        return

    df = pd.DataFrame(normalized)
    df["remaining"] = (df["budget"] - df["credits"]).clip(lower=0)

    # Gráfico: consumo vs budget
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Budget",
            x=df["team"],
            y=df["budget"],
            marker_color="#3a3a5e",
        )
    )

    def bar_color(p):
        if p >= 90:
            return COLOR_CRIT
        if p >= 70:
            return COLOR_WARN
        return COLOR_OK

    fig.add_trace(
        go.Bar(
            name="Usado",
            x=df["team"],
            y=df["credits"],
            marker_color=[bar_color(p) for p in df["percent_used"]],
        )
    )
    fig.update_layout(
        barmode="overlay",
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font={"color": "#eee"},
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        title="Consumo vs Budget por Time",
    )
    st.plotly_chart(fig, use_container_width=True)

    # % usado por time
    fig_pct = px.bar(
        df.sort_values("percent_used", ascending=False),
        x="team",
        y="percent_used",
        color="percent_used",
        color_continuous_scale=[COLOR_OK, COLOR_WARN, COLOR_CRIT],
        labels={"percent_used": "% Usado", "team": "Time"},
        title="% do Budget Usado por Time",
    )
    fig_pct.add_hline(y=70, line_dash="dash", line_color=COLOR_WARN, annotation_text="Warning 70%")
    fig_pct.add_hline(y=90, line_dash="dash", line_color=COLOR_CRIT, annotation_text="Critical 90%")
    fig_pct.update_layout(
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font={"color": "#eee"},
        height=350,
        showlegend=False,
    )
    st.plotly_chart(fig_pct, use_container_width=True)

    # Destaques
    crit = df[df["percent_used"] >= 90]
    warn = df[(df["percent_used"] >= 70) & (df["percent_used"] < 90)]
    if not crit.empty:
        st.error(f"🔴 Times em estado crítico (≥90%): {', '.join(crit['team'].astype(str))}")
    if not warn.empty:
        st.warning(f"🟡 Times em alerta (≥70%): {', '.join(warn['team'].astype(str))}")

    # Tabela
    st.subheader("📋 Detalhes por Time")
    table = df.rename(
        columns={
            "team": "Time",
            "budget": "Budget",
            "credits": "Usado",
            "remaining": "Restante",
            "percent_used": "% Usado",
            "active_users": "Ativos",
        }
    )[["Time", "Budget", "Usado", "Restante", "% Usado", "Ativos"]]
    st.dataframe(table, use_container_width=True, hide_index=True)


# ============================================================
# PÁGINA 3 — POR PROJETO
# ============================================================

def page_projects(data):
    st.markdown("### 📁 Consumo por Projeto")

    by_project = data.get("by_project", {}) or {}
    rows = dict_to_rows(by_project, "project")
    if not rows:
        st.info("Sem dados de consumo por projeto na janela selecionada.")
        return

    df = pd.DataFrame(rows).sort_values("credits", ascending=False)

    col1, col2 = st.columns([2, 1])
    with col1:
        fig = px.bar(
            df,
            x="credits",
            y="project",
            orientation="h",
            color="credits",
            color_continuous_scale=[COLOR_OK, COLOR_WARN, COLOR_CRIT],
            labels={"credits": "Créditos", "project": "Projeto"},
        )
        fig.update_layout(
            paper_bgcolor=PAPER_BG,
            plot_bgcolor=PLOT_BG,
            font={"color": "#eee"},
            height=420,
            showlegend=False,
            yaxis={"categoryorder": "total ascending"},
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig_pie = px.pie(df, values="credits", names="project", hole=0.4)
        fig_pie.update_layout(
            paper_bgcolor=PAPER_BG,
            font={"color": "#eee"},
            height=420,
            legend=dict(orientation="h", yanchor="bottom", y=-0.3),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    table = df.rename(columns={"project": "Projeto", "credits": "Créditos"})
    st.dataframe(table, use_container_width=True, hide_index=True)


# ============================================================
# PÁGINA 4 — DETALHE DE USUÁRIO
# ============================================================

def page_user_detail(data):
    st.markdown("### 🔍 Detalhe de Usuário")

    users = data.get("users", []) or []
    user_ids = sorted({u.get("user_id") for u in users if u.get("user_id")})

    if not user_ids:
        st.info("Nenhum usuário disponível na janela selecionada.")
        return

    selected = st.selectbox("Selecione o usuário", options=user_ids)
    if not selected:
        return

    try:
        detail = fetch_user_detail(API_URL, API_KEY, selected, period)
    except ApiError as exc:
        st.error(f"❌ {exc.message}")
        return

    if not detail:
        st.info("Sem dados para este usuário.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Time", detail.get("team") or "—")
    c2.metric("Créditos", f"{safe_num(detail.get('total_credits')):,.0f}")
    c3.metric("Requisições", f"{int(safe_num(detail.get('request_count'))):,}")
    c4.metric("Última Atividade", fmt_dt(detail.get("last_activity")))

    in_tok = int(safe_num(detail.get("total_input_tokens")))
    out_tok = int(safe_num(detail.get("total_output_tokens")))
    cc1, cc2 = st.columns(2)
    cc1.metric("Input Tokens", f"{in_tok:,}")
    cc2.metric("Output Tokens", f"{out_tok:,}")

    st.divider()

    # Série diária
    st.subheader("📈 Série Diária")
    daily = detail.get("daily", {}) or {}
    rows = dict_to_rows(daily, "date")
    if rows:
        df_daily = pd.DataFrame(rows)
        try:
            df_daily["date"] = pd.to_datetime(df_daily["date"])
            df_daily = df_daily.sort_values("date")
        except Exception:
            pass
        fig = px.line(
            df_daily,
            x="date",
            y="credits",
            markers=True,
            labels={"credits": "Créditos", "date": "Data"},
        )
        fig.update_traces(line_color=COLOR_OK)
        fig.update_layout(
            paper_bgcolor=PAPER_BG,
            plot_bgcolor=PLOT_BG,
            font={"color": "#eee"},
            height=320,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem série diária para este usuário.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Por Fonte")
        fig = render_source_distribution(detail.get("by_source", {}))
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados por fonte.")
    with col2:
        st.subheader("🤖 Por Modelo")
        fig = render_model_distribution(detail.get("by_model", {}))
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados por modelo.")


# ============================================================
# PÁGINA 5 — ADMINISTRAÇÃO
# ============================================================

def page_admin():
    st.markdown("### ⚙️ Administração")
    st.caption("Operações administrativas (requer X-Admin-Key).")

    tab_teams, tab_users, tab_config = st.tabs(
        ["🏷️ Times", "👤 Usuários", "🎛️ Config do Pool"]
    )

    # ---- TIMES ----
    with tab_teams:
        st.subheader("Gestão de Times")
        try:
            teams = admin_list_teams() or []
        except ApiError as exc:
            st.error(f"❌ {exc.message}")
            teams = []

        if teams:
            st.dataframe(pd.DataFrame(teams), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum time cadastrado.")

        st.markdown("#### ➕ Criar Time")
        with st.form("create_team_form"):
            name = st.text_input("Nome do time")
            budget = st.number_input("Budget (créditos)", min_value=0, value=3900, step=100)
            warn_pct = st.number_input(
                "Alerta Warning (%)", min_value=0, max_value=100, value=70
            )
            crit_pct = st.number_input(
                "Alerta Critical (%)", min_value=0, max_value=100, value=90
            )
            submitted = st.form_submit_button("Criar")
            if submitted:
                if not name.strip():
                    st.error("Informe o nome do time.")
                else:
                    payload = {
                        "name": name.strip(),
                        "budget_credits": int(budget),
                        "alert_warning_pct": int(warn_pct),
                        "alert_critical_pct": int(crit_pct),
                    }
                    try:
                        admin_create_team(payload)
                        st.success(f"Time '{name}' criado com sucesso.")
                        fetch_teams.clear()
                        st.rerun()
                    except ApiError as exc:
                        st.error(f"❌ {exc.message}")

        if teams:
            st.markdown("#### ✏️ Editar / Excluir Time")
            team_names = [t.get("name") for t in teams if t.get("name")]
            edit_name = st.selectbox("Time", options=team_names, key="edit_team_select")
            current = next((t for t in teams if t.get("name") == edit_name), {})
            with st.form("edit_team_form"):
                e_budget = st.number_input(
                    "Budget (créditos)",
                    min_value=0,
                    value=int(safe_num(current.get("budget_credits"))),
                    step=100,
                )
                e_warn = st.number_input(
                    "Alerta Warning (%)",
                    min_value=0,
                    max_value=100,
                    value=int(safe_num(current.get("alert_warning_pct"), 70)),
                )
                e_crit = st.number_input(
                    "Alerta Critical (%)",
                    min_value=0,
                    max_value=100,
                    value=int(safe_num(current.get("alert_critical_pct"), 90)),
                )
                col_upd, col_del = st.columns(2)
                do_update = col_upd.form_submit_button("Salvar alterações")
                do_delete = col_del.form_submit_button("🗑️ Excluir time")
                if do_update:
                    payload = {
                        "budget_credits": int(e_budget),
                        "alert_warning_pct": int(e_warn),
                        "alert_critical_pct": int(e_crit),
                    }
                    try:
                        admin_update_team(edit_name, payload)
                        st.success(f"Time '{edit_name}' atualizado.")
                        fetch_teams.clear()
                        st.rerun()
                    except ApiError as exc:
                        st.error(f"❌ {exc.message}")
                if do_delete:
                    try:
                        admin_delete_team(edit_name)
                        st.success(f"Time '{edit_name}' excluído.")
                        fetch_teams.clear()
                        st.rerun()
                    except ApiError as exc:
                        st.error(f"❌ {exc.message}")

    # ---- USUÁRIOS ----
    with tab_users:
        st.subheader("Atribuição de Usuários")
        try:
            users = admin_list_users() or []
        except ApiError as exc:
            st.error(f"❌ {exc.message}")
            users = []

        if not users:
            st.info("Nenhum usuário cadastrado.")
        else:
            st.dataframe(pd.DataFrame(users), use_container_width=True, hide_index=True)

            user_ids = [u.get("user_id") for u in users if u.get("user_id")]
            st.markdown("#### ✏️ Editar Usuário")
            sel_user = st.selectbox("Usuário", options=user_ids, key="edit_user_select")
            current = next((u for u in users if u.get("user_id") == sel_user), {})
            with st.form("edit_user_form"):
                u_team = st.text_input("Time", value=current.get("team") or "")
                u_name = st.text_input(
                    "Nome de exibição", value=current.get("display_name") or ""
                )
                if st.form_submit_button("Salvar"):
                    payload = {}
                    if u_team.strip():
                        payload["team"] = u_team.strip()
                    if u_name.strip():
                        payload["display_name"] = u_name.strip()
                    try:
                        admin_update_user(sel_user, payload)
                        st.success(f"Usuário '{sel_user}' atualizado.")
                        st.rerun()
                    except ApiError as exc:
                        st.error(f"❌ {exc.message}")

    # ---- CONFIG ----
    with tab_config:
        st.subheader("Configuração do Pool")
        try:
            config = admin_get_config() or {}
        except ApiError as exc:
            st.error(f"❌ {exc.message}")
            config = {}

        with st.form("config_form"):
            promo = st.number_input(
                "Créditos por usuário (promo)",
                min_value=0,
                value=int(safe_num(config.get("credits_per_user_promo"), 7000)),
                step=100,
            )
            normal = st.number_input(
                "Créditos por usuário (normal)",
                min_value=0,
                value=int(safe_num(config.get("credits_per_user_normal"), 3900)),
                step=100,
            )
            size = st.number_input(
                "Tamanho do time",
                min_value=0,
                value=int(safe_num(config.get("team_size"), 18)),
                step=1,
            )
            promo_start = st.text_input(
                "Início do período promo (YYYY-MM-DD)",
                value=str(config.get("promo_start") or ""),
            )
            promo_end = st.text_input(
                "Fim do período promo (YYYY-MM-DD)",
                value=str(config.get("promo_end") or ""),
            )
            if st.form_submit_button("Salvar configuração"):
                payload = {
                    "credits_per_user_promo": int(promo),
                    "credits_per_user_normal": int(normal),
                    "team_size": int(size),
                }
                if promo_start.strip():
                    payload["promo_start"] = promo_start.strip()
                if promo_end.strip():
                    payload["promo_end"] = promo_end.strip()
                try:
                    admin_update_config(payload)
                    st.success("Configuração atualizada com sucesso.")
                    fetch_team_summary.clear()
                    st.rerun()
                except ApiError as exc:
                    st.error(f"❌ {exc.message}")


# ============================================================
# MAIN
# ============================================================

st.title("⚡ O11yIA BR — Painel de Administração")

# Seleção de página
pages = ["Visão Geral", "Por Time", "Por Projeto", "Detalhe de Usuário"]
if ADMIN_ENABLED:
    pages.append("Administração")

page = st.sidebar.radio("Página", options=pages)

# Carrega dados base (resumo + alertas) com tratamento de erro amigável.
data = None
alerts_data = {"alerts": []}
load_error = None
try:
    data = fetch_team_summary(API_URL, API_KEY, period)
except ApiError as exc:
    load_error = exc
try:
    alerts_data = fetch_alerts(API_URL, API_KEY)
except ApiError:
    alerts_data = {"alerts": []}

# Páginas que dependem do summary
needs_summary = page in ("Visão Geral", "Por Time", "Por Projeto", "Detalhe de Usuário")

if needs_summary and not data:
    if load_error and load_error.status in (401, 403):
        st.error(f"🔒 {load_error.message}")
    elif load_error:
        st.error(f"❌ {load_error.message}")
    else:
        st.warning("Sem dados disponíveis no momento.")
    st.info(f"Verifique se o servidor está rodando em: {API_URL}")
else:
    if page == "Visão Geral":
        team_size = 18
        page_overview(data, alerts_data, team_size)
    elif page == "Por Time":
        page_teams(data)
    elif page == "Por Projeto":
        page_projects(data)
    elif page == "Detalhe de Usuário":
        page_user_detail(data)
    elif page == "Administração":
        page_admin()

# Footer
st.divider()
refresh_mode = "auto (30s)" if auto_refresh else "manual"
st.caption(
    f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} "
    f"| Refresh: {refresh_mode} | API: {API_URL}"
)
