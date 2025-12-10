from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Self

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    and_,
    column,
    func,
    or_,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.orm.collections import (
    InstrumentedDict,
    InstrumentedList,
    InstrumentedSet,
)
from sqlalchemy.sql.schema import Index

from .Base import Base
from .TransactionType import TransactionType, TransactionTypeSQL

if TYPE_CHECKING:
    from .Product import Product
    from .User import User

# NOTE: these only matter when there are no adjustments made in the database.
DEFAULT_INTEREST_RATE_PERCENT = 100
DEFAULT_PENALTY_THRESHOLD = -100
DEFAULT_PENALTY_MULTIPLIER_PERCENT = 200

_DYNAMIC_FIELDS: set[str] = {
    "amount",
    "interest_rate_percent",
    "joint_transaction_id",
    "penalty_multiplier_percent",
    "penalty_threshold",
    "per_product",
    "product_count",
    "product_id",
    "transfer_user_id",
}

EXPECTED_FIELDS: dict[TransactionType, set[str]] = {
    TransactionType.ADD_PRODUCT: {"amount", "per_product", "product_count", "product_id"},
    TransactionType.ADJUST_BALANCE: {"amount"},
    TransactionType.ADJUST_INTEREST: {"interest_rate_percent"},
    TransactionType.ADJUST_PENALTY: {"penalty_multiplier_percent", "penalty_threshold"},
    TransactionType.ADJUST_STOCK: {"product_count", "product_id"},
    TransactionType.BUY_PRODUCT: {"product_count", "product_id"},
    TransactionType.JOINT: {"product_count", "product_id"},
    TransactionType.JOINT_BUY_PRODUCT: {"joint_transaction_id"},
    TransactionType.THROW_PRODUCT: {"product_count", "product_id"},
    TransactionType.TRANSFER: {"amount", "transfer_user_id"},
}

assert all(x <= _DYNAMIC_FIELDS for x in EXPECTED_FIELDS.values()), (
    "All expected fields must be part of _DYNAMIC_FIELDS."
)


def _transaction_type_field_constraints(
    transaction_type: TransactionType,
    expected_fields: set[str],
) -> CheckConstraint:
    unexpected_fields = _DYNAMIC_FIELDS - expected_fields

    return CheckConstraint(
        or_(
            column("type") != transaction_type.value,
            and_(
                *[column(field).is_not(None) for field in expected_fields],
                *[column(field).is_(None) for field in unexpected_fields],
            ),
        ),
        name=f"trx_type_{transaction_type.value}_expected_fields",
    )


