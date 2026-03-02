"""
Named retrieval profiles: fixed parameter sets chosen by query complexity.

Instead of manually toggling 10 boolean flags on RAGPipeline, callers pick a
profile that encapsulates a cost/quality tradeoff.

  fast     — keyword + vector only, no LLM enrichment (sub-second)
  balanced — hybrid search + rewriting + self-RAG (default for most queries)
  deep     — everything enabled including KG, propositions, HyDE, decomposition
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ProfileName(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    DEEP = "deep"


@dataclass(frozen=True)
class RetrievalProfile:
    """Immutable bag of RAGPipeline toggle overrides."""

    name: ProfileName
    use_hybrid_search: bool
    use_query_rewriting: bool
    use_hyde: bool
    use_adaptive_retrieval: bool
    use_multi_query: bool
    use_self_rag: bool
    use_query_decomposition: bool
    use_response_cache: bool
    use_propositions: bool
    use_knowledge_graph: bool

    def to_pipeline_kwargs(self) -> Dict[str, Any]:
        """Return kwargs suitable for ``RAGPipeline(**profile.to_pipeline_kwargs())``."""
        return {
            "use_hybrid_search": self.use_hybrid_search,
            "use_query_rewriting": self.use_query_rewriting,
            "use_hyde": self.use_hyde,
            "use_adaptive_retrieval": self.use_adaptive_retrieval,
            "use_multi_query": self.use_multi_query,
            "use_self_rag": self.use_self_rag,
            "use_query_decomposition": self.use_query_decomposition,
            "use_response_cache": self.use_response_cache,
            "use_propositions": self.use_propositions,
            "use_knowledge_graph": self.use_knowledge_graph,
        }


# ── Pre-built profiles ────────────────────────────────────────────────────────

FAST = RetrievalProfile(
    name=ProfileName.FAST,
    use_hybrid_search=True,
    use_query_rewriting=False,
    use_hyde=False,
    use_adaptive_retrieval=True,
    use_multi_query=False,
    use_self_rag=False,
    use_query_decomposition=False,
    use_response_cache=True,
    use_propositions=False,
    use_knowledge_graph=False,
)

BALANCED = RetrievalProfile(
    name=ProfileName.BALANCED,
    use_hybrid_search=True,
    use_query_rewriting=True,
    use_hyde=False,
    use_adaptive_retrieval=True,
    use_multi_query=True,
    use_self_rag=True,
    use_query_decomposition=False,
    use_response_cache=True,
    use_propositions=False,
    use_knowledge_graph=False,
)

DEEP = RetrievalProfile(
    name=ProfileName.DEEP,
    use_hybrid_search=True,
    use_query_rewriting=True,
    use_hyde=True,
    use_adaptive_retrieval=True,
    use_multi_query=True,
    use_self_rag=True,
    use_query_decomposition=True,
    use_response_cache=True,
    use_propositions=True,
    use_knowledge_graph=True,
)

_PROFILES: Dict[ProfileName, RetrievalProfile] = {
    ProfileName.FAST: FAST,
    ProfileName.BALANCED: BALANCED,
    ProfileName.DEEP: DEEP,
}


def get_profile(name: str | ProfileName) -> RetrievalProfile:
    """Look up a profile by name.  Raises ``KeyError`` for unknown names."""
    if isinstance(name, str):
        name = ProfileName(name.lower())
    return _PROFILES[name]


def select_profile_for_query(query: str) -> RetrievalProfile:
    """
    Heuristic profile selection based on query surface features.

    Rules (intentionally simple — no LLM call):
      - Short, single-clause questions → fast
      - Questions with comparison / multi-part markers → deep
      - Everything else → balanced
    """
    q = query.lower().strip()
    words = q.split()

    multi_part_markers = {"vs", "versus", "compare", "differences", "similarities",
                          "contrast", "and also", "in addition"}
    decomposition_markers = {"step by step", "step-by-step", "explain each",
                             "trace through", "walk me through"}

    if any(m in q for m in decomposition_markers) or any(m in q for m in multi_part_markers):
        logger.debug("Profile selector: deep (multi-part/decomposition markers)")
        return DEEP

    if len(words) <= 6:
        logger.debug("Profile selector: fast (short query, %d words)", len(words))
        return FAST

    logger.debug("Profile selector: balanced (default)")
    return BALANCED
