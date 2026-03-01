"""
Knowledge graph extraction and traversal for Academe.

Extracts entities and relationships from document chunks using an LLM,
stores them in MongoDB, and supports multi-hop graph traversal for
questions that span multiple documents or concepts.

Example extracted triples:
    ("PCA", "reduces", "dimensionality")
    ("backpropagation", "uses", "chain rule")
    ("gradient descent", "minimizes", "loss function")

Multi-hop query example:
    Q: "What optimization method is used by the algorithm that applies chain rule?"
    → chain rule ← backpropagation → uses → gradient descent
"""

import logging
import re
from collections import defaultdict, deque
from typing import List, Dict, Any, Optional, Tuple, Set

from core.config.llm_config import get_openai_llm

logger = logging.getLogger(__name__)


class KGTriple:
    """A (subject, predicate, object) triple in the knowledge graph."""

    __slots__ = (
        "subject",
        "predicate",
        "object_",
        "document_id",
        "chunk_index",
        "confidence",
        "metadata",
    )

    def __init__(
        self,
        subject: str,
        predicate: str,
        object_: str,
        document_id: str = "",
        chunk_index: int = -1,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.subject = subject.strip().lower()
        self.predicate = predicate.strip().lower()
        self.object_ = object_.strip().lower()
        self.document_id = document_id
        self.chunk_index = chunk_index
        self.confidence = confidence
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object_,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KGTriple":
        return cls(
            subject=data["subject"],
            predicate=data["predicate"],
            object_=data.get("object", data.get("object_", "")),
            document_id=data.get("document_id", ""),
            chunk_index=data.get("chunk_index", -1),
            confidence=data.get("confidence", 1.0),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        return f"({self.subject} --[{self.predicate}]--> {self.object_})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, KGTriple):
            return False
        return (
            self.subject == other.subject
            and self.predicate == other.predicate
            and self.object_ == other.object_
        )

    def __hash__(self) -> int:
        return hash((self.subject, self.predicate, self.object_))


EXTRACTION_PROMPT = """Extract knowledge graph triples (subject, predicate, object) from the following text.

Rules:
1. Each triple represents a factual relationship: (entity1, relationship, entity2).
2. Use concise noun phrases for entities and short verb phrases for relationships.
3. Normalize entities: use lowercase, canonical forms (e.g., "neural network" not "Neural Networks").
4. Common relationship types: is_a, has, uses, causes, part_of, defined_as, produces, requires, applies_to, reduces, optimizes, measures.
5. Extract 3-8 triples per chunk. Focus on the most important relationships.
6. Output format: one triple per line as: subject | predicate | object
7. Only extract factual relationships explicitly stated or strongly implied in the text.

Text:
{chunk_text}

Triples:"""


class KGExtractor:
    """Extracts knowledge graph triples from text using an LLM."""

    def __init__(self, llm=None, max_triples_per_chunk: int = 8):
        self.llm = llm
        self.max_triples = max_triples_per_chunk
        self._llm_initialized = False

    def _ensure_llm(self):
        if self.llm is None and not self._llm_initialized:
            try:
                self.llm = get_openai_llm("gpt-4o-mini", temperature=0.0)
            except Exception as e:
                logger.warning(f"Could not initialize LLM for KG extraction: {e}")
            self._llm_initialized = True

    def extract(
        self,
        chunk_text: str,
        document_id: str = "",
        chunk_index: int = -1,
    ) -> List[KGTriple]:
        """Extract triples from a single chunk."""
        self._ensure_llm()
        if not self.llm:
            return self._fallback_extract(chunk_text, document_id, chunk_index)

        prompt = EXTRACTION_PROMPT.format(chunk_text=chunk_text)
        try:
            response = self.llm.invoke(prompt)
            raw = response.content if hasattr(response, "content") else str(response)
            return self._parse_triples(raw, document_id, chunk_index)
        except Exception as e:
            logger.warning(f"LLM KG extraction failed: {e}")
            return self._fallback_extract(chunk_text, document_id, chunk_index)

    def _parse_triples(
        self, raw_text: str, document_id: str, chunk_index: int
    ) -> List[KGTriple]:
        """Parse 'subject | predicate | object' lines from LLM output."""
        triples = []
        for line in raw_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Remove leading number/bullet
            line = re.sub(r"^\d+[\.\)\-]\s*", "", line)
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3 and all(len(p) > 0 for p in parts[:3]):
                triple = KGTriple(
                    subject=parts[0],
                    predicate=parts[1],
                    object_=parts[2],
                    document_id=document_id,
                    chunk_index=chunk_index,
                )
                triples.append(triple)
            if len(triples) >= self.max_triples:
                break
        return triples

    def _fallback_extract(
        self, chunk_text: str, document_id: str, chunk_index: int
    ) -> List[KGTriple]:
        """
        Regex-based fallback: extracts simple 'X is/are/uses/has Y' patterns.
        """
        patterns = [
            (r"(\b[A-Z][a-z]+(?:\s+[a-z]+)*)\s+(?:is|are)\s+(?:a|an|the)?\s*(.+?)(?:\.|,|;|$)", "is_a"),
            (r"(\b[A-Z][a-z]+(?:\s+[a-z]+)*)\s+uses?\s+(.+?)(?:\.|,|;|$)", "uses"),
            (r"(\b[A-Z][a-z]+(?:\s+[a-z]+)*)\s+has\s+(.+?)(?:\.|,|;|$)", "has"),
        ]
        triples = []
        for pattern, predicate in patterns:
            for match in re.finditer(pattern, chunk_text):
                subj = match.group(1).strip()
                obj = match.group(2).strip()
                if len(subj) > 2 and len(obj) > 2 and len(obj.split()) <= 6:
                    triples.append(
                        KGTriple(
                            subject=subj,
                            predicate=predicate,
                            object_=obj,
                            document_id=document_id,
                            chunk_index=chunk_index,
                            confidence=0.6,
                        )
                    )
            if len(triples) >= self.max_triples:
                break
        return triples

    def extract_from_chunks(
        self,
        chunks,
        document_id: str,
    ) -> List[KGTriple]:
        """Extract triples from a list of DocumentChunk objects."""
        all_triples: List[KGTriple] = []
        for chunk in chunks:
            triples = self.extract(chunk.content, document_id, chunk.chunk_index)
            all_triples.extend(triples)

        # Deduplicate
        unique = list(set(all_triples))
        logger.info(
            f"Extracted {len(unique)} unique triples from "
            f"{len(chunks)} chunks (doc={document_id})"
        )
        return unique


class KnowledgeGraphRepository:
    """MongoDB storage for knowledge graph triples."""

    COLLECTION_NAME = "knowledge_graph"

    def __init__(self, db=None):
        if db is None:
            from core.database import get_database
            db = get_database()
        self.db = db

    def _collection(self):
        return self.db.get_database()[self.COLLECTION_NAME]

    def store_triples(self, triples: List[KGTriple]) -> int:
        """Batch-insert triples. Returns count inserted."""
        if not triples:
            return 0
        docs = [t.to_dict() for t in triples]
        result = self._collection().insert_many(docs)
        return len(result.inserted_ids)

    def get_document_triples(self, document_id: str) -> List[KGTriple]:
        """Get all triples for a document."""
        cursor = self._collection().find({"document_id": document_id})
        return [KGTriple.from_dict(d) for d in cursor]

    def get_entity_triples(
        self, entity: str, user_id: Optional[str] = None
    ) -> List[KGTriple]:
        """Get all triples where entity appears as subject or object."""
        entity_lower = entity.strip().lower()
        query: Dict[str, Any] = {
            "$or": [
                {"subject": {"$regex": entity_lower, "$options": "i"}},
                {"object": {"$regex": entity_lower, "$options": "i"}},
            ]
        }
        if user_id:
            # Filter by documents belonging to user (requires join or denormalization)
            pass
        cursor = self._collection().find(query)
        return [KGTriple.from_dict(d) for d in cursor]

    def delete_document_triples(self, document_id: str) -> int:
        """Delete all triples for a document."""
        result = self._collection().delete_many({"document_id": document_id})
        return result.deleted_count


class KnowledgeGraphTraverser:
    """
    In-memory graph traversal for multi-hop reasoning.

    Loads triples into an adjacency list and supports BFS traversal
    to find paths between entities.
    """

    def __init__(self, triples: Optional[List[KGTriple]] = None):
        self.adjacency: Dict[str, List[Tuple[str, str, KGTriple]]] = defaultdict(list)
        self.entities: Set[str] = set()
        if triples:
            self.load(triples)

    def load(self, triples: List[KGTriple]):
        """Load triples into the adjacency list (bidirectional)."""
        for t in triples:
            self.adjacency[t.subject].append((t.predicate, t.object_, t))
            self.adjacency[t.object_].append((f"~{t.predicate}", t.subject, t))
            self.entities.add(t.subject)
            self.entities.add(t.object_)

    def get_neighbors(self, entity: str) -> List[Tuple[str, str, KGTriple]]:
        """Get all (predicate, neighbor, triple) for an entity."""
        entity_lower = entity.strip().lower()
        results = []
        for key in self.adjacency:
            if entity_lower in key or key in entity_lower:
                results.extend(self.adjacency[key])
        return results

    def find_entity(self, query_term: str) -> List[str]:
        """Fuzzy-match a query term to known entities."""
        query_lower = query_term.strip().lower()
        exact = [e for e in self.entities if e == query_lower]
        if exact:
            return exact
        partial = [e for e in self.entities if query_lower in e or e in query_lower]
        return partial[:5]

    def multi_hop(
        self, start_entity: str, max_hops: int = 2, max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        BFS traversal from start_entity up to max_hops.

        Returns a list of paths, each path is:
            {"entities": [e1, e2, ...], "predicates": [p1, p2, ...],
             "triples": [t1, t2, ...], "hops": int}
        """
        starts = self.find_entity(start_entity)
        if not starts:
            return []

        results: List[Dict[str, Any]] = []
        visited: Set[str] = set()

        queue: deque = deque()
        for s in starts:
            queue.append({"entities": [s], "predicates": [], "triples": [], "hops": 0})
            visited.add(s)

        while queue and len(results) < max_results:
            path = queue.popleft()
            current = path["entities"][-1]
            hops = path["hops"]

            if hops > 0:
                results.append(path)

            if hops >= max_hops:
                continue

            for predicate, neighbor, triple in self.adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_path = {
                        "entities": path["entities"] + [neighbor],
                        "predicates": path["predicates"] + [predicate],
                        "triples": path["triples"] + [triple],
                        "hops": hops + 1,
                    }
                    queue.append(new_path)

        return results

    def find_paths(
        self,
        start: str,
        end: str,
        max_hops: int = 3,
    ) -> List[Dict[str, Any]]:
        """Find paths between two entities using BFS."""
        starts = self.find_entity(start)
        ends = set(self.find_entity(end))
        if not starts or not ends:
            return []

        results: List[Dict[str, Any]] = []
        visited: Set[str] = set()

        queue: deque = deque()
        for s in starts:
            queue.append({"entities": [s], "predicates": [], "triples": []})
            visited.add(s)

        while queue:
            path = queue.popleft()
            current = path["entities"][-1]

            if current in ends and len(path["entities"]) > 1:
                path["hops"] = len(path["predicates"])
                results.append(path)
                continue

            if len(path["entities"]) > max_hops + 1:
                continue

            for predicate, neighbor, triple in self.adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_path = {
                        "entities": path["entities"] + [neighbor],
                        "predicates": path["predicates"] + [predicate],
                        "triples": path["triples"] + [triple],
                    }
                    queue.append(new_path)

        return results

    def format_context(
        self, paths: List[Dict[str, Any]], max_triples: int = 15
    ) -> str:
        """
        Format graph paths into a context string for the LLM.

        Collects unique triples from all paths and formats them as
        readable relationship statements.
        """
        seen: Set[KGTriple] = set()
        statements: List[str] = []

        for path in paths:
            for triple in path.get("triples", []):
                if triple not in seen:
                    seen.add(triple)
                    statements.append(
                        f"- {triple.subject} {triple.predicate} {triple.object_}"
                    )
                if len(statements) >= max_triples:
                    break
            if len(statements) >= max_triples:
                break

        if not statements:
            return ""

        return "Knowledge Graph Relationships:\n" + "\n".join(statements)
