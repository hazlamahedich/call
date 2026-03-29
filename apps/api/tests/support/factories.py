"""
Test data factories for centralized test data generation.

Usage:
    from tests.support.factories import LeadFactory

    lead = LeadFactory.build()
    lead = LeadFactory.build(name="Custom", email="custom@example.com")
    leads = LeadFactory.build_batch(5)
"""

import uuid
from models.lead import Lead


class LeadFactory:
    _counter = 0

    @classmethod
    def _next_counter(cls) -> int:
        cls._counter += 1
        return cls._counter

    @classmethod
    def _unique_email(cls) -> str:
        return f"lead-{cls._next_counter()}-{uuid.uuid4().hex[:8]}@example.com"

    @classmethod
    def build(cls, **overrides) -> Lead:
        defaults = {
            "name": f"Test Lead {cls._next_counter()}",
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
