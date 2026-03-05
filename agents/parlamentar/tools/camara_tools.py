"""FunctionTools for querying the Câmara dos Deputados API.

These tools are used by ProposicaoAgent and DeputadoAgent to fetch
legislative data. Each tool is a plain Python function that will be
auto-wrapped as a FunctionTool by the ADK.
"""

from __future__ import annotations

from app.integrations.camara_client import CamaraClient


async def buscar_proposicoes(
    tema: str = "",
    tipo: str = "",
    ano: int = 0,
    pagina: int = 1,
    itens: int = 10,
) -> dict:
    """Busca proposições legislativas na Câmara dos Deputados.

    Use esta ferramenta para pesquisar projetos de lei, PECs, medidas
    provisórias e outras proposições. Pode filtrar por tema, tipo ou ano.

    Args:
        tema: Área temática (ex: 'saúde', 'educação', 'economia').
            Deixe vazio para não filtrar por tema.
        tipo: Tipo de proposição (ex: 'PL', 'PEC', 'MPV', 'PLP').
            Deixe vazio para todos os tipos.
        ano: Ano de apresentação. Use 0 para não filtrar por ano.
        pagina: Número da página de resultados (padrão 1).
        itens: Quantidade de resultados por página (padrão 10, máximo 100).

    Returns:
        Dict com status, lista de proposições e total de resultados.
    """
    try:
        async with CamaraClient() as client:
            filtros: dict = {}
            if tema:
                filtros["keywords"] = tema
            if tipo:
                filtros["sigla_tipo"] = tipo
            if ano > 0:
                filtros["ano"] = ano
            filtros["pagina"] = pagina
            filtros["itens"] = min(itens, 100)
            filtros["ordenar_por"] = "id"
            filtros["ordem"] = "DESC"

            proposicoes = await client.listar_proposicoes(**filtros)

            items = []
            for p in proposicoes:
                items.append({
                    "id": p.id,
                    "tipo": p.siglaTipo,
                    "numero": p.numero,
                    "ano": p.ano,
                    "ementa": p.ementa,
                })

            return {
                "status": "success",
                "proposicoes": items,
                "total": len(items),
                "pagina": pagina,
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def obter_detalhes_proposicao(proposicao_id: int) -> dict:
    """Obtém detalhes completos de uma proposição legislativa pelo ID.

    Use esta ferramenta quando o eleitor perguntar sobre uma proposição
    específica ou quando precisar de mais informações sobre um projeto.

    Args:
        proposicao_id: ID numérico da proposição na API da Câmara.

    Returns:
        Dict com status e detalhes da proposição incluindo ementa e situação.
    """
    try:
        async with CamaraClient() as client:
            prop = await client.obter_proposicao(proposicao_id)
            autores = await client.obter_autores(proposicao_id)
            temas = await client.obter_temas(proposicao_id)

            return {
                "status": "success",
                "proposicao": {
                    "id": prop.id,
                    "tipo": prop.siglaTipo,
                    "numero": prop.numero,
                    "ano": prop.ano,
                    "ementa": prop.ementa,
                    "texto_url": prop.urlInteiroTeor,
                    "situacao": prop.statusProposicao.get("descricaoSituacao", "")
                    if prop.statusProposicao else "",
                    "data_apresentacao": prop.dataApresentacao,
                    "autores": [
                        {"nome": a.nome, "tipo": a.tipo} for a in autores
                    ],
                    "temas": [t.tema for t in temas],
                },
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def listar_tramitacoes_proposicao(proposicao_id: int) -> dict:
    """Lista o histórico de tramitação de uma proposição.

    Mostra como uma proposição evoluiu pelas comissões e plenário.

    Args:
        proposicao_id: ID da proposição.

    Returns:
        Dict com status e lista de tramitações (mais recentes primeiro).
    """
    try:
        async with CamaraClient() as client:
            tramitacoes = await client.obter_tramitacoes(proposicao_id)

            items = []
            for t in tramitacoes[:10]:  # Últimas 10
                items.append({
                    "data": t.dataHora,
                    "descricao": t.descricaoSituacao or "",
                    "despacho": t.despacho or "",
                    "tramitacao": t.descricaoTramitacao or "",
                })

            return {
                "status": "success",
                "tramitacoes": items,
                "total": len(tramitacoes),
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def buscar_votacoes_recentes(
    proposicao_id: int = 0,
    pagina: int = 1,
    itens: int = 10,
) -> dict:
    """Busca votações recentes na Câmara dos Deputados.

    Pode buscar votações gerais ou de uma proposição específica.

    Args:
        proposicao_id: Se > 0, filtra votações desta proposição.
            Use 0 para votações gerais recentes.
        pagina: Número da página de resultados.
        itens: Quantidade de resultados por página.

    Returns:
        Dict com status e lista de votações recentes.
    """
    try:
        async with CamaraClient() as client:
            # API Câmara: /votacoes endpoint with optional filters
            votacoes = await client.listar_votacoes(
                pagina=pagina, itens=min(itens, 100)
            )

            items = []
            for v in votacoes:
                items.append({
                    "id": v.id,
                    "data": v.data,
                    "descricao": v.descricao or "",
                    "aprovacao": v.aprovacao,
                })

            return {
                "status": "success",
                "votacoes": items,
                "total": len(items),
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def obter_votos_parlamentares(votacao_id: int) -> dict:
    """Obtém como cada parlamentar votou em uma votação específica.

    Args:
        votacao_id: ID da votação na API da Câmara.

    Returns:
        Dict com status, orientações de bancada e votos individuais.
    """
    try:
        async with CamaraClient() as client:
            votos = await client.obter_votos(votacao_id)
            orientacoes = await client.obter_orientacoes(votacao_id)

            return {
                "status": "success",
                "orientacoes": [
                    {
                        "bancada": o.nomeBancada,
                        "orientacao": o.orientacao,
                    }
                    for o in orientacoes
                ],
                "votos": [
                    {
                        "deputado": (v.deputado_ or {}).get("nome", ""),
                        "partido": (v.deputado_ or {}).get("siglaPartido", ""),
                        "uf": (v.deputado_ or {}).get("siglaUf", ""),
                        "voto": v.tipoVoto or "",
                    }
                    for v in votos[:50]  # Limita para não sobrecarregar contexto
                ],
                "total_votos": len(votos),
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def buscar_deputado(
    nome: str = "",
    uf: str = "",
    partido: str = "",
) -> dict:
    """Busca deputados federais na Câmara.

    Pesquisa por nome, UF (estado) ou partido.

    Args:
        nome: Nome ou parte do nome do deputado.
        uf: Sigla do estado (ex: 'SP', 'RJ', 'MG').
        partido: Sigla do partido (ex: 'PT', 'PL', 'PSDB').

    Returns:
        Dict com status e lista de deputados encontrados.
    """
    try:
        async with CamaraClient() as client:
            filtros: dict = {}
            if nome:
                filtros["nome"] = nome
            if uf:
                filtros["sigla_uf"] = uf
            if partido:
                filtros["sigla_partido"] = partido

            deputados = await client.listar_deputados(**filtros)

            items = []
            for d in deputados:
                items.append({
                    "id": d.id,
                    "nome": d.nome,
                    "partido": d.siglaPartido,
                    "uf": d.siglaUf,
                    "foto_url": d.urlFoto or "",
                })

            return {
                "status": "success",
                "deputados": items,
                "total": len(items),
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def obter_perfil_deputado(deputado_id: int) -> dict:
    """Obtém o perfil detalhado de um deputado federal.

    Args:
        deputado_id: ID do deputado na API da Câmara.

    Returns:
        Dict com status e dados detalhados do deputado.
    """
    try:
        async with CamaraClient() as client:
            dep = await client.obter_deputado(deputado_id)

            return {
                "status": "success",
                "deputado": {
                    "id": dep.id,
                    "nome_civil": dep.nomeCivil,
                    "nome_parlamentar": dep.ultimoStatus.get("nomeEleitoral", "")
                    if dep.ultimoStatus else "",
                    "partido": dep.ultimoStatus.get("siglaPartido", "")
                    if dep.ultimoStatus else "",
                    "uf": dep.ultimoStatus.get("siglaUf", "")
                    if dep.ultimoStatus else "",
                    "situacao": dep.ultimoStatus.get("situacao", "")
                    if dep.ultimoStatus else "",
                    "email": dep.ultimoStatus.get("gabinete", {}).get("email", "")
                    if dep.ultimoStatus else "",
                    "data_nascimento": dep.dataNascimento or "",
                    "foto_url": dep.ultimoStatus.get("urlFoto", "")
                    if dep.ultimoStatus else "",
                },
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def obter_despesas_deputado(
    deputado_id: int,
    ano: int = 0,
    mes: int = 0,
) -> dict:
    """Consulta despesas da cota parlamentar de um deputado.

    Ferramenta de transparência que permite ao eleitor verificar
    como o deputado está usando recursos públicos.

    Args:
        deputado_id: ID do deputado.
        ano: Ano das despesas. 0 para o ano corrente.
        mes: Mês das despesas (1-12). 0 para todos os meses.

    Returns:
        Dict com status e lista de despesas com valores e descrições.
    """
    try:
        async with CamaraClient() as client:
            filtros: dict = {}
            if ano > 0:
                filtros["ano"] = ano
            if 1 <= mes <= 12:
                filtros["mes"] = mes

            despesas = await client.obter_despesas(deputado_id, **filtros)

            total_gasto = 0.0
            items = []
            for d in despesas[:20]:  # Últimas 20
                valor = d.valorDocumento or 0.0
                total_gasto += valor
                items.append({
                    "tipo": d.tipoDespesa,
                    "fornecedor": d.nomeFornecedor or "",
                    "valor": round(valor, 2),
                    "data": d.dataDocumento or "",
                })

            return {
                "status": "success",
                "despesas": items,
                "total_gasto": round(total_gasto, 2),
                "total_registros": len(despesas),
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def buscar_eventos_pauta(dias: int = 7) -> dict:
    """Busca eventos e pautas recentes do plenário da Câmara.

    Mostra o que está sendo discutido e votado nos próximos dias.

    Args:
        dias: Número de dias à frente para buscar (padrão 7).

    Returns:
        Dict com status e lista de eventos com suas pautas.
    """
    try:
        from datetime import datetime, timedelta

        data_inicio = datetime.now().strftime("%Y-%m-%d")
        data_fim = (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")

        async with CamaraClient() as client:
            eventos = await client.listar_eventos(
                data_inicio=data_inicio,
                data_fim=data_fim,
            )

            items = []
            for e in eventos[:10]:
                items.append({
                    "id": e.id,
                    "data_inicio": e.dataHoraInicio or "",
                    "descricao": e.descricao or "",
                    "situacao": e.situacao or "",
                    "tipo": e.descricaoTipo or "",
                })

            return {
                "status": "success",
                "eventos": items,
                "total": len(eventos),
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}
