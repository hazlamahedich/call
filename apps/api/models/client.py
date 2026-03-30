import json
from sqlmodel import Field
from typing import Optional

from .base import TenantModel


class Client(TenantModel, table=True):
    __tablename__ = "clients"

    name: str = Field(max_length=255, description="Client display name")
    agency_id: Optional[str] = Field(
        default=None, max_length=255, description="Clerk org ID of the parent agency"
    )
    settings_json: Optional[str] = Field(
        default=None, description="JSON blob of client settings"
    )

    @property
    def settings(self) -> dict:
        if self.settings_json:
            try:
                return json.loads(self.settings_json)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @settings.setter
    def settings(self, value: dict) -> None:
        self.settings_json = json.dumps(value) if value else None
