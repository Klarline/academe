"""
Tests for proposition-based indexing and knowledge graph extraction.

Covers:
    - PropositionExtractor (LLM + fallback)
    - Proposition model (serialization, repr)
    - PropositionRepository (store, query, delete)
    - KGExtractor (LLM + fallback)
    - KGTriple model (equality, hashing, serialization)
    - KnowledgeGraphRepository (store, query, delete)
    - KnowledgeGraphTraverser (neighbors, multi-hop, find_paths, format_context)
    - Pipeline wiring (init flags, _extract_query_entities, _get_kg_context)
    - Module exports
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from types import SimpleNamespace

from core.rag.proposition_indexer import (
    Proposition,
    PropositionExtractor,
    PropositionRepository,
    DECOMPOSITION_PROMPT,
)
from core.rag.knowledge_graph import (
    KGTriple,
    KGExtractor,
    KnowledgeGraphRepository,
    KnowledgeGraphTraverser,
    EXTRACTION_PROMPT,
)


# ---------------------------------------------------------------------------
# Proposition model
# ---------------------------------------------------------------------------
class TestProposition(unittest.TestCase):
    def test_to_dict_roundtrip(self):
        p = Proposition(
            text="PCA reduces dimensionality.",
            document_id="doc1",
            user_id="u1",
            source_chunk_index=3,
            source_chunk_content="PCA is a technique...",
            proposition_index=0,
            metadata={"page_number": 5},
        )
        d = p.to_dict()
        p2 = Proposition.from_dict(d)
        self.assertEqual(p2.text, p.text)
        self.assertEqual(p2.document_id, "doc1")
        self.assertEqual(p2.source_chunk_index, 3)
        self.assertEqual(p2.metadata["page_number"], 5)

    def test_repr(self):
        p = Proposition(
            text="Short fact.",
            document_id="d",
            user_id="u",
            source_chunk_index=0,
            source_chunk_content="",
            proposition_index=7,
        )
        self.assertIn("idx=7", repr(p))


# ---------------------------------------------------------------------------
# PropositionExtractor
# ---------------------------------------------------------------------------
class TestPropositionExtractor(unittest.TestCase):
    def test_fallback_extract_splits_sentences(self):
        ext = PropositionExtractor(llm=False)
        ext._llm_initialized = True
        text = (
            "Neural networks learn by adjusting weights. "
            "Backpropagation computes the gradient of the loss function. "
            "Short. "
            "Gradient descent minimizes the loss iteratively."
        )
        props = ext.extract(text)
        self.assertTrue(len(props) >= 2)
        self.assertTrue(any("gradient" in p.lower() for p in props))

    def test_fallback_skips_short_sentences(self):
        ext = PropositionExtractor(llm=False)
        ext._llm_initialized = True
        props = ext.extract("OK. Hi. Yes.")
        self.assertEqual(len(props), 0)

    def test_llm_extract(self):
        mock_llm = Mock()
        mock_llm.invoke.return_value = SimpleNamespace(
            content="1. PCA reduces dimensionality of data.\n"
                    "2. PCA finds principal components using eigenvectors.\n"
                    "3. x"
        )
        ext = PropositionExtractor(llm=mock_llm)
        props = ext.extract("PCA is a statistical technique that reduces...")
        self.assertEqual(len(props), 2)
        self.assertIn("PCA", props[0])

    def test_extract_from_chunks(self):
        mock_llm = Mock()
        mock_llm.invoke.return_value = SimpleNamespace(
            content="1. Chunk one fact about topic X in detail.\n"
                    "2. Another relevant fact from topic X.\n"
        )
        ext = PropositionExtractor(llm=mock_llm)
        chunk = Mock()
        chunk.content = "Topic X is important."
        chunk.chunk_index = 0
        chunk.page_number = 1
        chunk.section_title = "Intro"

        propositions = ext.extract_from_chunks([chunk], "doc1", "u1")
        self.assertEqual(len(propositions), 2)
        self.assertEqual(propositions[0].document_id, "doc1")
        self.assertEqual(propositions[0].source_chunk_index, 0)

    def test_max_propositions_respected(self):
        ext = PropositionExtractor(llm=False, max_propositions_per_chunk=2)
        ext._llm_initialized = True
        text = (
            "First long sentence about neural networks and their applications. "
            "Second long sentence about deep learning architectures and designs. "
            "Third long sentence about optimization algorithms and convergence."
        )
        props = ext.extract(text)
        self.assertLessEqual(len(props), 2)


# ---------------------------------------------------------------------------
# PropositionRepository
# ---------------------------------------------------------------------------
class TestPropositionRepository(unittest.TestCase):
    def setUp(self):
        self.mock_db = Mock()
        self.mock_collection = Mock()
        self.mock_db.get_database.return_value = {"propositions": self.mock_collection}
        self.repo = PropositionRepository(db=self.mock_db)

    def test_store_propositions(self):
        props = [
            Proposition("Fact A.", "doc1", "u1", 0, "chunk text", 0),
            Proposition("Fact B.", "doc1", "u1", 0, "chunk text", 1),
        ]
        self.mock_collection.insert_many.return_value = Mock(inserted_ids=["id1", "id2"])
        count = self.repo.store_propositions(props)
        self.assertEqual(count, 2)
        self.mock_collection.insert_many.assert_called_once()

    def test_store_empty_returns_zero(self):
        self.assertEqual(self.repo.store_propositions([]), 0)

    def test_delete_document_propositions(self):
        self.mock_collection.delete_many.return_value = Mock(deleted_count=5)
        count = self.repo.delete_document_propositions("doc1")
        self.assertEqual(count, 5)


# ---------------------------------------------------------------------------
# KGTriple model
# ---------------------------------------------------------------------------
class TestKGTriple(unittest.TestCase):
    def test_to_dict_roundtrip(self):
        t = KGTriple("PCA", "reduces", "dimensionality", "doc1", 2, 0.9)
        d = t.to_dict()
        t2 = KGTriple.from_dict(d)
        self.assertEqual(t2.subject, "pca")
        self.assertEqual(t2.predicate, "reduces")
        self.assertEqual(t2.object_, "dimensionality")

    def test_equality_and_hash(self):
        t1 = KGTriple("gradient descent", "minimizes", "loss function")
        t2 = KGTriple("Gradient Descent", "minimizes", "Loss Function")
        self.assertEqual(t1, t2)
        self.assertEqual(hash(t1), hash(t2))

    def test_not_equal_to_non_triple(self):
        t = KGTriple("a", "b", "c")
        self.assertNotEqual(t, "not a triple")

    def test_repr(self):
        t = KGTriple("pca", "uses", "svd")
        self.assertIn("pca", repr(t))
        self.assertIn("svd", repr(t))


# ---------------------------------------------------------------------------
# KGExtractor
# ---------------------------------------------------------------------------
class TestKGExtractor(unittest.TestCase):
    def test_llm_extraction(self):
        mock_llm = Mock()
        mock_llm.invoke.return_value = SimpleNamespace(
            content="neural network | uses | backpropagation\n"
                    "backpropagation | applies | chain rule\n"
                    "gradient descent | minimizes | loss function\n"
        )
        ext = KGExtractor(llm=mock_llm)
        triples = ext.extract("Neural networks use backpropagation...", "doc1", 0)
        self.assertEqual(len(triples), 3)
        self.assertEqual(triples[0].subject, "neural network")
        self.assertEqual(triples[1].predicate, "applies")

    def test_fallback_extract_is_a(self):
        ext = KGExtractor(llm=False)
        ext._llm_initialized = True
        text = "Backpropagation is a method for computing gradients."
        triples = ext.extract(text, "doc1", 0)
        self.assertTrue(len(triples) >= 1)
        self.assertEqual(triples[0].predicate, "is_a")

    def test_max_triples_respected(self):
        mock_llm = Mock()
        lines = "\n".join([f"entity{i} | rel | entity{i+100}" for i in range(20)])
        mock_llm.invoke.return_value = SimpleNamespace(content=lines)
        ext = KGExtractor(llm=mock_llm, max_triples_per_chunk=5)
        triples = ext.extract("text", "doc1", 0)
        self.assertLessEqual(len(triples), 5)

    def test_extract_from_chunks_deduplicates(self):
        mock_llm = Mock()
        mock_llm.invoke.return_value = SimpleNamespace(
            content="pca | reduces | dimensionality\n"
        )
        ext = KGExtractor(llm=mock_llm)
        chunk1 = Mock(content="PCA reduces dim", chunk_index=0)
        chunk2 = Mock(content="PCA reduces dim again", chunk_index=1)
        triples = ext.extract_from_chunks([chunk1, chunk2], "doc1")
        # Same triple from two chunks should be deduplicated
        self.assertEqual(len(triples), 1)

    def test_parse_triples_with_numbered_lines(self):
        mock_llm = Mock()
        mock_llm.invoke.return_value = SimpleNamespace(
            content="1. neural net | uses | relu\n"
                    "2) cnn | applies_to | images\n"
        )
        ext = KGExtractor(llm=mock_llm)
        triples = ext.extract("text", "d1", 0)
        self.assertEqual(len(triples), 2)


# ---------------------------------------------------------------------------
# KnowledgeGraphRepository
# ---------------------------------------------------------------------------
class TestKnowledgeGraphRepository(unittest.TestCase):
    def setUp(self):
        self.mock_db = Mock()
        self.mock_collection = Mock()
        self.mock_db.get_database.return_value = {"knowledge_graph": self.mock_collection}
        self.repo = KnowledgeGraphRepository(db=self.mock_db)

    def test_store_triples(self):
        triples = [KGTriple("a", "b", "c", "doc1")]
        self.mock_collection.insert_many.return_value = Mock(inserted_ids=["id1"])
        count = self.repo.store_triples(triples)
        self.assertEqual(count, 1)

    def test_store_empty_returns_zero(self):
        self.assertEqual(self.repo.store_triples([]), 0)

    def test_delete_document_triples(self):
        self.mock_collection.delete_many.return_value = Mock(deleted_count=3)
        count = self.repo.delete_document_triples("doc1")
        self.assertEqual(count, 3)


# ---------------------------------------------------------------------------
# KnowledgeGraphTraverser
# ---------------------------------------------------------------------------
class TestKnowledgeGraphTraverser(unittest.TestCase):
    def _build_sample_graph(self):
        triples = [
            KGTriple("neural network", "uses", "backpropagation"),
            KGTriple("backpropagation", "applies", "chain rule"),
            KGTriple("gradient descent", "minimizes", "loss function"),
            KGTriple("neural network", "trained_by", "gradient descent"),
            KGTriple("pca", "reduces", "dimensionality"),
        ]
        return KnowledgeGraphTraverser(triples)

    def test_entities_loaded(self):
        g = self._build_sample_graph()
        self.assertIn("neural network", g.entities)
        self.assertIn("chain rule", g.entities)
        self.assertIn("pca", g.entities)

    def test_get_neighbors(self):
        g = self._build_sample_graph()
        neighbors = g.get_neighbors("backpropagation")
        # Forward: applies → chain rule. Reverse: ~uses → neural network
        neighbor_entities = {n[1] for n in neighbors}
        self.assertIn("chain rule", neighbor_entities)
        self.assertIn("neural network", neighbor_entities)

    def test_find_entity_exact(self):
        g = self._build_sample_graph()
        matches = g.find_entity("pca")
        self.assertIn("pca", matches)

    def test_find_entity_partial(self):
        g = self._build_sample_graph()
        matches = g.find_entity("neural")
        self.assertTrue(any("neural" in m for m in matches))

    def test_multi_hop_from_neural_network(self):
        g = self._build_sample_graph()
        paths = g.multi_hop("neural network", max_hops=2)
        reached = set()
        for path in paths:
            reached.update(path["entities"])
        self.assertIn("backpropagation", reached)
        self.assertIn("chain rule", reached)

    def test_find_paths(self):
        g = self._build_sample_graph()
        paths = g.find_paths("neural network", "chain rule", max_hops=3)
        self.assertTrue(len(paths) >= 1)
        for path in paths:
            self.assertEqual(path["entities"][0], "neural network")
            self.assertEqual(path["entities"][-1], "chain rule")

    def test_find_paths_no_connection(self):
        g = self._build_sample_graph()
        paths = g.find_paths("pca", "chain rule", max_hops=3)
        self.assertEqual(len(paths), 0)

    def test_format_context(self):
        g = self._build_sample_graph()
        paths = g.multi_hop("neural network", max_hops=1)
        ctx = g.format_context(paths)
        self.assertIn("Knowledge Graph Relationships:", ctx)

    def test_format_context_empty(self):
        g = KnowledgeGraphTraverser([])
        ctx = g.format_context([])
        self.assertEqual(ctx, "")

    def test_multi_hop_empty_graph(self):
        g = KnowledgeGraphTraverser([])
        paths = g.multi_hop("anything")
        self.assertEqual(paths, [])


# ---------------------------------------------------------------------------
# Pipeline wiring
# ---------------------------------------------------------------------------
class TestPipelineKGAndPropositions(unittest.TestCase):
    @patch("core.rag.pipeline.RetrievalFeedback")
    @patch("core.rag.pipeline.ChunkRepository")
    @patch("core.rag.pipeline.KnowledgeGraphRepository")
    @patch("core.rag.pipeline.PropositionRepository")
    @patch("core.rag.pipeline.KGExtractor")
    @patch("core.rag.pipeline.PropositionExtractor")
    @patch("core.rag.pipeline.SelfRAGController")
    @patch("core.rag.pipeline.QueryDecomposer")
    @patch("core.rag.pipeline.SemanticResponseCache")
    @patch("core.rag.pipeline.QueryRewriter")
    @patch("core.rag.pipeline.DocumentManager")
    def test_pipeline_init_with_propositions_and_kg(
        self, MockDM, MockQR, MockCache, MockDecomp,
        MockSelfRAG, MockPropExt, MockKGExt, MockPropRepo,
        MockKGRepo, MockChunkRepo, MockFeedback,
    ):
        from core.rag.pipeline import RAGPipeline
        from core.vectors import HybridSearchService

        mock_hs = Mock(spec=HybridSearchService)

        pipeline = RAGPipeline(
            search_service=mock_hs,
            use_hybrid_search=False,
            use_propositions=True,
            use_knowledge_graph=True,
        )
        self.assertIsNotNone(pipeline.proposition_extractor)
        self.assertIsNotNone(pipeline.proposition_repo)
        self.assertIsNotNone(pipeline.kg_extractor)
        self.assertIsNotNone(pipeline.kg_repo)

    @patch("core.rag.pipeline.RetrievalFeedback")
    @patch("core.rag.pipeline.ChunkRepository")
    @patch("core.rag.pipeline.KnowledgeGraphRepository")
    @patch("core.rag.pipeline.PropositionRepository")
    @patch("core.rag.pipeline.KGExtractor")
    @patch("core.rag.pipeline.PropositionExtractor")
    @patch("core.rag.pipeline.SelfRAGController")
    @patch("core.rag.pipeline.QueryDecomposer")
    @patch("core.rag.pipeline.SemanticResponseCache")
    @patch("core.rag.pipeline.QueryRewriter")
    @patch("core.rag.pipeline.DocumentManager")
    def test_pipeline_init_disabled(
        self, MockDM, MockQR, MockCache, MockDecomp,
        MockSelfRAG, MockPropExt, MockKGExt, MockPropRepo,
        MockKGRepo, MockChunkRepo, MockFeedback,
    ):
        from core.rag.pipeline import RAGPipeline
        from core.vectors import HybridSearchService

        mock_hs = Mock(spec=HybridSearchService)

        pipeline = RAGPipeline(
            search_service=mock_hs,
            use_hybrid_search=False,
            use_propositions=False,
            use_knowledge_graph=False,
        )
        self.assertIsNone(pipeline.proposition_extractor)
        self.assertIsNone(pipeline.kg_extractor)


class TestExtractQueryEntities(unittest.TestCase):
    def test_filters_stop_words(self):
        from core.rag.pipeline import RAGPipeline
        entities = RAGPipeline._extract_query_entities(
            "What is the relationship between PCA and neural networks?"
        )
        entity_strs = " ".join(entities)
        self.assertIn("pca", entity_strs)
        self.assertIn("neural", entity_strs)
        self.assertNotIn("what", entities)
        self.assertNotIn("the", entities)

    def test_includes_bigrams(self):
        from core.rag.pipeline import RAGPipeline
        entities = RAGPipeline._extract_query_entities(
            "How does gradient descent work?"
        )
        self.assertTrue(any("gradient descent" in e for e in entities))


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------
class TestModuleExports(unittest.TestCase):
    def test_proposition_exports(self):
        from core.rag import (
            PropositionExtractor,
            PropositionRepository,
            Proposition,
        )
        self.assertIsNotNone(PropositionExtractor)
        self.assertIsNotNone(PropositionRepository)
        self.assertIsNotNone(Proposition)

    def test_kg_exports(self):
        from core.rag import (
            KGExtractor,
            KnowledgeGraphRepository,
            KnowledgeGraphTraverser,
            KGTriple,
        )
        self.assertIsNotNone(KGExtractor)
        self.assertIsNotNone(KnowledgeGraphRepository)
        self.assertIsNotNone(KnowledgeGraphTraverser)
        self.assertIsNotNone(KGTriple)


if __name__ == "__main__":
    unittest.main()
