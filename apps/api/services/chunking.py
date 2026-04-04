"""Semantic chunking service for intelligent text segmentation.

Splits documents into semantic chunks with context overlap for better
RAG retrieval.
"""

import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# Configuration constants
MIN_CHUNK_SIZE = 500  # tokens
MAX_CHUNK_SIZE = 1000  # tokens
OVERLAP_RATIO = 0.10  # 10% overlap between chunks

# Approximate tokens per word (varies by language, but 1.3 is reasonable for English)
TOKENS_PER_WORD = 1.3


class SemanticChunkingService:
    """Service for intelligent text chunking with context overlap.

    Splits text into semantic chunks preserving sentence boundaries
    and maintaining context through overlap.
    """

    def __init__(self):
        pass

    async def chunk_text(self, text: str, metadata: dict) -> List[str]:
        """Split text into semantic chunks with context overlap.

        Args:
            text: Text to chunk
            metadata: Document metadata for enrichment

        Returns:
            List of chunk strings
        """
        if not text or not text.strip():
            return []

        # Split into sentences first
        sentences = self._split_into_sentences(text)

        if not sentences:
            # Fallback: split by paragraphs if sentence splitting fails
            sentences = text.split("\n\n")

        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)

            # Check if adding this sentence would exceed max chunk size
            if current_tokens + sentence_tokens > MAX_CHUNK_SIZE and current_chunk:
                # Save current chunk and start new one
                chunks.append(" ".join(current_chunk))

                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(current_chunk)
                current_chunk = overlap_sentences + [sentence]
                current_tokens = sum(self._estimate_tokens(s) for s in current_chunk)
            else:
                # Add sentence to current chunk
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        # Merge final chunk if too small
        if len(chunks) > 1:
            last_chunk = chunks[-1]
            if not self.validate_chunk(last_chunk):
                chunks[-2] = chunks[-2] + " " + last_chunk
                chunks.pop()

        logger.info(f"Split text into {len(chunks)} chunks")
        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using regex.

        Preserves common abbreviations to avoid false splits.
        """
        # Common abbreviations that should NOT end a sentence
        abbreviations = {
            "Mr",
            "Mrs",
            "Ms",
            "Dr",
            "Prof",
            "Sr",
            "Jr",
            "vs",
            "etc",
            "eg",
            "ie",
            "i.e",
            "e.g",
            "US",
            "UK",
            "USA",
            "U.S.A",
            "U.S.",
            "ft",
            "in",
            "cm",
            "mm",
            "km",
            "lb",
            "kg",
            "oz",
            "g",
            "AM",
            "PM",
            "a.m",
            "p.m",
            "A.M",
            "P.M",
        }

        # Build pattern to match sentence boundaries
        # Look for period, question mark, or exclamation point followed by space and capital letter
        pattern = r"(?<=[.!?])\s+(?=[A-Z])"

        # First, protect abbreviations by temporarily replacing them
        protected_text = text
        for abbr in abbreviations:
            # Match abbreviations with periods (e.g., "Mr.", "U.S.")
            protected_text = re.sub(rf"\b{abbr}\.", f"__ABBR_{abbr}__", protected_text)

        # Split on sentence boundaries
        sentences = re.split(pattern, protected_text)

        # Restore abbreviations
        restored_sentences = []
        for sentence in sentences:
            for abbr in abbreviations:
                sentence = sentence.replace(f"__ABBR_{abbr}__", f"{abbr}.")
            restored_sentences.append(sentence.strip())

        # Filter out empty sentences
        return [s for s in restored_sentences if s]

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Approximates tokens by word count * TOKENS_PER_WORD.
        """
        words = text.split()
        return int(len(words) * TOKENS_PER_WORD)

    def _get_overlap_sentences(self, chunk: List[str]) -> List[str]:
        """Get overlap sentences from previous chunk.

        Returns approximately OVERLAP_RATIO (10%) of the previous chunk.
        """
        if not chunk:
            return []

        # Calculate how many sentences to include for overlap
        overlap_count = max(1, int(len(chunk) * OVERLAP_RATIO))

        # Return the last N sentences from the chunk
        return chunk[-overlap_count:]

    def enrich_chunk_metadata(self, chunk: str, index: int, metadata: dict) -> dict:
        """Add metadata to each chunk.

        Args:
            chunk: Chunk text content
            index: Chunk index within document
            metadata: Document metadata

        Returns:
            Enriched metadata dictionary
        """
        chunk_metadata = {
            "chunk_index": index,
            "chunk_token_count": self._estimate_tokens(chunk),
            "chunk_char_count": len(chunk),
        }

        if metadata:
            if "page_count" in metadata:
                chunk_metadata["page_count"] = metadata["page_count"]
            if "source_url" in metadata:
                chunk_metadata["source_url"] = metadata["source_url"]
            if "title" in metadata:
                chunk_metadata["document_title"] = metadata["title"]
            if "extraction_method" in metadata:
                chunk_metadata["extraction_method"] = metadata["extraction_method"]
            if "source" in metadata:
                chunk_metadata["source"] = metadata["source"]
            if "page" in metadata:
                chunk_metadata["page"] = metadata["page"]
            if "embedding_model" in metadata:
                chunk_metadata["embedding_model"] = metadata["embedding_model"]

        return chunk_metadata

    def validate_chunk(self, chunk: str) -> bool:
        """Validate chunk meets minimum requirements.

        Args:
            chunk: Chunk text to validate

        Returns:
            True if chunk is valid, False otherwise
        """
        # Check minimum size
        if self._estimate_tokens(chunk) < MIN_CHUNK_SIZE:
            return False

        # Check for obviously invalid content
        if not chunk or not chunk.strip():
            return False

        return True
