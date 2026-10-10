"""add simulation run_number and name

Gives every simulation a permanent, human-friendly number (#1, #2, ...) and
an optional user-given name.

Existing simulations are numbered oldest-first, so the very first run you
ever made becomes #1. New runs continue from the highest number.

Revision ID: d4e1a7c2b9f0
Revises: cfa9abee5c71
Create Date: 2026-10-10 17:30:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "d4e1a7c2b9f0"
down_revision: Union[str, None] = "cfa9abee5c71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. A counter that Postgres increments for us
    op.execute("CREATE SEQUENCE IF NOT EXISTS simulations_run_number_seq")

    # 2. New columns (run_number starts nullable so we can fill old rows first)
    op.add_column("simulations", sa.Column("run_number", sa.Integer(), nullable=True))
    op.add_column("simulations", sa.Column("name", sa.String(length=120), nullable=True))

    # 3. Number the existing simulations oldest-first
    op.execute(
        """
        UPDATE simulations AS s
        SET run_number = numbered.rn
        FROM (
            SELECT id, ROW_NUMBER() OVER (ORDER BY created_at, id) AS rn
            FROM simulations
        ) AS numbered
        WHERE s.id = numbered.id
        """
    )

    # 4. Continue the counter after the highest number used
    op.execute(
        "SELECT setval('simulations_run_number_seq', "
        "COALESCE((SELECT MAX(run_number) FROM simulations), 0) + 1, false)"
    )

    # 5. New rows get the next number automatically; numbers are unique
    op.execute(
        "ALTER TABLE simulations ALTER COLUMN run_number "
        "SET DEFAULT nextval('simulations_run_number_seq')"
    )
    op.execute("ALTER SEQUENCE simulations_run_number_seq OWNED BY simulations.run_number")
    op.alter_column("simulations", "run_number", nullable=False)
    op.create_index("ix_simulations_run_number", "simulations", ["run_number"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_simulations_run_number", table_name="simulations")
    op.drop_column("simulations", "name")
    op.drop_column("simulations", "run_number")  # also drops the OWNED BY sequence
    op.execute("DROP SEQUENCE IF EXISTS simulations_run_number_seq")