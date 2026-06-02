"""
O11yIA BR - Parsing OTLP (JSON e protobuf) para extração de métricas de tokens.

Extrai dos spans:
- gen_ai.usage.input_tokens / gen_ai.usage.output_tokens
  (fallback: llm.usage.prompt_tokens / llm.usage.completion_tokens)
- gen_ai.usage.reasoning_tokens / gen_ai.usage.output_reasoning_tokens (opcional)
- gen_ai.request.model / llm.request.model
Identifica o usuário pelo resource attribute user.id, user.name, ou derivando
de service.name (ex.: "copilot-<email>").
"""

import logging
from typing import List

from models import TokenMetric

logger = logging.getLogger("o11yia.otlp")


def _av(value: dict):
    """Extrai o valor escalar de um AnyValue OTLP/JSON."""
    if value is None:
        return None
    if "stringValue" in value:
        return value["stringValue"]
    if "intValue" in value:
        return value["intValue"]
    if "doubleValue" in value:
        return value["doubleValue"]
    if "boolValue" in value:
        return value["boolValue"]
    return None


def _attrs_json(attr_list) -> dict:
    return {a["key"]: _av(a.get("value", {})) for a in (attr_list or [])}


def _derive_user(resource_attrs: dict) -> str:
    for key in ("user.id", "user.name", "enduser.id"):
        if resource_attrs.get(key):
            return str(resource_attrs[key])
    service = resource_attrs.get("service.name")
    if service:
        s = str(service)
        # ex.: "copilot-foo@bar.com" -> "foo@bar.com"
        if "-" in s:
            candidate = s.split("-", 1)[1]
            if candidate:
                return candidate
        return s
    return "unknown"


def _int(v, default=0) -> int:
    if v is None:
        return default
    try:
        return int(v)
    except (ValueError, TypeError):
        return default


def _metric_from_attrs(resource_attrs: dict, span_attrs: dict, span_name: str):
    has_tokens = any(
        k in span_attrs
        for k in (
            "gen_ai.usage.input_tokens",
            "gen_ai.usage.output_tokens",
            "llm.usage.prompt_tokens",
            "llm.usage.completion_tokens",
        )
    )
    if not has_tokens:
        return None

    input_tokens = _int(
        span_attrs.get("gen_ai.usage.input_tokens", span_attrs.get("llm.usage.prompt_tokens"))
    )
    output_tokens = _int(
        span_attrs.get("gen_ai.usage.output_tokens", span_attrs.get("llm.usage.completion_tokens"))
    )
    reasoning_tokens = _int(
        span_attrs.get(
            "gen_ai.usage.reasoning_tokens",
            span_attrs.get("gen_ai.usage.output_reasoning_tokens", 0),
        )
    )
    model = (
        span_attrs.get("gen_ai.request.model")
        or span_attrs.get("llm.request.model")
        or span_attrs.get("gen_ai.response.model")
        or "unknown"
    )

    return TokenMetric(
        user_id=_derive_user(resource_attrs),
        source="otel",
        gateway=resource_attrs.get("service.name"),
        model=str(model),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens,
        context=span_name or "",
        request_id=span_attrs.get("gen_ai.request.id"),
    )


def parse_otlp_json(data: dict) -> List[TokenMetric]:
    """Parseia ExportTraceServiceRequest em OTLP/JSON."""
    metrics: List[TokenMetric] = []
    for rs in data.get("resourceSpans", []):
        resource_attrs = _attrs_json(rs.get("resource", {}).get("attributes", []))
        for ss in rs.get("scopeSpans", []):
            for span in ss.get("spans", []):
                span_attrs = _attrs_json(span.get("attributes", []))
                m = _metric_from_attrs(resource_attrs, span_attrs, span.get("name", ""))
                if m:
                    metrics.append(m)
    return metrics


def _av_proto(value):
    """Extrai escalar de um AnyValue protobuf."""
    kind = value.WhichOneof("value")
    if kind is None:
        return None
    return getattr(value, kind)


def _attrs_proto(kv_list) -> dict:
    return {kv.key: _av_proto(kv.value) for kv in kv_list}


def parse_otlp_protobuf(body: bytes) -> List[TokenMetric]:
    """
    Parseia ExportTraceServiceRequest em OTLP/protobuf usando opentelemetry-proto.
    """
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
        ExportTraceServiceRequest,
    )

    req = ExportTraceServiceRequest()
    req.ParseFromString(body)

    metrics: List[TokenMetric] = []
    for rs in req.resource_spans:
        resource_attrs = _attrs_proto(rs.resource.attributes)
        for ss in rs.scope_spans:
            for span in ss.spans:
                span_attrs = _attrs_proto(span.attributes)
                m = _metric_from_attrs(resource_attrs, span_attrs, span.name)
                if m:
                    metrics.append(m)
    return metrics
