"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
"""

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    """이 리비전의 스키마 변경을 적용합니다."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """이 리비전의 스키마 변경을 되돌립니다."""
    ${downgrades if downgrades else "pass"}
