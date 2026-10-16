"""initial schema: stations, measurements, commands

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("station_uid", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("api_key_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_stations"),
        sa.UniqueConstraint("station_uid", name="uq_stations_station_uid"),
        sa.UniqueConstraint("api_key_hash", name="uq_stations_api_key_hash"),
    )
    op.create_index("ix_stations_station_uid", "stations", ["station_uid"])

    op.create_table(
        "measurements",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("station_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_measurements"),
        sa.ForeignKeyConstraint(
            ["station_id"],
            ["stations.id"],
            name="fk_measurements_stations",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_measurements_station_received", "measurements", ["station_id", "received_at"]
    )
    op.create_index("ix_measurements_received_at", "measurements", ["received_at"])

    op.create_table(
        "commands",
        sa.Column("uid", sa.String(length=36), nullable=False),
        sa.Column("station_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("uid", name="pk_commands"),
        sa.ForeignKeyConstraint(
            ["station_id"],
            ["stations.id"],
            name="fk_commands_stations",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_commands_station_status", "commands", ["station_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_commands_station_status", table_name="commands")
    op.drop_table("commands")
    op.drop_index("ix_measurements_received_at", table_name="measurements")
    op.drop_index("ix_measurements_station_received", table_name="measurements")
    op.drop_table("measurements")
    op.drop_index("ix_stations_station_uid", table_name="stations")
    op.drop_table("stations")
