"""HTTP client for the Câmara dos Deputados Dados Abertos API.

Async client with retry, rate limiting, and structured response parsing.
Base URL: https://dadosabertos.camara.leg.br/api/v2
"""

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.exceptions import ExternalAPIException
from app.logging import get_logger
from app.integrations.camara_types import (
    AutorAPI,
    CamaraAPIResponse,
    DeputadoDetalhadoAPI,
    DeputadoResumoAPI,
    DespesaAPI,
    EventoResumoAPI,
    ItemPautaAPI,
    OrientacaoAPI,
    PartidoDetalhadoAPI,
    PartidoResumoAPI,
    ProposicaoDetalhadaAPI,
    ProposicaoResumoAPI,
    ReferenciaAPI,
    TemaAPI,
    TramitacaoAPI,
    VotacaoDetalhadaAPI,
    VotacaoResumoAPI,
    VotoParlamentarAPI,
)

logger = get_logger(__name__)

# Retryable HTTP errors
RETRYABLE_STATUS_CODES = {500, 502, 503, 504, 429}


class CamaraClient:
    """Async HTTP client for the Câmara dos Deputados Open Data API.

    Features:
        - Automatic retry with exponential backoff for transient errors.
        - Structured response parsing with Pydantic models.
        - Transparent pagination support.

    Usage:
        async with CamaraClient() as client:
            proposicoes = await client.listar_proposicoes(ano=2024)
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = (base_url or settings.camara_api_base_url).rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "CamaraClient":
        """Create the HTTP client on context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers={"Accept": "application/json"},
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Close the HTTP client on context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Return the underlying httpx client, raising if not initialized."""
        if self._client is None:
            raise RuntimeError(
                "CamaraClient not initialized. Use 'async with CamaraClient() as client:'"
            )
        return self._client

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(ExternalAPIException),
        reraise=True,
    )
    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GET request with retry logic.

        Args:
            path: API path relative to base URL (e.g., '/proposicoes').
            params: Query parameters.

        Returns:
            Parsed JSON response as dict.

        Raises:
            ExternalAPIException: On non-retryable HTTP errors or after retries exhausted.
        """
        try:
            response = await self.client.get(path, params=params)
        except httpx.HTTPError as e:
            logger.error("camara_api.http_error", path=path, error=str(e))
            raise ExternalAPIException(detail=f"Erro de conexão com API da Câmara: {e}") from e

        if response.status_code in RETRYABLE_STATUS_CODES:
            logger.warning(
                "camara_api.retryable_error",
                path=path,
                status=response.status_code,
            )
            raise ExternalAPIException(
                detail=f"API da Câmara retornou status {response.status_code}"
            )

        if response.status_code != 200:
            logger.error(
                "camara_api.unexpected_status",
                path=path,
                status=response.status_code,
            )
            raise ExternalAPIException(
                detail=f"API da Câmara retornou status inesperado: {response.status_code}"
            )

        return response.json()

    async def _get_dados(
        self, path: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """GET request returning the 'dados' key from paginated response.

        Args:
            path: API path.
            params: Query parameters.

        Returns:
            List of data items from the 'dados' key.
        """
        data = await self._get(path, params)
        return data.get("dados", [])

    async def _get_dados_single(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """GET request returning the 'dados' key for a single resource.

        Args:
            path: API path.
            params: Query parameters.

        Returns:
            Single data dict from the 'dados' key.

        Raises:
            ExternalAPIException: If 'dados' key is missing.
        """
        data = await self._get(path, params)
        dados = data.get("dados")
        if dados is None:
            raise ExternalAPIException(detail=f"Resposta inesperada da API para {path}")
        return dados

    @staticmethod
    def _clean_params(params: dict[str, Any]) -> dict[str, Any]:
        """Remove None values from params dict."""
        return {k: v for k, v in params.items() if v is not None}

    # ------------------------------------------------------------------
    # Proposições
    # ------------------------------------------------------------------

    async def listar_proposicoes(
        self,
        sigla_tipo: str | None = None,
        numero: int | None = None,
        ano: int | None = None,
        cod_tema: int | None = None,
        keywords: str | None = None,
        pagina: int = 1,
        itens: int = 15,
        ordenar_por: str = "id",
        ordem: str = "DESC",
    ) -> list[ProposicaoResumoAPI]:
        """List propositions with optional filters.

        Args:
            sigla_tipo: Type abbreviation (PL, PEC, MPV, etc.).
            numero: Proposition number.
            ano: Year of presentation.
            cod_tema: Theme code from /referencias/proposicoes/codTema.
            keywords: Free-text search on the proposition ementa/description.
            pagina: Page number (1-indexed).
            itens: Items per page (max 100).
            ordenar_por: Sort field.
            ordem: Sort order (ASC/DESC).

        Returns:
            List of proposition summaries.
        """
        params = self._clean_params({
            "siglaTipo": sigla_tipo,
            "numero": numero,
            "ano": ano,
            "codTema": cod_tema,
            "keywords": keywords,
            "pagina": pagina,
            "itens": itens,
            "ordenarPor": ordenar_por,
            "ordem": ordem,
        })
        dados = await self._get_dados("/proposicoes", params)
        return [ProposicaoResumoAPI(**item) for item in dados]

    async def obter_proposicao(self, proposicao_id: int) -> ProposicaoDetalhadaAPI:
        """Get detailed information about a single proposition.

        Args:
            proposicao_id: Proposition ID from the Câmara API.

        Returns:
            Detailed proposition data.
        """
        dados = await self._get_dados_single(f"/proposicoes/{proposicao_id}")
        return ProposicaoDetalhadaAPI(**dados)

    async def obter_autores(self, proposicao_id: int) -> list[AutorAPI]:
        """Get the authors of a proposition.

        Args:
            proposicao_id: Proposition ID.

        Returns:
            List of authors.
        """
        dados = await self._get_dados(f"/proposicoes/{proposicao_id}/autores")
        return [AutorAPI(**item) for item in dados]

    async def obter_temas(self, proposicao_id: int) -> list[TemaAPI]:
        """Get the themes of a proposition.

        Args:
            proposicao_id: Proposition ID.

        Returns:
            List of themes.
        """
        dados = await self._get_dados(f"/proposicoes/{proposicao_id}/temas")
        return [TemaAPI(**item) for item in dados]

    async def obter_tramitacoes(self, proposicao_id: int) -> list[TramitacaoAPI]:
        """Get the tramitation history of a proposition.

        Args:
            proposicao_id: Proposition ID.

        Returns:
            List of tramitation events.
        """
        dados = await self._get_dados(f"/proposicoes/{proposicao_id}/tramitacoes")
        return [TramitacaoAPI(**item) for item in dados]

    # ------------------------------------------------------------------
    # Votações
    # ------------------------------------------------------------------

    async def listar_votacoes(
        self,
        pagina: int = 1,
        itens: int = 15,
        ordem: str = "DESC",
        ordenar_por: str = "dataHoraRegistro",
    ) -> list[VotacaoResumoAPI]:
        """List recent parliamentary votes.

        Args:
            pagina: Page number.
            itens: Items per page (max 100).
            ordem: Sort order.
            ordenar_por: Sort field.

        Returns:
            List of vote session summaries.
        """
        params = self._clean_params({
            "pagina": pagina,
            "itens": itens,
            "ordem": ordem,
            "ordenarPor": ordenar_por,
        })
        dados = await self._get_dados("/votacoes", params)
        return [VotacaoResumoAPI(**item) for item in dados]

    async def obter_votacao(self, votacao_id: str) -> VotacaoDetalhadaAPI:
        """Get detailed information about a single vote session.

        Args:
            votacao_id: Vote session ID.

        Returns:
            Detailed vote data.
        """
        dados = await self._get_dados_single(f"/votacoes/{votacao_id}")
        return VotacaoDetalhadaAPI(**dados)

    async def obter_orientacoes(self, votacao_id: str) -> list[OrientacaoAPI]:
        """Get party/bloc orientations for a vote session.

        Args:
            votacao_id: Vote session ID.

        Returns:
            List of party orientations.
        """
        dados = await self._get_dados(f"/votacoes/{votacao_id}/orientacoes")
        return [OrientacaoAPI(**item) for item in dados]

    async def obter_votos(self, votacao_id: str) -> list[VotoParlamentarAPI]:
        """Get individual parliamentary votes for a vote session.

        Args:
            votacao_id: Vote session ID.

        Returns:
            List of individual votes.
        """
        dados = await self._get_dados(f"/votacoes/{votacao_id}/votos")
        return [VotoParlamentarAPI(**item) for item in dados]

    # ------------------------------------------------------------------
    # Deputados
    # ------------------------------------------------------------------

    async def listar_deputados(
        self,
        sigla_uf: str | None = None,
        sigla_partido: str | None = None,
        nome: str | None = None,
        pagina: int = 1,
        itens: int = 15,
    ) -> list[DeputadoResumoAPI]:
        """List active deputies with optional filters.

        Args:
            sigla_uf: State abbreviation filter.
            sigla_partido: Party abbreviation filter.
            nome: Name filter.
            pagina: Page number.
            itens: Items per page.

        Returns:
            List of deputy summaries.
        """
        params = self._clean_params({
            "siglaUf": sigla_uf,
            "siglaPartido": sigla_partido,
            "nome": nome,
            "pagina": pagina,
            "itens": itens,
        })
        dados = await self._get_dados("/deputados", params)
        return [DeputadoResumoAPI(**item) for item in dados]

    async def obter_deputado(self, deputado_id: int) -> DeputadoDetalhadoAPI:
        """Get detailed information about a deputy.

        Args:
            deputado_id: Deputy ID.

        Returns:
            Detailed deputy data.
        """
        dados = await self._get_dados_single(f"/deputados/{deputado_id}")
        return DeputadoDetalhadoAPI(**dados)

    async def obter_despesas(
        self,
        deputado_id: int,
        ano: int | None = None,
        mes: int | None = None,
        pagina: int = 1,
        itens: int = 15,
    ) -> list[DespesaAPI]:
        """Get deputy expense records.

        Args:
            deputado_id: Deputy ID.
            ano: Year filter.
            mes: Month filter.
            pagina: Page number.
            itens: Items per page.

        Returns:
            List of expense records.
        """
        params = self._clean_params({
            "ano": ano,
            "mes": mes,
            "pagina": pagina,
            "itens": itens,
        })
        dados = await self._get_dados(f"/deputados/{deputado_id}/despesas", params)
        return [DespesaAPI(**item) for item in dados]

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------

    async def listar_eventos(
        self,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        pagina: int = 1,
        itens: int = 15,
    ) -> list[EventoResumoAPI]:
        """List plenary events.

        Args:
            data_inicio: Start date filter (YYYY-MM-DD).
            data_fim: End date filter (YYYY-MM-DD).
            pagina: Page number.
            itens: Items per page.

        Returns:
            List of event summaries.
        """
        params = self._clean_params({
            "dataInicio": data_inicio,
            "dataFim": data_fim,
            "pagina": pagina,
            "itens": itens,
        })
        dados = await self._get_dados("/eventos", params)
        return [EventoResumoAPI(**item) for item in dados]

    async def obter_pauta_evento(self, evento_id: int) -> list[ItemPautaAPI]:
        """Get the agenda items of an event.

        Args:
            evento_id: Event ID.

        Returns:
            List of agenda items.
        """
        dados = await self._get_dados(f"/eventos/{evento_id}/pauta")
        return [ItemPautaAPI(**item) for item in dados]

    # ------------------------------------------------------------------
    # Partidos
    # ------------------------------------------------------------------

    async def listar_partidos(
        self,
        pagina: int = 1,
        itens: int = 100,
        ordem: str = "ASC",
        ordenar_por: str = "sigla",
    ) -> list[PartidoResumoAPI]:
        """List political parties.

        Args:
            pagina: Page number.
            itens: Items per page (max 100).
            ordem: Sort order.
            ordenar_por: Sort field.

        Returns:
            List of party summaries.
        """
        params = self._clean_params({
            "pagina": pagina,
            "itens": itens,
            "ordem": ordem,
            "ordenarPor": ordenar_por,
        })
        dados = await self._get_dados("/partidos", params)
        return [PartidoResumoAPI(**item) for item in dados]

    async def obter_partido(self, partido_id: int) -> PartidoDetalhadoAPI:
        """Get detailed information about a political party.

        Args:
            partido_id: Party ID.

        Returns:
            Detailed party data.
        """
        dados = await self._get_dados_single(f"/partidos/{partido_id}")
        return PartidoDetalhadoAPI(**dados)

    # ------------------------------------------------------------------
    # Referências (códigos oficiais)
    # ------------------------------------------------------------------

    async def listar_temas_referencia(self) -> list[ReferenciaAPI]:
        """List official theme codes for propositions.

        Calls GET /referencias/proposicoes/codTema to retrieve the
        complete list of theme codes used by the Câmara API.

        Returns:
            List of reference items with cod, sigla, nome, descricao.
        """
        dados = await self._get_dados("/referencias/proposicoes/codTema")
        return [ReferenciaAPI(**item) for item in dados]
