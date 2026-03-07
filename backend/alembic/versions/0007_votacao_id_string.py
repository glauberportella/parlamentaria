"""Change votacoes.id from Integer to String(50).

The Câmara API returns votação IDs as strings like '2485246-28',
not integers. This migration alters the primary key and the
foreign key in comparativos_votacao to match.

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Convert votacoes.id and comparativos_votacao.votacao_camara_id to String(50)."""
    # 1. Drop FK constraint on comparativos_votacao referencing votacoes.id
    op.drop_constraint(
        "comparativos_votacao_votacao_camara_id_fkey",
        "comparativos_votacao",
        type_="foreignkey",
    )

    # 2. Alter votacoes.id from Integer to String(50)
    #    PostgreSQL requires USING clause to cast existing int values to text
    op.execute(
        'ALTER TABLE votacoes ALTER COLUMN id TYPE VARCHAR(50) USING id::VARCHAR(50)'
    )

    # 3. Alter comparativos_votacao.votacao_camara_id from Integer to String(50)
    op.execute(
        'ALTER TABLE comparativos_votacao ALTER COLUMN votacao_camara_id '
        'TYPE VARCHAR(50) USING votacao_camara_id::VARCHAR(50)'
    )

    # 4. Re-create FK constraint
    op.create_foreign_key(
        "comparativos_votacao_votacao_camara_id_fkey",
        "comparativos_votacao",
        "votacoes",
        ["votacao_camara_id"],
        ["id"],
    )


def downgrade() -> None:
    """Revert votacoes.id and comparativos_votacao.votacao_camara_id to Integer."""
    op.drop_constraint(
        "comparativos_votacao_votacao_camara_id_fkey",
        "comparativos_votacao",
        type_="foreignkey",
    )

    # Revert: this may fail if non-numeric IDs exist in the table
    op.execute(
        'ALTER TABLE votacoes ALTER COLUMN id TYPE INTEGER USING id::INTEGER'
    )
    op.execute(
        'ALTER TABLE comparativos_votacao ALTER COLUMN votacao_camara_id '
        'TYPE INTEGER USING votacao_camara_id::INTEGER'
    )

    op.create_foreign_key(
        "comparativos_votacao_votacao_camara_id_fkey",
        "comparativos_votacao",
        "votacoes",
        ["votacao_camara_id"],
        ["id"],
    )
