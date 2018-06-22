"""empty message

Revision ID: 35795a8c3a4
Revises: 30066ed2e97
Create Date: 2014-12-11 14:30:22.435632

"""

# revision identifiers, used by Alembic.
revision = '35795a8c3a4'
down_revision = '30066ed2e97'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_index('blockheight', 'block', ['height'], unique=False)


def downgrade():
    raise Exception()
