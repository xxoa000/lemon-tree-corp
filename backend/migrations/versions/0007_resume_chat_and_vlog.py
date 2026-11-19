"""resume chat and vlog

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """이 리비전의 스키마 변경을 적용합니다."""
    op.create_table(
        "resumes",
        sa.Column("owner_id", sa.Integer(), nullable=False, comment="소유 계정 ID"),
        sa.Column(
            "filename",
            sa.String(length=255),
            nullable=False,
            comment="업로드한 파일 이름",
        ),
        sa.Column(
            "original",
            sa.LargeBinary().with_variant(mysql.MEDIUMBLOB(), "mysql"),
            nullable=False,
            comment="원본 PDF 또는 TXT",
        ),
        sa.Column(
            "content",
            sa.Text().with_variant(mysql.MEDIUMTEXT(), "mysql"),
            nullable=False,
            comment="확인 및 수정 가능한 이력서 텍스트",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["accounts.id"],
        ),
        sa.PrimaryKeyConstraint("owner_id"),
    )
    op.create_table(
        "talk_rooms",
        sa.Column("id", sa.Integer(), nullable=False, comment="대화방 ID"),
        sa.Column("owner_id", sa.Integer(), nullable=False, comment="대화방 관리자"),
        sa.Column(
            "name", sa.String(length=80), nullable=False, comment="팀 대화방 이름"
        ),
        sa.Column("team", sa.String(length=40), nullable=True, comment="대화방의 팀"),
        sa.Column(
            "dm_key",
            sa.String(length=64),
            nullable=True,
            comment="DM 참여자 쌍의 고유 키",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["accounts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dm_key"),
    )
    op.create_table(
        "vlog_posts",
        sa.Column("id", sa.Integer(), nullable=False, comment="게시글 ID"),
        sa.Column("author_id", sa.Integer(), nullable=False, comment="작성 계정 ID"),
        sa.Column("title", sa.String(length=120), nullable=False, comment="글 제목"),
        sa.Column("body", sa.Text(), nullable=False, comment="Markdown 글 본문"),
        sa.Column(
            "created_at", sa.String(length=32), nullable=False, comment="등록 UTC 시각"
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["accounts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "talk_members",
        sa.Column("room_id", sa.Integer(), nullable=False, comment="대화방 ID"),
        sa.Column("account_id", sa.Integer(), nullable=False, comment="참여 계정 ID"),
        sa.Column(
            "joined_after",
            sa.Integer(),
            nullable=False,
            comment="참여 전에 존재한 마지막 메시지 ID",
        ),
        sa.Column(
            "last_read",
            sa.Integer(),
            nullable=False,
            comment="마지막으로 확인한 메시지 ID",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["talk_rooms.id"],
        ),
        sa.PrimaryKeyConstraint("room_id", "account_id"),
    )
    with op.batch_alter_table("talk_members", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_talk_members_account_id"), ["account_id"], unique=False
        )

    op.create_table(
        "talk_messages",
        sa.Column("id", sa.Integer(), nullable=False, comment="메시지 ID"),
        sa.Column("room_id", sa.Integer(), nullable=False, comment="대화방 ID"),
        sa.Column("sender", sa.Integer(), nullable=False, comment="보낸 계정 ID"),
        sa.Column("body", sa.Text(), nullable=False, comment="메시지 본문"),
        sa.Column(
            "sent_at",
            sa.String(length=32),
            nullable=False,
            comment="메시지 전송 UTC 시각",
        ),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["talk_rooms.id"],
        ),
        sa.ForeignKeyConstraint(
            ["sender"],
            ["accounts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("talk_messages", schema=None) as batch_op:
        batch_op.create_index(
            "ix_talk_messages_room_id_id", ["room_id", "id"], unique=False
        )


def downgrade() -> None:
    """새 기능의 테이블을 제거합니다."""
    for table in (
        "talk_messages",
        "talk_members",
        "vlog_posts",
        "talk_rooms",
        "resumes",
    ):
        op.drop_table(table)
