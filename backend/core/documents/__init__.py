"""Document processing module for Academe."""

from .chunker import DocumentChunker
from .doc_type_detector import ContentType, detect_document_type
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
    "ContentType",
    "detect_document_type",
]