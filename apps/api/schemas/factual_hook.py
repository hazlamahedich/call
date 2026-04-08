from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ClaimVerificationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    claim_text: str
    is_supported: bool
    max_similarity: float
    verification_error: bool = False


class FactualVerificationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    was_corrected: bool
    correction_count: int
    verified_claims: list[ClaimVerificationResponse]
    verification_timed_out: bool


class FactualHookVerifyRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    response_text: str
    agent_id: int | None = None
