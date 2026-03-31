"""
Story 2.2: Real-time Audio Stream & Transcription Pipeline
Latency Benchmark Test

Simulates 100 transcript events and verifies p95 processing < 200ms.

Test ID Format: [2.2-UNIT-XXX]
"""

import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.transcription import handle_transcript_event


def _make_latency_row(counter):
    now = datetime.now(timezone.utc)
    row = MagicMock()
    row._mapping = {
        "id": counter,
        "org_id": "org_perf",
        "call_id": 99,
        "vapi_call_id": f"vci_perf_{counter}",
        "role": "lead",
        "text": f"utterance {counter}",
        "start_time": 0.0,
        "end_time": 1.0,
        "confidence": None,
        "words_json": None,
        "received_at": now,
        "vapi_event_timestamp": None,
        "created_at": now,
        "updated_at": now,
        "soft_delete": False,
    }
    return row


def _make_latency_result(counter):
    result = MagicMock()
    result.first.return_value = _make_latency_row(counter)
    return result


class TestTranscriptionLatency:
    """[2.2-UNIT-600] Latency benchmark tests"""

    @pytest.mark.asyncio
    async def test_2_2_unit_600_given_100_events_when_process_then_p95_under_200ms(
        self,
    ):
        mock_session = AsyncMock()

        with patch(
            "services.transcription._resolve_call_id",
            new_callable=AsyncMock,
            return_value=99,
        ):
            latencies = []
            for i in range(100):
                mock_session.execute.return_value = _make_latency_result(i + 1)

                start = time.perf_counter()
                await handle_transcript_event(
                    mock_session,
                    f"vci_perf_{i + 1}",
                    "org_perf",
                    {
                        "transcript": {
                            "role": "user",
                            "text": f"utterance {i + 1}",
                        },
                        "timestamp": time.time() - 0.01,
                    },
                )
                elapsed_ms = (time.perf_counter() - start) * 1000
                latencies.append(elapsed_ms)

        latencies.sort()
        p95_index = int(len(latencies) * 0.95)
        p95 = latencies[p95_index]

        assert p95 < 200, f"p95 latency {p95:.1f}ms exceeds 200ms SLA"
