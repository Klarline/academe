"""
Auto-detect document content type for adaptive chunking.

Classifies documents as textbook, paper, notes, or code based on
structural signals in the extracted text.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ContentType:
    TEXTBOOK = "textbook"
    PAPER = "paper"
    NOTES = "notes"
    CODE = "code"
    GENERAL = "general"


def detect_document_type(
    text: str,
    page_count: Optional[int] = None,
    filename: Optional[str] = None,
) -> str:
    """
    Detect document content type from text and metadata.

    Heuristic signals:
    - Textbook: chapters, numbered sections, definitions, theorems, long
    - Paper: abstract, introduction, references, methodology, short-medium
    - Code: high density of code patterns
    - Notes: short, informal, bullet points
    - General: fallback

    Args:
        text: Extracted document text
        page_count: Number of pages (if known)
        filename: Original filename (for hints)

    Returns:
        One of ContentType constants
    """
    if not text or len(text.strip()) < 50:
        return ContentType.GENERAL

    text_lower = text.lower()
    word_count = len(text.split())

    scores = {
        ContentType.TEXTBOOK: 0,
        ContentType.PAPER: 0,
        ContentType.NOTES: 0,
        ContentType.CODE: 0,
    }

    # --- Textbook signals ---
    if re.search(r"chapter\s+\d", text_lower):
        scores[ContentType.TEXTBOOK] += 3
    if re.search(r"(definition|theorem|lemma|proof|corollary)\s*[\d.]", text_lower):
        scores[ContentType.TEXTBOOK] += 2
    if re.search(r"section\s+\d+\.\d+", text_lower):
        scores[ContentType.TEXTBOOK] += 2
    if re.search(r"(exercises?|problems?)\s*$", text_lower, re.MULTILINE):
        scores[ContentType.TEXTBOOK] += 1
    if page_count and page_count > 20:
        scores[ContentType.TEXTBOOK] += 2
    if word_count > 10000:
        scores[ContentType.TEXTBOOK] += 1

    # --- Paper signals ---
    if re.search(r"\babstract\b", text_lower[:2000]):
        scores[ContentType.PAPER] += 3
    if re.search(r"\bintroduction\b", text_lower[:3000]):
        scores[ContentType.PAPER] += 1
    if re.search(r"\breferences\b", text_lower[-3000:]):
        scores[ContentType.PAPER] += 2
    if re.search(r"\b(methodology|method|approach|related work)\b", text_lower):
        scores[ContentType.PAPER] += 1
    if re.search(r"\b(et al\.|proceedings|journal|conference)\b", text_lower):
        scores[ContentType.PAPER] += 1
    if page_count and 4 <= page_count <= 30:
        scores[ContentType.PAPER] += 1

    # --- Code signals ---
    code_patterns = [
        r"def\s+\w+\s*\(",
        r"class\s+\w+.*:",
        r"import\s+\w+",
        r"function\s+\w+",
        r"```",
    ]
    code_hits = sum(1 for p in code_patterns if re.search(p, text))
    if code_hits >= 3:
        scores[ContentType.CODE] += 3
    elif code_hits >= 2:
        scores[ContentType.CODE] += 1
    code_line_ratio = sum(1 for line in text.split("\n") if line.strip().startswith(("#", "//", "import ", "from ", "def ", "class "))) / max(len(text.split("\n")), 1)
    if code_line_ratio > 0.2:
        scores[ContentType.CODE] += 2

    # --- Notes signals ---
    bullet_lines = len(re.findall(r"^\s*[-*•]\s", text, re.MULTILINE))
    total_lines = max(len(text.split("\n")), 1)
    if bullet_lines / total_lines > 0.3:
        scores[ContentType.NOTES] += 2
    if word_count < 3000:
        scores[ContentType.NOTES] += 1
    if page_count and page_count <= 5:
        scores[ContentType.NOTES] += 1

    # --- Filename hints ---
    if filename:
        fn = filename.lower()
        if any(w in fn for w in ["textbook", "book", "chapter"]):
            scores[ContentType.TEXTBOOK] += 2
        if any(w in fn for w in ["paper", "arxiv", "ieee", "acm"]):
            scores[ContentType.PAPER] += 2
        if any(w in fn for w in ["notes", "summary", "cheat"]):
            scores[ContentType.NOTES] += 2

    # Pick highest score
    best = max(scores, key=scores.get)
    if scores[best] < 2:
        return ContentType.GENERAL

    logger.info(f"Detected document type: {best} (scores: {scores})")
    return best
