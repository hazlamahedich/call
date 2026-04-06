"""Script generation request/response schemas.

Uses AliasGenerator(to_camel) exclusively for camelCase JSON mapping.
"""

from typing import List, Literal, Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ScriptGenerateRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=AliasGenerator(to_camel),
    )

    query: str = Field(..., min_length=1, max_length=2000)
    agent_id: Optional[int] = None
    override_grounding_mode: Optional[Literal["strict", "balanced", "creative"]] = None
    override_max_chunks: Optional[int] = Field(None, ge=1, le=20)


class SourceChunkInfo(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=AliasGenerator(to_camel),
    )

    chunk_id: int
    knowledge_base_id: int
    similarity: float


class ScriptGenerateResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=AliasGenerator(to_camel),
    )

    response: str
    grounding_confidence: float = Field(ge=0.0, le=1.0)
    is_low_confidence: bool
    source_chunks: List[SourceChunkInfo]
    model: str
    latency_ms: float
    grounding_mode: str
    was_truncated: bool = False
    cached: bool = False
    config_version: Optional[int] = None


class ScriptConfigRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=AliasGenerator(to_camel),
    )

    agent_id: int
    expected_version: int
    grounding_mode: Literal["strict", "balanced", "creative"] = "strict"
    max_source_chunks: int = Field(default=5, ge=1, le=20)
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    system_prompt_template: Optional[str] = None


class ScriptConfigResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=AliasGenerator(to_camel),
    )

    agent_id: int
    grounding_mode: str
    max_source_chunks: int
    min_confidence: float
    system_prompt_template: Optional[str] = None
    config_version: int
