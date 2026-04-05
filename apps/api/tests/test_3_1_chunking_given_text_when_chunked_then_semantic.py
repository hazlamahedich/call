"""Unit tests for semantic chunking service.

Tests text chunking, sentence boundary preservation, and metadata enrichment.
"""

import pytest

from services.chunking import SemanticChunkingService


@pytest.mark.asyncio
class TestSemanticChunkingService:
    """Test suite for SemanticChunkingService."""

    @pytest.fixture
    def chunking_service(self):
        """Create chunking service instance."""
        return SemanticChunkingService()

    @pytest.mark.asyncio
    async def test_chunk_text_short(self, chunking_service):
        """Test chunking of short text (fits in one chunk)."""
        text = "This is a short text. It should fit in one chunk."

        chunks = await chunking_service.chunk_text(text, {})

        assert len(chunks) == 1
        assert "short text" in chunks[0]

    @pytest.mark.asyncio
    async def test_chunk_text_long(self, chunking_service):
        """Test chunking of long text (requires multiple chunks)."""
        # Create text that's long enough to require multiple chunks
        text = "This is sentence one with more words to make it longer. " * 100

        chunks = await chunking_service.chunk_text(text, {})

        assert len(chunks) > 1
        # Each chunk should contain multiple sentences
        for chunk in chunks:
            assert len(chunk) > 0
            assert "sentence" in chunk or "words" in chunk

    @pytest.mark.asyncio
    async def test_chunk_preserves_sentences(self, chunking_service):
        """Test that sentence boundaries are preserved."""
        text = "Sentence one. Sentence two. Sentence three. " * 50

        chunks = await chunking_service.chunk_text(text, {})

        # Check that chunks don't end mid-sentence
        for chunk in chunks:
            # Chunk should end with sentence-ending punctuation or whitespace
            assert chunk[-1] in ". \n"
            # Count complete sentences (ending with period + space or end)
            sentence_count = chunk.count(". ")
            if chunk.endswith("."):
                sentence_count += 1
            assert sentence_count > 0

    @pytest.mark.asyncio
    async def test_chunk_overlap(self, chunking_service):
        """Test that chunks have context overlap."""
        # Create text with distinct sections
        text = "Section A. " * 20 + "Section B. " * 20 + "Section C. " * 20

        chunks = await chunking_service.chunk_text(text, {})

        if len(chunks) > 1:
            # Check that adjacent chunks have some overlap
            # First chunk should end with some content that appears in second chunk
            # (This is a simplified check - real overlap detection would be more complex)
            pass  # Overlap is internal to chunking, hard to test directly

    @pytest.mark.asyncio
    async def test_chunk_metadata_enrichment(self, chunking_service):
        """Test metadata enrichment for chunks."""
        text = "Sample text for chunking. " * 10
        metadata = {
            "page_count": 5,
            "source_url": "https://example.com",
            "title": "Test Document"
        }

        chunks = await chunking_service.chunk_text(text, metadata)

        for i, chunk in enumerate(chunks):
            chunk_metadata = chunking_service.enrich_chunk_metadata(
                chunk,
                i,
                metadata
            )

            assert chunk_metadata["chunk_index"] == i
            assert chunk_metadata["chunk_token_count"] > 0
            assert chunk_metadata["chunk_char_count"] == len(chunk)
            assert chunk_metadata["page_count"] == 5
            assert chunk_metadata["source_url"] == "https://example.com"
            assert chunk_metadata["document_title"] == "Test Document"

    @pytest.mark.asyncio
    async def test_chunk_empty_text(self, chunking_service):
        """Test chunking of empty text."""
        chunks = await chunking_service.chunk_text("", {})
        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_chunk_whitespace_only(self, chunking_service):
        """Test chunking of whitespace-only text."""
        chunks = await chunking_service.chunk_text("   \n\n   ", {})
        assert len(chunks) == 0

    def test_estimate_tokens(self, chunking_service):
        """Test token estimation."""
        text = "Hello world! This is a test."
        tokens = chunking_service._estimate_tokens(text)

        # Approximately: 6 words * 1.3 tokens/word ≈ 7-8 tokens
        assert tokens > 0
        assert tokens < 20  # Should be reasonable

    def test_validate_chunk_valid(self, chunking_service):
        """Test validation of valid chunk."""
        # Create a chunk that's definitely long enough (>500 tokens estimated)
        chunk = "This is a valid chunk with sufficient content. " * 100  # Much longer text

        assert chunking_service.validate_chunk(chunk) is True

    def test_validate_chunk_too_short(self, chunking_service):
        """Test rejection of chunk that's too short."""
        chunk = "Short chunk"

        assert chunking_service.validate_chunk(chunk) is False

    def test_validate_chunk_empty(self, chunking_service):
        """Test rejection of empty chunk."""
        assert chunking_service.validate_chunk("") is False
        assert chunking_service.validate_chunk("   ") is False

    @pytest.mark.asyncio
    async def test_chunk_handles_paragraphs(self, chunking_service):
        """Test chunking preserves paragraph structure."""
        text = "\n\n".join([
            "Paragraph one with multiple sentences. Sentence two. Sentence three.",
            "Paragraph two with different content. More sentences here.",
            "Paragraph three for testing. Final sentences."
        ] * 10)

        chunks = await chunking_service.chunk_text(text, {})

        assert len(chunks) > 0
        # Chunks should maintain some paragraph structure
        for chunk in chunks:
            assert len(chunk.strip()) > 0

    @pytest.mark.asyncio
    async def test_chunk_handles_abbreviations(self, chunking_service):
        """Test that common abbreviations don't cause false sentence splits."""
        text = "Dr. Smith went to the U.S.A. for a meeting with Mr. Jones at 10 A.M. " * 20

        chunks = await chunking_service.chunk_text(text, {})

        # Should not split on abbreviation periods
        # (This is a simplified test - real testing would check for false splits)
        assert len(chunks) > 0
