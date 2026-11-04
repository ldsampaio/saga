from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Corpo de login (senha descartada logo após a autenticação)."""

    login: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=4096)


class User(BaseModel):
    """Identidade canônica (schema auth.users). Nenhum campo de credencial."""

    id: str
    login: str
    name: str | None = None
    email: str | None = None
    role_base: str
    profile_complete: bool = False
    status: str = "ATIVO"
    created_at: str | None = None
    last_login_at: str | None = None


class AcademicProfile(BaseModel):
    """Campos de papel — COLUNAS de auth.user_profiles, não JSONB."""

    user_id: str
    matricula: str | None = None
    curso: str | None = None
    programa_pos: str | None = None
    departamento: str | None = None
    data_matricula: str | None = None


class ProfileRequest(BaseModel):
    """Entrada da tela de perfil. Campos de papel são colunas, não um blob."""

    name: str = Field(..., min_length=1, max_length=200)
    email: str | None = Field(None, max_length=255)
    role_base: str | None = Field(None, max_length=20)
    matricula: str | None = Field(None, max_length=60)
    curso: str | None = Field(None, max_length=120)
    programa_pos: str | None = Field(None, max_length=120)
    departamento: str | None = Field(None, max_length=120)
    data_matricula: str | None = Field(None, max_length=20)
