from sqlmodel import Field

from models.base import TenantModel


class FactualVerificationLog(TenantModel, table=True):
    __tablename__ = "factual_verification_logs"

    query_hash: str
    was_corrected: bool = Field(default=False)
    correction_count: int = Field(default=0)
    claims_total: int = Field(default=0)
    claims_supported: int = Field(default=0)
    claims_unsupported: int = Field(default=0)
    claims_errored: int = Field(default=0)
    verification_timed_out: bool = Field(default=False)
    total_verification_ms: float = Field(default=0.0)
