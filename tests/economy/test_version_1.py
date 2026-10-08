import pytest

from dibbler.economy import version_1
from dibbler.models import Product


@pytest.mark.parametrize(
    ("credit", "low_credit", "penalty"),
    [
        pytest.param(0, False, 1, id="above-limit"),
        pytest.param(version_1.LOW_CREDIT_LIMIT + 1, False, 1, id="just-above-limit"),
        pytest.param(version_1.LOW_CREDIT_LIMIT, True, version_1.PENALTY_MULTIPLIER, id="at-limit"),
        pytest.param(version_1.LOW_CREDIT_LIMIT - 1, True, version_1.PENALTY_MULTIPLIER, id="below-limit"),
    ],
)  # fmt: skip
def test_penalty_depends_on_credit(credit: int, low_credit: bool, penalty: int) -> None:
    assert version_1.has_low_credit(credit) is low_credit
    assert version_1.buyer_penalty_multiplier(credit) == penalty


def test_purchase_price() -> None:
    cola = Product("1111111111", "Cola", 15)
    pepsi = Product("2222222222", "Pepsi", 8)

    assert version_1.purchase_price([(cola, 2), (pepsi, 3)]) == 2 * 15 + 3 * 8


@pytest.mark.parametrize(
    ("total_price", "share_count", "penalty", "expected"),
    [
        pytest.param(30, 1, 1, 30, id="single-share"),
        pytest.param(30, 3, 1, 10, id="even-split"),
        pytest.param(10, 3, 1, 4, id="uneven-split-rounds-up"),
        pytest.param(10, 3, 2, 8, id="penalty-multiplies-rounded-share"),
        pytest.param(0, 2, 1, 0, id="free"),
    ],
)
def test_buyer_charge(total_price: int, share_count: int, penalty: int, expected: int) -> None:
    assert version_1.buyer_charge(total_price, share_count, penalty) == expected


@pytest.mark.parametrize(
    ("buyers", "expected"),
    [
        pytest.param([("alice", 1)], [("alice", 1, 10)], id="single-buyer"),
        pytest.param(
            [("alice", 1), ("bob", 2), ("carol", 1)],
            [("alice", 1, 4), ("bob", 2, 8), ("carol", 1, 4)],
            id="penalty-for-one-buyer",
        ),
        pytest.param(
            [("alice", 1), ("bob", 1), ("alice", 1)],
            [("alice", 1, 4), ("bob", 1, 4), ("alice", 1, 4)],
            id="repeated-buyer-gets-more-shares",
        ),
        pytest.param(
            [("alice", 1), ("alice", 1), ("bob", 1), ("bob", 1)],
            [("alice", 1, 5), ("bob", 1, 5)],
            id="shares-are-simplified",
        ),
    ],
)
def test_buyer_charges(
    buyers: list[tuple[str, int]],
    expected: list[tuple[str, int, int]],
) -> None:
    assert version_1.buyer_charges(10, buyers) == expected


@pytest.mark.parametrize(
    ("users", "expected"),
    [
        pytest.param(["alice"], [("alice", 100)], id="single-user"),
        pytest.param(["alice", "bob"], [("alice", 50), ("bob", 50)], id="even-split"),
        pytest.param(
            ["alice", "bob", "carol"],
            [("alice", 34), ("bob", 34), ("carol", 34)],
            id="uneven-split-rounds-up",
        ),
        pytest.param(["alice", "alice"], [("alice", 100)], id="shares-are-simplified"),
    ],
)
def test_restock_credits(users: list[str], expected: list[tuple[str, int]]) -> None:
    assert version_1.restock_credits(100, users) == expected


@pytest.mark.parametrize(
    ("stock", "expected"),
    [
        pytest.param(5, 0, id="positive"),
        pytest.param(0, 0, id="empty"),
        pytest.param(-3, 3, id="negative-is-reset"),
    ],
)
def test_stock_reset_before_restock(stock: int, expected: int) -> None:
    assert version_1.stock_reset_before_restock(stock) == expected


@pytest.mark.parametrize(
    ("stock", "price", "added_amount", "paid_amount", "expected"),
    [
        pytest.param(10, 15, 5, 75, 15, id="same-price-per-item"),
        pytest.param(10, 15, 5, 100, 17, id="average-rounds-up"),
        pytest.param(0, 15, 5, 50, 10, id="empty-stock-takes-the-paid-price"),
        pytest.param(-3, 15, 5, 50, 10, id="negative-stock-counts-as-empty"),
        pytest.param(10, 15, 5, 0, 10, id="free-stock-lowers-the-price"),
        pytest.param(0, 15, 5, 0, 0, id="free-stock-into-empty-stock-makes-it-free"),
    ],
)
def test_restock_price(
    stock: int,
    price: int,
    added_amount: int,
    paid_amount: int,
    expected: int,
) -> None:
    assert version_1.restock_price(stock, price, added_amount, paid_amount) == expected
