"""Call performance metrics model for voice preset recommendations.

Tracks call outcomes to provide data-driven voice preset recommendations.
"""

from sqlmodel import Field, SQLModel
from datetime import datetime, timezone
from typing import Optional

from .base import TenantModel


class CallPerformance(TenantModel, table=True):
    """Call performance metrics for voice preset optimization.

    Tracks individual call outcomes to analyze which voice presets
    perform best for each use case and organization.
    """

    __tablename__ = "call_performance"  # type: ignore

    # Call details
    call_id: str = Field(max_length=100, description="Unique call identifier")
    agent_id: Optional[int] = Field(default=None, description="Agent ID used for call")
    preset_id: Optional[int] = Field(default=None, description="Voice preset ID used")
    use_case: str = Field(
        max_length=50, description="Use case: sales, support, marketing"
    )

    # Performance metrics
    duration_seconds: float = Field(description="Call duration in seconds")
    was_answered: bool = Field(description="Whether call was answered by human")
    was_connected: bool = Field(description="Whether call connected to agent")
    has_callback: bool = Field(
        default=False, description="Whether recipient requested callback"
    )

    # Outcome metrics
    outcome: str = Field(
        max_length=50,
        description="Call outcome: completed, declined, voicemail, no_answer, failed",
    )
    sentiment_score: Optional[float] = Field(
        default=None,
        ge=-1.0,
        le=1.0,
        description="Sentiment analysis score (-1 to 1)",
    )

    # Timestamps
    call_started_at: datetime = Field(description="When the call started")
    call_ended_at: Optional[datetime] = Field(
        default=None, description="When the call ended"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this record was created",
    )

    # Metadata
    metadata: dict = Field(
        default_factory=dict,
        description="Additional call metadata (provider, region, etc.)",
    )
