#!/usr/bin/env python3
"""Script de teste end-to-end para o sistema de notificações.

Testa o fluxo completo: desde o envio de uma mensagem via Telegram
até a verificação de que eleitores cadastrados recebem notificações
quando novas proposições são sincronizadas.

Uso:
    # Teste 1: Verificar se o bot Telegram está conectado
    python scripts/test_notifications.py --check-bot

    # Teste 2: Enviar mensagem de teste para um chat_id específico
    python scripts/test_notifications.py --send-test --chat-id SEU_CHAT_ID

    # Teste 3: Simular fluxo completo de notificação (sem enviar no Telegram)
    python scripts/test_notifications.py --dry-run

    # Teste 4: Simular fluxo completo COM envio real no Telegram
    python scripts/test_notifications.py --live-test --chat-id SEU_CHAT_ID

    # Teste 5: Listar eleitores cadastrados e seus temas de interesse
    python scripts/test_notifications.py --list-voters

    # Teste 6: Testar o NotificationService diretamente (com DB real)
    python scripts/test_notifications.py --test-service --chat-id SEU_CHAT_ID

Pré-requisitos:
    - Variáveis de ambiente configuradas no .env (TELEGRAM_BOT_TOKEN, DATABASE_URL)
    - PostgreSQL e Redis rodando (docker-compose up db redis)
    - Virtualenv ativado: source backend/.venv/bin/activate
    - Executar a partir da raiz do projeto

Para saber seu chat_id no Telegram:
    1. Abra conversa com @userinfobot no Telegram
    2. Envie /start — ele mostrará seu chat_id
    3. Ou abra conversa com seu bot e envie /start
       Depois consulte: https://api.telegram.org/bot<TOKEN>/getUpdates
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

# Adicionar o diretório backend ao path para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


async def check_bot() -> bool:
    """Teste 1: Verificar se o bot Telegram está acessível e configurado."""
    from app.config import settings

    print("\n" + "=" * 60)
    print("🤖 TESTE: Verificar conexão do Bot Telegram")
    print("=" * 60)

    if not settings.telegram_bot_token:
        print("❌ TELEGRAM_BOT_TOKEN não está configurado no .env")
        return False

    print(f"✅ Token configurado: {settings.telegram_bot_token[:10]}...{settings.telegram_bot_token[-5:]}")

    try:
        from telegram import Bot

        bot = Bot(token=settings.telegram_bot_token)
        me = await bot.get_me()
        print(f"✅ Bot conectado com sucesso!")
        print(f"   Nome: {me.first_name}")
        print(f"   Username: @{me.username}")
        print(f"   ID: {me.id}")
        print(f"   Pode entrar em grupos: {me.can_join_groups}")
        return True
    except Exception as e:
        print(f"❌ Falha ao conectar com o bot: {e}")
        return False


async def send_test_message(chat_id: str) -> bool:
    """Teste 2: Enviar mensagem de teste diretamente via TelegramAdapter."""
    from app.config import settings

    print("\n" + "=" * 60)
    print(f"📩 TESTE: Enviar mensagem de teste para chat_id={chat_id}")
    print("=" * 60)

    if not settings.telegram_bot_token:
        print("❌ TELEGRAM_BOT_TOKEN não está configurado")
        return False

    try:
        from channels.telegram.bot import TelegramAdapter

        adapter = TelegramAdapter(token=settings.telegram_bot_token)

        test_message = (
            "🧪 <b>Teste de Notificação — Parlamentaria</b>\n\n"
            "Esta é uma mensagem de teste do sistema de notificações.\n"
            "Se você está vendo isso, o envio via Telegram está funcionando! ✅\n\n"
            f"Chat ID: <code>{chat_id}</code>"
        )

        await adapter.send_message(chat_id, test_message)
        print(f"✅ Mensagem enviada com sucesso para {chat_id}!")
        print("   Verifique no Telegram se a mensagem chegou.")
        return True
    except Exception as e:
        print(f"❌ Falha ao enviar mensagem: {e}")
        return False


async def dry_run_notification() -> dict:
    """Teste 3: Simular fluxo de notificação sem enviar no Telegram."""
    print("\n" + "=" * 60)
    print("🏃 TESTE: Dry-run do NotificationService")
    print("=" * 60)

    from app.db.session import async_session_factory
    from app.services.notification_service import NotificationService

    async with async_session_factory() as session:
        service = NotificationService(session)

        # Buscar todos os eleitores com temas de interesse
        from sqlalchemy import select
        from app.domain.eleitor import Eleitor

        stmt = select(Eleitor).where(Eleitor.temas_interesse.isnot(None))
        result = await session.execute(stmt)
        all_voters = result.scalars().all()

        print(f"\n📊 Estado do banco de dados:")
        print(f"   Eleitores cadastrados: {len(all_voters)}")

        voters_with_temas = [v for v in all_voters if v.temas_interesse]
        print(f"   Eleitores com temas: {len(voters_with_temas)}")

        voters_with_chat = [v for v in voters_with_temas if v.chat_id]
        print(f"   Eleitores com temas + chat_id: {len(voters_with_chat)}")

        if voters_with_temas:
            # Coletar todos os temas únicos
            all_temas = set()
            for v in voters_with_temas:
                if v.temas_interesse:
                    all_temas.update(v.temas_interesse)
            print(f"   Temas com interesse: {sorted(all_temas)}")

        # Simular notificação (dry run - send_fn=None)
        stats = await service.notify_voters_about_proposicao(
            proposicao_id=99999,
            tipo="PL",
            numero=9999,
            ano=2026,
            ementa="[TESTE] Proposição de teste para verificar sistema de notificações",
            temas=["economia", "saúde", "educação"],
            send_fn=None,  # Dry run
        )

        print(f"\n📤 Resultado do dry run:")
        print(f"   Total de eleitores encontrados: {stats['total_voters']}")
        print(f"   Notificações que seriam enviadas: {stats['sent']}")
        print(f"   Pulados (sem chat_id): {stats['skipped']}")
        print(f"   Erros: {stats['errors']}")

        if stats["total_voters"] == 0:
            print("\n⚠️  Nenhum eleitor com temas de interesse encontrado.")
            print("   Para testar, cadastre um eleitor com temas via bot do Telegram")
            print("   ou insira diretamente no banco:")
            print("""
   INSERT INTO eleitores (nome, email, uf, channel, chat_id, temas_interesse, verificado)
   VALUES ('Teste', 'teste@email.com', 'SP', 'telegram', 'SEU_CHAT_ID',
           '{"economia","saúde","educação"}', true);
            """)

        return stats


async def live_test_notification(chat_id: str) -> dict:
    """Teste 4: Fluxo completo com envio real no Telegram."""
    from app.config import settings

    print("\n" + "=" * 60)
    print(f"🚀 TESTE LIVE: Notificação real para chat_id={chat_id}")
    print("=" * 60)

    if not settings.telegram_bot_token:
        print("❌ TELEGRAM_BOT_TOKEN não está configurado")
        return {"error": "no_token"}

    from app.db.session import async_session_factory
    from app.services.notification_service import NotificationService
    from channels.telegram.bot import TelegramAdapter

    adapter = TelegramAdapter(token=settings.telegram_bot_token)

    async def real_send(target_chat_id: str, text: str) -> None:
        await adapter.send_message(target_chat_id, text)

    async with async_session_factory() as session:
        service = NotificationService(session)

        # Verificar se o chat_id está cadastrado como eleitor
        from sqlalchemy import select
        from app.domain.eleitor import Eleitor

        stmt = select(Eleitor).where(Eleitor.chat_id == chat_id)
        result = await session.execute(stmt)
        voter = result.scalar_one_or_none()

        if voter:
            print(f"✅ Eleitor encontrado: {voter.nome} (UF: {voter.uf})")
            print(f"   Temas: {voter.temas_interesse}")
            temas_test = voter.temas_interesse if voter.temas_interesse else ["economia"]
        else:
            print(f"⚠️  Eleitor com chat_id={chat_id} não encontrado no banco.")
            print("   Enviando notificação diretamente mesmo assim...")
            temas_test = ["economia"]

            # Enviar diretamente já que o eleitor pode não estar no banco
            msg = service.format_nova_proposicao_message(
                proposicao_id=99999,
                tipo="PL",
                numero=9999,
                ano=2026,
                ementa="[TESTE] Proposição de teste para notificações",
                temas=temas_test,
            )
            try:
                await real_send(chat_id, msg)
                print("✅ Mensagem de teste enviada com sucesso!")
                return {"sent": 1, "total_voters": 0, "errors": 0}
            except Exception as e:
                print(f"❌ Erro ao enviar: {e}")
                return {"sent": 0, "errors": 1}

        # Fluxo completo via NotificationService
        stats = await service.notify_voters_about_proposicao(
            proposicao_id=99999,
            tipo="PL",
            numero=9999,
            ano=2026,
            ementa="[TESTE] Proposição de teste — verificação do sistema de notificações",
            temas=temas_test,
            send_fn=real_send,
        )

        print(f"\n📤 Resultado do teste live:")
        print(f"   Total de eleitores encontrados: {stats['total_voters']}")
        print(f"   Notificações enviadas: {stats['sent']}")
        print(f"   Pulados: {stats['skipped']}")
        print(f"   Erros: {stats['errors']}")

        if stats["sent"] > 0:
            print("\n✅ Verifique no Telegram se a(s) mensagem(ns) chegou(aram)!")
        elif stats["errors"] > 0:
            print("\n❌ Houve erros no envio. Verifique os logs.")
        else:
            print("\n⚠️  Nenhuma notificação enviada. Verifique se há eleitores com temas correspondentes.")

        return stats


async def list_voters() -> None:
    """Teste 5: Listar todos os eleitores e seus dados relevantes para notificação."""
    print("\n" + "=" * 60)
    print("👥 LISTAR ELEITORES CADASTRADOS")
    print("=" * 60)

    from app.db.session import async_session_factory
    from sqlalchemy import select, func
    from app.domain.eleitor import Eleitor

    async with async_session_factory() as session:
        stmt = select(Eleitor).order_by(Eleitor.data_cadastro.desc())
        result = await session.execute(stmt)
        voters = result.scalars().all()

        if not voters:
            print("\n⚠️  Nenhum eleitor cadastrado no banco de dados.")
            print("   Inicie uma conversa com o bot do Telegram para cadastrar.")
            return

        print(f"\nTotal: {len(voters)} eleitor(es)\n")

        for i, v in enumerate(voters, 1):
            status = "✅" if v.verificado else "⏳"
            chat = v.chat_id or "N/A"
            temas = ", ".join(v.temas_interesse) if v.temas_interesse else "Nenhum"
            print(f"  {i}. {status} {v.nome} ({v.uf}) — chat_id: {chat}")
            print(f"     Channel: {v.channel} | Email: {v.email}")
            print(f"     Temas: {temas}")
            print()

        # Resumo para notificações
        with_chat = sum(1 for v in voters if v.chat_id)
        with_temas = sum(1 for v in voters if v.temas_interesse)
        notifiable = sum(1 for v in voters if v.chat_id and v.temas_interesse)
        print(f"📊 Resumo para notificações:")
        print(f"   Com chat_id: {with_chat}/{len(voters)}")
        print(f"   Com temas de interesse: {with_temas}/{len(voters)}")
        print(f"   Notificáveis (chat_id + temas): {notifiable}/{len(voters)}")


async def test_service_with_db(chat_id: str) -> None:
    """Teste 6: Testar todo o pipeline do NotificationService com DB real."""
    from app.config import settings

    print("\n" + "=" * 60)
    print("🔧 TESTE COMPLETO DO PIPELINE DE NOTIFICAÇÃO")
    print("=" * 60)

    # Step 1: Verificar bot
    print("\n--- Step 1/5: Verificar Bot Telegram ---")
    bot_ok = await check_bot()
    if not bot_ok:
        print("❌ Abortando — bot não está acessível.")
        return

    # Step 2: Verificar banco de dados
    print("\n--- Step 2/5: Verificar conexão com o banco ---")
    try:
        from app.db.session import async_session_factory
        from sqlalchemy import text as sql_text

        async with async_session_factory() as session:
            result = await session.execute(sql_text("SELECT 1"))
            assert result.scalar() == 1
            print("✅ Banco de dados acessível")
    except Exception as e:
        print(f"❌ Erro de conexão com o banco: {e}")
        return

    # Step 3: Verificar eleitor
    print(f"\n--- Step 3/5: Verificar eleitor com chat_id={chat_id} ---")
    from app.db.session import async_session_factory
    from sqlalchemy import select
    from app.domain.eleitor import Eleitor

    async with async_session_factory() as session:
        stmt = select(Eleitor).where(Eleitor.chat_id == chat_id)
        result = await session.execute(stmt)
        voter = result.scalar_one_or_none()

    if voter:
        print(f"✅ Eleitor: {voter.nome} ({voter.uf})")
        print(f"   Temas: {voter.temas_interesse}")
    else:
        print(f"⚠️  Eleitor com chat_id={chat_id} não encontrado.")
        print("   Criando eleitor de teste temporário...")

        from app.db.session import async_session_factory

        async with async_session_factory() as session:
            test_voter = Eleitor(
                nome="Teste Notificação",
                email=f"teste.notif.{chat_id}@parlamentaria.test",
                uf="SP",
                channel="telegram",
                chat_id=chat_id,
                temas_interesse=["economia", "saúde", "educação"],
                verificado=True,
            )
            session.add(test_voter)
            await session.commit()
            await session.refresh(test_voter)
            voter = test_voter
            print(f"✅ Eleitor de teste criado: {voter.nome}")

    # Step 4: Testar formatação de mensagem
    print("\n--- Step 4/5: Testar formatação de mensagem ---")
    from app.services.notification_service import NotificationService

    async with async_session_factory() as session:
        service = NotificationService(session)
        msg = service.format_nova_proposicao_message(
            proposicao_id=12345,
            tipo="PL",
            numero=1234,
            ano=2026,
            ementa="Dispõe sobre a regulamentação de inteligência artificial no Brasil",
            temas=["tecnologia", "economia"],
        )
        print(f"✅ Mensagem formatada ({len(msg)} chars):")
        print(f"   {msg[:100]}...")

    # Step 5: Enviar notificação real
    print(f"\n--- Step 5/5: Enviar notificação para {chat_id} ---")
    from channels.telegram.bot import TelegramAdapter

    adapter = TelegramAdapter(token=settings.telegram_bot_token)

    async def real_send(target_chat_id: str, text: str) -> None:
        await adapter.send_message(target_chat_id, text)

    async with async_session_factory() as session:
        service = NotificationService(session)

        # Testar notificação de nova proposição
        print("\n   📜 Enviando notificação de nova proposição...")
        stats_prop = await service.notify_voters_about_proposicao(
            proposicao_id=12345,
            tipo="PL",
            numero=1234,
            ano=2026,
            ementa="Dispõe sobre a regulamentação de IA no Brasil",
            temas=voter.temas_interesse or ["economia"],
            send_fn=real_send,
        )
        print(f"   Resultado: enviadas={stats_prop['sent']}, erros={stats_prop['errors']}")

        # Testar notificação de comparativo
        print("\n   🏛️ Enviando notificação de comparativo...")
        msg_comp = service.format_comparativo_message(
            proposicao_id=12345,
            tipo="PL",
            numero=1234,
            ano=2026,
            resultado_camara="APROVADO",
            percentual_sim_popular=78.5,
            alinhamento=0.92,
        )
        try:
            await real_send(chat_id, msg_comp)
            print("   ✅ Notificação de comparativo enviada!")
        except Exception as e:
            print(f"   ❌ Erro: {e}")

        # Testar notificação de resultado de votação
        print("\n   📊 Enviando notificação de resultado...")
        msg_res = service.format_resultado_votacao_message(
            proposicao_id=12345,
            tipo="PL",
            numero=1234,
            ano=2026,
            total_votos=542,
            percentual_sim=78.5,
            percentual_nao=18.3,
            percentual_abstencao=3.2,
        )
        try:
            await real_send(chat_id, msg_res)
            print("   ✅ Notificação de resultado enviada!")
        except Exception as e:
            print(f"   ❌ Erro: {e}")

    print("\n" + "=" * 60)
    print("✅ TESTE COMPLETO FINALIZADO")
    print("   Verifique no Telegram se as 3 mensagens chegaram:")
    print("   1. Nova proposição")
    print("   2. Comparativo (voto popular vs Câmara)")
    print("   3. Resultado de votação popular")
    print("=" * 60)


async def test_celery_task_sync() -> None:
    """Teste extra: Verificar se a Celery task é chamada após sync."""
    print("\n" + "=" * 60)
    print("⚙️ TESTE: Verificar encadeamento sync → notificação")
    print("=" * 60)

    # Verificar se o código da sync task tem o trigger de notificação
    import inspect
    from app.tasks.sync_proposicoes import sync_proposicoes_task

    source = inspect.getsource(sync_proposicoes_task)
    has_notification_trigger = "notificar_eleitores_task" in source

    if has_notification_trigger:
        print("✅ sync_proposicoes_task encadeia notificar_eleitores_task")
    else:
        print("❌ sync_proposicoes_task NÃO encadeia notificação!")
        print("   As notificações não serão disparadas automaticamente após sync.")

    # Verificar se a task de notificação usa send_fn real
    from app.tasks.notificar_eleitores import notificar_eleitores_task

    source_notif = inspect.getsource(notificar_eleitores_task)
    uses_dry_run = 'send_fn=None' in source_notif and '_get_telegram_send_fn' not in source_notif

    if uses_dry_run:
        print("❌ notificar_eleitores_task está em modo dry-run (send_fn=None)")
        print("   As notificações são apenas logadas, não enviadas ao Telegram.")
    else:
        print("✅ notificar_eleitores_task usa TelegramAdapter para envio real")


def main() -> None:
    """Parse arguments and run the appropriate test."""
    parser = argparse.ArgumentParser(
        description="Teste end-to-end do sistema de notificações do Parlamentaria",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python scripts/test_notifications.py --check-bot
  python scripts/test_notifications.py --send-test --chat-id 123456789
  python scripts/test_notifications.py --dry-run
  python scripts/test_notifications.py --live-test --chat-id 123456789
  python scripts/test_notifications.py --list-voters
  python scripts/test_notifications.py --test-service --chat-id 123456789
  python scripts/test_notifications.py --check-chain

Para descobrir seu chat_id:
  1. Converse com @userinfobot no Telegram
  2. Ou envie /start ao bot e consulte:
     https://api.telegram.org/bot<TOKEN>/getUpdates
        """,
    )

    parser.add_argument("--check-bot", action="store_true", help="Verificar conexão do bot Telegram")
    parser.add_argument("--send-test", action="store_true", help="Enviar mensagem de teste")
    parser.add_argument("--dry-run", action="store_true", help="Simular notificações (sem enviar)")
    parser.add_argument("--live-test", action="store_true", help="Notificação real via Telegram")
    parser.add_argument("--list-voters", action="store_true", help="Listar eleitores cadastrados")
    parser.add_argument("--test-service", action="store_true", help="Teste completo do pipeline")
    parser.add_argument("--check-chain", action="store_true", help="Verificar encadeamento sync→notificação")
    parser.add_argument("--chat-id", type=str, help="Chat ID do Telegram para enviar mensagens")

    args = parser.parse_args()

    if not any([args.check_bot, args.send_test, args.dry_run, args.live_test,
                args.list_voters, args.test_service, args.check_chain]):
        parser.print_help()
        return

    if (args.send_test or args.live_test or args.test_service) and not args.chat_id:
        print("❌ --chat-id é obrigatório para este teste.")
        print("   Use @userinfobot no Telegram para descobrir.")
        return

    if args.check_bot:
        asyncio.run(check_bot())
    elif args.send_test:
        asyncio.run(send_test_message(args.chat_id))
    elif args.dry_run:
        asyncio.run(dry_run_notification())
    elif args.live_test:
        asyncio.run(live_test_notification(args.chat_id))
    elif args.list_voters:
        asyncio.run(list_voters())
    elif args.test_service:
        asyncio.run(test_service_with_db(args.chat_id))
    elif args.check_chain:
        asyncio.run(test_celery_task_sync())


if __name__ == "__main__":
    main()
