from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnalysisResult:
    verdict: str
    score: int
    scam_type: str
    reasons: list[str] = field(default_factory=list)
    advice: str = ""
    links_found: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
