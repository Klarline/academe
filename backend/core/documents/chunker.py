"""Document chunking strategies for Academe."""

import logging
import re
from typing import List, Optional, Dict, Any

try:
    from langchain.text_splitter import (
        RecursiveCharacterTextSplitter,
        CharacterTextSplitter,
        TokenTextSplitter,
    )
except ImportError:
    # Fallback to langchain_text_splitters if available
    try:
        from langchain_text_splitters import (
            RecursiveCharacterTextSplitter,
            CharacterTextSplitter,
            TokenTextSplitter,
        )
    except ImportError:
        # Simple fallback implementation
        class RecursiveCharacterTextSplitter:
            def __init__(self, chunk_size=1000, chunk_overlap=200, **kwargs):
                self.chunk_size = chunk_size
                self.chunk_overlap = chunk_overlap

            def split_text(self, text):
                # Simple implementation
                chunks = []
                start = 0
                while start < len(text):
                    end = start + self.chunk_size
                    chunks.append(text[start:end])
                    start = end - self.chunk_overlap
                return chunks

        CharacterTextSplitter = RecursiveCharacterTextSplitter
        TokenTextSplitter = RecursiveCharacterTextSplitter

from core.models.document import DocumentChunk

logger = logging.getLogger(__name__)


class DocumentChunker:
    """Intelligent document chunking for RAG."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        strategy: str = "recursive"
    ):
        """
        Initialize document chunker.

        Args:
            chunk_size: Target size for chunks
            chunk_overlap: Overlap between chunks
            strategy: Chunking strategy to use
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy

        # Initialize splitters
        self._init_splitters()

    def _init_splitters(self):
        """Initialize text splitters."""
        # Recursive splitter (default) - best for most documents
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=[
                "\n\n",  # Paragraphs
                "\n",    # Lines
                ". ",    # Sentences
                ", ",    # Clauses
                " ",     # Words
                ""       # Characters
            ]
        )

        # Character splitter - simple splitting
        self.character_splitter = CharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separator="\n"
        )

        # Token splitter - for precise token counts
        self.token_splitter = TokenTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )

    def chunk_document(
        self,
        text: str,
        document_id: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """
        Chunk a document into smaller pieces.

        Args:
            text: Document text to chunk
            document_id: ID of parent document
            user_id: ID of document owner
            metadata: Optional metadata for chunks

        Returns:
            List of DocumentChunk objects
        """
        # Preprocess text
        processed_text = self._preprocess_text(text)

        # Split into chunks based on strategy
        if self.strategy == "recursive":
            chunks = self.recursive_splitter.split_text(processed_text)
        elif self.strategy == "character":
            chunks = self.character_splitter.split_text(processed_text)
        elif self.strategy == "token":
            chunks = self.token_splitter.split_text(processed_text)
        elif self.strategy == "semantic":
            chunks = self._semantic_chunk(processed_text)
        else:
            chunks = self.recursive_splitter.split_text(processed_text)

        # Create DocumentChunk objects
        document_chunks = []
        for idx, chunk_text in enumerate(chunks):
            if not chunk_text.strip():
                continue

            # Extract page number if present
            page_num = self._extract_page_number(chunk_text)

            # Extract section title if present
            section = self._extract_section(chunk_text)

            # Clean chunk text
            clean_text = self._clean_chunk_text(chunk_text)
            
            # Skip if cleaning resulted in empty text (strict check)
            if not clean_text:
                logger.debug(f"Skipping empty chunk {idx} (after type check)")
                continue
            if len(clean_text.strip()) == 0:
                logger.debug(f"Skipping whitespace-only chunk {idx}")
                continue
            if len(clean_text.split()) == 0:  # No words
                logger.debug(f"Skipping wordless chunk {idx}")
                continue

            # Detect content types
            has_equations = self._has_equations(clean_text)
            has_code = self._has_code(clean_text)
            has_tables = self._has_tables(clean_text)

            # Create chunk object
            chunk = DocumentChunk(
                document_id=document_id,
                user_id=user_id,
                chunk_index=idx,
                content=clean_text,
                page_number=page_num,
                section_title=section,
                char_count=len(clean_text),
                word_count=len(clean_text.split()),
                has_equations=has_equations,
                has_code=has_code,
                has_tables=has_tables,
                metadata=metadata or {}
            )

            document_chunks.append(chunk)

        logger.info(f"Created {len(document_chunks)} chunks from document")
        return document_chunks

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text before chunking."""
        # Ensure consistent spacing
        text = re.sub(r'\s+', ' ', text)

        # Preserve page markers
        text = re.sub(r'\[PAGE (\d+)\]', r'\n\n[PAGE \1]\n\n', text)

        # Preserve section headers
        text = re.sub(r'^(#+\s+.+)$', r'\n\n\1\n\n', text, flags=re.MULTILINE)

        return text.strip()

    def _semantic_chunk(self, text: str) -> List[str]:
        """
        Chunk text based on semantic boundaries.

        This is a simplified version - in production, you might use
        sentence embeddings to find semantic boundaries.
        """
        chunks = []
        current_chunk = []
        current_size = 0

        # Split by paragraphs first
        paragraphs = text.split('\n\n')

        for para in paragraphs:
            para_size = len(para)

            # If paragraph is too large, split it further
            if para_size > self.chunk_size:
                # Split large paragraph
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0

                # Use recursive splitter for large paragraph
                sub_chunks = self.recursive_splitter.split_text(para)
                chunks.extend(sub_chunks)

            # If adding paragraph exceeds chunk size, start new chunk
            elif current_size + para_size > self.chunk_size:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = para_size

            # Add to current chunk
            else:
                current_chunk.append(para)
                current_size += para_size

        # Add remaining chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    def _extract_page_number(self, text: str) -> Optional[int]:
        """Extract page number from chunk text."""
        match = re.search(r'\[PAGE (\d+)\]', text)
        if match:
            return int(match.group(1))
        return None

    def _extract_section(self, text: str) -> Optional[str]:
        """Extract section title from chunk text."""
        # Look for markdown headers
        match = re.search(r'^#+\s+(.+)$', text, re.MULTILINE)
        if match:
            return match.group(1).strip()

        # Look for uppercase section headers
        match = re.search(r'^([A-Z][A-Z\s]+)$', text, re.MULTILINE)
        if match:
            title = match.group(1).strip()
            if len(title) < 50:  # Reasonable title length
                return title

        return None

    def _clean_chunk_text(self, text: str) -> str:
        """Clean chunk text for storage."""
        # Remove page markers from content (already extracted)
        text = re.sub(r'\[PAGE \d+\]', '', text)

        # Clean up whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)

        return text.strip()

    def _has_equations(self, text: str) -> bool:
        """Detect if chunk contains mathematical equations."""
        # Check for mathematical symbols
        math_symbols = r'[∑∫∂∇√π±×÷≈≠≤≥αβγδεζηθικλμνξοπρστυφχψω]'
        if re.search(math_symbols, text):
            return True

        # Check for LaTeX commands
        if re.search(r'\\[A-Za-z]+\{', text):
            return True

        # Check for common equation patterns
        if re.search(r'\b[a-z]\s*=\s*\d+', text, re.IGNORECASE):
            return True

        return False

    def _has_code(self, text: str) -> bool:
        """Detect if chunk contains code."""
        code_patterns = [
            r'def\s+\w+\s*\(',
            r'class\s+\w+',
            r'import\s+\w+',
            r'function\s+\w+',
            r'if\s*\(.+\)\s*\{',
            r'for\s*\(.+\)\s*\{',
            r'```[\w]*\n',
        ]

        for pattern in code_patterns:
            if re.search(pattern, text):
                return True

        return False

    def _has_tables(self, text: str) -> bool:
        """Detect if chunk contains tables."""
        # Markdown table pattern
        if re.search(r'\|.+\|.+\|', text):
            return True

        # Tab-separated values
        if re.search(r'\t.+\t', text):
            lines_with_tabs = [l for l in text.split('\n') if '\t' in l]
            if len(lines_with_tabs) > 2:
                return True

        return False

    # Per-type chunking profiles: (chunk_size, chunk_overlap, strategy)
    TYPE_PROFILES = {
        "textbook": (1200, 300, "semantic"),
        "paper": (800, 200, "recursive"),
        "notes": (600, 100, "recursive"),
        "code": (1000, 150, "recursive"),
        "general": (1000, 200, "recursive"),
    }

    def adaptive_chunk(
        self,
        text: str,
        document_type: str,
        document_id: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        """
        Adaptively chunk based on document type without mutating instance state.

        Uses per-type profiles for chunk_size, overlap, and strategy.
        Creates a temporary chunker so the caller's defaults are preserved.

        Args:
            text: Document text
            document_type: One of textbook, paper, notes, code, general
            document_id: Document ID
            user_id: User ID
            metadata: Optional metadata passed through to chunks

        Returns:
            List of DocumentChunk objects
        """
        size, overlap, strategy = self.TYPE_PROFILES.get(
            document_type, self.TYPE_PROFILES["general"]
        )
        logger.info(
            f"Adaptive chunking: type={document_type}, "
            f"size={size}, overlap={overlap}, strategy={strategy}"
        )

        tmp = DocumentChunker(chunk_size=size, chunk_overlap=overlap, strategy=strategy)
        return tmp.chunk_document(text, document_id, user_id, metadata=metadata)

    def chunk_with_parents(
        self,
        text: str,
        document_id: str,
        user_id: str,
        parent_size: int = 1500,
        child_size: int = 400,
        child_overlap: int = 50,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        """
        Two-level parent-child chunking.

        Creates large 'parent' windows first, then splits each into smaller
        'child' chunks that are used for retrieval.  Each child stores its
        parent_chunk_index in metadata so the pipeline can expand to the
        full parent at context-building time.

        Args:
            text: Document text
            document_id: Document ID
            user_id: User ID
            parent_size: Target size for parent chunks
            child_size: Target size for child retrieval chunks
            child_overlap: Overlap between children inside a parent
            metadata: Extra metadata for every chunk

        Returns:
            List of child DocumentChunk objects (with parent refs in metadata)
        """
        base_meta = metadata or {}

        # Step 1: create parent chunks
        parent_chunker = DocumentChunker(
            chunk_size=parent_size, chunk_overlap=200, strategy="recursive"
        )
        parent_texts = parent_chunker.recursive_splitter.split_text(
            parent_chunker._preprocess_text(text)
        )

        # Step 2: split each parent into children
        child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=child_size,
            chunk_overlap=child_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", ", ", " ", ""],
        )

        child_chunks: List[DocumentChunk] = []
        global_idx = 0
        for parent_idx, parent_text in enumerate(parent_texts):
            clean_parent = self._clean_chunk_text(parent_text)
            if not clean_parent or not clean_parent.strip():
                continue

            child_texts = child_splitter.split_text(parent_text)
            for child_text in child_texts:
                clean = self._clean_chunk_text(child_text)
                if not clean or not clean.strip():
                    continue

                page_num = self._extract_page_number(child_text)
                section = self._extract_section(child_text)

                chunk_meta = {
                    **base_meta,
                    "parent_chunk_index": parent_idx,
                    "parent_content": clean_parent,
                }

                child_chunks.append(
                    DocumentChunk(
                        document_id=document_id,
                        user_id=user_id,
                        chunk_index=global_idx,
                        content=clean,
                        page_number=page_num,
                        section_title=section,
                        char_count=len(clean),
                        word_count=len(clean.split()),
                        has_equations=self._has_equations(clean),
                        has_code=self._has_code(clean),
                        has_tables=self._has_tables(clean),
                        metadata=chunk_meta,
                    )
                )
                global_idx += 1

        logger.info(
            f"Parent-child chunking: {len(parent_texts)} parents → "
            f"{len(child_chunks)} children"
        )
        return child_chunks