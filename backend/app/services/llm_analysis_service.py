"""Service for generating AI analyses of legislative propositions via LLM.

Uses the Google Generative AI (google-genai) SDK to call Gemini and
produce structured analysis of propositions: summary, impact, affected
areas, arguments for/against — all in accessible language.
"""

from __future__ import annotations

import json
from typing import Any

from google import genai
from google.genai import types as genai_types

from app.config import settings
from app.logging import get_logger

logger = get_logger(__name__)

# System instruction for the LLM analysis
_SYSTEM_INSTRUCTION = """\
Você é um analista legislativo especializado em traduzir proposições legislativas \
brasileiras para linguagem acessível ao cidadão comum.

Sua tarefa é analisar uma proposição legislativa e produzir uma análise estruturada \
com os seguintes campos:

1. **resumo_leigo**: Resumo da proposição em linguagem simples, que qualquer \
   brasileiro possa entender. Máximo 3 parágrafos.
2. **impacto_esperado**: Análise do impacto esperado da proposição na vida dos \
   cidadãos. Máximo 2 parágrafos.
3. **areas_afetadas**: Lista de áreas afetadas pela proposição (ex: "saúde", \
   "educação", "economia", "segurança", "meio ambiente", "trabalho", "transporte", \
   "tecnologia", "direitos humanos", "cultura"). Máximo 5 áreas.
4. **argumentos_favor**: Lista de 3 a 5 argumentos a favor da proposição.
5. **argumentos_contra**: Lista de 3 a 5 argumentos contra a proposição.

REGRAS IMPORTANTES:
- Seja apartidário e imparcial. Nunca emita opinião pessoal.
- Use linguagem clara e acessível, evitando jargão jurídico.
- Apresente argumentos equilibrados (mesma qualidade nos prós e contras).
- Baseie-se apenas nas informações fornecidas sobre a proposição.
- Responda SOMENTE com o JSON estruturado, sem markdown ou texto adicional.

Formato de resposta (JSON puro, sem blocos de código):
{
  "resumo_leigo": "texto...",
  "impacto_esperado": "texto...",
  "areas_afetadas": ["área1", "área2"],
  "argumentos_favor": ["argumento 1", "argumento 2", "argumento 3"],
  "argumentos_contra": ["argumento 1", "argumento 2", "argumento 3"]
}
"""


class LLMAnalysisService:
    """Generates AI analyses of legislative propositions using Gemini.

    This service calls the LLM to produce structured, citizen-accessible
    analyses of propositions. It does NOT persist the result — that is
    the responsibility of the caller (AnaliseIAService).
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._model = model or settings.agent_model
        self._client = genai.Client(
            api_key=api_key or settings.google_api_key,
        )

    def _build_prompt(self, proposicao_data: dict[str, Any]) -> str:
        """Build the user prompt with proposition details.

        Args:
            proposicao_data: Dict with proposition fields (tipo, numero,
                ano, ementa, situacao, temas, autores, etc.).

        Returns:
            Formatted prompt string.
        """
        tipo = proposicao_data.get("tipo", "")
        numero = proposicao_data.get("numero", "")
        ano = proposicao_data.get("ano", "")
        ementa = proposicao_data.get("ementa", "")
        situacao = proposicao_data.get("situacao", "")
        temas = proposicao_data.get("temas") or []
        autores = proposicao_data.get("autores") or {}

        temas_str = ", ".join(temas) if temas else "Não informado"

        # Handle autores — can be a list of dicts or a plain dict
        if isinstance(autores, list):
            autores_str = ", ".join(
                a.get("nome", str(a)) for a in autores
            )
        elif isinstance(autores, dict):
            autores_str = autores.get("nome", str(autores))
        else:
            autores_str = str(autores) if autores else "Não informado"

        prompt = f"""Analise a seguinte proposição legislativa:

