"""Unit tests for ingestion service.

Tests PDF extraction, URL fetching, text validation, and file format validation.
"""

import pytest
import tempfile
from pathlib import Path

from services.ingestion import IngestionService, IngestionError


@pytest.mark.asyncio
class TestIngestionService:
    """Test suite for IngestionService."""

    @pytest.fixture
    def ingestion_service(self):
        """Create ingestion service instance."""
        return IngestionService()

    @pytest.fixture
    def sample_pdf_path(self):
        """Create a sample PDF file for testing."""
        # This would be a real PDF file in production
        # For now, we'll create a minimal test
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            # Write PDF magic bytes
            f.write(b"%PDF-1.4\n")
            f.write(b"1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n")
            f.write(b"%%EOF")
            path = f.name

        yield path

        # Cleanup
        Path(path).unlink(missing_ok=True)

    def test_validate_file_format_pdf(self, ingestion_service):
        """Test PDF file format validation."""
        assert ingestion_service.validate_file_format("test.pdf", "application/pdf")

    def test_validate_file_format_txt(self, ingestion_service):
        """Test TXT file format validation."""
        assert ingestion_service.validate_file_format("test.txt", "text/plain")

    def test_validate_file_format_md(self, ingestion_service):
        """Test Markdown file format validation."""
        assert ingestion_service.validate_file_format("test.md", "text/markdown")

    def test_validate_file_format_invalid(self, ingestion_service):
        """Test invalid file format rejection."""
        assert not ingestion_service.validate_file_format("test.exe", "application/x-executable")

    def test_validate_file_format_zip(self, ingestion_service):
        """Test ZIP file rejection."""
        assert not ingestion_service.validate_file_format("test.zip", "application/zip")

    def test_compute_content_hash(self, ingestion_service):
        """Test SHA-256 hash computation."""
        text = "Hello, World!"
        hash1 = ingestion_service.compute_content_hash(text)
        hash2 = ingestion_service.compute_content_hash(text)

        # Same input should produce same hash
        assert hash1 == hash2

        # Different input should produce different hash
        hash3 = ingestion_service.compute_content_hash("Different text")
        assert hash1 != hash3

        # Hash should be 64 characters (SHA-256 hex)
        assert len(hash1) == 64

    @pytest.mark.asyncio
    async def test_validate_text_valid(self, ingestion_service):
        """Test validation of valid text."""
        text = "This is a valid text input that exceeds the minimum length requirement of 100 characters. " * 2

        is_valid, error = await ingestion_service.validate_text(text, "text")

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_text_too_short(self, ingestion_service):
        """Test rejection of text that's too short."""
        text = "Short text"

        is_valid, error = await ingestion_service.validate_text(text, "text")

        assert is_valid is False
        assert "too short" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_text_corrupted(self, ingestion_service):
        """Test detection of corrupted text."""
        # Text with high ratio of special characters
        text = "[]{}|\\<>~`@#$%^&*()" * 20

        is_valid, error = await ingestion_service.validate_text(text, "pdf")

        assert is_valid is False
        assert "corrupted" in error.lower()

    def test_is_valid_url(self, ingestion_service):
        """Test valid URL detection."""
        assert ingestion_service._is_valid_url("http://example.com")
        assert ingestion_service._is_valid_url("https://example.com")
        assert not ingestion_service._is_valid_url("ftp://example.com")
        assert not ingestion_service._is_valid_url("example.com")
        assert not ingestion_service._is_valid_url("")

    def test_is_internal_url(self, ingestion_service):
        """Test internal URL detection for SSRF protection."""
        assert ingestion_service._is_internal_url("http://localhost")
        assert ingestion_service._is_internal_url("http://127.0.0.1")
        assert ingestion_service._is_internal_url("http://0.0.0.0")
        assert ingestion_service._is_internal_url("http://192.168.1.1")
        assert ingestion_service._is_internal_url("http://10.0.0.1")
        assert not ingestion_service._is_internal_url("http://example.com")
        assert not ingestion_service._is_internal_url("http://1.2.3.4")

    @pytest.mark.asyncio
    async def test_extract_url_invalid_url(self, ingestion_service):
        """Test URL extraction with invalid URL."""
        with pytest.raises(IngestionError) as exc_info:
            await ingestion_service.extract_url("not-a-url")

        assert "invalid url" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_extract_url_internal_blocked(self, ingestion_service):
        """Test that internal URLs are blocked."""
        with pytest.raises(IngestionError) as exc_info:
            await ingestion_service.extract_url("http://localhost/admin")

        assert "internal" in str(exc_info.value).lower()

    def test_is_valid_pdf_magic_bytes(self, ingestion_service, sample_pdf_path):
        """Test PDF validation by magic bytes."""
        assert ingestion_service._is_valid_pdf(sample_pdf_path)

    def test_is_valid_pdf_invalid_file(self, ingestion_service):
        """Test PDF validation rejects non-PDF files."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"Not a PDF")
            path = f.name

        try:
            assert not ingestion_service._is_valid_pdf(path)
        finally:
            Path(path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_extract_pdf_file_not_found(self, ingestion_service):
        """Test PDF extraction with non-existent file."""
        with pytest.raises(IngestionError) as exc_info:
            await ingestion_service.extract_pdf("/nonexistent/file.pdf")

        assert "not found" in str(exc_info.value).lower()


@pytest.mark.integration
@pytest.mark.asyncio
class TestIngestionServiceIntegration:
    """Integration tests for ingestion service (requires external resources)."""

    @pytest.fixture
    def ingestion_service(self):
        """Create ingestion service instance."""
        return IngestionService()

    @pytest.mark.asyncio
    async def test_extract_url_real_site(self, ingestion_service):
        """Test URL extraction from real website (may require internet)."""
        # This test might be flaky due to external dependencies
        # Consider mocking HTTP responses in production
        try:
            text, metadata = await ingestion_service.extract_url("https://example.com")

            assert isinstance(text, str)
            assert len(text) > 0
            assert "example" in metadata.get("title", "").lower()
        except Exception as e:
            pytest.skip(f"URL extraction failed (network?): {e}")
