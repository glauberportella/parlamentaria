"""Authentication service for the parliamentarian dashboard.

Handles Magic Link generation/verification, JWT token management,
invitation codes, and email dispatch via Resend.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
import resend
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain.parlamentar_user import ParlamentarUser, TipoParlamentarUser
from app.exceptions import (
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)
from app.logging import get_logger

logger = get_logger(__name__)


class ParlamentarAuthService:
    """Service for parliamentarian dashboard authentication flows."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ──────────────────────────────────────────────
    #  JWT helpers
    # ──────────────────────────────────────────────

    @staticmethod
    def _create_token(data: dict, expires_delta: timedelta) -> str:
        """Create a signed JWT token."""
        payload = data.copy()
        now = datetime.now(timezone.utc)
        payload["exp"] = now + expires_delta
        payload["iat"] = now
        payload["jti"] = secrets.token_hex(16)
        return jwt.encode(
            payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

    @staticmethod
    def create_access_token(user: ParlamentarUser) -> str:
        """Create a short-lived access token for API calls."""
        return ParlamentarAuthService._create_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "tipo": user.tipo.value,
                "deputado_id": user.deputado_id,
                "plano": getattr(user, "plano", "FREE"),
                "type": "access",
            },
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        )

    @staticmethod
    def create_refresh_token(user: ParlamentarUser) -> str:
        """Create a long-lived refresh token."""
        return ParlamentarAuthService._create_token(
            data={
                "sub": str(user.id),
                "type": "refresh",
            },
            expires_delta=timedelta(days=settings.refresh_token_expire_days),
        )

    @staticmethod
    def create_magic_link_token(user: ParlamentarUser) -> str:
        """Create a short-lived token for Magic Link email."""
        return ParlamentarAuthService._create_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "type": "magic_link",
            },
            expires_delta=timedelta(minutes=settings.magic_link_expire_minutes),
        )

    @staticmethod
    def decode_token(token: str) -> dict:
        """Decode and validate a JWT token.

        Raises:
            UnauthorizedException: If token is invalid or expired.
        """
        try:
            payload = jwt.decode(
                token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise UnauthorizedException("Token expirado. Solicite um novo link de acesso.")
        except jwt.InvalidTokenError:
            raise UnauthorizedException("Token inválido.")

    @staticmethod
    def _hash_token(token: str) -> str:
        """SHA-256 hash of a refresh token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    # ──────────────────────────────────────────────
    #  User queries
    # ──────────────────────────────────────────────

    async def get_user_by_email(self, email: str) -> ParlamentarUser | None:
        """Find a parlamentar user by email."""
        result = await self.session.execute(
            select(ParlamentarUser).where(ParlamentarUser.email == email)
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> ParlamentarUser | None:
        """Find a parlamentar user by ID."""
        result = await self.session.execute(
            select(ParlamentarUser).where(ParlamentarUser.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_convite(self, codigo: str) -> ParlamentarUser | None:
        """Find a user by invitation code (unused)."""
        result = await self.session.execute(
            select(ParlamentarUser).where(
                ParlamentarUser.codigo_convite == codigo,
                ParlamentarUser.convite_usado == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def update_user_profile(
        self,
        user_id: str,
        nome: str | None = None,
        cargo: str | None = None,
        temas_acompanhados: list[str] | None = None,
        notificacoes_email: bool | None = None,
    ) -> ParlamentarUser:
        """Update a parlamentar user's profile and preferences.

        Only non-None values are applied (partial update).

        Raises:
            NotFoundException: If the user is not found.
        """
        user = await self.get_user_by_id(user_id)
        if user is None:
            raise NotFoundException("Conta não encontrada.")

        if nome is not None:
            user.nome = nome
        if cargo is not None:
            user.cargo = cargo
        if temas_acompanhados is not None:
            user.temas_acompanhados = temas_acompanhados
        if notificacoes_email is not None:
            user.notificacoes_email = notificacoes_email

        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(user)
        return user

    # ──────────────────────────────────────────────
    #  Login flow
    # ──────────────────────────────────────────────

    async def request_magic_link(
        self, email: str, codigo_convite: str | None = None
    ) -> bool:
        """Initiate Magic Link login. Returns True if email was sent.

        If codigo_convite is provided and valid, activates the user account first.
        Always returns True to prevent email enumeration attacks.
        """
        user = await self.get_user_by_email(email)

        # First-time login with invitation code
        if user is None and codigo_convite:
            user = await self.get_user_by_convite(codigo_convite)
            if user is not None:
                # Activate account: set email and mark convite as used
                user.email = email
                user.convite_usado = True
                await self.session.flush()

        if user is None or not user.ativo:
            # Don't reveal whether email exists — always return True
            logger.info("parlamentar.auth.login_attempt_unknown", email=email)
            return True

        # Generate Magic Link token and send email
        token = self.create_magic_link_token(user)
        magic_link_url = f"{settings.magic_link_base_url}?token={token}"

        await self._send_magic_link_email(user.email, user.nome, magic_link_url)
        logger.info("parlamentar.auth.magic_link_sent", user_id=user.id)
        return True

    async def verify_magic_link(self, token: str) -> tuple[ParlamentarUser, str, str]:
        """Verify a Magic Link token and return user + JWT tokens.

        Returns:
            Tuple of (user, access_token, refresh_token).

        Raises:
            UnauthorizedException: If token is invalid, expired, or user not found.
        """
        payload = self.decode_token(token)

        if payload.get("type") != "magic_link":
            raise UnauthorizedException("Token inválido para esta operação.")

        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Token inválido.")

        user = await self.get_user_by_id(user_id)
        if user is None or not user.ativo:
            raise UnauthorizedException("Conta não encontrada ou desativada.")

        # Update last login
        user.ultimo_login = datetime.now(timezone.utc)

        # Create JWT pair
        access_token = self.create_access_token(user)
        refresh_token = self.create_refresh_token(user)

        # Store refresh token hash for future revocation
        user.refresh_token_hash = self._hash_token(refresh_token)
        await self.session.flush()

        logger.info("parlamentar.auth.login_success", user_id=user.id)
        return user, access_token, refresh_token

    async def refresh_access_token(
        self, refresh_token: str
    ) -> tuple[ParlamentarUser, str, str]:
        """Refresh an access token using a valid refresh token.

        Issues a new access + refresh token pair (token rotation).

        Returns:
            Tuple of (user, new_access_token, new_refresh_token).

        Raises:
            UnauthorizedException: If refresh token is invalid or revoked.
        """
        payload = self.decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise UnauthorizedException("Token inválido para esta operação.")

        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Token inválido.")

        user = await self.get_user_by_id(user_id)
        if user is None or not user.ativo:
            raise UnauthorizedException("Conta não encontrada ou desativada.")

        # Validate refresh token hash matches stored hash
        token_hash = self._hash_token(refresh_token)
        if user.refresh_token_hash != token_hash:
            logger.warning(
                "parlamentar.auth.refresh_token_mismatch", user_id=user.id
            )
            raise UnauthorizedException("Token de atualização revogado.")

        # Token rotation: issue new pair
        new_access = self.create_access_token(user)
        new_refresh = self.create_refresh_token(user)
        user.refresh_token_hash = self._hash_token(new_refresh)
        await self.session.flush()

        logger.info("parlamentar.auth.token_refreshed", user_id=user.id)
        return user, new_access, new_refresh

    # ──────────────────────────────────────────────
    #  Invitation management
    # ──────────────────────────────────────────────

    async def create_invitation(
        self,
        email: str,
        nome: str,
        tipo: str = "ASSESSOR",
        cargo: str | None = None,
        deputado_id: int | None = None,
        is_admin: bool = False,
    ) -> ParlamentarUser:
        """Create a new parlamentar user with an invitation code.

        Raises:
            ValidationException: If email is already registered or tipo is invalid.
        """
        existing = await self.get_user_by_email(email)
        if existing is not None:
            raise ValidationException("Email já cadastrado no dashboard.")

        try:
            tipo_enum = TipoParlamentarUser(tipo)
        except ValueError:
            raise ValidationException(
                f"Tipo inválido. Use: {', '.join(t.value for t in TipoParlamentarUser)}"
            )

        codigo = secrets.token_urlsafe(32)

        user = ParlamentarUser(
            email=email,
            nome=nome,
            tipo=tipo_enum,
            cargo=cargo,
            deputado_id=deputado_id,
            codigo_convite=codigo,
            is_admin=is_admin,
            ativo=True,
        )
        self.session.add(user)
        await self.session.flush()

        logger.info(
            "parlamentar.auth.invitation_created",
            user_id=user.id,
            email=email,
        )

        # Send invitation email
        await self._send_invitation_email(email, nome, codigo)

        return user

    # ──────────────────────────────────────────────
    #  Demo login (development only)
    # ──────────────────────────────────────────────

    async def demo_login(self) -> tuple[ParlamentarUser, str, str]:
        """Create or find demo user and return JWT tokens directly.

        Only works when DEMO_MODE=true and not in production.

        Returns:
            Tuple of (user, access_token, refresh_token).

        Raises:
            ValidationException: If demo mode is disabled or in production.
        """
        if not settings.demo_mode or settings.is_production:
            raise ValidationException("Modo demo desabilitado.")

        user = await self.get_user_by_email(settings.demo_user_email)

        if user is None:
            user = ParlamentarUser(
                email=settings.demo_user_email,
                nome=settings.demo_user_nome,
                tipo=TipoParlamentarUser.DEPUTADO,
                cargo="Deputado(a) Federal",
                deputado_id=settings.demo_deputado_id,
                ativo=True,
                convite_usado=True,
            )
            self.session.add(user)
            await self.session.flush()
            logger.info("parlamentar.auth.demo_user_created", user_id=user.id)

        # Update last login
        user.ultimo_login = datetime.now(timezone.utc)

        # Create JWT pair
        access_token = self.create_access_token(user)
        refresh_token = self.create_refresh_token(user)
        user.refresh_token_hash = self._hash_token(refresh_token)
        await self.session.flush()

        logger.info("parlamentar.auth.demo_login", user_id=user.id)
        return user, access_token, refresh_token

    # ──────────────────────────────────────────────
    #  Admin — user management
    # ──────────────────────────────────────────────

    async def list_users(
        self,
        tipo: str | None = None,
        ativo: bool | None = None,
    ) -> list[ParlamentarUser]:
        """List all parlamentar users, optionally filtered."""
        stmt = select(ParlamentarUser).order_by(ParlamentarUser.created_at.desc())
        if tipo is not None:
            stmt = stmt.where(ParlamentarUser.tipo == tipo)
        if ativo is not None:
            stmt = stmt.where(ParlamentarUser.ativo == ativo)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def admin_update_user(
        self,
        user_id: str,
        nome: str | None = None,
        cargo: str | None = None,
        tipo: str | None = None,
        ativo: bool | None = None,
        is_admin: bool | None = None,
        deputado_id: int | None = None,
    ) -> ParlamentarUser:
        """Admin update of any parlamentar user.

        Raises:
            NotFoundException: If the user is not found.
            ValidationException: If tipo is invalid.
        """
        user = await self.get_user_by_id(user_id)
        if user is None:
            raise NotFoundException("Conta não encontrada.")

        if nome is not None:
            user.nome = nome
        if cargo is not None:
            user.cargo = cargo
        if tipo is not None:
            try:
                user.tipo = TipoParlamentarUser(tipo)
            except ValueError:
                raise ValidationException(
                    f"Tipo inválido. Use: {', '.join(t.value for t in TipoParlamentarUser)}"
                )
        if ativo is not None:
            user.ativo = ativo
        if is_admin is not None:
            user.is_admin = is_admin
        if deputado_id is not None:
            user.deputado_id = deputado_id

        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def delete_user(self, user_id: str) -> None:
        """Delete a parlamentar user permanently.

        Raises:
            NotFoundException: If the user is not found.
        """
        user = await self.get_user_by_id(user_id)
        if user is None:
            raise NotFoundException("Conta não encontrada.")
        await self.session.delete(user)
        await self.session.commit()

    async def list_pending_invites(self) -> list[ParlamentarUser]:
        """List all users with unused invitation codes."""
        result = await self.session.execute(
            select(ParlamentarUser)
            .where(
                ParlamentarUser.convite_usado == False,  # noqa: E712
                ParlamentarUser.codigo_convite.isnot(None),
            )
            .order_by(ParlamentarUser.created_at.desc())
        )
        return list(result.scalars().all())

    async def count_users(self) -> dict[str, int]:
        """Return summary counts of parlamentar users."""
        result = await self.session.execute(
            select(func.count(ParlamentarUser.id)).where(
                ParlamentarUser.ativo == True  # noqa: E712
            )
        )
        total_ativos = result.scalar() or 0

        result = await self.session.execute(
            select(func.count(ParlamentarUser.id)).where(
                ParlamentarUser.convite_usado == False,  # noqa: E712
                ParlamentarUser.codigo_convite.isnot(None),
            )
        )
        convites_pendentes = result.scalar() or 0

        result = await self.session.execute(
            select(func.count(ParlamentarUser.id))
        )
        total = result.scalar() or 0

        return {
            "total": total,
            "ativos": total_ativos,
            "convites_pendentes": convites_pendentes,
        }

    # ──────────────────────────────────────────────
    #  Email dispatch (Resend)
    # ──────────────────────────────────────────────

    async def _send_magic_link_email(
        self, to_email: str, nome: str, magic_link_url: str
    ) -> None:
        """Send a Magic Link email via Resend API."""
        if not settings.resend_api_key:
            logger.warning(
                "parlamentar.auth.resend_not_configured",
                detail="RESEND_API_KEY não configurada. Email não enviado.",
            )
            # In development, log the link for manual testing
            if settings.app_debug:
                logger.info(
                    "parlamentar.auth.magic_link_debug",
                    url=magic_link_url,
                )
            return

        resend.api_key = settings.resend_api_key

        try:
            resend.Emails.send(
                {
                    "from": settings.email_from,
                    "to": [to_email],
                    "subject": "Parlamentaria — Seu link de acesso",
                    "html": self._build_magic_link_html(nome, magic_link_url),
                }
            )
            logger.info("parlamentar.auth.email_sent", to=to_email)
        except Exception:
            logger.error(
                "parlamentar.auth.email_send_failed",
                to=to_email,
            )
            # Don't raise — login should still "succeed" to prevent enumeration
            return

    async def _send_invitation_email(
        self, to_email: str, nome: str, codigo_convite: str
    ) -> None:
        """Send an invitation email via Resend API."""
        if not settings.resend_api_key:
            logger.warning(
                "parlamentar.auth.resend_not_configured",
                detail="RESEND_API_KEY não configurada. Email de convite não enviado.",
            )
            if settings.app_debug:
                logger.info(
                    "parlamentar.auth.invitation_debug",
                    email=to_email,
                    codigo=codigo_convite,
                )
            return

        resend.api_key = settings.resend_api_key

        try:
            resend.Emails.send(
                {
                    "from": settings.email_from,
                    "to": [to_email],
                    "subject": "Parlamentaria — Você foi convidado(a) para o Dashboard",
                    "html": self._build_invitation_html(nome, codigo_convite),
                }
            )
            logger.info("parlamentar.auth.invitation_email_sent", to=to_email)
        except Exception:
            logger.error(
                "parlamentar.auth.invitation_email_failed",
                to=to_email,
            )
            # Don't raise — invitation was created successfully regardless of email
            return

    @staticmethod
    def _build_invitation_html(nome: str, codigo_convite: str) -> str:
        """Build HTML email body for invitation."""
        login_url = settings.dashboard_url + "/login"
        return f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #1a73e8;">Parlamentaria</h2>
            <p>Olá, <strong>{nome}</strong>!</p>
            <p>Você foi convidado(a) para acessar o <strong>Dashboard do Parlamentar</strong> —
               a plataforma de democracia participativa que conecta parlamentares à opinião popular.</p>
            <p>Para fazer seu primeiro acesso, siga os passos abaixo:</p>
            <ol style="line-height: 1.8;">
                <li>Acesse a página de login</li>
                <li>Informe seu email: <strong>{nome}</strong></li>
                <li>Informe o código de convite abaixo</li>
                <li>Clique em &ldquo;Enviar link de acesso&rdquo;</li>
                <li>Abra o link recebido por email</li>
            </ol>
            <div style="text-align: center; margin: 24px 0;">
                <div style="background-color: #f5f5f5; border: 2px dashed #1a73e8;
                            padding: 16px; border-radius: 8px; display: inline-block;">
                    <span style="font-family: monospace; font-size: 18px; letter-spacing: 1px;
                                 color: #1a73e8; font-weight: bold;">{codigo_convite}</span>
                </div>
                <p style="color: #666; font-size: 13px; margin-top: 8px;">Seu código de convite</p>
            </div>
            <div style="text-align: center; margin: 24px 0;">
                <a href="{login_url}"
                   style="background-color: #1a73e8; color: white; padding: 14px 28px;
                          text-decoration: none; border-radius: 6px; font-size: 16px;">
                    Acessar Dashboard
                </a>
            </div>
            <p style="color: #666; font-size: 14px;">
                Após o primeiro login, você poderá acessar usando apenas seu email —
                sem precisar do código novamente.
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;"/>
            <p style="color: #999; font-size: 12px;">
                Parlamentaria — Plataforma de democracia participativa
            </p>
        </div>
        """

    @staticmethod
    def _build_magic_link_html(nome: str, magic_link_url: str) -> str:
        """Build HTML email body for Magic Link."""
        return f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #1a73e8;">Parlamentaria</h2>
            <p>Olá, <strong>{nome}</strong>!</p>
            <p>Você solicitou acesso ao Dashboard do Parlamentar. Clique no botão abaixo para entrar:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{magic_link_url}"
                   style="background-color: #1a73e8; color: white; padding: 14px 28px;
                          text-decoration: none; border-radius: 6px; font-size: 16px;">
                    Acessar Dashboard
                </a>
            </div>
            <p style="color: #666; font-size: 14px;">
                Este link expira em {settings.magic_link_expire_minutes} minutos.<br/>
                Se você não solicitou este acesso, ignore este email.
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;"/>
            <p style="color: #999; font-size: 12px;">
                Parlamentaria — Plataforma de democracia participativa
            </p>
        </div>
        """
