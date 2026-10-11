"""add role-specific limited-seat event registration

Revision ID: 20261011_02
Revises: 20261011_01
"""
from alembic import op
import sqlalchemy as sa

revision = "20261011_02"
down_revision = "20261011_01"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("registration_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("faculty_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("rooms.id")),
        sa.Column("name", sa.String(), nullable=False), sa.Column("description", sa.Text()),
        sa.Column("starts_at", sa.DateTime(), nullable=False), sa.Column("registration_deadline", sa.DateTime()),
        sa.Column("capacity", sa.Integer(), nullable=False), sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("event_ticket_allocations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("registration_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("roll_number", sa.String(), nullable=False), sa.Column("participant_name", sa.String(), nullable=False),
        sa.Column("department", sa.String(), nullable=False), sa.Column("status", sa.String(), nullable=False, server_default="HELD"),
        sa.Column("booking_id", sa.String(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("expires_at", sa.DateTime()),
        sa.UniqueConstraint("event_id", "student_id", name="uq_event_student_ticket"),
        sa.UniqueConstraint("event_id", "roll_number", name="uq_event_roll_ticket"))

def downgrade():
    op.drop_table("event_ticket_allocations")
    op.drop_table("registration_events")
