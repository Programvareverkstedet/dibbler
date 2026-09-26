import math

import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, User
from dibbler.queries import buy_products

DEFAULT_PEPSI_STOCK = 10
DEFAULT_PEPSI_PRICE = 15


def _make_product(
    sql_session: Session,
    bar_code: str = "1234567890",
    name: str = "Pepsi",
    stock: int = DEFAULT_PEPSI_STOCK,
    price: int = DEFAULT_PEPSI_PRICE,
) -> Product:
    product = Product(bar_code, name, price, stock=stock)
    sql_session.add(product)
    sql_session.flush()
    return product


def _make_user(sql_session: Session, name: str, credit: int = 100) -> User:
    user = User(name, None, credit=credit)
    sql_session.add(user)
    sql_session.flush()
    return user


def test_buy_products_charges_a_single_buyer_and_decrements_stock(sql_session: Session) -> None:
    product = _make_product(sql_session)
    alice = _make_user(sql_session, "alice", credit=100)
    amount = 3

    purchase = buy_products(sql_session, [(alice, 1)], [(product, amount)])

    sql_session.expire_all()

    assert purchase.price == amount * DEFAULT_PEPSI_PRICE
    assert alice.credit == 100 - amount * DEFAULT_PEPSI_PRICE
    assert product.stock == DEFAULT_PEPSI_STOCK - amount


def test_buy_products_splits_the_price_evenly_across_buyers(sql_session: Session) -> None:
    product = _make_product(sql_session)
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")
    amount = 3

    buy_products(sql_session, [(alice, 1), (bob, 1)], [(product, amount)])

    sql_session.expire_all()

    buyer_share = math.ceil(amount * DEFAULT_PEPSI_PRICE / 2)
    assert alice.credit == 100 - buyer_share
    assert bob.credit == 100 - buyer_share


def test_buy_products_rounds_each_buyers_share_up(sql_session: Session) -> None:
    product = _make_product(sql_session, price=10)
    users = [_make_user(sql_session, name) for name in ("alice", "bob", "carol")]

    purchase = buy_products(sql_session, [(u, 1) for u in users], [(product, 1)])

    sql_session.expire_all()

    buyer_share = math.ceil(purchase.price / len(users))

    assert [100 - u.credit for u in users] == [buyer_share] * len(users)
    assert purchase.price == 10


def test_buy_products_applies_penalty_per_buyer(sql_session: Session) -> None:
    product = _make_product(sql_session, price=10)
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    purchase = buy_products(sql_session, [(alice, 1), (bob, 2)], [(product, 1)])

    sql_session.expire_all()

    buyer_share = math.ceil(purchase.price / 2)

    assert alice.credit == 100 - buyer_share
    assert bob.credit == 100 - buyer_share * 2
    assert purchase.price == 10


def test_buy_products_multiplies_penalty_onto_the_already_rounded_share(
    sql_session: Session,
) -> None:
    # Just pinning the implementation here, the penalty is multiplied onto
    # the already rounded-up share, not the other way around.

    product = _make_product(sql_session, price=10)
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")
    carol = _make_user(sql_session, "carol")

    buy_products(sql_session, [(alice, 1), (bob, 1), (carol, 2)], [(product, 1)])

    sql_session.expire_all()

    base_share = math.ceil(10 / 3)
    assert alice.credit == 100 - base_share
    assert bob.credit == 100 - base_share
    assert carol.credit == 100 - base_share * 2


def test_buy_products_updates_multiple_products_independently(sql_session: Session) -> None:
    cola = _make_product(sql_session, bar_code="1111111111", name="Cola", stock=10, price=15)
    pepsi = _make_product(sql_session, bar_code="2222222222", name="Pepsi", stock=4, price=8)
    alice = _make_user(sql_session, "alice")

    purchase = buy_products(sql_session, [(alice, 1)], [(cola, 2), (pepsi, 3)])

    sql_session.expire_all()

    assert cola.stock == 8
    assert pepsi.stock == 1
    assert purchase.price == 2 * 15 + 3 * 8
    assert alice.credit == 100 - (2 * 15 + 3 * 8)


def test_buy_products_allows_the_same_buyer_twice(sql_session: Session) -> None:
    # NOTE: this behaviour might be edited in the future,
    #       see https://git.pvv.ntnu.no/Projects/dibbler/issues/54
    product = _make_product(sql_session, price=10)
    alice = _make_user(sql_session, "alice")

    purchase = buy_products(sql_session, [(alice, 1), (alice, 1)], [(product, 1)])

    sql_session.expire_all()

    assert alice.credit == 100 - 10
    assert len(purchase.transactions) == 2
    assert {t.user for t in purchase.transactions} == {alice}
    assert [t.penalty for t in purchase.transactions] == [1, 1]


def test_buy_products_allows_a_repeated_buyer_alongside_another_buyer(
    sql_session: Session,
) -> None:
    product = _make_product(sql_session, price=12)
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    purchase = buy_products(sql_session, [(alice, 1), (alice, 1), (bob, 2)], [(product, 1)])

    sql_session.expire_all()

    buyer_share = math.ceil(purchase.price / 3)

    # 2 buyer shares for alice
    assert alice.credit == 100 - 2 * buyer_share

    # 1 buyer share for bob, but multiplied by his penalty of 2
    assert bob.credit == 100 - buyer_share * 2

    assert len(purchase.transactions) == 3
    assert {t.user for t in purchase.transactions} == {alice, bob}


def test_buy_products_records_a_purchase_linking_entries_and_transactions(
    sql_session: Session,
) -> None:
    product = _make_product(sql_session)
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    purchase = buy_products(sql_session, [(alice, 1), (bob, 2)], [(product, 5)])

    sql_session.expire_all()

    assert [entry.product for entry in purchase.entries] == [product]
    assert [entry.amount for entry in purchase.entries] == [5]
    assert {t.user for t in purchase.transactions} == {alice, bob}
    assert {t.penalty for t in purchase.transactions} == {1, 2}


def test_buy_products_rejects_no_buyers(sql_session: Session) -> None:
    product = _make_product(sql_session)

    with pytest.raises(ValueError, match="At least one buyer"):
        buy_products(sql_session, [], [(product, 1)])


def test_buy_products_rejects_no_products(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")

    with pytest.raises(ValueError, match="At least one product"):
        buy_products(sql_session, [(alice, 1)], [])


def test_buy_products_rejects_penalty_below_one(sql_session: Session) -> None:
    product = _make_product(sql_session)
    alice = _make_user(sql_session, "alice")

    with pytest.raises(ValueError, match="Penalty must be at least 1"):
        buy_products(sql_session, [(alice, 0)], [(product, 1)])


def test_buy_products_rejects_inconsistent_penalty_for_the_same_buyer(
    sql_session: Session,
) -> None:
    product = _make_product(sql_session)
    alice = _make_user(sql_session, "alice")

    with pytest.raises(ValueError, match="cannot have more than one penalty"):
        buy_products(sql_session, [(alice, 1), (alice, 2)], [(product, 1)])


def test_buy_products_rejects_non_positive_product_amount(sql_session: Session) -> None:
    product = _make_product(sql_session)
    alice = _make_user(sql_session, "alice")

    with pytest.raises(ValueError, match="Product amounts must be positive"):
        buy_products(sql_session, [(alice, 1)], [(product, 0)])
