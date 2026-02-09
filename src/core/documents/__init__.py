"""Document processing module for Academe."""

from .chunker import DocumentChunker
from .processor import DocumentProcessorFactory, PDFProcessor, TextProcessor
from .storage import ChunkRepository, DocumentRepository, DocumentStorage
from .manager import DocumentManager

__all__ = [
    "DocumentProcessorFactory",
    "PDFProcessor",
    "TextProcessor",
    "DocumentChunker",
    "DocumentStorage",
    "DocumentRepository",
    "ChunkRepository",
    "DocumentManager",
]