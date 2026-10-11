"""add amenities booking tables

Revision ID: 20261011_01
Revises:
Create Date: 2026-10-11
"""
from alembic import op
import sqlalchemy as sa

revision = "20261011_01"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("amenities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("resource_kind", sa.String(), nullable=False, server_default="EQUIPMENT"),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("capacity", sa.Integer()), sa.Column("location", sa.String()),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(), nullable=False, server_default="AVAILABLE"))
    op.create_index("ix_amenities_category", "amenities", ["category"])
    op.create_table("amenity_bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("amenity_id", sa.Integer(), sa.ForeignKey("amenities.id"), nullable=False),
        sa.Column("requester_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False), sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING_FACULTY_APPROVAL"),
        sa.Column("decision_comment", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("decided_at", sa.DateTime(timezone=True)))

def downgrade():
    op.drop_table("amenity_bookings")
    op.drop_index("ix_amenities_category", table_name="amenities")
    op.drop_table("amenities")
