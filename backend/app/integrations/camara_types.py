"""Type definitions for API Dados Abertos da Câmara dos Deputados responses."""

from datetime import date, datetime

from pydantic import BaseModel, Field


# --- Proposições ---


class AutorAPI(BaseModel):
    """Author of a proposition from the API."""

    nome: str
    tipo: str | None = None
    uri: str | None = None


class ProposicaoResumoAPI(BaseModel):
    """Summary proposition from listing endpoint."""

    id: int
    uri: str | None = None
    siglaTipo: str
    codTipo: int | None = None
    numero: int
    ano: int
    ementa: str


class ProposicaoDetalhadaAPI(BaseModel):
    """Detailed proposition from single endpoint."""

    id: int
    uri: str | None = None
    siglaTipo: str
    codTipo: int | None = None
    numero: int
    ano: int
    ementa: str
    dataApresentacao: str | None = None
    urlInteiroTeor: str | None = None
    statusProposicao: dict | None = None
    keywords: str | None = None


class TemaAPI(BaseModel):
    """Theme of a proposition."""

    codTema: int
    tema: str


class TramitacaoAPI(BaseModel):
    """Tramitation event of a proposition."""

    dataHora: str | None = None
    descricaoTramitacao: str | None = None
    descricaoSituacao: str | None = None
    despacho: str | None = None
    sequencia: int | None = None


# --- Votações ---


class VotacaoResumoAPI(BaseModel):
    """Summary vote from listing endpoint."""

    id: str
    uri: str | None = None
    data: str | None = None
    dataHoraRegistro: str | None = None
    siglaOrgao: str | None = None
    descricao: str = ""
    aprovacao: int | None = None


class VotacaoDetalhadaAPI(BaseModel):
    """Detailed vote from single endpoint."""

    id: str
    uri: str | None = None
    data: str | None = None
    dataHoraRegistro: str | None = None
    siglaOrgao: str | None = None
    descricao: str = ""
    aprovacao: int | None = None
    proposicaoObjeto: str | None = None


class OrientacaoAPI(BaseModel):
    """Party orientation on a vote."""

    nomeBancada: str | None = None
    siglaPartidoBlocoParlamentar: str | None = None
    orientacao: str | None = None


class VotoParlamentarAPI(BaseModel):
    """Individual parliamentary vote."""

    deputado_: dict | None = Field(None, alias="deputado_")
    tipoVoto: str | None = None
    dataRegistroVoto: str | None = None


# --- Deputados ---


class DeputadoResumoAPI(BaseModel):
    """Summary deputy from listing endpoint."""

    id: int
    uri: str | None = None
    nome: str
    siglaPartido: str | None = None
    siglaUf: str | None = None
    urlFoto: str | None = None
    email: str | None = None


class DeputadoDetalhadoAPI(BaseModel):
    """Detailed deputy from single endpoint."""

    id: int
    uri: str | None = None
    nomeCivil: str | None = None
    cpf: str | None = None
    sexo: str | None = None
    dataNascimento: str | None = None
    dataFalecimento: str | None = None
    ufNascimento: str | None = None
    municipioNascimento: str | None = None
    ultimoStatus: dict | None = None


class DespesaAPI(BaseModel):
    """Deputy expense from the API."""

    ano: int | None = None
    mes: int | None = None
    tipoDespesa: str | None = None
    valorDocumento: float | None = None
    valorLiquido: float | None = None
    dataDocumento: str | None = None
    nomeFornecedor: str | None = None
    cnpjCpfFornecedor: str | None = None


# --- Eventos ---


class OrgaoEventoAPI(BaseModel):
    """Orgão (body/committee) linked to an event."""

    id: int | None = None
    sigla: str | None = None
    nome: str | None = None
    uri: str | None = None


class EventoResumoAPI(BaseModel):
    """Summary event from listing endpoint."""

    id: int
    uri: str | None = None
    dataHoraInicio: str | None = None
    dataHoraFim: str | None = None
    situacao: str | None = None
    descricaoTipo: str | None = None
    descricao: str | None = None
    orgaos: list[OrgaoEventoAPI] | None = None
    localCamara: dict | None = None


class ItemPautaAPI(BaseModel):
    """Agenda item of an event."""

    ordem: int | None = None
    topico: str | None = None
    regime: str | None = None
    proposicao_: dict | None = Field(None, alias="proposicao_")
    titulo: str | None = None
    situacao: str | None = None
    codRegime: int | None = None


# --- Partidos ---


class PartidoResumoAPI(BaseModel):
    """Summary political party from listing endpoint."""

    id: int
    sigla: str
    nome: str
    uri: str | None = None


class PartidoDetalhadoAPI(BaseModel):
    """Detailed political party from single endpoint."""

    id: int
    sigla: str
    nome: str
    uri: str | None = None
    status: dict | None = None
    numeroEleitoral: int | None = None
    urlLogo: str | None = None
    urlWebSite: str | None = None
    urlFacebook: str | None = None


# --- Deputados: endpoints complementares ---


class OrgaoDeputadoAPI(BaseModel):
    """Committee/body that a deputy participates in."""

    idOrgao: int | None = None
    siglaOrgao: str | None = None
    nomeOrgao: str | None = None
    nomePublicacao: str | None = None
    titulo: str | None = None  # cargo (Titular, Suplente, Presidente)
    codTitulo: int | None = None
    dataInicio: str | None = None
    dataFim: str | None = None


class FrenteAPI(BaseModel):
    """Parliamentary front that a deputy is part of."""

    id: int
    uri: str | None = None
    titulo: str
    idSituacao: int | None = None


class ProfissaoAPI(BaseModel):
    """Deputy profession/education."""

    titulo: str | None = None
    codTipoProfissao: int | None = None
    dataHora: str | None = None


class HistoricoAPI(BaseModel):
    """Deputy status history (party changes, leaves, etc.)."""

    id: int | None = None
    uri: str | None = None
    nome: str | None = None
    siglaPartido: str | None = None
    siglaUf: str | None = None
    idLegislatura: int | None = None
    urlFoto: str | None = None
    email: str | None = None
    data: str | None = None
    nomeEleitoral: str | None = None
    descricaoStatus: str | None = None
    situacao: str | None = None


class EventoDeputadoAPI(BaseModel):
    """Event that a deputy participated in."""

    id: int
    uri: str | None = None
    dataHoraInicio: str | None = None
    dataHoraFim: str | None = None
    descricaoTipo: str | None = None
    descricao: str | None = None
    situacao: str | None = None


# --- Referências ---


class ReferenciaAPI(BaseModel):
    """Reference item (codes for types, themes, situations)."""

    cod: str | None = None
    sigla: str | None = None
    nome: str | None = None
    descricao: str | None = None


# --- API Response Wrapper ---


class CamaraAPIResponse(BaseModel):
    """Generic wrapper for Câmara API paginated responses."""

    dados: list[dict]
    links: list[dict] = []
