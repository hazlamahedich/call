from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CreateLabSessionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    agent_id: int
    script_id: int
    lead_id: Optional[int] = None


class LabSessionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    session_id: int
    agent_id: int
    script_id: int
    lead_id: Optional[int]
    status: str
    expires_at: str
    scenario_overlay: Optional[dict[str, str]]


class LabChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    message: str = Field(..., min_length=1, max_length=2000)


class SourceAttribution(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    chunk_id: int
    document_name: str
    page_number: Optional[int]
    excerpt: str
    similarity_score: float


class LabChatResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    response_text: str
    source_attributions: list[SourceAttribution]
    grounding_confidence: float
    turn_number: int
    low_confidence_warning: bool


class ScenarioOverlayRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    overlay: dict[str, str] = Field(..., min_length=1, max_length=20)


class LabSourceEntry(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    turn_number: int
    user_message: str
    ai_response: str
    sources: list[SourceAttribution]
    grounding_confidence: float


class SessionSourcesResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    session_id: int
    total_turns: int
    sources: list[LabSourceEntry]
