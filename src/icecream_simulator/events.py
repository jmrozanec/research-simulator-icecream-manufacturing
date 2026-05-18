"""
Structured events — things a supervisor or operator should react to.

Replaces the single ``maintenance_required`` boolean with typed Event records.
An event has a stage, a stable code (e.g. ``pasteurization.lethality_below_target``),
a severity, a human-readable message, and an evidence dict pointing to the
specific values that triggered it. Codes are stable strings so downstream rules,
dashboards, or LLM prompts can pattern-match on them.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    INFO = "info"
    WARN = "warn"
    ALARM = "alarm"
    CRITICAL = "critical"


class Event(BaseModel):
    stage: str
    code: str
    severity: Severity
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    timestamp_s: float | None = None


class EventBus(BaseModel):
    """Collected events for one run."""

    events: list[Event] = Field(default_factory=list)

    def emit(self, event: Event) -> None:
        self.events.append(event)

    def info(self, stage: str, code: str, message: str, **evidence: Any) -> None:
        self.emit(Event(stage=stage, code=code, severity=Severity.INFO,
                        message=message, evidence=dict(evidence)))

    def warn(self, stage: str, code: str, message: str, **evidence: Any) -> None:
        self.emit(Event(stage=stage, code=code, severity=Severity.WARN,
                        message=message, evidence=dict(evidence)))

    def alarm(self, stage: str, code: str, message: str, **evidence: Any) -> None:
        self.emit(Event(stage=stage, code=code, severity=Severity.ALARM,
                        message=message, evidence=dict(evidence)))

    def critical(self, stage: str, code: str, message: str, **evidence: Any) -> None:
        self.emit(Event(stage=stage, code=code, severity=Severity.CRITICAL,
                        message=message, evidence=dict(evidence)))

    def count_by_severity(self) -> dict[str, int]:
        out: dict[str, int] = {s.value: 0 for s in Severity}
        for e in self.events:
            out[e.severity.value] += 1
        return out

    def filter(self, *, stage: str | None = None,
               severity: Severity | None = None,
               code_prefix: str | None = None) -> list[Event]:
        out = self.events
        if stage:
            out = [e for e in out if e.stage == stage]
        if severity:
            out = [e for e in out if e.severity == severity]
        if code_prefix:
            out = [e for e in out if e.code.startswith(code_prefix)]
        return out

    def worst_severity(self) -> Severity:
        order = [Severity.INFO, Severity.WARN, Severity.ALARM, Severity.CRITICAL]
        worst = Severity.INFO
        for e in self.events:
            if order.index(e.severity) > order.index(worst):
                worst = e.severity
        return worst


__all__ = ["Severity", "Event", "EventBus"]
