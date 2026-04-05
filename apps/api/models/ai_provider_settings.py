import base64
import logging
from datetime import datetime, timezone
from typing import Optional

from cryptography.fernet import Fernet
from sqlmodel import Field, Session, select

from models.base import TenantModel
from config.settings import settings

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode().ljust(32)[:32])
    return Fernet(key)


class AIProviderSettings(TenantModel, table=True):
    __tablename__ = "ai_provider_settings"

    provider: str = Field(default="openai", max_length=50)
    encrypted_api_key: Optional[str] = Field(default=None, max_length=500)
    embedding_model: str = Field(default="text-embedding-3-small", max_length=100)
    embedding_dimensions: int = Field(default=1536)
    llm_model: str = Field(default="gpt-4o-mini", max_length=100)
    connection_status: str = Field(default="untested", max_length=20)
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def set_api_key(self, api_key: str) -> None:
        f = _get_fernet()
        self.encrypted_api_key = f.encrypt(api_key.encode()).decode()

    def get_api_key(self) -> Optional[str]:
        if not self.encrypted_api_key:
            return None
        f = _get_fernet()
        return f.decrypt(self.encrypted_api_key.encode()).decode()

    @staticmethod
    def get_for_org(session: Session, org_id: str) -> Optional["AIProviderSettings"]:
        stmt = select(AIProviderSettings).where(
            AIProviderSettings.org_id == org_id,
            AIProviderSettings.soft_delete == False,
        )
        return session.exec(stmt).first()

    @staticmethod
    def get_or_create(session: Session, org_id: str) -> "AIProviderSettings":
        existing = AIProviderSettings.get_for_org(session, org_id)
        if existing:
            return existing
        settings_obj = AIProviderSettings(org_id=org_id)
        session.add(settings_obj)
        session.flush()
        return settings_obj
