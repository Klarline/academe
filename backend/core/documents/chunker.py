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

    def adaptive_chunk(
        self,
        text: str,
        document_type: str,
        document_id: str,
        user_id: str
    ) -> List[DocumentChunk]:
        """
        Adaptively chunk based on document type.

        Args:
            text: Document text
            document_type: Type of document (textbook, paper, notes)
            document_id: Document ID
            user_id: User ID

        Returns:
            List of chunks
        """
        # Adjust parameters based on document type
        if document_type == "textbook":
            # Larger chunks for textbooks
            self.chunk_size = 1200
            self.chunk_overlap = 300
            self.strategy = "semantic"
        elif document_type == "paper":
            # Smaller chunks for papers
            self.chunk_size = 800
            self.chunk_overlap = 200
            self.strategy = "recursive"
        elif document_type == "notes":
            # Medium chunks for notes
            self.chunk_size = 1000
            self.chunk_overlap = 200
            self.strategy = "recursive"

        # Reinitialize splitters with new parameters
        self._init_splitters()

        # Chunk the document
        return self.chunk_document(text, document_id, user_id)