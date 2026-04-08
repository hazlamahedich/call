"""Story 3.5 AC3: Source Attribution Formatting.

Tests that _format_source_attribution correctly converts raw chunks
into SourceAttribution objects with proper document names, pages,
excerpts, and similarity scores.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from conftest_3_5 import *
from services.script_lab import ScriptLabService
from unittest.mock import AsyncMock


@pytest.mark.asyncio
class TestAC3SourceAttribution:
    @pytest.mark.p0
    async def test_3_5_011_given_source_attribution_when_inspecting_then_document_name_present(
        self, lab_service, sample_raw_chunks
    ):
        # [3.5-UNIT-011]
        attributions = lab_service._format_source_attribution(sample_raw_chunks)
        assert len(attributions) == 3

        assert attributions[0].document_name == "product_brochure.pdf"
        assert attributions[1].document_name == "pricing_guide.docx"
        assert attributions[2].document_name == "faq.md"

    @pytest.mark.p0
    async def test_3_5_012_given_source_attribution_with_page_number_when_inspecting_then_page_number_present(
        self, lab_service, sample_raw_chunks
    ):
        # [3.5-UNIT-012]
        attributions = lab_service._format_source_attribution(sample_raw_chunks)

        assert attributions[0].page_number == 3
        assert attributions[1].page_number == 1
        assert attributions[2].page_number is None

    @pytest.mark.p0
    async def test_3_5_013_given_source_attribution_when_inspecting_then_excerpt_is_first_200_chars(
        self, lab_service, sample_raw_chunks
    ):
        # [3.5-UNIT-013]
        long_content = "A" * 350
        long_chunk = make_raw_chunk(
            chunk_id=99,
            content=long_content,
            metadata={"source_file": "big_doc.pdf", "page_number": 1, "chunk_index": 0},
            similarity=0.80,
        )

        attributions = lab_service._format_source_attribution([long_chunk])
        assert len(attributions[0].excerpt) == 200
        assert attributions[0].excerpt == "A" * 200

        short_chunk = make_raw_chunk(content="Short text")
        short_attrs = lab_service._format_source_attribution([short_chunk])
        assert short_attrs[0].excerpt == "Short text"

    @pytest.mark.p0
    async def test_3_5_014_given_source_attribution_when_inspecting_then_similarity_score_between_0_and_1(
        self, lab_service, sample_raw_chunks
    ):
        # [3.5-UNIT-014]
        attributions = lab_service._format_source_attribution(sample_raw_chunks)

        for attr in attributions:
            assert 0.0 <= attr.similarity_score <= 1.0

        assert attributions[0].similarity_score == 0.92
        assert attributions[1].similarity_score == 0.85
        assert attributions[2].similarity_score == 0.78

    @pytest.mark.p1
    async def test_3_5_014b_given_chunk_without_metadata_when_formatted_then_defaults_applied(
        self, lab_service
    ):
        bare_chunk = make_raw_chunk(
            chunk_id=50,
            content="some content",
            metadata=None,
            similarity=0.60,
        )

        attributions = lab_service._format_source_attribution([bare_chunk])
        assert len(attributions) == 1
        assert attributions[0].document_name == "Unknown Document"
        assert attributions[0].page_number is None
        assert attributions[0].excerpt == "some content"
        assert attributions[0].similarity_score == 0.6

    @pytest.mark.p1
    async def test_3_5_014c_given_empty_chunks_list_when_formatted_then_empty_result(
        self, lab_service
    ):
        attributions = lab_service._format_source_attribution([])
        assert attributions == []
