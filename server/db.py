"""
O11yIA BR - Camada de acesso a dados (SQLite).

Isola TODO o acesso ao banco para que uma futura migração para Postgres seja
localizada apenas neste módulo.

Concorrência / SQLite:
- Conexão aberta com check_same_thread=False (FastAPI roda handlers async em
  threads do event loop / threadpool).
- PRAGMA journal_mode=WAL para permitir leituras concorrentes durante escrita.
- Todas as ESCRITAS são serializadas por um threading.Lock global e usam retry
  com backoff em "database is locked".
- Limitação conhecida: SQLite tem um único writer. Para alto volume / múltiplas
  réplicas, migrar para Postgres (este módulo é o único ponto de mudança).
"""

import os
import json
import sqlite3
import time
import threading
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from pricing import calculate_credits, calculate_cost_usd

logger = logging.getLogger("o11yia.db")

DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/metrics.db")

# Serializa escritas (SQLite = single writer).
_WRITE_LOCK = threading.Lock()
_MAX_RETRIES = 5
_RETRY_BASE_SLEEP = 0.1  # segundos

# Defaults de config do pool (sobrescrevíveis via tabela config / env).
DEFAULT_CONFIG = {
    "credits_per_user_promo": 7000,
    "credits_per_user_normal": 3900,
    "team_size": 18,
    "promo_start": "2026-06-01",
    "promo_end": "2026-08-31",
}


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    """Abre uma conexão configurada. Uma conexão por operação (simples e seguro)."""
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _execute_write(fn):
    """
    Executa uma função de escrita com lock global + retry em 'database is locked'.
    `fn(conn)` recebe a conexão e deve retornar o resultado desejado.
    """
    last_err = None
    with _WRITE_LOCK:
        for attempt in range(_MAX_RETRIES):
            conn = _connect()
            try:
                result = fn(conn)
                conn.commit()
                return result
            except sqlite3.OperationalError as e:
                last_err = e
                if "locked" in str(e).lower():
                    conn.rollback()
                    conn.close()
                    time.sleep(_RETRY_BASE_SLEEP * (attempt + 1))
                    continue
                conn.close()
                raise
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
    raise last_err


def _query(fn):
    """Executa uma função de leitura. `fn(conn)` retorna o resultado."""
    conn = _connect()
    try:
        return fn(conn)
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# Schema / migração
# ----------------------------------------------------------------------------

def _column_exists(conn, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == column for r in rows)


