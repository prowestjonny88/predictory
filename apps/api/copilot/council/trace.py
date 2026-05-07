from __future__ import annotations

from typing import Any

from .schemas import AgentTraceItem, CouncilSource


def graph_step(trace: list[dict[str, Any]], node: str, status: str = "ok", **details: Any) -> list[dict[str, Any]]:
    return [*trace, {"node": node, "status": status, **details}]


def agent_trace_item(
    *,
    agent: str,
    role: str,
    claim: str,
    evidence: dict[str, Any] | None = None,
    stance: str | None = None,
    severity: str = "info",
    source: CouncilSource = "rules_based",
) -> AgentTraceItem:
    return AgentTraceItem(
        agent=agent,
        role=role,
        claim=claim,
        evidence=evidence or {},
        stance=stance,
        severity=severity,  # type: ignore[arg-type]
        source=source,
    )

