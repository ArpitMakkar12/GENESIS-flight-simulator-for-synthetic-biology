"""add simulation expression_all

Stores every gene's expression prediction (about 1,500 per run) so the
results page can search all genes, not only the 50 most-changed ones.
Compact form: {gene_id: [fold, confidence, source, reference_tpm]}.
Older runs keep NULL here and fall back to their saved top 50.

Revision ID: e7b3c91d4a20
Revises: d4e1a7c2b9f0
Create Date: 2026-10-11 02:10:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e7b3c91d4a20"
down_revision: Union[str, None] = "d4e1a7c2b9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("simulations", sa.Column("expression_all", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("simulations", "expression_all")