class Transaction(Base):
    __table_args__ = (
        *[
            _transaction_type_field_constraints(transaction_type, expected_fields)
            for transaction_type, expected_fields in EXPECTED_FIELDS.items()
        ],
        CheckConstraint(
            or_(
                column("type") != TransactionType.TRANSFER.value,
                column("user_id") != column("transfer_user_id"),
            ),
            name="trx_type_transfer_no_self_transfers",
        ),
        CheckConstraint(
            func.coalesce(column("product_count"), 1) != 0,
            name="trx_product_count_non_zero",
        ),
        CheckConstraint(
            func.coalesce(column("penalty_multiplier_percent"), 100) >= 100,
            name="trx_penalty_multiplier_percent_min_100",
        ),
        CheckConstraint(
            func.coalesce(column("interest_rate_percent"), 0) >= 0,
            name="trx_interest_rate_percent_non_negative",
        ),
        CheckConstraint(
            func.coalesce(column("amount"), 1) != 0,
            name="trx_amount_non_zero",
        ),
        CheckConstraint(
            func.coalesce(column("per_product"), 1) > 0,
            name="trx_per_product_positive",
        ),
        CheckConstraint(
            func.coalesce(column("penalty_threshold"), 0) <= 0,
            name="trx_penalty_threshold_max_0",
        ),
        CheckConstraint(
            or_(
                column("joint_transaction_id").is_(None),
                column("joint_transaction_id") != column("id"),
            ),
            name="trx_joint_transaction_id_not_self",
        ),
        # Speed up product stock calculation
        Index("ix__transaction__product_id_type_time", "product_id", "type", "time"),
        # Speed up product owner calculation
        Index("ix__transaction__user_id_product_time", "user_id", "product_id", "time"),
        # Speed up user transaction list / credit calculation
        Index("ix__transaction__user_id_time", "user_id", "time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    """
        A unique identifier for the transaction.

        Not used for anything else than identifying the transaction in the database.
    """

    time: Mapped[datetime] = mapped_column(DateTime, index=True)
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

    type_: Mapped[TransactionType] = mapped_column(TransactionTypeSQL, name="type", index=True)
    """
        Which type of transaction this is.

        The type determines which fields are expected to be set.
    """

    amount: Mapped[int | None] = mapped_column(Integer)
    """
        This field means different things depending on the transaction type:

         - `ADD_PRODUCT`: The real amount spent on the products.

         - `ADJUST_BALANCE`: The amount of credit to add or subtract from the user's balance.

         - `TRANSFER`: The amount of balance to transfer to another user.
    """

    per_product: Mapped[int | None] = mapped_column(Integer)
    """
        If adding products, how much is each product worth

        Note that this is distinct from the total amount of the transaction,
        because this gets rounded up to the nearest integer, while the total amount
        that the user paid in the store would be stored in the `amount` field.
    """

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
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

        In the case of `JOINT` transactions, this is the user who initiated the joint transaction.
    """

    joint_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transaction.id"),
        index=True,
    )
    """
    An optional ID to group multiple transactions together as part of a joint transaction.

    This is used for `JOINT` and `JOINT_BUY_PRODUCT` transactions, where multiple users
    are involved in a single transaction.
    """
    joint_transaction: Mapped[Transaction | None] = relationship(
        lazy="joined",
        foreign_keys=[joint_transaction_id],
    )
    """
    The joint transaction that this transaction is part of, if any.
    """

    # Receiving user when moving credit from one user to another
    transfer_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), index=True)
    """The user who receives money in a `TRANSFER` transaction."""
    transfer_user: Mapped[User | None] = relationship(
        lazy="joined",
        foreign_keys=[transfer_user_id],
    )
    """The user who receives money in a `TRANSFER` transaction."""

    # The product that is either being added or bought
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product.id"), index=True)
    """The product being added or bought."""
    product: Mapped[Product | None] = relationship(lazy="joined")
    """The product being added or bought."""

    # The amount of products being added or bought
    product_count: Mapped[int | None] = mapped_column(Integer)
    """
        The amount of products being added or bought.

        This is always relative to the existing stock.

        - `ADD_PRODUCT` increases the stock by this amount.

        - `BUY_PRODUCT` decreases the stock by this amount.

        - `ADJUST_STOCK` increases or decreases the stock by this amount,
          depending on whether the amount is positive or negative.
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

    interest_rate_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """
        On `ADJUST_INTEREST` transactions, this is the interest rate in percent
        that the user has to pay on their balance.

        The interest rate is a percentage, so `100` means the user has to pay the full
        price of the product, `200` means they have to pay double, etc.
    """

    economy_spec_version: Mapped[int] = mapped_column(Integer, default=1)
    """
        The version of the economy specification that this transaction adheres to.

        This is used to handle changes in the economy rules over time.
    """

    def __init__(
        self: Self,
        type_: TransactionType,
        user_id: int,
        amount: int | None = None,
        interest_rate_percent: int | None = None,
        joint_transaction_id: int | None = None,
        message: str | None = None,
        penalty_multiplier_percent: int | None = None,
        penalty_threshold: int | None = None,
        per_product: int | None = None,
        product_count: int | None = None,
        product_id: int | None = None,
        time: datetime | None = None,
        transfer_user_id: int | None = None,
    ) -> None:
        """
        Please do not call this constructor directly, use the factory methods instead.
        """
        if time is None:
            time = datetime.now()

        self.amount = amount
        self.interest_rate_percent = interest_rate_percent
        self.joint_transaction_id = joint_transaction_id
        self.message = message
        self.penalty_multiplier_percent = penalty_multiplier_percent
        self.penalty_threshold = penalty_threshold
        self.per_product = per_product
        self.product_count = product_count
        self.product_id = product_id
        self.time = time
        self.transfer_user_id = transfer_user_id
        self.type_ = type_
        self.user_id = user_id

        self._validate_by_transaction_type()

    def _validate_by_transaction_type(self: Self) -> None:
        """
        Validates the transaction's fields based on its type.
        Raises `ValueError` if the transaction is invalid.
        """
        if self.amount == 0:
            raise ValueError("Amount must not be zero.")

        for field in EXPECTED_FIELDS[self.type_]:
            if getattr(self, field) is None:
                raise ValueError(f"{field} must not be None for {self.type_.value} transactions.")

        for field in _DYNAMIC_FIELDS - EXPECTED_FIELDS[self.type_]:
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
                "The real amount of the transaction must be less than the total value of the products.",
            )

    # TODO: improve printing further

    def __repr__(self) -> str:
        sort_order = [
            "id",
            "time",
        ]

        columns = ", ".join(
            f"{k}={repr(v)}"
            for k, v in sorted(
                self.__dict__.items(),
                key=lambda item: chr(sort_order.index(item[0]))
                if item[0] in sort_order
                else item[0],
            )
            if not any(
                [
                    k == "type_",
                    (k == "message" and v is None),
                    k.startswith("_"),
                    # Ensure that we don't try to print out the entire list of
                    # relationships, which could create an infinite loop
                    isinstance(v, Base),
                    isinstance(v, InstrumentedList),
                    isinstance(v, InstrumentedSet),
                    isinstance(v, InstrumentedDict),
                    *[k in (_DYNAMIC_FIELDS - EXPECTED_FIELDS[self.type_])],
                ],
            )
        )
        return f"{self.type_.upper()}({columns})"

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
    ) -> Self:
        """
        Convenience constructor for creating an `ADJUST_BALANCE` transaction.

        Should NOT be used directly in the application code; use the various queries instead.
        """
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
    ) -> Self:
        """
        Convenience constructor for creating an `ADJUST_INTEREST` transaction.

        Note that the `interest_rate_percent` is absolute, not relative to the previous interest rate.

        Should NOT be used directly in the application code; use the various queries instead.
        """

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
    ) -> Self:
        """
        Convenience constructor for creating an `ADJUST_PENALTY` transaction.

        Note that both `penalty_multiplier_percent` and `penalty_threshold` are absolute,
        not relative to the previous settings.

        Should NOT be used directly in the application code; use the various queries instead.
        """
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
    ) -> Self:
        """
        Convenience constructor for creating an `ADJUST_STOCK` transaction.

        Should NOT be used directly in the application code; use the various queries instead.
        """
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
    ) -> Self:
        """
        Convenience constructor for creating an `ADD_PRODUCT` transaction.

        Should NOT be used directly in the application code; use the various queries instead.
        """
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
    ) -> Self:
        """
        Convenience constructor for creating a `BUY_PRODUCT` transaction.

        Should NOT be used directly in the application code; use the various queries instead.
        """
        return cls(
            time=time,
            type_=TransactionType.BUY_PRODUCT,
            user_id=user_id,
            product_id=product_id,
            product_count=product_count,
            message=message,
        )

    @classmethod
    def joint(
        cls: type[Self],
        user_id: int,
        product_id: int,
        product_count: int,
        time: datetime | None = None,
        message: str | None = None,
    ) -> Self:
        """
        Convenience constructor for creating a `JOINT` transaction.

        Should NOT be used directly in the application code; use the various queries instead.
        """
        return cls(
            time=time,
            type_=TransactionType.JOINT,
            user_id=user_id,
            product_id=product_id,
            product_count=product_count,
            message=message,
        )

    @classmethod
    def joint_buy_product(
        cls: type[Self],
        joint_transaction_id: int,
        user_id: int,
        time: datetime | None = None,
        message: str | None = None,
    ) -> Self:
        """
        Convenience constructor for creating a `JOINT_BUY_PRODUCT` transaction.

        Should NOT be used directly in the application code; use the various queries instead.
        """
        return cls(
            time=time,
            type_=TransactionType.JOINT_BUY_PRODUCT,
            joint_transaction_id=joint_transaction_id,
            user_id=user_id,
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
    ) -> Self:
        """
        Convenience constructor for creating a `TRANSFER` transaction.

        Should NOT be used directly in the application code; use the various queries instead.
        """
        return cls(
            time=time,
            type_=TransactionType.TRANSFER,
            amount=amount,
            user_id=user_id,
            transfer_user_id=transfer_user_id,
            message=message,
        )

    @classmethod
    def throw_product(
        cls: type[Self],
        user_id: int,
        product_id: int,
        product_count: int,
        time: datetime | None = None,
        message: str | None = None,
    ) -> Self:
        """
        Convenience constructor for creating a `THROW_PRODUCT` transaction.

        Should NOT be used directly in the application code; use the various queries instead.
        """
        return cls(
            time=time,
            type_=TransactionType.THROW_PRODUCT,
            user_id=user_id,
            product_id=product_id,
            product_count=product_count,
            message=message,
        )
