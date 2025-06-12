from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Self

from sqlalchemy import (
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


# NOTE: these only matter when there are no adjustments made in the database.

DEFAULT_INTEREST_RATE_PERCENTAGE = 100
DEFAULT_PENALTY_THRESHOLD = -100
DEFAULT_PENALTY_MULTIPLIER_PERCENTAGE = 200

# TODO: allow for joint transactions?
#       dibbler allows joint transactions (e.g. buying more than one product at once, several people buying the same product, etc.)
#       instead of having the software split the transactions up, making them hard to reconnect,
#       maybe we should add some sort of joint transaction id field to allow multiple transactions to be grouped together?

_DYNAMIC_FIELDS: set[str] = {
    "amount",
    "interest_rate_percent",
    "penalty_multiplier_percent",
    "penalty_threshold",
    "per_product",
    "product_count",
    "product_id",
    "transfer_user_id",
}

_EXPECTED_FIELDS: dict[TransactionType, set[str]] = {
    TransactionType.ADD_PRODUCT: {"amount", "per_product", "product_count", "product_id"},
    TransactionType.ADJUST_BALANCE: {"amount"},
    TransactionType.ADJUST_INTEREST: {"interest_rate_percent"},
    TransactionType.ADJUST_PENALTY: {"penalty_multiplier_percent", "penalty_threshold"},
    TransactionType.ADJUST_STOCK: {"product_count", "product_id"},
    # TODO: remove amount from BUY_PRODUCT
    #       this requires modifications to user credit calculations
    TransactionType.BUY_PRODUCT: {"product_count", "product_id"},
    TransactionType.TRANSFER: {"amount", "transfer_user_id"},
}

assert all(x <= _DYNAMIC_FIELDS for x in _EXPECTED_FIELDS.values()), (
    "All expected fields must be part of _DYNAMIC_FIELDS."
)


def _transaction_type_field_constraints(
    transaction_type: TransactionType,
    expected_fields: set[str],
) -> CheckConstraint:
    unexpected_fields = _DYNAMIC_FIELDS - expected_fields

    expected_constraints = ["{} IS NOT NULL".format(field) for field in expected_fields]
    unexpected_constraints = ["{} IS NULL".format(field) for field in unexpected_fields]

    constraints = expected_constraints + unexpected_constraints

    # TODO: use sqlalchemy's `and_` and `or_` to build the constraints
    return CheckConstraint(
        f"type <> '{transaction_type}' OR ({' AND '.join(constraints)})",
        name=f"trx_type_{transaction_type.value}_expected_fields",
    )


class Transaction(Base):
    __table_args__ = (
        *[
            _transaction_type_field_constraints(transaction_type, expected_fields)
            for transaction_type, expected_fields in _EXPECTED_FIELDS.items()
        ],
        # Speed up product count calculation
        Index("product_user_time", "product_id", "user_id", "time"),
        # Speed up product owner calculation
        Index("user_product_time", "user_id", "product_id", "time"),
        # Speed up user transaction list / credit calculation
        Index("user_time", "user_id", "time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    """
        A unique identifier for the transaction.

        Not used for anything else than identifying the transaction in the database.
    """

    time: Mapped[datetime] = mapped_column(DateTime, unique=True)
    """
        The time when the transaction took place.

        This is used to order transactions chronologically, and to calculate
        all kinds of state.
    """

    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    """
        A message that can be set by the user to describe the reason
        behind the transaction (or potentially a place to write som fan fiction).

        This is not used for any calculations, but can be useful for debugging.
    """

    type_: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType), name="type")
    """
        Which type of transaction this is.

        The type determines which fields are expected to be set.
    """

    amount: Mapped[int | None] = mapped_column(Integer)
    """
        This field means different things depending on the transaction type:

         - `ADD_PRODUCT`: The real amount spent on the products.

         - `ADJUST_BALANCE`: The amount of credit to add or subtract from the user's balance.

         - `BUY_PRODUCT`: The amount of credit spent on the product.
                         Note that this includes any penalties and interest that the user
                         had to pay as well.

         - `TRANSFER`: The amount of balance to transfer to another user.
    """

    per_product: Mapped[int | None] = mapped_column(Integer)
    """
        If adding products, how much is each product worth

        Note that this is distinct from the total amount of the transaction,
        because this gets rounded up to the nearest integer, while the total amount
        that the user paid in the store would be stored in the `amount` field.
    """

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    """The user who performs the transaction. See `user` for more details."""
    user: Mapped[User] = relationship(
        lazy="joined",
        foreign_keys=[user_id],
    )
    """
        The user who performs the transaction.

        For some transaction types, like `TRANSFER` and `ADD_PRODUCT`, this is a
        functional field with "real world consequences" for price calculations.

        For others, like `ADJUST_PENALTY` and `ADJUST_STOCK`, this is just a record of who
        performed the transaction, and does not affect any state calculations.
    """

    # Receiving user when moving credit from one user to another
    transfer_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    """The user who receives money in a `TRANSFER` transaction."""
    transfer_user: Mapped[User | None] = relationship(
        lazy="joined",
        foreign_keys=[transfer_user_id],
    )
    """The user who receives money in a `TRANSFER` transaction."""

    # The product that is either being added or bought
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product.id"))
    """The product being added or bought."""
    product: Mapped[Product | None] = relationship(lazy="joined")
    """The product being added or bought."""

    # The amount of products being added or bought
    product_count: Mapped[int | None] = mapped_column(Integer)
    """
        The amount of products being added or bought.
    """

    penalty_threshold: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """
        On `ADJUST_PENALTY` transactions, this is the threshold in krs for when the user
        should start getting penalized for low credit.

        See also `penalty_multiplier`.
    """

    penalty_multiplier_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """
        On `ADJUST_PENALTY` transactions, this is the multiplier for the amount of
        money the user has to pay when they have too low credit.

        The multiplier is a percentage, so `100` means the user has to pay the full
        price of the product, `200` means they have to pay double, etc.

        See also `penalty_threshold`.
    """

    # TODO: this should be inferred
    # Assuming this is a BUY_PRODUCT transaction, was the user penalized for having
    # too low credit in this transaction?
    # is_penalized: Mapped[Boolean] = mapped_column(Boolean, default=False)

    interest_rate_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """
        On `ADJUST_INTEREST` transactions, this is the interest rate in percent
        that the user has to pay on their balance.

        The interest rate is a percentage, so `100` means the user has to pay the full
        price of the product, `200` means they have to pay double, etc.
    """

    def __init__(
        self: Self,
        type_: TransactionType,
        user_id: int,
        amount: int | None = None,
        time: datetime | None = None,
        message: str | None = None,
        product_id: int | None = None,
        transfer_user_id: int | None = None,
        per_product: int | None = None,
        product_count: int | None = None,
        penalty_threshold: int | None = None,
        penalty_multiplier_percent: int | None = None,
        interest_rate_percent: int | None = None,
    ) -> None:
        """
        Please do not call this constructor directly, use the factory methods instead.
        """
        if time is None:
            time = datetime.now()

        self.time = time
        self.message = message
        self.type_ = type_
        self.amount = amount
        self.user_id = user_id
        self.product_id = product_id
        self.transfer_user_id = transfer_user_id
        self.per_product = per_product
        self.product_count = product_count
        self.penalty_threshold = penalty_threshold
        self.penalty_multiplier_percent = penalty_multiplier_percent
        self.interest_rate_percent = interest_rate_percent

        self._validate_by_transaction_type()

    def _validate_by_transaction_type(self: Self) -> None:
        """
        Validates the transaction's fields based on its type.
        Raises `ValueError` if the transaction is invalid.
        """
        # TODO: do we allow free products?
        if self.amount == 0:
            raise ValueError("Amount must not be zero.")

        for field in _EXPECTED_FIELDS[self.type_]:
            if getattr(self, field) is None:
                raise ValueError(f"{field} must not be None for {self.type_.value} transactions.")

        for field in _DYNAMIC_FIELDS - _EXPECTED_FIELDS[self.type_]:
            if getattr(self, field) is not None:
                raise ValueError(f"{field} must be None for {self.type_.value} transactions.")

        if self.per_product is not None and self.per_product <= 0:
            raise ValueError("per_product must be greater than zero.")

        if (
            self.per_product is not None
            and self.product_count is not None
            and self.amount is not None
            and self.amount > self.per_product * self.product_count
        ):
            raise ValueError(
                "The real amount of the transaction must be less than the total value of the products."
            )

    ###################
    # FACTORY METHODS #
    ###################

    @classmethod
    def adjust_balance(
        cls: type[Self],
        amount: int,
        user_id: int,
        time: datetime | None = None,
        message: str | None = None,
    ) -> Transaction:
        return cls(
            time=time,
            type_=TransactionType.ADJUST_BALANCE,
            amount=amount,
            user_id=user_id,
            message=message,
        )

    @classmethod
    def adjust_interest(
        cls: type[Self],
        interest_rate_percent: int,
        user_id: int,
        time: datetime | None = None,
        message: str | None = None,
    ) -> Transaction:
        return cls(
            time=time,
            type_=TransactionType.ADJUST_INTEREST,
            interest_rate_percent=interest_rate_percent,
            user_id=user_id,
            message=message,
        )

    @classmethod
    def adjust_penalty(
        cls: type[Self],
        penalty_multiplier_percent: int,
        penalty_threshold: int,
        user_id: int,
        time: datetime | None = None,
        message: str | None = None,
    ) -> Transaction:
        return cls(
            time=time,
            type_=TransactionType.ADJUST_PENALTY,
            penalty_multiplier_percent=penalty_multiplier_percent,
            penalty_threshold=penalty_threshold,
            user_id=user_id,
            message=message,
        )

    @classmethod
    def adjust_stock(
        cls: type[Self],
        user_id: int,
        product_id: int,
        product_count: int,
        time: datetime | None = None,
        message: str | None = None,
    ) -> Transaction:
        return cls(
            time=time,
            type_=TransactionType.ADJUST_STOCK,
            user_id=user_id,
            product_id=product_id,
            product_count=product_count,
            message=message,
        )

    @classmethod
    def add_product(
        cls: type[Self],
        amount: int,
        user_id: int,
        product_id: int,
        per_product: int,
        product_count: int,
        time: datetime | None = None,
        message: str | None = None,
    ) -> Transaction:
        return cls(
            time=time,
            type_=TransactionType.ADD_PRODUCT,
            amount=amount,
            user_id=user_id,
            product_id=product_id,
            per_product=per_product,
            product_count=product_count,
            message=message,
        )

    @classmethod
    def buy_product(
        cls: type[Self],
        user_id: int,
        product_id: int,
        product_count: int,
        time: datetime | None = None,
        message: str | None = None,
    ) -> Transaction:
        return cls(
            time=time,
            type_=TransactionType.BUY_PRODUCT,
            user_id=user_id,
            product_id=product_id,
            product_count=product_count,
            message=message,
        )

    @classmethod
    def transfer(
        cls: type[Self],
        amount: int,
        user_id: int,
        transfer_user_id: int,
        time: datetime | None = None,
        message: str | None = None,
    ) -> Transaction:
        return cls(
            time=time,
            type_=TransactionType.TRANSFER,
            amount=amount,
            user_id=user_id,
            transfer_user_id=transfer_user_id,
            message=message,
        )
