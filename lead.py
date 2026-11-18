from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Lead(BaseModel):
    """Representa o lead ja tratado, pronto para o Pipefy."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = "Nao informado"
    email: str = ""
    phone: str = ""
    company: str = "Nao informado"
    pain_points: list[str] = Field(default_factory=list)
    source: str = "Nao informado"
    landing_page: str = ""
    tags: list[str] = Field(default_factory=list)
    commercial_summary: str = ""
    raw_payload: dict[str, Any] = Field(default_factory=dict)

