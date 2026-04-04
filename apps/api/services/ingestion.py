"""Content ingestion service for multi-format document processing.

Extracts text from PDFs, URLs, and raw text for knowledge base ingestion.
"""

import hashlib
import logging
from pathlib import Path
from typing import Literal, Optional, Tuple

import httpx
from bs4 import BeautifulSoup
import pdfplumber

logger = logging.getLogger(__name__)

SourceType = Literal["pdf", "url", "text"]

# Configuration constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MIN_TEXT_LENGTH = 100  # Minimum characters for valid content
URL_FETCH_TIMEOUT = 10.0  # seconds
MAX_REDIRECTS = 3


class IngestionError(Exception):
    """Base exception for ingestion errors."""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class IngestionService:
    """Service for extracting and validating content from multiple sources.

    Supports:
    - PDF extraction (pdfplumber with PyPDF2 fallback)
    - URL fetching with SSRF protection
    - Raw text validation
    """

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=URL_FETCH_TIMEOUT,
            follow_redirects=True,
            max_redirects=MAX_REDIRECTS,
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def extract_pdf(self, file_path: str) -> Tuple[str, dict]:
        """Extract text from PDF and return (text, metadata).

        Args:
            file_path: Path to PDF file

        Returns:
            Tuple of (extracted_text, metadata_dict)

        Raises:
            IngestionError: If PDF extraction fails
        """
        path = Path(file_path)

        # Validate file exists and size
        if not path.exists():
            raise IngestionError(
                f"File not found: {file_path}",
                "FILE_NOT_FOUND"
            )

        file_size = path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            raise IngestionError(
                f"File too large: {file_size} bytes (max {MAX_FILE_SIZE})",
                "FILE_TOO_LARGE"
            )

        # Validate file format by magic bytes (not extension)
        if not self._is_valid_pdf(file_path):
            raise IngestionError(
                "Invalid or unsupported PDF format",
                "INVALID_FILE_FORMAT"
            )

        try:
            # Try pdfplumber first (better text extraction)
            text, metadata = await self._extract_with_pdfplumber(file_path)
            logger.info(f"Extracted {len(text)} chars from PDF using pdfplumber")
            return text, metadata

        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}, trying PyPDF2 fallback")
            # Fallback to PyPDF2
            try:
                text, metadata = await self._extract_with_pypdf2(file_path)
                logger.info(f"Extracted {len(text)} chars from PDF using PyPDF2")
                return text, metadata
            except Exception as fallback_error:
                raise IngestionError(
                    f"Failed to extract PDF text: {str(fallback_error)}",
                    "PDF_EXTRACTION_FAILED"
                )

    async def _extract_with_pdfplumber(self, file_path: str) -> Tuple[str, dict]:
        """Extract text using pdfplumber."""
        text_parts = []
        metadata = {
            "page_count": 0,
            "word_count": 0,
            "extraction_method": "pdfplumber"
        }

        with pdfplumber.open(file_path) as pdf:
            metadata["page_count"] = len(pdf.pages)

            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        text = "\n\n".join(text_parts)
        metadata["word_count"] = len(text.split())

        return text, metadata

    async def _extract_with_pypdf2(self, file_path: str) -> Tuple[str, dict]:
        """Extract text using PyPDF2 as fallback."""
        import PyPDF2

        text_parts = []
        metadata = {
            "page_count": 0,
            "word_count": 0,
            "extraction_method": "PyPDF2"
        }

        with open(file_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            metadata["page_count"] = len(pdf_reader.pages)

            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        text = "\n\n".join(text_parts)
        metadata["word_count"] = len(text.split())

        return text, metadata

    def _is_valid_pdf(self, file_path: str) -> bool:
        """Validate PDF format by magic bytes.

        PDF magic bytes: %PDF (25 50 44 46 in hex)
        """
        try:
            with open(file_path, "rb") as f:
                header = f.read(4)
                return header == b"%PDF"
        except Exception:
            return False

    async def extract_url(self, url: str) -> Tuple[str, dict]:
        """Fetch URL and extract main content.

        Args:
            url: URL to fetch

        Returns:
            Tuple of (extracted_text, metadata_dict)

        Raises:
            IngestionError: If URL fetching or extraction fails
        """
        # Validate URL format
        if not self._is_valid_url(url):
            raise IngestionError(
                "Invalid URL format",
                "INVALID_URL"
            )

        # Check for SSRF risks (internal IPs, localhost)
        if self._is_internal_url(url):
            raise IngestionError(
                "Internal URLs are not allowed",
                "INTERNAL_URL_BLOCKED"
            )

        try:
            response = await self.client.get(url)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script, style, navigation, footer elements
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()

            # Extract main content
            title = soup.find("title")
            title_text = title.get_text() if title else "Untitled"

            # Get body text
            body = soup.find("body")
            if body:
                text = body.get_text(separator="\n", strip=True)
            else:
                text = soup.get_text(separator="\n", strip=True)

            # Clean up whitespace
            text = "\n".join(line.strip() for line in text.split("\n") if line.strip())

            metadata = {
                "source_url": url,
                "title": title_text,
                "content_type": response.headers.get("content-type", "text/html"),
                "status_code": response.status_code
            }

            logger.info(f"Extracted {len(text)} chars from URL: {url}")
            return text, metadata

        except httpx.TimeoutException:
            raise IngestionError(
                f"URL request timed out after {URL_FETCH_TIMEOUT}s",
                "URL_TIMEOUT"
            )
        except httpx.HTTPStatusError as e:
            raise IngestionError(
                f"Failed to fetch URL: HTTP {e.response.status_code}",
                "URL_HTTP_ERROR"
            )
        except Exception as e:
            raise IngestionError(
                f"Failed to fetch URL: {str(e)}",
                "URL_FETCH_ERROR"
            )

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        if not url.startswith(("http://", "https://")):
            return False
        return True

    def _is_internal_url(self, url: str) -> bool:
        """Check if URL is internal (SSRF protection)."""
        internal_patterns = [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "::1",
            "[::1]",
            "10.",
            "172.16.",
            "192.168.",
        ]

        url_lower = url.lower()
        return any(pattern in url_lower for pattern in internal_patterns)

    async def validate_text(
        self,
        text: str,
        source_type: SourceType
    ) -> Tuple[bool, Optional[str]]:
        """Validate extracted text for minimum content and encoding.

        Args:
            text: Text to validate
            source_type: Type of source (pdf, url, text)

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check minimum length
        if len(text) < MIN_TEXT_LENGTH:
            return False, f"Text too short: {len(text)} chars (min {MIN_TEXT_LENGTH})"

        # Check for valid UTF-8 encoding
        try:
            text.encode("utf-8")
        except UnicodeEncodeError:
            return False, "Text contains invalid UTF-8 characters"

        # Check for obviously corrupted content (repeated special chars)
        if self._is_corrupted_text(text):
            return False, "Text appears to be corrupted or scanned"

        return True, None

    def _is_corrupted_text(self, text: str) -> bool:
        """Check if text appears corrupted (e.g., scanned PDF without OCR)."""
        # Check for high ratio of special characters
        special_chars = set("[]{}|\\<>~`@#$%^&*()")
        special_count = sum(1 for c in text if c in special_chars)
        ratio = special_count / len(text) if text else 0

        # More than 20% special chars likely indicates corruption
        return ratio > 0.2

    def validate_file_format(self, filename: str, content_type: str) -> bool:
        """Validate file is supported format.

        Args:
            filename: Name of uploaded file
            content_type: MIME type from upload

        Returns:
            True if format is supported, False otherwise
        """
        # Allowed extensions
        allowed_extensions = {".pdf", ".txt", ".md"}

        # Check extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in allowed_extensions:
            return False

        # Additional MIME type check for PDFs
        if file_ext == ".pdf":
            if content_type and not content_type.startswith("application/pdf"):
                return False

        return True

    def compute_content_hash(self, content: str) -> str:
        """Compute SHA-256 hash of content for deduplication.

        Args:
            content: Text content to hash

        Returns:
            Hexadecimal SHA-256 hash
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
