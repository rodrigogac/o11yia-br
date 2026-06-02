"""
O11yIA BR - Dashboard de Observabilidade
Streamlit Dashboard para métricas do GitHub Copilot
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# Configuração da página
st.set_page_config(
    page_title="O11yIA BR - Copilot Metrics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado (tema dark)
st.markdown("""
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
""", unsafe_allow_html=True)

# Configurações
API_URL = st.sidebar.text_input("URL do Servidor", value="http://localhost:8080")
TEAM_SIZE = 18
CREDITS_PROMO = 7000  # Jun-Ago 2026
CREDITS_NORMAL = 3900

# Período
period = st.sidebar.selectbox(
    "Período",
    options=[7, 30, 90],
    format_func=lambda x: f"Últimos {x} dias",
    index=1
)

# Auto-refresh
auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=True)


@st.cache_data(ttl=30)
def fetch_team_summary(days: int):
    """Busca resumo do time"""
    try:
        response = requests.get(f"{API_URL}/v1/team/summary", params={"days": days}, timeout=10)
        if response.ok:
            return response.json()
    except Exception as e:
        st.error(f"Erro ao conectar: {e}")
    return None


@st.cache_data(ttl=30)
def fetch_alerts():
    """Busca alertas ativos"""
    try:
        response = requests.get(f"{API_URL}/v1/alerts", timeout=10)
        if response.ok:
            return response.json()
    except:
        pass
    return {"alerts": []}


def render_pool_gauge(data):
    """Renderiza gauge do pool de créditos"""
    pool = data.get("pool", {})
    total = pool.get("total", 1)
    used = pool.get("used", 0)
    remaining = pool.get("remaining", 0)
    percent = pool.get("percent_used", 0)
    
    # Cor baseada no uso
    if percent > 90:
        color = "#ff6b6b"
    elif percent > 70:
        color = "#f9c74f"
    else:
        color = "#4ecdc4"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=used,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Créditos Utilizados", 'font': {'color': '#eee', 'size': 20}},
        delta={'reference': total * 0.7, 'increasing': {'color': "#ff6b6b"}, 'decreasing': {'color': "#4ecdc4"}},
        number={'suffix': f" / {total:,.0f}", 'font': {'color': '#eee', 'size': 24}},
        gauge={
            'axis': {'range': [0, total], 'tickcolor': '#666'},
            'bar': {'color': color},
            'bgcolor': '#252542',
            'borderwidth': 0,
            'steps': [
                {'range': [0, total * 0.7], 'color': '#1a3a2e'},
                {'range': [total * 0.7, total * 0.9], 'color': '#3a3a1e'},
                {'range': [total * 0.9, total], 'color': '#3a1a1e'}
            ],
            'threshold': {
                'line': {'color': "#ff6b6b", 'width': 4},
                'thickness': 0.75,
                'value': total * 0.9
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='#1a1a2e',
        font={'color': '#eee'},
        height=300,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig


def render_users_ranking(users):
    """Renderiza ranking de usuários"""
    if not users:
        st.info("Nenhum usuário com atividade")
        return
    
    df = pd.DataFrame(users)
    df['user_short'] = df['user_id'].apply(lambda x: x.split('@')[0] if '@' in x else x[:15])
    
    fig = px.bar(
        df.head(10),
        x='credits',
        y='user_short',
        orientation='h',
        color='credits',
        color_continuous_scale=['#4ecdc4', '#f9c74f', '#ff6b6b'],
        labels={'credits': 'Créditos', 'user_short': 'Usuário'}
    )
    
    fig.update_layout(
        paper_bgcolor='#1a1a2e',
        plot_bgcolor='#252542',
        font={'color': '#eee'},
        height=400,
        showlegend=False,
        yaxis={'categoryorder': 'total ascending'}
    )
    
    return fig


def render_source_distribution(by_source):
    """Distribuição por fonte"""
    if not by_source:
        return None
    
    df = pd.DataFrame([
        {'source': k, 'credits': v} 
        for k, v in by_source.items()
    ])
    
    colors = {
        'vscode': '#007ACC',
        'vscode-otel': '#0078D7',
        'intellij': '#FE315D',
        'browser': '#F1502F',
        'default': '#4ecdc4'
    }
    
    fig = px.pie(
        df,
        values='credits',
        names='source',
        color='source',
        color_discrete_map=colors,
        hole=0.4
    )
    
    fig.update_layout(
        paper_bgcolor='#1a1a2e',
        font={'color': '#eee'},
        height=300,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2)
    )
    
    return fig


def render_model_distribution(by_model):
    """Distribuição por modelo"""
    if not by_model:
        return None
    
    df = pd.DataFrame([
        {'model': k, 'credits': v} 
        for k, v in by_model.items()
    ])
    
    fig = px.bar(
        df,
        x='model',
        y='credits',
        color='credits',
        color_continuous_scale=['#4ecdc4', '#44a08d'],
        labels={'credits': 'Créditos', 'model': 'Modelo'}
    )
    
    fig.update_layout(
        paper_bgcolor='#1a1a2e',
        plot_bgcolor='#252542',
        font={'color': '#eee'},
        height=300,
        showlegend=False
    )
    
    return fig


def render_alerts(alerts):
    """Renderiza alertas"""
    for alert in alerts:
        level = alert.get('level', 'info')
        icon = "🔴" if level == 'critical' else "🟡" if level == 'warning' else "ℹ️"
        
        if level == 'critical':
            st.error(f"{icon} {alert['message']}")
        elif level == 'warning':
            st.warning(f"{icon} {alert['message']}")
        else:
            st.info(f"{icon} {alert['message']}")


# ============================================================
# MAIN LAYOUT
# ============================================================

st.title("⚡ O11yIA BR - Copilot Metrics Dashboard")

# Fetch data
data = fetch_team_summary(period)
alerts_data = fetch_alerts()

if data:
    # Header com período
    is_promo = data.get('period') == 'promo'
    period_label = "🎁 Período Promocional (7.000 cr/user)" if is_promo else "📊 Período Normal (3.900 cr/user)"
    st.markdown(f"### {period_label}")
    
    # Alertas
    if alerts_data.get('alerts'):
        with st.expander(f"⚠️ {len(alerts_data['alerts'])} Alerta(s) Ativo(s)", expanded=True):
            render_alerts(alerts_data['alerts'])
    
    # Row 1: Pool gauge + Stats
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.plotly_chart(render_pool_gauge(data), use_container_width=True)
    
    with col2:
        stats = data.get('stats', {})
        pool = data.get('pool', {})
        
        st.metric(
            "Créditos Restantes",
            f"{pool.get('remaining', 0):,.0f}",
            delta=f"-{pool.get('used', 0):,.0f} usados"
        )
        
        st.metric(
            "Usuários Ativos",
            f"{stats.get('active_users', 0)} / {TEAM_SIZE}"
        )
        
        st.metric(
            "Total de Tokens",
            f"{(stats.get('total_input_tokens', 0) + stats.get('total_output_tokens', 0)):,}"
        )
        
        # Projeção de fim do mês
        days_elapsed = period
        daily_rate = pool.get('used', 0) / max(days_elapsed, 1)
        days_remaining = pool.get('remaining', 0) / max(daily_rate, 0.1)
        
        if days_remaining < 30:
            st.warning(f"⏱️ Pool acaba em ~{int(days_remaining)} dias")
        else:
            st.success(f"✓ Pool suficiente para {int(days_remaining)} dias")
    
    st.divider()
    
    # Row 2: Rankings
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 Ranking de Consumo")
        users = data.get('users', [])
        fig = render_users_ranking(users)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 Distribuição por Fonte")
        by_source = data.get('by_source', {})
        fig = render_source_distribution(by_source)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Row 3: Modelos
    st.subheader("🤖 Consumo por Modelo")
    by_model = data.get('by_model', {})
    fig = render_model_distribution(by_model)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Row 4: Tabela detalhada
    st.subheader("📋 Detalhes por Usuário")
    users = data.get('users', [])
    if users:
        df = pd.DataFrame(users)
        df['last_activity'] = pd.to_datetime(df['last_activity']).dt.strftime('%d/%m %H:%M')
        df = df.rename(columns={
            'user_id': 'Usuário',
            'credits': 'Créditos',
            'input_tokens': 'Input Tokens',
            'output_tokens': 'Output Tokens',
            'last_activity': 'Última Atividade'
        })
        st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.error("❌ Não foi possível conectar ao servidor")
    st.info(f"Verifique se o servidor está rodando em: {API_URL}")

# Footer
st.divider()
st.caption(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Time: {TEAM_SIZE} pessoas | API: {API_URL}")

# Auto-refresh
if auto_refresh:
    time.sleep(30)
    st.rerun()
