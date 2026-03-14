#!/usr/bin/env python3
"""Bootstrap the first admin user for the parlamentar dashboard.

Usage:
    # Interactive (prompts for values):
    python -m scripts.create_admin

    # Non-interactive (all args provided):
    python -m scripts.create_admin \
        --email admin@parlamentaria.app \
        --nome "Administrador" \
        --tipo ASSESSOR

    # Via Docker:
    docker compose exec backend python -m scripts.create_admin \
        --email admin@parlamentaria.app \
        --nome "Administrador"

The script creates a user with is_admin=True and prints the invitation code.
Send this code along with the email to login at the dashboard.
"""

import argparse
import asyncio
import sys

from app.config import settings
from app.db.session import async_session_factory
from app.services.parlamentar_auth_service import ParlamentarAuthService


async def main(email: str, nome: str, tipo: str, cargo: str | None) -> None:
    async with async_session_factory() as session:
        service = ParlamentarAuthService(session)

        # Check if email already exists
        existing = await service.get_user_by_email(email)
        if existing is not None:
            if existing.is_admin:
                print(f"\n✓ Usuário {email} já é admin.")
                if existing.codigo_convite and not existing.convite_usado:
                    print(f"  Código de convite: {existing.codigo_convite}")
                    print(f"\n  Login: acesse o dashboard → insira o email + código acima.")
                else:
                    print(f"  Convite já utilizado — faça login normalmente com email.")
                return

            # Promote existing user to admin
            existing.is_admin = True
            await session.commit()
            print(f"\n✓ Usuário {email} promovido a admin.")
            print(f"  Faça login normalmente com seu email.")
            return

        user = await service.create_invitation(
            email=email,
            nome=nome,
            tipo=tipo,
            cargo=cargo,
            is_admin=True,
        )
        await session.commit()

    print(f"\n{'='*60}")
    print(f"  Admin criado com sucesso!")
    print(f"{'='*60}")
    print(f"  Email:   {user.email}")
    print(f"  Nome:    {user.nome}")
    print(f"  Tipo:    {user.tipo.value if hasattr(user.tipo, 'value') else user.tipo}")
    print(f"  Admin:   ✓")
    print(f"  Código:  {user.codigo_convite}")
    print(f"{'='*60}")
    print(f"\n  Para fazer login no dashboard:")
    print(f"  1. Acesse {settings.dashboard_url}/login")
    print(f"  2. Insira o email: {user.email}")
    print(f"  3. Insira o código de convite acima")
    print(f"  4. Clique em 'Enviar link de acesso'")
    print(f"  5. Acesse o link recebido por email")
    print(f"  6. Após o primeiro login, basta usar só o email.\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Criar primeiro usuário admin do dashboard parlamentar."
    )
    parser.add_argument("--email", help="Email do admin")
    parser.add_argument("--nome", help="Nome do admin")
    parser.add_argument(
        "--tipo",
        default="ASSESSOR",
        choices=["DEPUTADO", "ASSESSOR", "LIDERANCA"],
        help="Tipo de usuário (padrão: ASSESSOR)",
    )
    parser.add_argument("--cargo", default=None, help="Cargo (opcional)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    email = args.email
    nome = args.nome

    if not email:
        email = input("Email do admin: ").strip()
    if not nome:
        nome = input("Nome do admin: ").strip()

    if not email or not nome:
        print("Erro: email e nome são obrigatórios.", file=sys.stderr)
        sys.exit(1)

    asyncio.run(main(email, nome, args.tipo, args.cargo))
