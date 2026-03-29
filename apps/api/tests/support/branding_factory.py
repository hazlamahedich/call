"""
Story 1-5: White-labeled Admin Portal & Custom Branding
Test Data Factory
"""

from models.agency_branding import AgencyBranding


class BrandingFactory:
    _counter = 0

    @classmethod
    def _next_counter(cls) -> int:
        cls._counter += 1
        return cls._counter

    @classmethod
    def build(cls, **overrides) -> AgencyBranding:
        defaults = {
            "logo_url": None,
            "primary_color": "#10B981",
            "custom_domain": None,
            "domain_verified": False,
            "brand_name": f"Test Brand {cls._next_counter()}",
        }
        defaults.update(overrides)
        return AgencyBranding(**defaults)

    @classmethod
    def build_batch(cls, count: int, **shared_overrides) -> list[AgencyBranding]:
        return [cls.build(**shared_overrides) for _ in range(count)]
