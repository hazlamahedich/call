"""Content ingestion service for multi-format document processing.

Extracts text from PDFs, URLs, and raw text for knowledge base ingestion.
"""

import asyncio
import hashlib
import ipaddress
import logging
import socket
from pathlib import Path
from typing import Literal, Optional, Tuple
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
import pdfplumber

logger = logging.getLogger(__name__)

SourceType = Literal["pdf", "url", "text"]

MAX_FILE_SIZE = 50 * 1024 * 1024
MIN_TEXT_LENGTH = 100
URL_FETCH_TIMEOUT = 10.0
MAX_REDIRECTS = 3

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fd00::/8"),
]


class IngestionError(Exception):
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class IngestionService:
    """Service for extracting and validating content from multiple sources."""

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=URL_FETCH_TIMEOUT,
            follow_redirects=True,
            max_redirects=MAX_REDIRECTS,
        )

    async def close(self):
        await self.client.aclose()

    async def extract_pdf(self, file_path: str) -> Tuple[str, dict]:
        path = Path(file_path)
        if not path.exists():
            raise IngestionError("File not found", "FILE_NOT_FOUND")

        file_size = path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            raise IngestionError(
                f"File too large: {file_size} bytes (max {MAX_FILE_SIZE})",
                "FILE_TOO_LARGE",
            )

        if not self._is_valid_pdf(file_path):
            raise IngestionError(
                "Invalid or unsupported PDF format",
                "INVALID_FILE_FORMAT",
            )

        if self._is_encrypted_pdf(file_path):
            raise IngestionError(
                "PDF is password-protected or encrypted",
                "PDF_ENCRYPTED",
            )

        try:
            text, metadata = await asyncio.to_thread(
                self._extract_with_pdfplumber, file_path
            )
            if not text.strip():
                raise IngestionError(
                    "PDF contains no extractable text (possibly scanned image)",
                    "PDF_NO_TEXT",
                )
            logger.info(f"Extracted {len(text)} chars from PDF using pdfplumber")
            return text, metadata
        except IngestionError:
            raise
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}, trying PyPDF2 fallback")
            try:
                text, metadata = await asyncio.to_thread(
                    self._extract_with_pypdf2, file_path
                )
                if not text.strip():
                    raise IngestionError(
                        "PDF contains no extractable text",
                        "PDF_NO_TEXT",
                    )
                logger.info(f"Extracted {len(text)} chars from PDF using PyPDF2")
                return text, metadata
            except IngestionError:
                raise
            except Exception as fallback_error:
                raise IngestionError(
                    f"Failed to extract PDF text: {str(fallback_error)}",
                    "PDF_EXTRACTION_FAILED",
                )

    @staticmethod
    def _extract_with_pdfplumber(file_path: str) -> Tuple[str, dict]:
        text_parts = []
        metadata = {"page_count": 0, "word_count": 0, "extraction_method": "pdfplumber"}
        with pdfplumber.open(file_path) as pdf:
            metadata["page_count"] = len(pdf.pages)
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        text = "\n\n".join(text_parts)
        metadata["word_count"] = len(text.split())
        return text, metadata

    @staticmethod
    def _extract_with_pypdf2(file_path: str) -> Tuple[str, dict]:
        import PyPDF2

        text_parts = []
        metadata = {"page_count": 0, "word_count": 0, "extraction_method": "PyPDF2"}
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

    @staticmethod
    def _is_valid_pdf(file_path: str) -> bool:
        try:
            with open(file_path, "rb") as f:
                header = f.read(4)
                return header == b"%PDF"
        except Exception:
            return False

    @staticmethod
    def _is_encrypted_pdf(file_path: str) -> bool:
        try:
            import PyPDF2

            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return reader.is_encrypted
        except Exception:
            return False

    async def extract_url(self, url: str) -> Tuple[str, dict]:
        if not self._is_valid_url(url):
            raise IngestionError("Invalid URL format", "INVALID_URL")

        if self._is_internal_url(url):
            raise IngestionError(
                "Internal URLs are not allowed",
                "INTERNAL_URL_BLOCKED",
            )

        try:
            response = await self.client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            for element in soup(
                ["script", "style", "nav", "footer", "header", "aside"]
            ):
                element.decompose()

            title = soup.find("title")
            title_text = title.get_text() if title else "Untitled"

            body = soup.find("body")
            if body:
                text = body.get_text(separator="\n", strip=True)
            else:
                text = soup.get_text(separator="\n", strip=True)

            text = "\n".join(line.strip() for line in text.split("\n") if line.strip())

            metadata = {
                "source_url": url,
                "title": title_text,
                "content_type": response.headers.get("content-type", "text/html"),
                "status_code": response.status_code,
            }

            logger.info(f"Extracted {len(text)} chars from URL: {url}")
            return text, metadata

        except httpx.TimeoutException:
            raise IngestionError(
                f"URL request timed out after {URL_FETCH_TIMEOUT}s",
                "URL_TIMEOUT",
            )
        except httpx.HTTPStatusError as e:
            raise IngestionError(
                f"Failed to fetch URL: HTTP {e.response.status_code}",
                "URL_HTTP_ERROR",
            )
        except Exception as e:
            raise IngestionError(f"Failed to fetch URL: {str(e)}", "URL_FETCH_ERROR")

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.hostname)

    @staticmethod
    def _is_internal_url(url: str) -> bool:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False

        try:
            ip_obj = ipaddress.ip_address(hostname)
            return any(ip_obj in net for net in BLOCKED_NETWORKS)
        except ValueError:
            pass

        try:
            addr_infos = socket.getaddrinfo(
                hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM
            )
            for addr_info in addr_infos:
                ip_str = addr_info[4][0]
                try:
                    ip_obj = ipaddress.ip_address(ip_str)
                    if any(ip_obj in net for net in BLOCKED_NETWORKS):
                        return True
                except ValueError:
                    continue
        except (socket.gaierror, socket.herror):
            pass

        return False

    async def validate_text(
        self, text: str, source_type: SourceType
    ) -> Tuple[bool, Optional[str]]:
        if len(text) < MIN_TEXT_LENGTH:
            return False, f"Text too short: {len(text)} chars (min {MIN_TEXT_LENGTH})"

        try:
            text.encode("utf-8")
        except UnicodeEncodeError:
            return False, "Text contains invalid UTF-8 characters"

        if self._is_corrupted_text(text):
            return False, "Text appears to be corrupted or scanned"

        return True, None

    @staticmethod
    def _is_corrupted_text(text: str) -> bool:
        special_chars = set("[]{}|\\<>~`@#$%^&*()")
        special_count = sum(1 for c in text if c in special_chars)
        ratio = special_count / len(text) if text else 0
        return ratio > 0.35

    def validate_file_format(self, filename: str, content_type: str) -> bool:
        allowed_extensions = {".pdf", ".txt", ".md"}
        file_ext = Path(filename).suffix.lower()
        if file_ext not in allowed_extensions:
            return False
        if file_ext == ".pdf":
            if content_type and not content_type.startswith("application/pdf"):
                return False
        return True

    @staticmethod
    def compute_content_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