**Tipo**: {tipo} {numero}/{ano}
**Ementa**: {ementa}
**Situação**: {situacao}
**Temas**: {temas_str}
**Autores**: {autores_str or 'Não informado'}

Gere a análise estruturada em JSON conforme instruído."""

        return prompt

    async def analyze_proposition(
        self,
        proposicao_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate an AI analysis for a proposition.

        Calls the LLM and parses the structured JSON response.

        Args:
            proposicao_data: Dict with proposition fields from the database
                (id, tipo, numero, ano, ementa, situacao, temas, autores).

        Returns:
            Dict with keys: resumo_leigo, impacto_esperado, areas_afetadas,
            argumentos_favor, argumentos_contra.

        Raises:
            LLMAnalysisError: If the LLM call fails or response is invalid.
        """
        prop_id = proposicao_data.get("id", "unknown")
        prompt = self._build_prompt(proposicao_data)

        logger.info(
            "llm_analysis.start",
            proposicao_id=prop_id,
            model=self._model,
        )

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=_SYSTEM_INSTRUCTION,
                    temperature=0.3,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                ),
            )
        except Exception as e:
            logger.error(
                "llm_analysis.api_error",
                proposicao_id=prop_id,
                model=self._model,
                error=str(e),
            )
            raise LLMAnalysisError(
                f"Falha ao chamar LLM para proposição {prop_id}: {e}"
            ) from e

        # Extract text from response
        raw_text = response.text
        if not raw_text:
            raise LLMAnalysisError(
                f"LLM retornou resposta vazia para proposição {prop_id}"
            )

        # Parse JSON response
        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError as e:
            # Try to extract JSON from markdown code blocks
            cleaned = raw_text.strip()
            if cleaned.startswith("```"):
                # Remove ```json and ``` markers
                lines = cleaned.split("\n")
                json_lines = [
                    ln for ln in lines
                    if not ln.strip().startswith("```")
                ]
                cleaned = "\n".join(json_lines)
                try:
                    result = json.loads(cleaned)
                except json.JSONDecodeError:
                    raise LLMAnalysisError(
                        f"Resposta do LLM não é JSON válido para proposição {prop_id}: {raw_text[:500]}"
                    ) from e
            else:
                raise LLMAnalysisError(
                    f"Resposta do LLM não é JSON válido para proposição {prop_id}: {raw_text[:500]}"
                ) from e

        # Validate required fields
        analysis = self._validate_and_normalize(result, prop_id)

        logger.info(
            "llm_analysis.complete",
            proposicao_id=prop_id,
            model=self._model,
            areas=len(analysis["areas_afetadas"]),
        )

        return analysis

    def _validate_and_normalize(
        self, result: dict, prop_id: Any
    ) -> dict[str, Any]:
        """Validate and normalize the LLM response.

        Ensures all required fields are present and have correct types.

        Args:
            result: Raw parsed JSON from LLM.
            prop_id: Proposition ID for error messages.

        Returns:
            Normalized analysis dict.

        Raises:
            LLMAnalysisError: If required fields are missing.
        """
        required_fields = [
            "resumo_leigo",
            "impacto_esperado",
            "areas_afetadas",
            "argumentos_favor",
            "argumentos_contra",
        ]

        for field in required_fields:
            if field not in result:
                raise LLMAnalysisError(
                    f"Campo obrigatório '{field}' ausente na resposta do LLM "
                    f"para proposição {prop_id}"
                )

        return {
            "resumo_leigo": str(result["resumo_leigo"]),
            "impacto_esperado": str(result["impacto_esperado"]),
            "areas_afetadas": [
                str(a) for a in (result["areas_afetadas"] or [])
            ][:5],
            "argumentos_favor": [
                str(a) for a in (result["argumentos_favor"] or [])
            ][:5],
            "argumentos_contra": [
                str(a) for a in (result["argumentos_contra"] or [])
            ][:5],
        }


class LLMAnalysisError(Exception):
    """Raised when the LLM analysis fails."""

    pass
