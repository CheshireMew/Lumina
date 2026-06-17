from __future__ import annotations

from pydantic import BaseModel, Field


class RuntimeLlmSettings(BaseModel):
    providerId: str = "custom_provider"
    apiKey: str = ""
    baseUrl: str = ""
    model: str
    temperature: float = 0.7
    topP: float = 1.0
    presencePenalty: float = 0.0
    frequencyPenalty: float = 0.0
    historyLimit: int = Field(default=20, ge=0, le=50)
    overflowStrategy: str = Field(default="slide", pattern="^(slide|reset)$")
