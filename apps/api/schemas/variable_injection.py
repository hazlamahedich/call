"""Variable injection request/response schemas.

Uses AliasGenerator(to_camel) exclusively for camelCase JSON mapping.
"""

from typing import Optional

from pydantic import (
    AliasGenerator,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
    field_validator,
)
from pydantic.alias_generators import to_camel


class ScriptRenderRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=AliasGenerator(to_camel),
    )

    script_id: int
    lead_id: int
    agent_id: Optional[int] = None
    custom_fallbacks: Optional[dict[str, str]] = None


class ResolvedVariable(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=AliasGenerator(to_camel),
    )

    name: str
    value: str
    source: str
    used_fallback: bool


class ScriptRenderResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=AliasGenerator(to_camel),
    )

    rendered_text: str
    resolved_variables: dict[str, str]
    unresolved_variables: list[str]
    was_rendered: bool


class VariablePreviewRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=AliasGenerator(to_camel),
    )

    template: str = Field(..., min_length=1, max_length=50000)
    sample_data: Optional[dict[str, str]] = None


class VariablePreviewResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=AliasGenerator(to_camel),
    )

    variables: list[str]
    variable_sources: dict[str, str]
    preview: str


class CustomFieldsUpdateRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=AliasGenerator(to_camel),
    )

    custom_fields: dict[str, str] = Field(..., min_length=1, max_length=50)

    @field_validator("custom_fields")
    @classmethod
    def validate_field_values(cls, v: dict[str, str]) -> dict[str, str]:
        for key, val in v.items():
            if len(val) > 500:
                raise ValueError(
                    f"Value for '{key}' exceeds maximum length of 500 characters"
                )
        return v
