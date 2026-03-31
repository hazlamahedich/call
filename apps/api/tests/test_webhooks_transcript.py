"""
Story 2.2: Real-time Audio Stream & Transcription Pipeline
Integration Tests for Transcript/Speech Webhook Dispatch

Test ID Format: [2.2-UNIT-XXX]
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from middleware.vapi_auth import verify_vapi_signature
from database.session import get_session
from tests.support.factories import TranscriptWebhookFactory


async def _bypass_vapi_sig(request: Request):
    return None


def _create_test_app():
    app = FastAPI()
    from routers.webhooks_vapi import router

    app.include_router(router)
    app.dependency_overrides[verify_vapi_signature] = _bypass_vapi_sig
    mock_session = AsyncMock()

    async def _override_get_session():
        yield mock_session

    app.dependency_overrides[get_session] = _override_get_session
    return app


class TestTranscriptWebhooks:
    """[2.2-UNIT-100..106] Transcript/Speech webhook dispatch tests"""

    @pytest.fixture
    def client(self):
        return TestClient(_create_test_app())

    @pytest.fixture
    def factory(self):
        return TranscriptWebhookFactory

    def test_2_2_unit_100_P0_given_transcript_event_when_webhook_then_returns_200(
        self, client, factory
    ):
        payload = factory.transcript()

        with patch(
            "routers.webhooks_vapi.handle_transcript_event",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ):
            response = client.post(
                "/webhooks/vapi/call-events",
                json=payload,
            )

        assert response.status_code == 200
        assert response.json() == {"received": True}

    def test_2_2_unit_101_P0_given_speech_start_when_webhook_then_returns_200(
        self, client, factory
    ):
        payload = factory.speech_start()

        with patch(
            "routers.webhooks_vapi.handle_speech_start",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ):
            response = client.post(
                "/webhooks/vapi/call-events",
                json=payload,
            )

        assert response.status_code == 200

    def test_2_2_unit_102_P0_given_speech_end_when_webhook_then_returns_200(
        self, client, factory
    ):
        payload = factory.speech_end()

        with patch(
            "routers.webhooks_vapi.handle_speech_end",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ):
            response = client.post(
                "/webhooks/vapi/call-events",
                json=payload,
            )

        assert response.status_code == 200

    def test_2_2_unit_103_P0_given_transcript_handler_error_when_webhook_then_returns_200(
        self, client, factory
    ):
        payload = factory.transcript()

        with patch(
            "routers.webhooks_vapi.handle_transcript_event",
            new_callable=AsyncMock,
            side_effect=RuntimeError("DB error"),
        ):
            response = client.post(
                "/webhooks/vapi/call-events",
                json=payload,
            )

        assert response.status_code == 200

    def test_2_2_unit_104_P1_given_transcript_with_words_when_webhook_then_passes_data(
        self, client, factory
    ):
        words = [
            {"word": "hello", "start": 0.0, "end": 0.5, "confidence": 0.98},
            {"word": "there", "start": 0.6, "end": 1.0, "confidence": 0.95},
        ]
        payload = factory.transcript(words=words)

        with patch(
            "routers.webhooks_vapi.handle_transcript_event",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ) as mock_handler:
            response = client.post(
                "/webhooks/vapi/call-events",
                json=payload,
            )

        assert response.status_code == 200
        mock_handler.assert_called_once()

    def test_2_2_unit_105_P1_given_speech_start_with_ai_speaker_when_webhook_then_passes_data(
        self, client, factory
    ):
        payload = factory.speech_start(speaker="assistant")

        with patch(
            "routers.webhooks_vapi.handle_speech_start",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ) as mock_handler:
            response = client.post(
                "/webhooks/vapi/call-events",
                json=payload,
            )

        assert response.status_code == 200
        mock_handler.assert_called_once()

    def test_2_2_unit_106_P1_given_transcript_no_longer_hits_catch_all(
        self, client, factory
    ):
        payload = factory.transcript()

        with patch(
            "routers.webhooks_vapi.handle_transcript_event",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ):
            response = client.post(
                "/webhooks/vapi/call-events",
                json=payload,
            )

        assert response.status_code == 200
