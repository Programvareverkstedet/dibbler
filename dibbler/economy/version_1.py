import math
from collections.abc import Hashable, Iterable
from fractions import Fraction
from typing import TypeVar

from dibbler.lib.helpers import simplify_shares
from dibbler.models import Product

ShareholderT = TypeVar("ShareholderT", bound=Hashable)

VERSION = 1
"""The version of this set of economy rules."""

PENALTY_MULTIPLIER = 2
"""Buyers with low credit get their prices multiplied for hurt and profit."""

LOW_CREDIT_LIMIT = -100
"""Buyers with this much credit will be penalized. Slabbedasker frfr"""


def has_low_credit(credit: int) -> bool:
    return credit <= LOW_CREDIT_LIMIT


def buyer_penalty_multiplier(credit: int) -> int:
    return PENALTY_MULTIPLIER if has_low_credit(credit) else 1


def purchase_price(products: Iterable[tuple[Product, int]]) -> int:
    """The total price of buying the given amounts of products."""
    return sum(product.price * amount for product, amount in products)


def buyer_charge(
    total_price: int,
    share_count: int,
    penalty: int,
) -> int:
    """
    What a single share of a purchase is charged.

    The share is rounded up before the penalty is applied, the users may be charged slightly more than the total price of the purchase.
    """
    return math.ceil(Fraction(total_price, share_count)) * penalty


def buyer_charges(
    total_price: int,
    buyers: list[tuple[ShareholderT, int]],
) -> list[tuple[ShareholderT, int, int]]:
    """
    Split a purchase between buyers.

    This will also simplify any repeated shares.

    Returns `(buyer, penalty, charge)` for every final share.
    """
    shares = simplify_shares(buyers)
    return [
        (buyer, penalty, buyer_charge(total_price, len(shares), penalty))
        for buyer, penalty in shares
    ]


def restock_credits(
    total_price: int,
    users: list[ShareholderT],
) -> list[tuple[ShareholderT, int]]:
    """
    Split what was paid for added stock between the users who paid for it.

    Returns `(user, credit)` for every share.

    Every share is rounded up, the users may be rewarded slightly more than the added stock value.
    """
    shares = simplify_shares(users)
    return [(user, math.ceil(Fraction(total_price, len(shares)))) for user in shares]


def stock_reset_before_restock(stock: int) -> int:
    """
    A term to be added to the product stock before restocking.

    This should ensure we reset the stock to zero if it was negative.
    """
    return -stock if stock < 0 else 0


def restock_price(stock: int, price: int, added_amount: int, paid_amount: int) -> int:
    """The price of a product after adding stock to it."""
    current_stock = max(stock, 0)
    total_value = current_stock * price + paid_amount
    return math.ceil(Fraction(total_value, current_stock + added_amount))
