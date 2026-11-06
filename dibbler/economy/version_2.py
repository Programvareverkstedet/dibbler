"""Version 1, and a fee on purchases.

Every share of a purchase pays a fee of `PURCHASE_FEE_RATE` of its
price, in whole kroner, on top of it. The penalty applies to both.
"""

import math
import random
from collections.abc import Hashable
from fractions import Fraction
from typing import TypeVar

from dibbler.lib.helpers import simplify_shares

from .version_1 import (
    LOW_CREDIT_LIMIT,
    PENALTY_MULTIPLIER,
    buyer_penalty_multiplier,
    has_low_credit,
    purchase_price,
    restock_credits,
    restock_price,
    stock_reset_before_restock,
)

__all__ = [
    "LOW_CREDIT_LIMIT",
    "PENALTY_MULTIPLIER",
    "PURCHASE_FEE_RATE",
    "VERSION",
    "buyer_charge",
    "buyer_charges",
    "buyer_penalty_multiplier",
    "has_low_credit",
    "purchase_price",
    "restock_credits",
    "restock_price",
    "share_fee",
    "share_price",
    "stock_reset_before_restock",
]

ShareholderT = TypeVar("ShareholderT", bound=Hashable)

VERSION = 2
"""The version of this set of economy rules."""

PURCHASE_FEE_RATE = 0.02
"""The share of a purchase's price that it pays on top, as a fee."""


def share_price(total_price: int, share_count: int) -> int:
    return math.ceil(Fraction(total_price, share_count))


def share_fee(price: int, rng: random.Random) -> int:
    """
    The fee on a share costing `price`, in whole kroner.

    stochastically rounded
    """
    exact = price * PURCHASE_FEE_RATE
    whole = math.floor(exact)
    fraction = exact - whole
    round_up = 1 if rng.random() < fraction else 0
    return whole + round_up


def buyer_charge(total_price: int, share_count: int, penalty: int, fee: int) -> int:
    return (share_price(total_price, share_count) + fee) * penalty


def buyer_charges(
    total_price: int,
    buyers: list[tuple[ShareholderT, int]],
    rng: random.Random | None = None,
) -> list[tuple[ShareholderT, int, int, int]]:
    """
    Split a purchase between buyers, and draw each share's fee with `rng`,

    This will also simplify any repeated shares.

    Returns `(buyer, penalty, fee, charge)` for each share.
    """
    if rng is None:
        rng = random.SystemRandom()
    shares = simplify_shares(buyers)
    price = share_price(total_price, len(shares))
    charges = []
    for buyer, penalty in shares:
        fee = share_fee(price, rng)
        charges.append((buyer, penalty, fee, buyer_charge(total_price, len(shares), penalty, fee)))
    return charges
