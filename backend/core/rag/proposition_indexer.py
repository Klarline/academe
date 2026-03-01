"""
Proposition-based indexing for Academe.

Decomposes document chunks into atomic factual statements (propositions)
before embedding. Each proposition is a single, self-contained fact that
can be independently verified.

This enables more precise retrieval: instead of matching against a 1000-char
chunk that contains many facts, we match against a single focused statement.
Each proposition retains a back-reference to its source chunk for context
expansion at generation time.

Based on: "Dense X Retrieval: What Retrieval Granularity Should We Use?"
(Chen et al., 2023)
"""

import logging
import re
from typing import List, Dict, Any, Optional

from core.config.llm_config import get_openai_llm

logger = logging.getLogger(__name__)


class Proposition:
    """An atomic factual statement extracted from a chunk."""

    __slots__ = (
        "text",
        "document_id",
        "user_id",
        "source_chunk_index",
        "source_chunk_content",
        "proposition_index",
        "metadata",
    )

    def __init__(
        self,
        text: str,
        document_id: str,
        user_id: str,
        source_chunk_index: int,
        source_chunk_content: str,
        proposition_index: int,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.text = text
        self.document_id = document_id
        self.user_id = user_id
        self.source_chunk_index = source_chunk_index
        self.source_chunk_content = source_chunk_content
        self.proposition_index = proposition_index
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "document_id": self.document_id,
            "user_id": self.user_id,
            "source_chunk_index": self.source_chunk_index,
            "source_chunk_content": self.source_chunk_content,
            "proposition_index": self.proposition_index,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Proposition":
        return cls(**data)

    def __repr__(self) -> str:
        return f"Proposition(idx={self.proposition_index}, text={self.text[:60]!r}...)"


DECOMPOSITION_PROMPT = """Break the following text into atomic factual propositions.

Rules:
1. Each proposition should be a single, self-contained factual statement.
2. Each proposition must be understandable without the other propositions.
3. De-contextualize: replace pronouns with the entities they refer to.
4. Keep technical terms, equations, and specific numbers exactly as they appear.
5. If the text contains definitions, each definition is one proposition.
6. If the text describes a process, each step is one proposition.
7. Output one proposition per line, numbered.
8. Do NOT include opinions, speculations, or anything not stated in the text.
9. Aim for 3-10 propositions per chunk. Skip trivial or redundant facts.

Text:
{chunk_text}

Propositions:"""


class PropositionExtractor:
    """Extracts atomic propositions from text chunks using an LLM."""

    def __init__(self, llm=None, max_propositions_per_chunk: int = 10):
        self.llm = llm
        self.max_propositions = max_propositions_per_chunk
        self._llm_initialized = False

    def _ensure_llm(self):
        if self.llm is None and not self._llm_initialized:
            try:
                self.llm = get_openai_llm("gpt-4o-mini", temperature=0.0)
            except Exception as e:
                logger.warning(f"Could not initialize LLM for proposition extraction: {e}")
            self._llm_initialized = True

    def extract(self, chunk_text: str) -> List[str]:
        """
        Extract atomic propositions from a single chunk.

        Args:
            chunk_text: The chunk content.

        Returns:
            List of proposition strings.
        """
        self._ensure_llm()
        if not self.llm:
            return self._fallback_extract(chunk_text)

        prompt = DECOMPOSITION_PROMPT.format(chunk_text=chunk_text)
        try:
            response = self.llm.invoke(prompt)
            raw = response.content if hasattr(response, "content") else str(response)
            return self._parse_propositions(raw)
        except Exception as e:
            logger.warning(f"LLM proposition extraction failed: {e}")
            return self._fallback_extract(chunk_text)

    def _parse_propositions(self, raw_text: str) -> List[str]:
        """Parse numbered propositions from LLM output."""
        propositions = []
        for line in raw_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            cleaned = re.sub(r"^\d+[\.\)\-]\s*", "", line).strip()
            if len(cleaned) > 10:
                propositions.append(cleaned)
            if len(propositions) >= self.max_propositions:
                break
        return propositions

    def _fallback_extract(self, chunk_text: str) -> List[str]:
        """
        Sentence-level fallback when LLM is unavailable.

        Splits on sentence boundaries and filters out trivial sentences.
        """
        sentences = re.split(r"(?<=[.!?])\s+", chunk_text.strip())
        propositions = []
        for sent in sentences:
            sent = sent.strip()
            if len(sent) > 20 and len(sent.split()) >= 4:
                propositions.append(sent)
            if len(propositions) >= self.max_propositions:
                break
        return propositions

    def extract_from_chunks(
        self,
        chunks,
        document_id: str,
        user_id: str,
    ) -> List[Proposition]:
        """
        Extract propositions from a list of DocumentChunk objects.

        Args:
            chunks: List of DocumentChunk instances.
            document_id: Document ID for back-references.
            user_id: Owner user ID.

        Returns:
            List of Proposition objects with source chunk references.
        """
        all_propositions: List[Proposition] = []
        global_idx = 0

        for chunk in chunks:
            prop_texts = self.extract(chunk.content)
            for text in prop_texts:
                prop = Proposition(
                    text=text,
                    document_id=document_id,
                    user_id=user_id,
                    source_chunk_index=chunk.chunk_index,
                    source_chunk_content=chunk.content,
                    proposition_index=global_idx,
                    metadata={
                        "page_number": chunk.page_number,
                        "section_title": chunk.section_title,
                    },
                )
                all_propositions.append(prop)
                global_idx += 1

        logger.info(
            f"Extracted {len(all_propositions)} propositions from "
            f"{len(chunks)} chunks (doc={document_id})"
        )
        return all_propositions


class PropositionRepository:
    """MongoDB storage for propositions."""

    COLLECTION_NAME = "propositions"

    def __init__(self, db=None):
        if db is None:
            from core.database import get_database
            db = get_database()
        self.db = db

    def _collection(self):
        return self.db.get_database()[self.COLLECTION_NAME]

    def store_propositions(self, propositions: List[Proposition]) -> int:
        """Batch-insert propositions. Returns count inserted."""
        if not propositions:
            return 0
        docs = [p.to_dict() for p in propositions]
        result = self._collection().insert_many(docs)
        return len(result.inserted_ids)

    def get_document_propositions(
        self, document_id: str
    ) -> List[Proposition]:
        """Get all propositions for a document, ordered by index."""
        cursor = self._collection().find(
            {"document_id": document_id}
        ).sort("proposition_index", 1)
        return [Proposition.from_dict(d) for d in cursor]

    def get_chunk_propositions(
        self, document_id: str, chunk_index: int
    ) -> List[Proposition]:
        """Get propositions originating from a specific chunk."""
        cursor = self._collection().find(
            {"document_id": document_id, "source_chunk_index": chunk_index}
        ).sort("proposition_index", 1)
        return [Proposition.from_dict(d) for d in cursor]

    def search_propositions(
        self, user_id: str, query: str, limit: int = 20
    ) -> List[Proposition]:
        """Simple regex text search across propositions."""
        cursor = self._collection().find(
            {"user_id": user_id, "text": {"$regex": query, "$options": "i"}}
        ).limit(limit)
        return [Proposition.from_dict(d) for d in cursor]

    def delete_document_propositions(self, document_id: str) -> int:
        """Delete all propositions for a document."""
        result = self._collection().delete_many({"document_id": document_id})
        return result.deleted_count

    def count(self, document_id: Optional[str] = None) -> int:
        query = {"document_id": document_id} if document_id else {}
        return self._collection().count_documents(query)
