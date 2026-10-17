from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_id: str = Field(pattern=r"^[A-Z0-9-]{3,32}$")
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=5, max_length=2000)
    owner: str | None = Field(default=None, max_length=120)
    status: Literal["active", "inactive", "suspended"] = "active"
    tools: list[str] = Field(default_factory=list, max_length=30)
    permissions: list[str] = Field(default_factory=list, max_length=50)
    scopes: list[str] = Field(default_factory=list, max_length=50)
    data_categories: list[str] = Field(default_factory=list, max_length=30)
    sensitivity: Literal["low", "moderate", "high", "restricted"] = "low"
    approval_required: bool = False

    @field_validator("tools", "permissions", "scopes", "data_categories")
    @classmethod
    def validate_strings(cls, values):
        if any(not value.strip() or len(value) > 120 for value in values):
            raise ValueError("Entries must be non-empty and at most 120 characters")
        return values


class ReviewRequest(BaseModel):
    request: str = Field(min_length=3, max_length=1000)


class ProposalRequest(BaseModel):
    finding_id: str | None = None
    change_type: Literal["remove_permission", "restrict_scope", "restrict_data", "set_approval", "deactivate_agent"]
    proposed_change: dict[str, Any]
    rationale: str = Field(min_length=8, max_length=1500)
    evidence: list[str] = Field(default_factory=list, max_length=20)


class DecisionRequest(BaseModel):
    reviewer: str = Field(min_length=2, max_length=120)
    confirmation: bool = False
