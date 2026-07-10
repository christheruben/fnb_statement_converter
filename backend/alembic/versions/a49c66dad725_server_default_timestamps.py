"""server default timestamps

Revision ID: a49c66dad725
Revises: 39ca197b9970
Create Date: 2026-03-09 11:27:59.339880

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a49c66dad725'
down_revision: Union[str, Sequence[str], None] = '39ca197b9970'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.alter_column('accounts', 'created_at',
        server_default=sa.func.now())
    op.alter_column('statements', 'uploaded_at',
        server_default=sa.func.now())


def downgrade() -> None:
    op.alter_column('accounts', 'created_at',
        server_default=None)
    op.alter_column('statements', 'uploaded_at',
        server_default=None)