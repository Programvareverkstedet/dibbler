from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Self

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
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
    from .Product import Product
    from .User import User

# TODO: allow for joint transactions?
#       dibbler allows joint transactions (e.g. buying more than one product at once, several people buying the same product, etc.)
#       instead of having the software split the transactions up, making them hard to reconnect,
#       maybe we should add some sort of joint transaction id field to allow multiple transactions to be grouped together?


class Transaction(Base):
    __table_args__ = (
        # TODO: embed everything from _validate_by_transaction_type into the constraints
        CheckConstraint(
            f"type != '{TransactionType.TRANSFER}' OR transfer_user_id IS NOT NULL",
            name="trx_type_transfer_required_fields",
        ),
        CheckConstraint(
            f"type != '{TransactionType.ADD_PRODUCT}' OR (product_id IS NOT NULL AND per_product IS NOT NULL AND product_count IS NOT NULL)",
            name="trx_type_add_product_required_fields",
        ),
        CheckConstraint(
            f"type != '{TransactionType.BUY_PRODUCT}' OR (product_id IS NOT NULL AND product_count IS NOT NULL)",
            name="trx_type_buy_product_required_fields",
        ),
        # Speed up product count calculation
        Index("product_user_time", "product_id", "user_id", "time"),
        # Speed up product owner calculation
        Index("user_product_time", "user_id", "product_id", "time"),
        # Speed up user transaction list / credit calculation
        Index("user_time", "user_id", "time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The type of transaction
    type: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType))

    # The amount of money being added or subtracted from the user's credit
    amount: Mapped[int] = mapped_column(Integer)

    # If buying products, is the user penalized for having too low credit?
    penalty: Mapped[Boolean] = mapped_column(Boolean, default=False)

    # If adding products, how much is each product worth
    per_product: Mapped[int | None] = mapped_column(Integer)

    # The user who performs the transaction
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    user: Mapped[User] = relationship(lazy="joined", foreign_keys=[user_id])

    # Receiving user when moving credit from one user to another
    transfer_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    transfer_user: Mapped[User | None] = relationship(
        lazy="joined", foreign_keys=[transfer_user_id]
    )

    # The product that is either being added or bought
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product.id"))
    product: Mapped[Product | None] = relationship(lazy="joined")

    # The amount of products being added or bought
    product_count: Mapped[int | None] = mapped_column(Integer)

    def __init__(
        self: Self,
        time: datetime,
        type: TransactionType,
        amount: int,
        user_id: int,
        message: str | None = None,
        product_id: int | None = None,
        transfer_user_id: int | None = None,
        per_product: int | None = None,
        product_count: int | None = None,
        # penalty: bool = False
    ) -> None:
        self.time = time
        self.message = message
        self.type = type
        self.amount = amount
        self.user_id = user_id
        self.product_id = product_id
        self.transfer_user_id = transfer_user_id
        self.per_product = per_product
        self.product_count = product_count
        # self.penalty = penalty

        self._validate_by_transaction_type()

    def _validate_by_transaction_type(self: Self) -> None:
        """
        Validates the transaction based on its type.
        Raises ValueError if the transaction is invalid.
        """
        match self.type:
            case TransactionType.ADJUST_BALANCE:
                if self.amount == 0:
                    raise ValueError("Amount must not be zero for ADJUST_BALANCE transactions.")

                if self.user_id is None:
                    raise ValueError("ADJUST_BALANCE transactions must have a user.")

                if self.product_id is not None:
                    raise ValueError("ADJUST_BALANCE transactions must not have a product.")

                if self.product_count is not None:
                    raise ValueError("ADJUST_BALANCE transactions must not have a product count.")

                if self.transfer_user_id is not None:
                    raise ValueError("ADJUST_BALANCE transactions must not have a transfer user.")

                if self.per_product is not None:
                    raise ValueError(
                        "ADJUST_BALANCE transactions must not have a per_product value."
                    )

            case TransactionType.ADJUST_STOCK:
                if self.amount == 0:
                    raise ValueError("Amount must not be zero for ADJUST_STOCK transactions.")

                if self.product_id is None:
                    raise ValueError("ADJUST_STOCK transactions must have a product.")

                if self.product_count is None:
                    raise ValueError("ADJUST_STOCK transactions must have a product count.")

                if self.transfer_user_id is not None:
                    raise ValueError("ADJUST_STOCK transactions must not have a transfer user.")

                if self.per_product is not None:
                    raise ValueError("ADJUST_STOCK transactions must not have a per_product value.")

            case TransactionType.TRANSFER:
                if self.amount == 0:
                    raise ValueError("Amount must not be zero for TRANSFER transactions.")

                if self.user_id is None:
                    raise ValueError("TRANSFER transactions must have a user.")

                if self.product_id is not None:
                    raise ValueError("TRANSFER transactions must not have a product.")

                if self.product_count is not None:
                    raise ValueError("TRANSFER transactions must not have a product count.")

                if self.transfer_user_id is None:
                    raise ValueError("TRANSFER transactions must have a transfer user.")

                if self.per_product is not None:
                    raise ValueError("TRANSFER transactions must not have a per_product value.")

            case TransactionType.ADD_PRODUCT:
                # TODO: do we allow free products?
                if self.amount == 0:
                    raise ValueError("Amount must not be zero for ADD_PRODUCT transactions.")

                if self.user_id is None:
                    raise ValueError("ADD_PRODUCT transactions must have a user.")

                if self.product_id is None:
                    raise ValueError("ADD_PRODUCT transactions must have a product.")

                if self.product_count is None:
                    raise ValueError("ADD_PRODUCT transactions must have a product count.")

                if self.transfer_user_id is not None:
                    raise ValueError("ADD_PRODUCT transactions must not have a transfer user.")

                if self.per_product is None:
                    raise ValueError("ADD_PRODUCT transactions must have a per_product value.")

                if self.per_product <= 0:
                    raise ValueError("per_product must be greater than zero.")

                if self.product_count <= 0:
                    raise ValueError("product_count must be greater than zero.")

                if self.amount > self.per_product * self.product_count:
                    raise ValueError(
                        "The real amount of the transaction must be less than the total value of the products."
                    )

            case TransactionType.BUY_PRODUCT:
                if self.amount == 0:
                    raise ValueError("Amount must not be zero for BUY_PRODUCT transactions.")

                if self.user_id is None:
                    raise ValueError("BUY_PRODUCT transactions must have a user.")

                if self.product_id is None:
                    raise ValueError("BUY_PRODUCT transactions must have a product.")

                if self.product_count is None:
                    raise ValueError("BUY_PRODUCT transactions must have a product count.")

                if self.transfer_user_id is not None:
                    raise ValueError("BUY_PRODUCT transactions must not have a transfer user.")

                if self.per_product is not None:
                    raise ValueError("BUY_PRODUCT transactions must not have a per_product value.")

            case _:
                raise ValueError(f"Unknown transaction type: {self.type}")

    def economy_difference(self: Self) -> int:
        """
        Returns the difference in economy caused by this transaction.
        """
        if self.type == TransactionType.ADJUST_BALANCE:
            return self.amount
        elif self.type == TransactionType.ADJUST_STOCK:
            return -self.amount
        elif self.type == TransactionType.TRANSFER:
            return 0
        elif self.type == TransactionType.ADD_PRODUCT:
            product_value = self.per_product * self.product_count
            return product_value - self.amount
        elif self.type == TransactionType.BUY_PRODUCT:
            return 0
        else:
            raise ValueError(f"Unknown transaction type: {self.type}")

    def adjust_balance(
        self: Self,
        amount: int,
        user_id: int,
        time: datetime | None = None,
        message: str | None = None,
    ) -> Transaction:
        """
        Creates an ADJUST transaction.
        """
        if time is None:
            time = datetime.now()

        return Transaction(
            time=time,
            type=TransactionType.ADJUST_BALANCE,
            amount=amount,
            user_id=user_id,
            message=message,
        )

    def transfer(
        self: Self,
        amount: int,
        user_id: int,
        transfer_user_id: int,
        time: datetime | None = None,
        message: str | None = None,
    ) -> Transaction:
        """
        Creates a TRANSFER transaction.
        """
        if time is None:
            time = datetime.now()

        return Transaction(
            time=time,
            type=TransactionType.TRANSFER,
            amount=amount,
            user_id=user_id,
            transfer_user_id=transfer_user_id,
            message=message,
        )

    def add_product(
        self: Self,
        amount: int,
        user_id: int,
        product_id: int,
        per_product: int,
        product_count: int,
        time: datetime | None = None,
        message: str | None = None,
    ) -> Transaction:
        """
        Creates an ADD_PRODUCT transaction.
        """
        if time is None:
            time = datetime.now()

        return Transaction(
            time=time,
            type=TransactionType.ADD_PRODUCT,
            amount=amount,
            user_id=user_id,
            product_id=product_id,
            per_product=per_product,
            product_count=product_count,
            message=message,
        )

    def buy_product(
        self: Self,
        amount: int,
        user_id: int,
        product_id: int,
        product_count: int,
        time: datetime | None = None,
        message: str | None = None,
    ) -> Transaction:
        """
        Creates a BUY_PRODUCT transaction.
        """
        if time is None:
            time = datetime.now()

        return Transaction(
            time=time,
            type=TransactionType.BUY_PRODUCT,
            amount=amount,
            user_id=user_id,
            product_id=product_id,
            product_count=product_count,
            message=message,
        )
