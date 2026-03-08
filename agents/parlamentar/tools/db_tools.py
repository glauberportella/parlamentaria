"""FunctionTools for database operations — propositions, analyses, voters.

These tools give agents access to the local database for cached propositions,
AI analyses, and voter data. They integrate with the service layer.
"""

from __future__ import annotations

from app.db.session import async_session_factory
from app.repositories.proposicao import ProposicaoRepository
from app.services.proposicao_service import ProposicaoService
from app.services.analise_service import AnaliseIAService
from app.services.eleitor_service import EleitorService
from app.schemas.eleitor import EleitorUpdate


async def consultar_proposicao_local(proposicao_id: int) -> dict:
    """Consulta uma proposição no banco de dados local do sistema.

    Proposições locais podem ter resumos e análises de IA já gerados.
    Prefira esta ferramenta quando a proposição já foi sincronizada.

    Args:
        proposicao_id: ID da proposição.

    Returns:
        Dict com status e dados da proposição incluindo análise IA se disponível.
    """
    try:
        async with async_session_factory() as session:
            service = ProposicaoService(session)
            try:
                prop = await service.get_by_id(proposicao_id)
            except Exception:
                return {
                    "status": "not_found",
                    "message": f"Proposição {proposicao_id} não encontrada localmente.",
                }

            return {
                "status": "success",
                "proposicao": {
                    "id": prop.id,
                    "tipo": prop.tipo,
                    "numero": prop.numero,
                    "ano": prop.ano,
                    "ementa": prop.ementa,
                    "situacao": prop.situacao or "",
                    "temas": prop.temas or [],
                    "resumo_ia": prop.resumo_ia or "",
                    "data_apresentacao": str(prop.data_apresentacao) if prop.data_apresentacao else "",
                },
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def listar_proposicoes_local(
    tema: str = "",
    ano: int = 0,
    limite: int = 10,
) -> dict:
    """Lista proposições sincronizadas no banco de dados local.

    Usa dados já sincronizados da API da Câmara, mais rápido e inclui
    análises de IA quando disponíveis.

    Args:
        tema: Filtrar por tema (ex: 'saúde', 'educação').
        ano: Filtrar por ano. 0 para todos.
        limite: Máximo de resultados (padrão 10).

    Returns:
        Dict com status e lista de proposições locais.
    """
    try:
        async with async_session_factory() as session:
            service = ProposicaoService(session)
            props = await service.list_proposicoes(
                tema=tema if tema else None,
                ano=ano if ano > 0 else None,
                limit=min(limite, 50),
            )

            items = []
            for p in props:
                items.append({
                    "id": p.id,
                    "tipo": p.tipo,
                    "numero": p.numero,
                    "ano": p.ano,
                    "ementa": p.ementa,
                    "resumo_ia": p.resumo_ia or "",
                })

            return {
                "status": "success",
                "proposicoes": items,
                "total": len(items),
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def obter_analise_ia(proposicao_id: int) -> dict:
    """Obtém a análise de IA mais recente para uma proposição.

    A análise inclui resumo em linguagem acessível, impacto esperado,
    áreas afetadas e argumentos a favor e contra.

    Args:
        proposicao_id: ID da proposição.

    Returns:
        Dict com status e análise completa da IA, ou mensagem se não disponível.
    """
    try:
        async with async_session_factory() as session:
            service = AnaliseIAService(session)
            analise = await service.get_latest(proposicao_id)

            if analise is None:
                return {
                    "status": "not_found",
                    "message": f"Nenhuma análise de IA disponível para a proposição {proposicao_id}.",
                }

            return {
                "status": "success",
                "analise": {
                    "resumo_leigo": analise.resumo_leigo,
                    "impacto_esperado": analise.impacto_esperado or "",
                    "areas_afetadas": analise.areas_afetadas or [],
                    "argumentos_favor": analise.argumentos_favor or [],
                    "argumentos_contra": analise.argumentos_contra or [],
                    "provedor_llm": analise.provedor_llm,
                    "modelo": analise.modelo,
                    "versao": analise.versao,
                    "data_geracao": str(analise.data_geracao),
                },
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def consultar_perfil_eleitor(chat_id: str) -> dict:
    """Consulta o perfil do eleitor pelo chat_id do mensageiro.

    Verifica se o eleitor está cadastrado e retorna seus dados.

    Args:
        chat_id: ID do chat no mensageiro (ex: Telegram user ID).

    Returns:
        Dict com status e dados do eleitor, ou 'not_found' se não cadastrado.
    """
    try:
        async with async_session_factory() as session:
            service = EleitorService(session)
            eleitor = await service.get_by_chat_id(chat_id)

            if eleitor is None:
                return {
                    "status": "not_found",
                    "message": "Eleitor não cadastrado. Inicie o cadastro.",
                }

            nivel = eleitor.nivel_verificacao
            nivel_str = nivel.value if hasattr(nivel, 'value') else str(nivel)

            return {
                "status": "success",
                "eleitor": {
                    "id": str(eleitor.id),
                    "nome": eleitor.nome,
                    "uf": eleitor.uf,
                    "verificado": eleitor.verificado,
                    "cidadao_brasileiro": eleitor.cidadao_brasileiro,
                    "data_nascimento": str(eleitor.data_nascimento) if eleitor.data_nascimento else None,
                    "elegivel": eleitor.elegivel,
                    "nivel_verificacao": nivel_str,
                    "cpf_registrado": eleitor.cpf_hash is not None,
                    "titulo_registrado": eleitor.titulo_eleitor_hash is not None,
                    "temas_interesse": eleitor.temas_interesse or [],
                    "channel": eleitor.channel,
                },
                "elegibilidade": EleitorService.verificar_elegibilidade(eleitor),
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def cadastrar_eleitor(
    chat_id: str,
    nome: str,
    uf: str,
    channel: str = "telegram",
    cidadao_brasileiro: bool = False,
    data_nascimento: str = "",
    cpf: str = "",
) -> dict:
    """Cadastra ou atualiza dados de um eleitor.

    Use quando o eleitor fornecer nome e UF durante a conversa.
    Pergunte também se é cidadão brasileiro, a data de nascimento
    e o CPF para determinar se o voto será oficial ou consultivo.

    Se o CPF for fornecido, ele será validado matematicamente e armazenado
    como hash SHA-256 (nunca em texto). Se todos os dados estiverem completos
    (nome, UF, CPF, data de nascimento, cidadania), o nível de verificação
    sobe para AUTO_DECLARADO automaticamente.

    Args:
        chat_id: ID do chat no mensageiro.
        nome: Nome completo do eleitor.
        uf: Sigla do estado (2 letras, ex: 'SP', 'RJ').
        channel: Canal de mensageria ('telegram' ou 'whatsapp').
        cidadao_brasileiro: Se o eleitor é cidadão brasileiro.
        data_nascimento: Data de nascimento no formato 'AAAA-MM-DD' (ex: '1990-05-15').
        cpf: CPF do eleitor (somente números, 11 dígitos). Opcional.

    Returns:
        Dict com status, dados do eleitor e informação de elegibilidade.
    """
    try:
        from datetime import date as _date

        ufs_validas = [
            "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
            "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
            "RO", "RR", "RS", "SC", "SE", "SP", "TO",
        ]
        uf_upper = uf.upper().strip()
        if uf_upper not in ufs_validas:
            return {
                "status": "error",
                "error": f"UF inválida: '{uf}'. Use a sigla do estado (ex: SP, RJ, MG).",
            }

        # Parse birth date if provided
        parsed_nascimento = None
        if data_nascimento and data_nascimento.strip():
            try:
                parsed_nascimento = _date.fromisoformat(data_nascimento.strip())
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Data de nascimento inválida: '{data_nascimento}'. Use o formato AAAA-MM-DD.",
                }

        async with async_session_factory() as session:
            service = EleitorService(session)
            eleitor, created = await service.get_or_create_by_chat_id(chat_id, channel)

            # Update with provided data
            update_fields: dict = {"nome": nome.strip(), "uf": uf_upper}
            if cidadao_brasileiro:
                update_fields["cidadao_brasileiro"] = True
            if parsed_nascimento is not None:
                update_fields["data_nascimento"] = parsed_nascimento

            update_data = EleitorUpdate(**update_fields)
            updated = await service.update_profile(eleitor.id, update_data)

            # Register CPF if provided
            cpf_result = None
            if cpf and cpf.strip():
                try:
                    updated, cpf_result = await service.registrar_cpf(updated.id, cpf.strip())
                except Exception as cpf_err:
                    cpf_result = {"cpf_valido": False, "erro": str(cpf_err)}

            await session.commit()

            elegibilidade = EleitorService.verificar_elegibilidade(updated)
            nivel = updated.nivel_verificacao
            nivel_str = nivel.value if hasattr(nivel, 'value') else str(nivel)

            result = {
                "status": "success",
                "message": "Cadastro realizado!" if created else "Dados atualizados!",
                "eleitor": {
                    "id": str(updated.id),
                    "nome": updated.nome,
                    "uf": updated.uf,
                    "verificado": updated.verificado,
                    "cidadao_brasileiro": updated.cidadao_brasileiro,
                    "elegivel": updated.elegivel,
                    "nivel_verificacao": nivel_str,
                    "cpf_registrado": updated.cpf_hash is not None,
                    "titulo_registrado": updated.titulo_eleitor_hash is not None,
                },
                "elegibilidade": elegibilidade,
            }

            if cpf_result:
                result["cpf_validacao"] = cpf_result

            if not updated.elegivel:
                result["aviso"] = (
                    "Seus votos serão registrados como OPINIÃO CONSULTIVA. "
                    + (elegibilidade.get("motivo") or "")
                )

            return result
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def atualizar_temas_interesse(
    chat_id: str,
    temas: str,
) -> dict:
    """Atualiza os temas de interesse do eleitor para notificações.

    O eleitor receberá notificações sobre proposições destes temas.

    Args:
        chat_id: ID do chat no mensageiro.
        temas: Temas separados por vírgula (ex: 'saúde, educação, economia').

    Returns:
        Dict com status e temas atualizados.
    """
    try:
        async with async_session_factory() as session:
            service = EleitorService(session)
            eleitor = await service.get_by_chat_id(chat_id)

            if eleitor is None:
                return {
                    "status": "not_found",
                    "message": "Eleitor não cadastrado. Faça o cadastro primeiro.",
                }

            temas_list = [t.strip().lower() for t in temas.split(",") if t.strip()]
            update_data = EleitorUpdate(temas_interesse=temas_list)
            await service.update_profile(eleitor.id, update_data)
            await session.commit()

            return {
                "status": "success",
                "temas": temas_list,
                "message": f"Seus temas de interesse foram atualizados: {', '.join(temas_list)}",
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def verificar_titulo_eleitor(
    chat_id: str,
    titulo: str,
) -> dict:
    """Verifica e registra o título de eleitor de um eleitor cadastrado.

    O título é validado matematicamente (12 dígitos + verificadores) e
    a UF do título é comparada com a UF do cadastro. Se válido,
    o nível de verificação sobe para VERIFICADO_TITULO (máximo offline).

    Este é o nível mais alto de verificação disponível na plataforma.
    O eleitor deve ter um cadastro completo (nome, UF, CPF) antes.

    Args:
        chat_id: ID do chat no mensageiro.
        titulo: Número do título de eleitor (12 dígitos, somente números).

    Returns:
        Dict com status, resultado da validação e novo nível de verificação.
    """
    try:
        async with async_session_factory() as session:
            service = EleitorService(session)
            eleitor = await service.get_by_chat_id(chat_id)

            if eleitor is None:
                return {
                    "status": "not_found",
                    "message": "Eleitor não cadastrado. Faça o cadastro primeiro com /cadastro.",
                }

            if eleitor.cpf_hash is None:
                return {
                    "status": "error",
                    "error": "Registre seu CPF antes de verificar o título de eleitor.",
                }

            try:
                updated, resultado = await service.verificar_titulo_eleitor(
                    eleitor.id, titulo.strip()
                )
                await session.commit()

                return {
                    "status": "success",
                    "message": "Título de eleitor verificado com sucesso! "
                               "Seu nível de verificação foi promovido para VERIFICADO_TITULO.",
                    "verificacao": resultado,
                    "eleitor": {
                        "id": str(updated.id),
                        "nome": updated.nome,
                        "elegivel": updated.elegivel,
                        "nivel_verificacao": resultado["nivel_verificacao"],
                    },
                }
            except Exception as val_err:
                return {
                    "status": "error",
                    "error": str(val_err),
                }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def listar_temas_disponiveis(incluir_referencia_oficial: bool = False) -> dict:
    """Lista todos os temas disponíveis para proposições legislativas.

    Retorna os temas que existem nas proposições já sincronizadas no sistema.
    Útil para saber quais áreas temáticas estão disponíveis para busca.
    Opcionalmente, inclui a lista oficial de temas da API da Câmara.

    Args:
        incluir_referencia_oficial: Se True, também busca a lista completa de
            temas oficiais da API da Câmara dos Deputados (pode ser mais lenta).
            Padrão False — retorna apenas temas das proposições sincronizadas.

    Returns:
        Dict com status, lista de temas locais e opcionalmente temas oficiais.
    """
    try:
        async with async_session_factory() as session:
            repo = ProposicaoRepository(session)
            temas_locais = await repo.listar_temas_distintos()

            resultado: dict = {
                "status": "success",
                "temas_disponiveis": temas_locais,
                "total": len(temas_locais),
                "descricao": (
                    "Estes são os temas das proposições que já foram "
                    "sincronizadas no sistema. O eleitor pode buscar "
                    "proposições usando qualquer um desses temas."
                ),
            }

            if incluir_referencia_oficial:
                try:
                    from app.integrations.camara_client import CamaraClient

                    async with CamaraClient() as client:
                        refs = await client.listar_temas_referencia()
                        resultado["temas_oficiais"] = [
                            {"codigo": r.cod, "nome": r.nome}
                            for r in refs
                        ]
                        resultado["total_oficiais"] = len(refs)
                except Exception:
                    resultado["temas_oficiais_erro"] = (
                        "Não foi possível consultar os temas oficiais "
                        "da API da Câmara no momento."
                    )

            return resultado
    except Exception:
        return {
            "status": "error",
            "error": (
                "Não foi possível listar os temas disponíveis no momento. "
                "Tente novamente em instantes."
            ),
        }
