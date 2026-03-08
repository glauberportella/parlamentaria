"""Pydantic DTOs for Eleitor."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field

from app.domain.eleitor import FrequenciaNotificacao, NivelVerificacao


class EleitorBase(BaseModel):
    """Shared fields for voter DTOs."""

    nome: str = Field(..., max_length=200)
    email: str = Field(..., max_length=300)
    uf: str = Field(..., min_length=2, max_length=2)


class EleitorCreate(EleitorBase):
    """DTO for creating a voter."""

    chat_id: str | None = None
    channel: str = "telegram"
    temas_interesse: list[str] | None = None
    data_nascimento: date | None = None
    cidadao_brasileiro: bool = False
    cpf: str | None = Field(None, description="CPF (only digits). Stored as SHA-256 hash.")
    titulo_eleitor: str | None = Field(None, description="Título de eleitor (12 digits). Stored as hash.")
    frequencia_notificacao: FrequenciaNotificacao = FrequenciaNotificacao.SEMANAL
    horario_preferido_notificacao: int = Field(9, ge=0, le=23, description="Preferred hour (0-23) for digest.")


class EleitorUpdate(BaseModel):
    """DTO for updating a voter."""

    nome: str | None = None
    uf: str | None = Field(None, min_length=2, max_length=2)
    chat_id: str | None = None
    channel: str | None = None
    verificado: bool | None = None
    temas_interesse: list[str] | None = None
    data_nascimento: date | None = None
    cidadao_brasileiro: bool | None = None
    cpf_hash: str | None = Field(None, description="Pre-hashed CPF (SHA-256).")
    titulo_eleitor_hash: str | None = Field(None, description="Pre-hashed título (SHA-256).")
    nivel_verificacao: NivelVerificacao | None = None
    frequencia_notificacao: FrequenciaNotificacao | None = None
    horario_preferido_notificacao: int | None = Field(None, ge=0, le=23)


class NotificationPreferencesUpdate(BaseModel):
    """DTO for updating notification preferences via agent tool."""

    frequencia_notificacao: FrequenciaNotificacao
    horario_preferido_notificacao: int = Field(9, ge=0, le=23)


class EleitorResponse(EleitorBase):
    """DTO for voter response."""

    id: uuid.UUID
    chat_id: str | None = None
    channel: str
    verificado: bool
    temas_interesse: list[str] | None = None
    data_nascimento: date | None = None
    cidadao_brasileiro: bool = False
    elegivel: bool = False
    nivel_verificacao: NivelVerificacao = NivelVerificacao.NAO_VERIFICADO
    cpf_registrado: bool = False
    titulo_registrado: bool = False
    frequencia_notificacao: FrequenciaNotificacao = FrequenciaNotificacao.SEMANAL
    horario_preferido_notificacao: int = 9
    data_cadastro: datetime

    model_config = {"from_attributes": True}

