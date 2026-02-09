"""PDF document processor for Academe."""

import hashlib
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import PyPDF2
from PyPDF2 import PdfReader

from core.models.document import Document, DocumentStatus, DocumentType

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Process PDF documents for text extraction and analysis."""

    def __init__(self):
        """Initialize PDF processor."""
        self.supported_extensions = ['.pdf']

    def process_pdf(self, file_path: str) -> Tuple[str, Dict]:
        """
        Process a PDF file and extract text and metadata.

        Args:
            file_path: Path to the PDF file

        Returns:
            Tuple of (extracted_text, metadata_dict)

        Raises:
            ValueError: If file is not a valid PDF
            Exception: If processing fails
        """
        try:
            path = Path(file_path)

            if not path.exists():
                raise ValueError(f"File not found: {file_path}")

            if path.suffix.lower() != '.pdf':
                raise ValueError(f"Not a PDF file: {file_path}")

            # Open and read PDF
            with open(file_path, 'rb') as file:
                reader = PdfReader(file)

                # Extract metadata
                metadata = self._extract_metadata(reader, path)

                # Extract text from all pages
                text_content = self._extract_text(reader)

                # Clean and normalize text
                cleaned_text = self._clean_text(text_content)

                # Add text statistics
                metadata.update(self._calculate_text_stats(cleaned_text))

                return cleaned_text, metadata

        except Exception as e:
            logger.error(f"Failed to process PDF {file_path}: {e}")
            raise

    def _extract_metadata(self, reader: PdfReader, path: Path) -> Dict:
        """Extract metadata from PDF."""
        metadata = {
            'page_count': len(reader.pages),
            'file_size': path.stat().st_size,
            'filename': path.name,
        }

        # Try to extract PDF metadata
        if reader.metadata:
            info = reader.metadata
            metadata['title'] = self._safe_get(info, '/Title')
            metadata['author'] = self._safe_get(info, '/Author')
            metadata['subject'] = self._safe_get(info, '/Subject')
            metadata['creator'] = self._safe_get(info, '/Creator')
            metadata['keywords'] = self._safe_get(info, '/Keywords')

            # Parse creation date if available
            if '/CreationDate' in info:
                metadata['creation_date'] = str(info['/CreationDate'])

        return metadata

    def _safe_get(self, info: Dict, key: str) -> Optional[str]:
        """Safely get metadata value."""
        try:
            value = info.get(key)
            if value:
                return str(value).strip()
        except:
            pass
        return None

    def _extract_text(self, reader: PdfReader) -> str:
        """Extract text from all pages."""
        text_parts = []

        for page_num, page in enumerate(reader.pages, 1):
            try:
                # Extract text from page
                page_text = page.extract_text()

                if page_text:
                    # Add page marker for reference
                    text_parts.append(f"\n[PAGE {page_num}]\n")
                    text_parts.append(page_text)

            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num}: {e}")
                text_parts.append(f"\n[PAGE {page_num} - EXTRACTION FAILED]\n")

        return "".join(text_parts)

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Fix common PDF extraction issues
        text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)  # Add space between camelCase

        # Remove control characters but keep newlines
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)

        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")

        # Fix hyphenation at line breaks
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)

        # Normalize page markers
        text = re.sub(r'\[PAGE\s+(\d+)\]', r'\n\n[PAGE \1]\n', text)

        return text.strip()

    def _calculate_text_stats(self, text: str) -> Dict:
        """Calculate text statistics."""
        # Remove page markers for stats
        clean_text = re.sub(r'\[PAGE \d+\]', '', text)

        # Calculate stats
        stats = {
            'char_count': len(clean_text),
            'word_count': len(clean_text.split()),
            'line_count': clean_text.count('\n'),
        }

        # Detect special content
        stats['has_equations'] = bool(
            re.search(r'[∑∫∂∇√π±×÷≈≠≤≥]', text) or
            re.search(r'\\[A-Za-z]+\{', text)  # LaTeX commands
        )

        stats['has_code'] = bool(
            re.search(r'def\s+\w+\s*\(|class\s+\w+|import\s+\w+|function\s+\w+', text)
        )

        stats['has_tables'] = bool(
            re.search(r'\|\s*\w+\s*\|', text)  # Markdown tables
        )

        return stats

    def calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA256 hash of file for deduplication.

        Args:
            file_path: Path to file

        Returns:
            SHA256 hash string
        """
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()

    def validate_pdf(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if a file is a valid PDF.

        Args:
            file_path: Path to file

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with open(file_path, 'rb') as file:
                reader = PdfReader(file)
                # Try to access first page to ensure it's readable
                if len(reader.pages) > 0:
                    _ = reader.pages[0]
                return True, None

        except PyPDF2.errors.PdfReadError as e:
            return False, f"Invalid PDF file: {e}"
        except Exception as e:
            return False, f"Error validating PDF: {e}"

    def extract_page_text(
        self,
        file_path: str,
        page_number: int
    ) -> Optional[str]:
        """
        Extract text from a specific page.

        Args:
            file_path: Path to PDF
            page_number: Page number (1-indexed)

        Returns:
            Text from page or None if failed
        """
        try:
            with open(file_path, 'rb') as file:
                reader = PdfReader(file)

                if page_number < 1 or page_number > len(reader.pages):
                    return None

                page = reader.pages[page_number - 1]
                return page.extract_text()

        except Exception as e:
            logger.error(f"Failed to extract page {page_number}: {e}")
            return None


class TextProcessor:
    """Process text documents (txt, md) for extraction."""

    def __init__(self):
        """Initialize text processor."""
        self.supported_extensions = ['.txt', '.md', '.markdown']

    def process_text_file(self, file_path: str) -> Tuple[str, Dict]:
        """
        Process a text file.

        Args:
            file_path: Path to text file

        Returns:
            Tuple of (text_content, metadata)
        """
        path = Path(file_path)

        if not path.exists():
            raise ValueError(f"File not found: {file_path}")

        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract metadata
        metadata = {
            'filename': path.name,
            'file_size': path.stat().st_size,
            'char_count': len(content),
            'word_count': len(content.split()),
            'line_count': content.count('\n'),
        }

        # For Markdown, try to extract title
        if path.suffix.lower() in ['.md', '.markdown']:
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if title_match:
                metadata['title'] = title_match.group(1).strip()

        return content, metadata


class DocumentProcessorFactory:
    """Factory for creating appropriate document processors."""

    def __init__(self):
        """Initialize processor factory."""
        self.pdf_processor = PDFProcessor()
        self.text_processor = TextProcessor()

    def get_processor(self, file_path: str):
        """
        Get appropriate processor for file type.

        Args:
            file_path: Path to file

        Returns:
            Appropriate processor instance

        Raises:
            ValueError: If file type not supported
        """
        path = Path(file_path)
        extension = path.suffix.lower()

        if extension in self.pdf_processor.supported_extensions:
            return self.pdf_processor
        elif extension in self.text_processor.supported_extensions:
            return self.text_processor
        else:
            raise ValueError(
                f"Unsupported file type: {extension}. "
                f"Supported: .pdf, .txt, .md"
            )

    def process_document(self, file_path: str) -> Tuple[str, Dict]:
        """
        Process any supported document type.

        Args:
            file_path: Path to document

        Returns:
            Tuple of (text_content, metadata)
        """
        processor = self.get_processor(file_path)

        if isinstance(processor, PDFProcessor):
            return processor.process_pdf(file_path)
        elif isinstance(processor, TextProcessor):
            return processor.process_text_file(file_path)
        else:
            raise ValueError(f"Unknown processor type for {file_path}")