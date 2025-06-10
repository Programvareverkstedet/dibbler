from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Self

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    asc,
    case,
    cast,
    func,
    literal,
    select,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import (
    Mapped,
    Session,
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

_DYNAMIC_FIELDS: set[str] = {
    "per_product",
    "user_id",
    "transfer_user_id",
    "product_id",
    "product_count",
}

_EXPECTED_FIELDS: dict[TransactionType, set[str]] = {
    TransactionType.ADJUST_BALANCE: {"user_id"},
    TransactionType.ADJUST_STOCK: {"user_id", "product_id", "product_count"},
    TransactionType.TRANSFER: {"user_id", "transfer_user_id"},
    TransactionType.ADD_PRODUCT: {"user_id", "product_id", "per_product", "product_count"},
    TransactionType.BUY_PRODUCT: {"user_id", "product_id", "product_count"},
}


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
    time: Mapped[datetime] = mapped_column(DateTime, unique=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The type of transaction
    type_: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType), name="type")

    # TODO: this should be inferred
    # If buying products, is the user penalized for having too low credit?
    # penalty: Mapped[Boolean] = mapped_column(Boolean, default=False)

    # The amount of money being added or subtracted from the user's credit
    # This amount means different things depending on the transaction type:
    #  - ADJUST_BALANCE: The amount of credit to add or subtract from the user's balance
    #  - ADJUST_STOCK: The amount of money which disappeared with this stock adjustment
    #                  (i.e. current price * product_count)
    #  - TRANSFER: The amount of credit to transfer to another user
    #  - ADD_PRODUCT: The real amount spent on the products
    #                 (i.e. not per_product * product_count, which should be rounded up)
    #  - BUY_PRODUCT: The amount of credit spent on the product
    amount: Mapped[int] = mapped_column(Integer)

    # If adding products, how much is each product worth
    per_product: Mapped[int | None] = mapped_column(Integer)

    # The user who performs the transaction
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    user: Mapped[User | None] = relationship(
        lazy="joined",
        foreign_keys=[user_id],
    )

    # Receiving user when moving credit from one user to another
    transfer_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    transfer_user: Mapped[User | None] = relationship(
        lazy="joined",
        foreign_keys=[transfer_user_id],
    )

    # The product that is either being added or bought
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product.id"))
    product: Mapped[Product | None] = relationship(lazy="joined")

    # The amount of products being added or bought
    product_count: Mapped[int | None] = mapped_column(Integer)

    def __init__(
        self: Self,
        type_: TransactionType,
        user_id: int,
        amount: int,
        time: datetime | None = None,
        message: str | None = None,
        product_id: int | None = None,
        transfer_user_id: int | None = None,
        per_product: int | None = None,
        product_count: int | None = None,
        # penalty: bool = False
    ) -> None:
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
        # self.penalty = penalty

        self._validate_by_transaction_type()

    def _validate_by_transaction_type(self: Self) -> None:
        """
        Validates the transaction based on its type.
        Raises ValueError if the transaction is invalid.
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
        """
        Creates an ADJUST transaction.
        """
        return cls(
            time=time,
            type_=TransactionType.ADJUST_BALANCE,
            amount=amount,
            user_id=user_id,
            message=message,
        )

    @classmethod
    def adjust_stock(
        cls: type[Self],
        amount: int,
        user_id: int,
        product_id: int,
        product_count: int,
        time: datetime | None = None,
        message: str | None = None,
    ) -> Transaction:
        """
        Creates an ADJUST_STOCK transaction.
        """
        return cls(
            time=time,
            type_=TransactionType.ADJUST_STOCK,
            amount=amount,
            user_id=user_id,
            product_id=product_id,
            product_count=product_count,
            message=message,
        )

    @classmethod
    def adjust_stock_auto_amount(
        cls: type[Self],
        sql_session: Session,
        user_id: int,
        product_id: int,
        product_count: int,
        time: datetime | None = None,
        message: str | None = None,
    ) -> Transaction:
        """
        Creates an ADJUST_STOCK transaction with the amount automatically calculated based on the product's current price.
        """
        from .Product import Product

        product = sql_session.scalar(select(Product).where(Product.id == product_id))
        if product is None:
            raise ValueError(f"Product with id {product_id} does not exist.")

        price = product.price(sql_session)

        return cls(
            time=time,
            type_=TransactionType.ADJUST_STOCK,
            amount=price * product_count,
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
        """
        Creates a TRANSFER transaction.
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
        """
        Creates an ADD_PRODUCT transaction.
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
        return cls(
            time=time,
            type_=TransactionType.BUY_PRODUCT,
            amount=amount,
            user_id=user_id,
            product_id=product_id,
            product_count=product_count,
            message=message,
        )

    @classmethod
    def buy_product_auto_amount(
        cls: type[Self],
        sql_session: Session,
        user_id: int,
        product_id: int,
        product_count: int,
        time: datetime | None = None,
        message: str | None = None,
    ) -> Transaction:
        """
        Creates a BUY_PRODUCT transaction with the amount automatically calculated based on the product's current price.
        """
        from .Product import Product

        product = sql_session.scalar(select(Product).where(Product.id == product_id))
        if product is None:
            raise ValueError(f"Product with id {product_id} does not exist.")

        price = product.price(sql_session)

        return cls(
            time=time,
            type_=TransactionType.BUY_PRODUCT,
            amount=price * product_count,
            user_id=user_id,
            product_id=product_id,
            product_count=product_count,
            message=message,
        )

    ############################
    # USER BALANCE CALCULATION #
    ############################

    @staticmethod
    def _user_balance_query(
        user: User,
        # until: datetime | None = None,
    ):
        """
        The inner query for calculating the user's balance.
        This is used both directly via user_balance() and in Transaction CHECK constraints.
        """

        balance_adjustments = (
            select(func.coalesce(func.sum(Transaction.amount).label("balance_adjustments"), 0))
            .where(
                Transaction.user_id == user.id,
                Transaction.type_ == TransactionType.ADJUST_BALANCE,
            )
            .scalar_subquery()
        )

        transfers_to_other_users = (
            select(func.coalesce(func.sum(Transaction.amount).label("transfers_to_other_users"), 0))
            .where(
                Transaction.user_id == user.id,
                Transaction.type_ == TransactionType.TRANSFER,
            )
            .scalar_subquery()
        )

        transfers_to_self = (
            select(func.coalesce(func.sum(Transaction.amount).label("transfers_to_self"), 0))
            .where(
                Transaction.transfer_user_id == user.id,
                Transaction.type_ == TransactionType.TRANSFER,
            )
            .scalar_subquery()
        )

        add_products = (
            select(func.coalesce(func.sum(Transaction.amount).label("add_products"), 0))
            .where(
                Transaction.user_id == user.id,
                Transaction.type_ == TransactionType.ADD_PRODUCT,
            )
            .scalar_subquery()
        )

        buy_products = (
            select(func.coalesce(func.sum(Transaction.amount).label("buy_products"), 0))
            .where(
                Transaction.user_id == user.id,
                Transaction.type_ == TransactionType.BUY_PRODUCT,
            )
            .scalar_subquery()
        )

        query = select(
            # TODO: clearly define and fix the sign of the amount
            (
                0
                + balance_adjustments
                - transfers_to_other_users
                + transfers_to_self
                + add_products
                - buy_products
            ).label("credit")
        )

        return query

    @staticmethod
    def user_balance(
        sql_session: Session,
        user: User,
        # Optional: calculate the balance until a certain transaction.
        # until: Transaction | None = None,
    ) -> int:
        """
        Calculates the balance of a user.
        """

        query = Transaction._user_balance_query(user)  # , until=until)

        result = sql_session.scalar(query)

        if result is None:
            # If there are no transactions for this user, the query should return 0, not None.
            raise RuntimeError(
                f"Something went wrong while calculating the balance for user {user.name} (ID: {user.id})."
            )

        return result

    #############################
    # PRODUCT PRICE CALCULATION #
    #############################

    @staticmethod
    def _product_price_query(
        product: Product,
        # until: datetime | None = None,
    ):
        """
        The inner query for calculating the product price.

        This is used both directly via product_price() and in Transaction CHECK constraints.
        """
        initial_element = select(
            literal(0).label("i"),
            literal(0).label("time"),
            literal(0).label("price"),
            literal(0).label("product_count"),
        )

        recursive_cte = initial_element.cte(name="rec_cte", recursive=True)

        # Subset of transactions that we'll want to iterate over.
        trx_subset = (
            select(
                func.row_number().over(order_by=asc(Transaction.time)).label("i"),
                Transaction.time,
                Transaction.type_,
                Transaction.product_count,
                Transaction.per_product,
            )
            .where(
                Transaction.type_.in_(
                    [
                        TransactionType.BUY_PRODUCT,
                        TransactionType.ADD_PRODUCT,
                        TransactionType.ADJUST_STOCK,
                    ]
                ),
                Transaction.product_id == product.id,
                # TODO:
                # If we have a transaction to limit the price calculation to, use it.
                # If not, use all transactions for the product.
                # (Transaction.time <= until.time) if until else True,
            )
            .order_by(Transaction.time.asc())
            .alias("trx_subset")
        )

        recursive_elements = (
            select(
                trx_subset.c.i,
                trx_subset.c.time,
                case(
                    # Someone buys the product -> price remains the same.
                    (trx_subset.c.type_ == TransactionType.BUY_PRODUCT, recursive_cte.c.price),
                    # Someone adds the product -> price is recalculated based on
                    #  product count, previous price, and new price.
                    (
                        trx_subset.c.type_ == TransactionType.ADD_PRODUCT,
                        cast(
                            func.ceil(
                                (trx_subset.c.per_product * trx_subset.c.product_count)
                                / (
                                    # The running product count can be negative if the accounting is bad.
                                    # This ensures that we never end up with negative prices or zero divisions
                                    # and other disastrous phenomena.
                                    func.min(recursive_cte.c.product_count, 0)
                                    + trx_subset.c.product_count
                                )
                            ),
                            Integer,
                        ),
                    ),
                    # Someone adjusts the stock -> price remains the same.
                    (trx_subset.c.type_ == TransactionType.ADJUST_STOCK, recursive_cte.c.price),
                    # Should never happen
                    else_=recursive_cte.c.price,
                ).label("price"),
                case(
                    # Someone buys the product -> product count is reduced.
                    (
                        trx_subset.c.type_ == TransactionType.BUY_PRODUCT,
                        recursive_cte.c.product_count - trx_subset.c.product_count,
                    ),
                    # Someone adds the product -> product count is increased.
                    (
                        trx_subset.c.type_ == TransactionType.ADD_PRODUCT,
                        recursive_cte.c.product_count + trx_subset.c.product_count,
                    ),
                    # Someone adjusts the stock -> product count is adjusted.
                    (
                        trx_subset.c.type_ == TransactionType.ADJUST_STOCK,
                        recursive_cte.c.product_count + trx_subset.c.product_count,
                    ),
                    # Should never happen
                    else_=recursive_cte.c.product_count,
                ).label("product_count"),
            )
            .select_from(trx_subset)
            .where(trx_subset.c.i == recursive_cte.c.i + 1)
        )

        return recursive_cte.union_all(recursive_elements)

    @staticmethod
    def product_price(
        sql_session: Session,
        product: Product,
        # Optional: calculate the price until a certain transaction.
        # until: Transaction | None = None,
    ) -> int:
        """
        Calculates the price of a product.
        """

        recursive_cte = Transaction._product_price_query(product)  # , until=until)

        # TODO: optionally verify subresults:
        #   - product_count should never be negative (but this happens sometimes, so just a warning)
        #   - price should never be negative

        result = sql_session.scalar(
            select(recursive_cte.c.price).order_by(recursive_cte.c.i.desc()).limit(1)
        )

        if result is None:
            # If there are no transactions for this product, the query should return 0, not None.
            raise RuntimeError(
                f"Something went wrong while calculating the price for product {product.name} (ID: {product.id})."
            )

        return result
