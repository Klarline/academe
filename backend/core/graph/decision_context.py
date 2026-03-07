"""
Unified decision context that accumulates all routing/grading signals.

Instead of scattering ``routing_confidence``, ``grader_verdict``,
``refinement_count``, etc. across a dozen WorkflowState fields, every
decision signal lives in one object.  Conditional edge functions read
from it; nodes write to it.

This makes the workflow easier to reason about — you can inspect a
single object to see *why* the graph took a particular path.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Literal, Optional

logger = logging.getLogger(__name__)

MAX_REFINEMENTS = 2
MAX_REROUTES = 1
CONFIDENCE_THRESHOLD = 0.4


@dataclass
class DecisionContext:
    """
    Single object accumulating every decision signal for one request.

    Nodes call mutating helpers (``record_routing``, ``record_grading``,
    ``record_reroute``); conditional edges call query properties
    (``should_clarify``, ``next_action``).
    """

    # ── Router signals ────────────────────────────────────────────────
    route: str = "concept"
    routing_confidence: float = 1.0
    routing_reasoning: str = ""

    # ── Grader signals ────────────────────────────────────────────────
    grader_verdict: Optional[str] = None   # "pass" | "refine" | "reroute"
    grader_feedback: Optional[str] = None

    # ── Loop counters ─────────────────────────────────────────────────
    refinement_count: int = 0
    reroute_count: int = 0
    previous_agents: List[str] = field(default_factory=list)

    # ── Thresholds (overridable per-request) ──────────────────────────
    confidence_threshold: float = CONFIDENCE_THRESHOLD
    max_refinements: int = MAX_REFINEMENTS
    max_reroutes: int = MAX_REROUTES

    # ── Recording helpers (called by nodes) ───────────────────────────

    def record_routing(
        self,
        route: str,
        confidence: float,
        reasoning: str = "",
    ) -> None:
        """Called by ``router_node`` after the LLM routes the query."""
        self.route = route
        self.routing_confidence = confidence
        self.routing_reasoning = reasoning

    def record_grading(
        self,
        verdict: str,
        feedback: Optional[str] = None,
    ) -> None:
        """Called by ``response_grader_node`` after evaluating the response."""
        self.grader_verdict = verdict
        self.grader_feedback = feedback
        if verdict == "refine":
            self.refinement_count += 1
        elif verdict == "reroute" and feedback:
            self.reroute_count += 1

    def record_agent_used(self, agent: str) -> None:
        if agent not in self.previous_agents:
            self.previous_agents.append(agent)

    def record_reroute(self, new_route: str) -> None:
        """Called by ``re_router_node`` when switching agents."""
        self.route = new_route
        self.grader_feedback = None
        self.grader_verdict = None

    # ── Query properties (called by conditional edges) ────────────────

    @property
    def should_clarify(self) -> bool:
        return self.routing_confidence < self.confidence_threshold

    @property
    def can_refine(self) -> bool:
        return self.refinement_count < self.max_refinements

    @property
    def can_reroute(self) -> bool:
        return self.reroute_count < self.max_reroutes

    @property
    def loops_exhausted(self) -> bool:
        return (
            self.refinement_count >= self.max_refinements
            and self.reroute_count >= self.max_reroutes
        )

    @property
    def next_action(self) -> Literal["pass", "refine", "reroute"]:
        """Single entry-point for the grading conditional edge."""
        verdict = self.grader_verdict or "pass"
        if verdict == "refine":
            return "refine"
        if verdict == "reroute":
            return "reroute"
        return "pass"

    def is_route_untried(self, route: str) -> bool:
        return route not in self.previous_agents

    # ── Serialization ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "route": self.route,
            "routing_confidence": self.routing_confidence,
            "routing_reasoning": self.routing_reasoning,
            "grader_verdict": self.grader_verdict,
            "grader_feedback": self.grader_feedback,
            "refinement_count": self.refinement_count,
            "reroute_count": self.reroute_count,
            "previous_agents": list(self.previous_agents),
        }

    def __str__(self) -> str:
        return (
            f"Decision(route={self.route}, confidence={self.routing_confidence:.2f}, "
            f"verdict={self.grader_verdict}, refine={self.refinement_count}/{self.max_refinements}, "
            f"reroute={self.reroute_count}/{self.max_reroutes})"
        )
