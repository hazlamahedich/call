"""
Story 2.2: Real-time Audio Stream & Transcription Pipeline
Latency Computation & Benchmark Tests

Part 1: _compute_latency helper unit tests
Part 2: p95 benchmark (100 events, <200ms SLA)

NOTE: The benchmark mocks the database layer (session.execute), so the measured
latency reflects in-process overhead only (JSON parsing, role mapping, SQL
construction) — NOT actual I/O latency (DB writes, WebSocket broadcasts).
The 200ms SLA assertion validates that the service logic itself is lightweight;
real end-to-end latency should be benchmarked separately with a live DB.

Test ID Format: [2.2-UNIT-XXX]
"""

import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.transcription import _compute_latency, handle_transcript_event


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


class TestComputeLatency:
    """[2.2-UNIT-005..008] Latency computation tests"""

    def test_2_2_unit_005_P2_given_none_timestamp_when_compute_then_returns_none(self):
        result = _compute_latency(datetime.now(timezone.utc), None)
        assert result is None

    def test_2_2_unit_006_P2_given_valid_timestamp_when_compute_then_returns_ms(self):
        now = datetime.now(timezone.utc)
        ts = now.timestamp() - 0.1
        result = _compute_latency(now, ts)
        assert result is not None
        assert 90 <= result <= 120

    def test_2_2_unit_007_P2_given_future_timestamp_when_compute_then_returns_negative(
        self,
    ):
        now = datetime.now(timezone.utc)
        ts = now.timestamp() + 1.0
        result = _compute_latency(now, ts)
        assert result is not None
        assert result < 0

    def test_2_2_unit_008_P2_given_invalid_timestamp_when_compute_then_returns_none(
        self,
    ):
        result = _compute_latency(datetime.now(timezone.utc), float("inf"))
        assert result is None


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
