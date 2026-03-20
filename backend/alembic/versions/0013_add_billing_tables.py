"""Add billing tables and plan fields for premium monetization.

Creates three new tables:
- billing_assinaturas: subscriptions (Stripe-backed, polymorphic FK)
- billing_api_keys: API SaaS keys (SHA-256 hashed, per-plan limits)
- billing_usage_records: per-request usage tracking

Alters existing tables:
- eleitores: adds plano, stripe_customer_id, billing_assinatura_id
- parlamentar_users: adds plano, stripe_customer_id, billing_assinatura_id, max_usuarios

Revision ID: 0013
Revises: 0012
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── billing_assinaturas ────────────────────────────────
    op.create_table(
        "billing_assinaturas",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tipo_assinante", sa.String(20), nullable=False),
        sa.Column("assinante_id", UUID(as_uuid=True), nullable=False),
        sa.Column("stripe_customer_id", sa.String(100), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(100), nullable=True),
        sa.Column("stripe_price_id", sa.String(100), nullable=False),
        sa.Column("plano_slug", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ATIVA"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancel_at_period_end", sa.Boolean, server_default="false"),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "idx_billing_assinaturas_assinante",
        "billing_assinaturas",
        ["tipo_assinante", "assinante_id"],
    )
    op.create_index(
        "idx_billing_stripe_subscription",
        "billing_assinaturas",
        ["stripe_subscription_id"],
        unique=True,
        postgresql_where=sa.text("stripe_subscription_id IS NOT NULL"),
    )

    # ── billing_api_keys ───────────────────────────────────
    op.create_table(
        "billing_api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("assinatura_id", UUID(as_uuid=True), sa.ForeignKey("billing_assinaturas.id"), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("plano", sa.String(20), nullable=False),
        sa.Column("ativo", sa.Boolean, server_default="true"),
        sa.Column("requests_mes_atual", sa.Integer, server_default="0"),
        sa.Column("max_requests_mes", sa.Integer, nullable=False),
        sa.Column("rate_limit_por_minuto", sa.Integer, nullable=False),
        sa.Column("ultimo_uso", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_api_keys_hash", "billing_api_keys", ["key_hash"])

    # ── billing_usage_records ──────────────────────────────
    op.create_table(
        "billing_usage_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("api_key_id", UUID(as_uuid=True), sa.ForeignKey("billing_api_keys.id"), nullable=False),
        sa.Column("endpoint", sa.String(200), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("response_status", sa.Integer, nullable=False),
        sa.Column("stripe_reported", sa.Boolean, server_default="false"),
    )
    op.create_index(
        "idx_usage_records_key_month",
        "billing_usage_records",
        ["api_key_id", "timestamp"],
    )
    op.create_index(
        "idx_usage_records_unreported",
        "billing_usage_records",
        ["stripe_reported"],
        postgresql_where=sa.text("stripe_reported = false"),
    )

    # ── Add billing columns to eleitores ───────────────────
    op.add_column("eleitores", sa.Column("plano", sa.String(20), server_default="GRATUITO", nullable=False))
    op.add_column("eleitores", sa.Column("stripe_customer_id", sa.String(100), nullable=True))
    op.add_column(
        "eleitores",
        sa.Column("billing_assinatura_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_unique_constraint("uq_eleitores_stripe_customer_id", "eleitores", ["stripe_customer_id"])

    # ── Add billing columns to parlamentar_users ───────────
    op.add_column("parlamentar_users", sa.Column("plano", sa.String(20), server_default="FREE", nullable=False))
    op.add_column("parlamentar_users", sa.Column("stripe_customer_id", sa.String(100), nullable=True))
    op.add_column(
        "parlamentar_users",
        sa.Column("billing_assinatura_id", UUID(as_uuid=True), nullable=True),
    )
    op.add_column("parlamentar_users", sa.Column("max_usuarios", sa.Integer, server_default="1", nullable=False))
    op.create_unique_constraint("uq_parlamentar_users_stripe_customer_id", "parlamentar_users", ["stripe_customer_id"])


def downgrade() -> None:
    # ── Remove billing columns from parlamentar_users ──────
    op.drop_constraint("uq_parlamentar_users_stripe_customer_id", "parlamentar_users", type_="unique")
    op.drop_column("parlamentar_users", "max_usuarios")
    op.drop_column("parlamentar_users", "billing_assinatura_id")
    op.drop_column("parlamentar_users", "stripe_customer_id")
    op.drop_column("parlamentar_users", "plano")

    # ── Remove billing columns from eleitores ──────────────
    op.drop_constraint("uq_eleitores_stripe_customer_id", "eleitores", type_="unique")
    op.drop_column("eleitores", "billing_assinatura_id")
    op.drop_column("eleitores", "stripe_customer_id")
    op.drop_column("eleitores", "plano")

    # ── Drop billing tables ────────────────────────────────
    op.drop_table("billing_usage_records")
    op.drop_table("billing_api_keys")
    op.drop_table("billing_assinaturas")
