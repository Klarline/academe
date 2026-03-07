"""Tests for arXiv MCP server tools."""

import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock

import pytest


# ─── Fixtures ─────────────────────────────────────────────────────────────────

SAMPLE_ATOM_ENTRY = """<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <entry>
    <id>http://arxiv.org/abs/2312.10997v5</id>
    <title>Retrieval-Augmented Generation for Large Language Models: A Survey</title>
    <summary>Large language models have issues with hallucination.</summary>
    <author><name>Yunfan Gao</name></author>
    <author><name>Yun Xiong</name></author>
    <published>2023-12-18T00:00:00Z</published>
    <updated>2024-03-27T00:00:00Z</updated>
    <link href="http://arxiv.org/pdf/2312.10997v5" title="pdf" />
    <category term="cs.CL" />
    <category term="cs.AI" />
    <arxiv:comment>Accepted at ACL 2024</arxiv:comment>
  </entry>
</feed>"""

EMPTY_FEED = """<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns="http://www.w3.org/2005/Atom">
</feed>"""


@pytest.fixture(autouse=True)
def mock_fetch():
    """Mock _fetch_xml to avoid real network calls."""
    with patch("mcp_servers.arxiv_server._fetch_xml") as m:
        m.return_value = ET.fromstring(SAMPLE_ATOM_ENTRY)
        yield m


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestSearchPapers:
    def test_returns_results(self, mock_fetch):
        from mcp_servers.arxiv_server import search_papers
        results = search_papers("RAG survey", max_results=1)
        assert len(results) == 1
        assert results[0]["arxiv_id"] == "2312.10997v5"
        assert "Retrieval" in results[0]["title"]

    def test_parses_authors(self, mock_fetch):
        from mcp_servers.arxiv_server import search_papers
        results = search_papers("RAG")
        assert "Yunfan Gao" in results[0]["authors"]

    def test_parses_categories(self, mock_fetch):
        from mcp_servers.arxiv_server import search_papers
        results = search_papers("RAG")
        assert "cs.CL" in results[0]["categories"]
        assert "cs.AI" in results[0]["categories"]

    def test_parses_urls(self, mock_fetch):
        from mcp_servers.arxiv_server import search_papers
        results = search_papers("RAG")
        assert results[0]["pdf_url"] == "http://arxiv.org/pdf/2312.10997v5"
        assert results[0]["arxiv_url"] == "https://arxiv.org/abs/2312.10997v5"

    def test_clamps_max_results(self, mock_fetch):
        from mcp_servers.arxiv_server import search_papers
        search_papers("RAG", max_results=50)
        call_url = mock_fetch.call_args[0][0]
        assert "max_results=20" in call_url

    def test_empty_results(self, mock_fetch):
        mock_fetch.return_value = ET.fromstring(EMPTY_FEED)
        from mcp_servers.arxiv_server import search_papers
        results = search_papers("nonexistent_xyz_123")
        assert len(results) == 1
        assert "No papers found" in results[0].get("message", "")

    def test_network_error(self, mock_fetch):
        mock_fetch.side_effect = Exception("Connection refused")
        from mcp_servers.arxiv_server import search_papers
        results = search_papers("RAG")
        assert "error" in results[0]


class TestGetPaperDetails:
    def test_returns_paper(self, mock_fetch):
        from mcp_servers.arxiv_server import get_paper_details
        result = get_paper_details("2312.10997")
        assert "Retrieval" in result["title"]
        assert result["published"] == "2023-12-18"

    def test_strips_prefix(self, mock_fetch):
        from mcp_servers.arxiv_server import get_paper_details
        get_paper_details("arXiv:2312.10997")
        call_url = mock_fetch.call_args[0][0]
        assert "2312.10997" in call_url
        assert "arXiv" not in call_url

    def test_not_found(self, mock_fetch):
        mock_fetch.return_value = ET.fromstring(EMPTY_FEED)
        from mcp_servers.arxiv_server import get_paper_details
        result = get_paper_details("0000.00000")
        assert "error" in result


class TestSearchByAuthor:
    def test_returns_results(self, mock_fetch):
        from mcp_servers.arxiv_server import search_by_author
        results = search_by_author("Gao")
        assert len(results) == 1
        assert results[0]["arxiv_id"] == "2312.10997v5"

    def test_builds_author_query(self, mock_fetch):
        from mcp_servers.arxiv_server import search_by_author
        search_by_author("Hinton", max_results=3)
        call_url = mock_fetch.call_args[0][0]
        assert "au" in call_url and "Hinton" in call_url
        assert "max_results=3" in call_url
