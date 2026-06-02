"""CollectionError model (data-model §12)."""

from pydantic import BaseModel, Field


class CollectionError(BaseModel):
    session_id: str = Field(alias="sessionId")
    collector_name: str = Field(alias="collectorName", max_length=100)
    error_code: str = Field(alias="errorCode", max_length=50)
    message: str = Field(max_length=2000)
    timestamp: str
    is_partial_data: bool = Field(alias="isPartialData")

    model_config = {"populate_by_name": True}
