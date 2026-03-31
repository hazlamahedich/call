"""
Test data factories for centralized test data generation.

Usage:
    from tests.support.factories import LeadFactory, CallFactory, WebhookPayloadFactory

    lead = LeadFactory.build()
    call = CallFactory.build()
    payload = WebhookPayloadFactory.call_start()
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from models.lead import Lead


class _AutoCounter:
    _counter = 0

    @classmethod
    def _next(cls) -> int:
        cls._counter += 1
        return cls._counter


class LeadFactory(_AutoCounter):
    @classmethod
    def _unique_email(cls) -> str:
        return f"lead-{cls._next()}-{uuid.uuid4().hex[:8]}@example.com"

    @classmethod
    def build(cls, **overrides) -> Lead:
        defaults = {
            "name": f"Test Lead {cls._next()}",
            "email": cls._unique_email(),
            "phone": None,
            "status": "new",
        }
        defaults.update(overrides)
        return Lead(**defaults)

    @classmethod
    def build_batch(
        cls, count: int, *, name_prefix: str = "Test Lead", **shared_overrides
    ) -> list[Lead]:
        leads = []
        for i in range(count):
            overrides = {**shared_overrides, "name": f"{name_prefix} {i}"}
            leads.append(cls.build(**overrides))
        return leads


class CallFactory(_AutoCounter):
    @classmethod
    def build(cls, **overrides) -> dict:
        cls._counter += 1
        defaults = {
            "id": cls._counter,
            "org_id": "org_test_001",
            "vapi_call_id": f"call_test_{cls._counter}",
            "lead_id": None,
            "agent_id": None,
            "campaign_id": None,
            "status": "pending",
            "duration": None,
            "recording_url": None,
            "phone_number": "+1234567890",
            "transcript": None,
            "ended_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "soft_delete": False,
        }
        defaults.update(overrides)
        return defaults

    @classmethod
    def build_pending(cls, **overrides) -> dict:
        return cls.build(status="pending", **overrides)

    @classmethod
    def build_in_progress(cls, **overrides) -> dict:
        return cls.build(status="in_progress", **overrides)

    @classmethod
    def build_completed(cls, **overrides) -> dict:
        return cls.build(
            status="completed",
            duration=120,
            recording_url="https://recordings.vapi.ai/test_recording.mp3",
            **overrides,
        )

    @classmethod
    def build_failed(cls, **overrides) -> dict:
        return cls.build(status="failed", **overrides)


class WebhookPayloadFactory(_AutoCounter):
    @classmethod
    def _base(
        cls,
        event_type: str,
        call_overrides: Optional[dict] = None,
        metadata_overrides: Optional[dict] = None,
    ) -> dict:
        cls._counter += 1
        call_data: dict = {"id": f"call_wh_{cls._counter}"}
        if call_overrides:
            call_data.update(call_overrides)

        metadata: dict = {"org_id": "org_test_001"}
        if metadata_overrides:
            metadata.update(metadata_overrides)

        return {
            "message": {
                "type": event_type,
                "call": call_data,
                "metadata": metadata,
            }
        }

    @classmethod
    def call_start(cls, **call_overrides) -> dict:
        return cls._base("call-start", call_overrides if call_overrides else None)

    @classmethod
    def call_start_with_context(
        cls, lead_id: int = 42, agent_id: int = 7, **extra
    ) -> dict:
        return cls._base(
            "call-start",
            call_overrides={"phoneNumber": "+15553334444", **extra},
            metadata_overrides={"lead_id": str(lead_id), "agent_id": str(agent_id)},
        )

    @classmethod
    def call_end(
        cls,
        duration: int = 120,
        recording_url: str = "https://recordings.vapi.ai/test.mp3",
        **call_overrides,
    ) -> dict:
        return cls._base(
            "call-end",
            call_overrides={
                "duration": duration,
                "recordingUrl": recording_url,
                **call_overrides,
            },
        )

    @classmethod
    def call_end_minimal(cls, **call_overrides) -> dict:
        return cls._base("call-end", call_overrides if call_overrides else None)

    @classmethod
    def call_failed(
        cls, error_message: str = "Carrier rejected", **call_overrides
    ) -> dict:
        return cls._base(
            "call-failed",
            call_overrides={"error": {"message": error_message}, **call_overrides},
        )

    @classmethod
    def call_failed_string_error(
        cls, error_string: str = "Simple string error"
    ) -> dict:
        return cls._base(
            "call-failed",
            call_overrides={"error": error_string},
        )

    @classmethod
    def call_failed_minimal(cls) -> dict:
        return cls._base("call-failed")

    @classmethod
    def unknown_event(cls, event_type: str = "unknown-event") -> dict:
        return cls._base(event_type)

    @classmethod
    def missing_call_id(cls) -> dict:
        return {
            "message": {
                "type": "call-start",
                "call": {},
                "metadata": {"org_id": "org_test_001"},
            }
        }

    @classmethod
    def missing_org_id(cls, vapi_call_id: Optional[str] = None) -> dict:
        call_data: dict = {}
        if vapi_call_id:
            call_data["id"] = vapi_call_id
        return {
            "message": {
                "type": "call-start",
                "call": call_data,
                "metadata": {},
            }
        }
