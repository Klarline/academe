"""
arXiv MCP Server for Academe.

Exposes arXiv paper search as MCP tools so any MCP-compatible client
(Claude Desktop, the research agent, or external tools) can discover
and query academic papers through a standard protocol.

Usage:
    # Run as standalone MCP server (stdio transport)
    python -m mcp_servers.arxiv_server

    # Or from project root
    python backend/mcp_servers/arxiv_server.py

    # Connect from Claude Desktop — add to claude_desktop_config.json:
    # {
    #   "mcpServers": {
    #     "arxiv": {
    #       "command": "python",
    #       "args": ["/path/to/academe/backend/mcp_servers/arxiv_server.py"]
    #     }
    #   }
    # }
"""

import logging
import ssl
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
OPENSEARCH_NS = "{http://a9.com/-/spec/opensearch/1.1/}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"

REQUEST_TIMEOUT = 10  # seconds

mcp = FastMCP("academe-arxiv")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_ssl_context() -> ssl.SSLContext:
    """Build SSL context, preferring certifi certs, then system, then unverified."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    try:
        ctx = ssl.create_default_context()
        # Quick test — if system certs work, use them
        return ctx
    except Exception:
        pass
    # Last resort: unverified (common on macOS stock Python)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


_ssl_ctx = _get_ssl_context()


def _fetch_xml(url: str) -> ET.Element:
    """Fetch URL and parse as XML. Raises on network or parse failure."""
    req = urllib.request.Request(url, headers={"User-Agent": "Academe/1.0"})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=_ssl_ctx) as resp:
        return ET.fromstring(resp.read())


def _text(element: Optional[ET.Element], default: str = "") -> str:
    """Safe text extraction from an XML element."""
    if element is None:
        return default
    return (element.text or default).strip()


def _parse_entry(entry: ET.Element) -> dict:
    """Parse a single Atom entry into a structured dict."""
    # Extract arxiv ID from the id URL
    raw_id = _text(entry.find(f"{ATOM_NS}id"))
    arxiv_id = raw_id.split("/abs/")[-1] if "/abs/" in raw_id else raw_id

    # Authors
    authors = [
        _text(a.find(f"{ATOM_NS}name"))
        for a in entry.findall(f"{ATOM_NS}author")
    ]

    # Categories
    categories = [
        c.get("term", "")
        for c in entry.findall(f"{ATOM_NS}category")
        if c.get("term")
    ]

    # PDF link
    pdf_link = ""
    for link in entry.findall(f"{ATOM_NS}link"):
        if link.get("title") == "pdf":
            pdf_link = link.get("href", "")
            break

    # Comment (often contains page count, conference info)
    comment = _text(entry.find(f"{ARXIV_NS}comment"))

    return {
        "arxiv_id": arxiv_id,
        "title": " ".join(_text(entry.find(f"{ATOM_NS}title")).split()),
        "authors": authors,
        "abstract": " ".join(_text(entry.find(f"{ATOM_NS}summary")).split()),
        "categories": categories,
        "published": _text(entry.find(f"{ATOM_NS}published"))[:10],
        "updated": _text(entry.find(f"{ATOM_NS}updated"))[:10],
        "pdf_url": pdf_link,
        "arxiv_url": f"https://arxiv.org/abs/{arxiv_id}",
        "comment": comment,
    }


# ─── MCP Tools ────────────────────────────────────────────────────────────────

@mcp.tool()
def search_papers(
    query: str,
    max_results: int = 5,
    category: str | None = None,
    sort_by: str = "relevance",
) -> list[dict]:
    """
    Search arXiv for academic papers.

    Args:
        query: Search terms (e.g. "attention mechanism", "RAG retrieval").
               Searches across title, abstract, and full text.
        max_results: Number of papers to return (1-20, default 5).
        category: Optional arXiv category filter (e.g. "cs.AI", "cs.CL",
                  "cs.IR", "stat.ML"). See https://arxiv.org/category_taxonomy.
        sort_by: Sort order — "relevance" (default) or "date".

    Returns:
        List of papers with title, authors, abstract, URL, and metadata.
    """
    max_results = max(1, min(max_results, 20))

    # Build search query
    search_query = f"all:{query}"
    if category:
        search_query += f"+AND+cat:{category}"

    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "lastUpdatedDate" if sort_by == "date" else "relevance",
        "sortOrder": "descending",
    }

    url = f"{ARXIV_API_URL}?{urllib.parse.urlencode(params, safe='+')}"

    try:
        root = _fetch_xml(url)
    except Exception as e:
        logger.error(f"arXiv API request failed: {e}")
        return [{"error": f"arXiv API request failed: {e}"}]

    entries = root.findall(f"{ATOM_NS}entry")
    if not entries:
        return [{"message": f"No papers found for query: {query}"}]

    return [_parse_entry(e) for e in entries]


@mcp.tool()
def get_paper_details(arxiv_id: str) -> dict:
    """
    Get full details for a specific arXiv paper by its ID.

    Args:
        arxiv_id: The arXiv paper identifier (e.g. "2301.00234" or
                  "2301.00234v2"). Accepts with or without version suffix.

    Returns:
        Paper details including title, authors, full abstract, categories,
        dates, and links.
    """
    clean_id = arxiv_id.strip().replace("arxiv:", "").replace("arXiv:", "")
    params = {"id_list": clean_id, "max_results": 1}
    url = f"{ARXIV_API_URL}?{urllib.parse.urlencode(params)}"

    try:
        root = _fetch_xml(url)
    except Exception as e:
        logger.error(f"arXiv API request failed for {arxiv_id}: {e}")
        return {"error": f"arXiv API request failed: {e}"}

    entries = root.findall(f"{ATOM_NS}entry")
    if not entries:
        return {"error": f"Paper not found: {arxiv_id}"}

    return _parse_entry(entries[0])


@mcp.tool()
def search_by_author(
    author: str,
    max_results: int = 5,
) -> list[dict]:
    """
    Search arXiv papers by author name.

    Args:
        author: Author name (e.g. "Vaswani", "Hinton").
        max_results: Number of papers to return (1-20, default 5).

    Returns:
        List of papers by the specified author.
    """
    max_results = max(1, min(max_results, 20))
    params = {
        "search_query": f"au:{author}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "lastUpdatedDate",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_API_URL}?{urllib.parse.urlencode(params)}"

    try:
        root = _fetch_xml(url)
    except Exception as e:
        logger.error(f"arXiv author search failed: {e}")
        return [{"error": f"arXiv API request failed: {e}"}]

    entries = root.findall(f"{ATOM_NS}entry")
    if not entries:
        return [{"message": f"No papers found for author: {author}"}]

    return [_parse_entry(e) for e in entries]


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
