from __future__ import annotations
from typing import TYPE_CHECKING

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    CheckConstraint
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql.schema import Index

from .Base import Base
from .TransactionType import TransactionType

if TYPE_CHECKING:
    from .User import User
    from .Product import Product

# TODO: allow for joint transactions?
#       dibbler allows joint transactions (e.g. buying more than one product at once, several people buying the same product, etc.)
#       instead of having the software split the transactions up, making them hard to reconnect,
#       maybe we should add some sort of joint transaction id field to allow multiple transactions to be grouped together?

class Transaction(Base):
    __table_args__ = (
        CheckConstraint(
            f'type != \'{TransactionType.TRANSFER}\' OR transfer_user_id IS NOT NULL',
            name='trx_type_transfer_required_fields',
        ),

        CheckConstraint(
            f'type != \'{TransactionType.ADD_PRODUCT}\' OR (product_id IS NOT NULL AND per_product IS NOT NULL AND product_count IS NOT NULL)',
            name='trx_type_add_product_required_fields',
        ),

        CheckConstraint(
            f'type != \'{TransactionType.BUY_PRODUCT}\' OR (product_id IS NOT NULL AND product_count IS NOT NULL)',
            name='trx_type_buy_product_required_fields',
        ),

        # Speed up product count calculation
        Index('product_user_time', 'product_id', 'user_id', 'time'),

        # Speed up product owner calculation
        Index('user_product_time', 'user_id', 'product_id', 'time'),

        # Speed up user transaction list / credit calculation
        Index('user_time', 'user_id', 'time'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime)

    # The type of transaction
    type: Mapped[TransactionType] = mapped_column(TransactionType)

    # The amount of money being added or subtracted from the user's credit
    amount: Mapped[int] = mapped_column(Integer)

    # If buying products, is the user penalized for having too low credit?
    penalty: Mapped[Boolean] = mapped_column(Boolean, default=False)

    # If adding products, how much is each product worth
    per_product: Mapped[int | None] = mapped_column(Integer)

    # The user who performs the transaction
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user : Mapped[User] = relationship(lazy="joined", foreign_keys=[user_id])

    # Receiving user when moving credit from one user to another
    transfer_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    transfer_user: Mapped[User | None] = relationship(lazy="joined", foreign_keys=[transfer_user_id])

    # The product that is either being added or bought
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product.id"))
    product: Mapped[Product | None] = relationship(lazy="joined")

    # The amount of products being added or bought
    product_count: Mapped[int | None] = mapped_column(Integer)

    # TODO: create a constructor for every transaction type (as well as a generic one)
