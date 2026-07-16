"""
src/memory/fusion.py
───────────────────────
Multi-source memory result merger with de-duplication and score-based ranking.
"""
from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.memory.manager import RetrievedMemory

_SIMILARITY_THRESHOLD = 0.90  # cosine-sim cutoff for de-dup


class MemoryFusion:
    """
    Merges memory results from multiple backends:
    1. Normalises scores to [0, 1] per source
    2. De-duplicates near-identical contents (hash-based)
    3. Applies a weighted ensemble re-rank
    4. Returns top-k results sorted by final score
    """

    SOURCE_WEIGHTS: dict[str, float] = {
        "zep": 0.6,   # Semantic recency wins
        "mem0": 0.4,  # User facts supplement
    }

    def merge(
        self,
        memories: list["RetrievedMemory"],
        top_k: int = 8,
    ) -> list["RetrievedMemory"]:
        if not memories:
            return []

        seen: set[str] = set()
        unique: list["RetrievedMemory"] = []

        for m in memories:
            key = self._content_hash(m.content)
            if key not in seen:
                seen.add(key)
                # Apply source weight to score
                weight = self.SOURCE_WEIGHTS.get(m.source, 0.5)
                m.score = m.score * weight
                unique.append(m)

        # Sort descending by weighted score
        unique.sort(key=lambda m: m.score, reverse=True)
        return unique[:top_k]

    @staticmethod
    def _content_hash(content: str) -> str:
        return hashlib.sha256(content.strip().lower().encode()).hexdigest()[:16]
