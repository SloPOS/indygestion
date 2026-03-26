"""initial

Revision ID: 001_initial
Revises:
Create Date: 2026-03-26
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    project_status_enum = sa.Enum("active", "review", "finished", "archiving", "archived", name="project_status_enum")
    ingest_source_enum = sa.Enum("web", "usb", "sd", name="ingest_source_enum")
    ingest_session_status_enum = sa.Enum("active", "complete", name="ingest_session_status_enum")
    proxy_status_enum = sa.Enum("pending", "processing", "ready", "failed", name="proxy_status_enum")
    clip_source_enum = sa.Enum("web_upload", "usb_ingest", "sd_ingest", name="clip_source_enum")
    clip_ingest_status_enum = sa.Enum(
        "uploading", "staged", "transcribing", "reviewing", "assigned", "archived", name="clip_ingest_status_enum"
    )
    job_type_enum = sa.Enum("proxy", "transcribe", "embed", "archive", name="job_type_enum")
    job_status_enum = sa.Enum("queued", "running", "completed", "failed", "cancelled", name="job_status_enum")
    file_operation_enum = sa.Enum("move", "copy", "delete", "archive", name="file_operation_enum")

    bind = op.get_bind()
    for enum_type in [
        project_status_enum,
        ingest_source_enum,
        ingest_session_status_enum,
        proxy_status_enum,
        clip_source_enum,
        clip_ingest_status_enum,
        job_type_enum,
        job_status_enum,
        file_operation_enum,
    ]:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", project_status_enum, nullable=False, server_default="active"),
        sa.Column("folder_path", sa.String(length=1024), nullable=True),
        sa.Column("archive_path", sa.String(length=1024), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("archive_preset", postgresql.JSONB(), nullable=True),
        sa.Column("estimated_archive_size", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_projects_id", "projects", ["id"])
    op.create_index("ix_projects_name", "projects", ["name"])
    op.create_index("ix_projects_status", "projects", ["status"])

    op.create_table(
        "ingest_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", ingest_source_enum, nullable=False),
        sa.Column("device_info", postgresql.JSONB(), nullable=True),
        sa.Column("clip_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("status", ingest_session_status_enum, nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ingest_sessions_id", "ingest_sessions", ["id"])
    op.create_index("ix_ingest_sessions_source", "ingest_sessions", ["source"])

    op.create_table(
        "clips",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ingest_session_id", sa.Integer(), sa.ForeignKey("ingest_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("original_path", sa.String(length=1024), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("resolution", sa.String(length=64), nullable=True),
        sa.Column("codec", sa.String(length=64), nullable=True),
        sa.Column("fps", sa.Float(), nullable=True),
        sa.Column("bitrate", sa.Integer(), nullable=True),
        sa.Column("proxy_path", sa.String(length=1024), nullable=True),
        sa.Column("proxy_status", proxy_status_enum, nullable=False, server_default="pending"),
        sa.Column("transcript_text", sa.Text(), nullable=True),
        sa.Column("transcript_json_path", sa.String(length=1024), nullable=True),
        sa.Column("embedding", Vector(dim=384), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=128), nullable=True),
        sa.Column("source", clip_source_enum, nullable=False, server_default="web_upload"),
        sa.Column("source_device", sa.String(length=255), nullable=True),
        sa.Column("ingest_status", clip_ingest_status_enum, nullable=False, server_default="uploading"),
        sa.Column("similarity_matches", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_clips_id", "clips", ["id"])
    op.create_index("ix_clips_project_id", "clips", ["project_id"])
    op.create_index("ix_clips_ingest_session_id", "clips", ["ingest_session_id"])
    op.create_index("ix_clips_ingest_status", "clips", ["ingest_status"])

    op.create_table(
        "ingest_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("clip_id", sa.Integer(), sa.ForeignKey("clips.id", ondelete="CASCADE"), nullable=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("job_type", job_type_enum, nullable=False),
        sa.Column("status", job_status_enum, nullable=False, server_default="queued"),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("worker_id", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ingest_jobs_id", "ingest_jobs", ["id"])
    op.create_index("ix_ingest_jobs_clip_id", "ingest_jobs", ["clip_id"])
    op.create_index("ix_ingest_jobs_project_id", "ingest_jobs", ["project_id"])
    op.create_index("ix_ingest_jobs_job_type", "ingest_jobs", ["job_type"])
    op.create_index("ix_ingest_jobs_status", "ingest_jobs", ["status"])

    op.create_table(
        "file_operations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("clip_id", sa.Integer(), sa.ForeignKey("clips.id", ondelete="SET NULL"), nullable=True),
        sa.Column("operation", file_operation_enum, nullable=False),
        sa.Column("source_path", sa.String(length=1024), nullable=False),
        sa.Column("dest_path", sa.String(length=1024), nullable=True),
        sa.Column("undone", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("performed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reversible_until", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_file_operations_id", "file_operations", ["id"])
    op.create_index("ix_file_operations_clip_id", "file_operations", ["clip_id"])

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=100), primary_key=True),
        sa.Column("value_type", sa.String(length=20), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_int", sa.Integer(), nullable=True),
        sa.Column("value_float", sa.Float(), nullable=True),
        sa.Column("value_bool", sa.Boolean(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_table("file_operations")
    op.drop_table("ingest_jobs")
    op.drop_table("clips")
    op.drop_table("ingest_sessions")
    op.drop_table("projects")

    bind = op.get_bind()
    for enum_name in [
        "file_operation_enum",
        "job_status_enum",
        "job_type_enum",
        "clip_ingest_status_enum",
        "clip_source_enum",
        "proxy_status_enum",
        "ingest_session_status_enum",
        "ingest_source_enum",
        "project_status_enum",
    ]:
        sa.Enum(name=enum_name).drop(bind, checkfirst=True)