def init_db():
    """Cria o schema e aplica migração leve de colunas novas."""
    def _init(conn):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                team TEXT,
                project TEXT,
                source TEXT NOT NULL,
                gateway TEXT,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                reasoning_tokens INTEGER NOT NULL DEFAULT 0,
                credits_used REAL NOT NULL DEFAULT 0,
                cost_usd REAL NOT NULL DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                context TEXT,
                request_id TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                display_name TEXT,
                team TEXT DEFAULT 'default',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                name TEXT PRIMARY KEY,
                budget_credits REAL DEFAULT 0,
                alert_warning_pct INTEGER DEFAULT 80,
                alert_critical_pct INTEGER DEFAULT 90,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Migração leve: adiciona colunas em DBs antigos da PoC.
        migrations = {
            "metrics": {
                "team": "TEXT",
                "project": "TEXT",
                "gateway": "TEXT",
                "reasoning_tokens": "INTEGER NOT NULL DEFAULT 0",
                "cost_usd": "REAL NOT NULL DEFAULT 0",
                "request_id": "TEXT",
            }
        }
        for table, cols in migrations.items():
            for col, decl in cols.items():
                if not _column_exists(conn, table, col):
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
                    logger.info("Migração: coluna %s.%s adicionada", table, col)

        # Índices
        conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_user ON metrics(user_id, timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_team ON metrics(team, timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_date ON metrics(date(timestamp))")

        # Garante o time 'default'
        conn.execute(
            "INSERT OR IGNORE INTO teams (name, budget_credits) VALUES ('default', 0)"
        )

    _execute_write(_init)


# ----------------------------------------------------------------------------
# Config (key/value)
# ----------------------------------------------------------------------------

def get_config() -> Dict[str, Any]:
    def _get(conn):
        rows = conn.execute("SELECT key, value FROM config").fetchall()
        stored = {r["key"]: r["value"] for r in rows}
        cfg = dict(DEFAULT_CONFIG)
        for k, v in stored.items():
            if k in ("credits_per_user_promo", "credits_per_user_normal"):
                cfg[k] = float(v)
            elif k == "team_size":
                cfg[k] = int(float(v))
            else:
                cfg[k] = v
        return cfg
    return _query(_get)


def update_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    def _upd(conn):
        for k, v in updates.items():
            if v is None:
                continue
            conn.execute(
                "INSERT INTO config (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (k, str(v)),
            )
    _execute_write(_upd)
    return get_config()


# ----------------------------------------------------------------------------
# Users / teams helpers
# ----------------------------------------------------------------------------

def _get_user_team(conn, user_id: str) -> Optional[str]:
    row = conn.execute("SELECT team FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return row["team"] if row else None


def upsert_user(user_id: str, team: Optional[str] = None, display_name: Optional[str] = None):
    def _up(conn):
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        if team is not None:
            conn.execute("INSERT OR IGNORE INTO teams (name) VALUES (?)", (team,))
            conn.execute("UPDATE users SET team = ? WHERE user_id = ?", (team, user_id))
        if display_name is not None:
            conn.execute("UPDATE users SET display_name = ? WHERE user_id = ?", (display_name, user_id))
    _execute_write(_up)


# ----------------------------------------------------------------------------
# Métricas
# ----------------------------------------------------------------------------

def save_metric(metric) -> dict:
    """
    Salva uma métrica. `metric` é um TokenMetric (Pydantic).
    Resolve o team: se vier no payload, faz upsert do user com esse team;
    senão usa o team já cadastrado do user (ou 'default').
    """
    credits = calculate_credits(
        metric.model, metric.input_tokens, metric.output_tokens, metric.reasoning_tokens or 0
    )
    cost = calculate_cost_usd(
        metric.model, metric.input_tokens, metric.output_tokens, metric.reasoning_tokens or 0
    )
    ts = metric.timestamp or utcnow_iso()

    def _save(conn):
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (metric.user_id,))

        if metric.team:
            team = metric.team
            conn.execute("INSERT OR IGNORE INTO teams (name) VALUES (?)", (team,))
            conn.execute("UPDATE users SET team = ? WHERE user_id = ?", (team, metric.user_id))
        else:
            team = _get_user_team(conn, metric.user_id) or "default"

        cur = conn.execute(
            """
            INSERT INTO metrics
            (user_id, team, project, source, gateway, model, input_tokens, output_tokens,
             reasoning_tokens, credits_used, cost_usd, timestamp, session_id, context, request_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metric.user_id,
                team,
                metric.project,
                metric.source,
                metric.gateway,
                metric.model,
                int(metric.input_tokens or 0),
                int(metric.output_tokens or 0),
                int(metric.reasoning_tokens or 0),
                credits,
                cost,
                ts,
                metric.session_id,
                metric.context,
                metric.request_id,
            ),
        )
        # lastrowid lido ANTES de fechar a conexão (bug #1 corrigido).
        return cur.lastrowid

    metric_id = _execute_write(_save)
    return {"id": metric_id, "credits_used": credits, "cost_usd": cost}


# ----------------------------------------------------------------------------
# Queries de agregação
# ----------------------------------------------------------------------------

def _since(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _resolve_pool(cfg: Dict[str, Any]):
    """Calcula pool total com base na config e na data atual."""
    now = datetime.now(timezone.utc).date()
    promo = False
    try:
        start = datetime.strptime(cfg["promo_start"], "%Y-%m-%d").date()
        end = datetime.strptime(cfg["promo_end"], "%Y-%m-%d").date()
        promo = start <= now <= end
    except Exception:
        promo = False

    per_user = cfg["credits_per_user_promo"] if promo else cfg["credits_per_user_normal"]
    total = per_user * cfg["team_size"]
    return total, ("promo" if promo else "normal")


def get_team_summary(days: int = 30) -> dict:
    since = _since(days)
    cfg = get_config()

    def _summary(conn):
        row = conn.execute(
            """
            SELECT COUNT(DISTINCT user_id) AS active_users,
                   COALESCE(SUM(input_tokens),0) AS total_input,
                   COALESCE(SUM(output_tokens),0) AS total_output,
                   COALESCE(SUM(credits_used),0) AS total_credits
            FROM metrics WHERE timestamp >= ?
            """,
            (since,),
        ).fetchone()

        users = [
            {
                "user_id": r["user_id"],
                "team": r["team"],
                "credits": round(r["credits"], 4),
                "input_tokens": r["input_tokens"],
                "output_tokens": r["output_tokens"],
                "last_activity": r["last_activity"],
            }
            for r in conn.execute(
                """
                SELECT user_id, team, SUM(credits_used) AS credits,
                       SUM(input_tokens) AS input_tokens, SUM(output_tokens) AS output_tokens,
                       MAX(timestamp) AS last_activity
                FROM metrics WHERE timestamp >= ?
                GROUP BY user_id ORDER BY credits DESC
                """,
                (since,),
            ).fetchall()
        ]

        by_source = {
            r["source"]: round(r["credits"], 4)
            for r in conn.execute(
                "SELECT source, SUM(credits_used) AS credits FROM metrics WHERE timestamp >= ? GROUP BY source",
                (since,),
            ).fetchall()
        }

        by_model = {
            r["model"]: round(r["credits"], 4)
            for r in conn.execute(
                "SELECT model, SUM(credits_used) AS credits FROM metrics WHERE timestamp >= ? "
                "GROUP BY model ORDER BY credits DESC LIMIT 20",
                (since,),
            ).fetchall()
        }

        by_project = {
            (r["project"] or "unknown"): round(r["credits"], 4)
            for r in conn.execute(
                "SELECT project, SUM(credits_used) AS credits FROM metrics WHERE timestamp >= ? "
                "GROUP BY project ORDER BY credits DESC",
                (since,),
            ).fetchall()
        }

        # by_team: junta consumo + budget configurado
        team_usage = {
            r["team"]: {"credits": r["credits"], "active_users": r["active_users"]}
            for r in conn.execute(
                """
                SELECT COALESCE(team,'default') AS team, SUM(credits_used) AS credits,
                       COUNT(DISTINCT user_id) AS active_users
                FROM metrics WHERE timestamp >= ? GROUP BY team
                """,
                (since,),
            ).fetchall()
        }
        team_rows = conn.execute(
            "SELECT name, budget_credits FROM teams"
        ).fetchall()
        budgets = {r["name"]: r["budget_credits"] for r in team_rows}

        by_team = []
        all_team_names = set(budgets) | set(team_usage)
        for name in sorted(all_team_names):
            credits = round(team_usage.get(name, {}).get("credits", 0) or 0, 4)
            active = team_usage.get(name, {}).get("active_users", 0)
            budget = budgets.get(name, 0) or 0
            percent = round((credits / budget) * 100, 1) if budget > 0 else 0
            by_team.append({
                "team": name,
                "credits": credits,
                "budget": budget,
                "percent_used": percent,
                "active_users": active,
            })

        return row, users, by_source, by_model, by_project, by_team

    row, users, by_source, by_model, by_project, by_team = _query(_summary)

    total_pool, period = _resolve_pool(cfg)
    used = row["total_credits"] or 0

    return {
        "period": period,
        "pool": {
            "total": total_pool,
            "used": round(used, 4),
            "remaining": round(total_pool - used, 4),
            "percent_used": round((used / total_pool) * 100, 1) if total_pool > 0 else 0,
        },
        "stats": {
            "active_users": row["active_users"] or 0,
            "total_input_tokens": row["total_input"] or 0,
            "total_output_tokens": row["total_output"] or 0,
            "total_credits": round(row["total_credits"] or 0, 4),
        },
        "users": users,
        "by_source": by_source,
        "by_model": by_model,
        "by_project": by_project,
        "by_team": by_team,
        "days": days,
    }


def get_user_detail(user_id: str, days: int = 30) -> dict:
    since = _since(days)

    def _detail(conn):
        row = conn.execute(
            """
            SELECT COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0),
                   COALESCE(SUM(credits_used),0), COUNT(*), MAX(timestamp)
            FROM metrics WHERE user_id = ? AND timestamp >= ?
            """,
            (user_id, since),
        ).fetchone()

        daily = {
            r[0]: round(r[1], 4)
            for r in conn.execute(
                "SELECT date(timestamp) AS day, SUM(credits_used) FROM metrics "
                "WHERE user_id = ? AND timestamp >= ? GROUP BY date(timestamp) ORDER BY day",
                (user_id, since),
            ).fetchall()
        }

        by_source = {
            r[0]: round(r[1], 4)
            for r in conn.execute(
                "SELECT source, SUM(credits_used) FROM metrics WHERE user_id = ? AND timestamp >= ? GROUP BY source",
                (user_id, since),
            ).fetchall()
        }

        by_model = {
            r[0]: round(r[1], 4)
            for r in conn.execute(
                "SELECT model, SUM(credits_used) FROM metrics WHERE user_id = ? AND timestamp >= ? "
                "GROUP BY model ORDER BY 2 DESC",
                (user_id, since),
            ).fetchall()
        }

        team = _get_user_team(conn, user_id) or "default"
        return row, daily, by_source, by_model, team

    row, daily, by_source, by_model, team = _query(_detail)

    return {
        "user_id": user_id,
        "team": team,
        "total_input_tokens": row[0] or 0,
        "total_output_tokens": row[1] or 0,
        "total_credits": round(row[2] or 0, 4),
        "request_count": row[3] or 0,
        "last_activity": row[4],
        "daily": daily,
        "by_source": by_source,
        "by_model": by_model,
    }


def list_teams(days: int = 30) -> List[dict]:
    since = _since(days)

    def _list(conn):
        usage = {
            r["team"]: {"credits": r["credits"], "active_users": r["active_users"]}
            for r in conn.execute(
                "SELECT COALESCE(team,'default') AS team, SUM(credits_used) AS credits, "
                "COUNT(DISTINCT user_id) AS active_users FROM metrics WHERE timestamp >= ? GROUP BY team",
                (since,),
            ).fetchall()
        }
        teams = conn.execute(
            "SELECT name, budget_credits, alert_warning_pct, alert_critical_pct FROM teams"
        ).fetchall()
        result = []
        names = {t["name"] for t in teams} | set(usage)
        team_map = {t["name"]: t for t in teams}
        for name in sorted(names):
            t = team_map.get(name)
            budget = (t["budget_credits"] if t else 0) or 0
            credits = round(usage.get(name, {}).get("credits", 0) or 0, 4)
            result.append({
                "name": name,
                "budget_credits": budget,
                "used": credits,
                "percent_used": round((credits / budget) * 100, 1) if budget > 0 else 0,
                "active_users": usage.get(name, {}).get("active_users", 0),
                "alert_warning_pct": t["alert_warning_pct"] if t else 80,
                "alert_critical_pct": t["alert_critical_pct"] if t else 90,
            })
        return result

    return _query(_list)


# ----------------------------------------------------------------------------
# Admin: CRUD teams
# ----------------------------------------------------------------------------

def admin_list_teams() -> List[dict]:
    def _l(conn):
        return [dict(r) for r in conn.execute(
            "SELECT name, budget_credits, alert_warning_pct, alert_critical_pct, created_at FROM teams ORDER BY name"
        ).fetchall()]
    return _query(_l)


def admin_create_team(name, budget_credits, alert_warning_pct, alert_critical_pct) -> dict:
    def _c(conn):
        conn.execute(
            "INSERT INTO teams (name, budget_credits, alert_warning_pct, alert_critical_pct) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(name) DO UPDATE SET "
            "budget_credits=excluded.budget_credits, alert_warning_pct=excluded.alert_warning_pct, "
            "alert_critical_pct=excluded.alert_critical_pct",
            (name, budget_credits, alert_warning_pct, alert_critical_pct),
        )
    _execute_write(_c)
    return get_team(name)


def get_team(name) -> Optional[dict]:
    def _g(conn):
        r = conn.execute(
            "SELECT name, budget_credits, alert_warning_pct, alert_critical_pct, created_at FROM teams WHERE name = ?",
            (name,),
        ).fetchone()
        return dict(r) if r else None
    return _query(_g)


def admin_update_team(name, updates: dict) -> Optional[dict]:
    fields = {k: v for k, v in updates.items() if v is not None}
    if not fields:
        return get_team(name)

    def _u(conn):
        exists = conn.execute("SELECT 1 FROM teams WHERE name = ?", (name,)).fetchone()
        if not exists:
            return False
        sets = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(f"UPDATE teams SET {sets} WHERE name = ?", (*fields.values(), name))
        return True

    ok = _execute_write(_u)
    return get_team(name) if ok else None


def admin_delete_team(name) -> bool:
    def _d(conn):
        cur = conn.execute("DELETE FROM teams WHERE name = ?", (name,))
        return cur.rowcount > 0
    return _execute_write(_d)


# ----------------------------------------------------------------------------
# Admin: users
# ----------------------------------------------------------------------------

def admin_list_users() -> List[dict]:
    def _l(conn):
        return [dict(r) for r in conn.execute(
            "SELECT user_id, display_name, team, created_at FROM users ORDER BY user_id"
        ).fetchall()]
    return _query(_l)


def admin_update_user(user_id, team=None, display_name=None) -> Optional[dict]:
    def _u(conn):
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        if team is not None:
            conn.execute("INSERT OR IGNORE INTO teams (name) VALUES (?)", (team,))
            conn.execute("UPDATE users SET team = ? WHERE user_id = ?", (team, user_id))
        if display_name is not None:
            conn.execute("UPDATE users SET display_name = ? WHERE user_id = ?", (display_name, user_id))
        r = conn.execute(
            "SELECT user_id, display_name, team, created_at FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(r) if r else None
    return _execute_write(_u)
