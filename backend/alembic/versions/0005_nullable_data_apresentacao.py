"""Make data_apresentacao nullable in proposicoes.

The Câmara dos Deputados API may return propositions without
data_apresentacao (null). This migration relaxes the NOT NULL constraint.

Revision ID: 0005_nullable_data_apresentacao
Revises: 0004_add_verification
Create Date: 2026-03-05
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_nullable_data_apresentacao"
down_revision: Union[str, None] = "0004_add_verification"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.alter_column(
        "proposicoes",
        "data_apresentacao",
        existing_type=sa.Date(),
        nullable=True,
    )


def downgrade() -> None:
    # Set a default date for any NULL values before making NOT NULL again
    op.execute(
        "UPDATE proposicoes SET data_apresentacao = '1970-01-01' "
        "WHERE data_apresentacao IS NULL"
    )
    op.alter_column(
        "proposicoes",
        "data_apresentacao",
        existing_type=sa.Date(),
        nullable=False,
    )
