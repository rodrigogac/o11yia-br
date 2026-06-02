"""
O11yIA BR - Autenticação (dependências FastAPI).

- Endpoints de ingestão/query: header `X-API-Key` validado contra `O11YIA_API_KEYS`
  (lista separada por vírgula).
- Endpoints admin: header `X-Admin-Key` validado contra `O11YIA_ADMIN_KEY`.
- `O11YIA_AUTH_DISABLED=true` desliga toda a autenticação (modo dev/PoC).
- Se nenhuma chave estiver configurada, loga um warning e opera em modo aberto
  (para não quebrar a PoC local).
"""

import os
import logging

from fastapi import Header, HTTPException, status

logger = logging.getLogger("o11yia.auth")


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes", "on")


def auth_disabled() -> bool:
    return _truthy(os.getenv("O11YIA_AUTH_DISABLED", "false"))


def _parse_keys(env_value: str) -> set:
    if not env_value:
        return set()
    return {k.strip() for k in env_value.split(",") if k.strip()}


def get_api_keys() -> set:
    return _parse_keys(os.getenv("O11YIA_API_KEYS", ""))


def get_admin_key() -> str:
    return (os.getenv("O11YIA_ADMIN_KEY", "") or "").strip()


async def require_api_key(x_api_key: str = Header(default=None, alias="X-API-Key")):
    """Dependência FastAPI para endpoints de ingestão/query."""
    if auth_disabled():
        return True

    valid_keys = get_api_keys()
    if not valid_keys:
        logger.warning(
            "O11YIA_API_KEYS não configurada — operando em modo ABERTO (sem auth). "
            "Configure chaves em produção."
        )
        return True

    if x_api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de API inválida ou ausente (header X-API-Key).",
        )
    return True


async def require_admin_key(x_admin_key: str = Header(default=None, alias="X-Admin-Key")):
    """Dependência FastAPI para endpoints admin."""
    if auth_disabled():
        return True

    admin_key = get_admin_key()
    if not admin_key:
        logger.warning(
            "O11YIA_ADMIN_KEY não configurada — endpoints admin operando em modo ABERTO. "
            "Configure a chave em produção."
        )
        return True

    if x_admin_key != admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave admin inválida ou ausente (header X-Admin-Key).",
        )
    return True
