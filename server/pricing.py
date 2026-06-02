"""
O11yIA BR - Pricing (fonte única da verdade)

Tabela de preços em CRÉDITOS por 1.000.000 de tokens (input/output).
Convenção do projeto: 1 AI credit = US$ 0.01.

Os tokens de "reasoning" (modelos o1/o3) são cobrados como tokens de output.
O match do nome do modelo é case-insensitive e por prefixo
(ex.: "gpt-4o-2024-08-06" -> "gpt-4o").
"""

from typing import Dict

# 1 AI credit = US$ 0.01
USD_PER_CREDIT = 0.01

# Créditos por 1.000.000 de tokens (input, output)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4o": {"input": 250, "output": 1000},
    "gpt-4o-mini": {"input": 15, "output": 60},
    "claude-sonnet-4": {"input": 300, "output": 1500},
    "claude-haiku": {"input": 25, "output": 125},
    "o1": {"input": 1500, "output": 6000},
    "o3-mini": {"input": 110, "output": 440},
    "default": {"input": 200, "output": 800},
}

# Ordena as chaves por tamanho decrescente para que o match por prefixo
# escolha sempre o nome mais específico (ex.: "gpt-4o-mini" antes de "gpt-4o").
_SORTED_KEYS = sorted(
    (k for k in MODEL_PRICING if k != "default"),
    key=len,
    reverse=True,
)


def _resolve_pricing(model: str) -> Dict[str, float]:
    """Resolve a tabela de preços para um nome de modelo (case-insensitive, prefixo)."""
    if not model:
        return MODEL_PRICING["default"]

    name = model.strip().lower()

    # Match exato primeiro
    if name in MODEL_PRICING:
        return MODEL_PRICING[name]

    # Match por prefixo (mais específico primeiro)
    for key in _SORTED_KEYS:
        if name.startswith(key):
            return MODEL_PRICING[key]

    # Match por "contém" como fallback adicional (ex.: nomes com vendor prefix)
    for key in _SORTED_KEYS:
        if key in name:
            return MODEL_PRICING[key]

    return MODEL_PRICING["default"]


def calculate_credits(
    model: str,
    input_tokens: int,
    output_tokens: int,
    reasoning_tokens: int = 0,
) -> float:
    """
    Calcula o custo em créditos para uma chamada.

    reasoning_tokens são cobrados na tarifa de output.
    Retorna float arredondado em 6 casas.
    """
    pricing = _resolve_pricing(model)
    input_tokens = max(int(input_tokens or 0), 0)
    output_tokens = max(int(output_tokens or 0), 0)
    reasoning_tokens = max(int(reasoning_tokens or 0), 0)

    credits = (
        (input_tokens * pricing["input"])
        + ((output_tokens + reasoning_tokens) * pricing["output"])
    ) / 1_000_000

    return round(credits, 6)


def calculate_cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    reasoning_tokens: int = 0,
) -> float:
    """Calcula o custo em USD (créditos * USD_PER_CREDIT)."""
    credits = calculate_credits(model, input_tokens, output_tokens, reasoning_tokens)
    return round(credits * USD_PER_CREDIT, 6)
