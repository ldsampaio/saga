from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Corpo de login (senha descartada logo após a autenticação)."""

    login: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=4096)
