from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dibbler.models import (
    Product,
    ProductLog,
    PurchaseEntry,
    TransactionLog,
    TransactionLogProduct,
    User,
)
from dibbler.models.enums import ProductLogEntryType, TransactionLogEntryType
from dibbler.queries import add_stock, buy_products, merge_products


def _make_product(
    sql_session: Session,
    bar_code: str = "1234567890",
    name: str = "Cola",
    price: int = 15,
    stock: int = 10,
    hidden: bool = False,
) -> Product:
    product = Product(bar_code, name, price, stock=stock, hidden=hidden)
    sql_session.add(product)
    sql_session.flush()
    return product


def _make_user(sql_session: Session, name: str = "alice", credit: int = 1000) -> User:
    user = User(name, None, credit=credit)
    sql_session.add(user)
    sql_session.flush()
    return user


@pytest.mark.parametrize("preload", [True, False])
def test_moves_barcodes_onto_the_target(sql_session: Session, preload: bool) -> None:
    alice = _make_user(sql_session)
    source = _make_product(sql_session, bar_code="1111111111")
    target = _make_product(sql_session, bar_code="2222222222")

    if preload:
        preloaded = set(source.barcodes)
        assert len(preloaded) == 1

    merge_products(sql_session, alice, source, target)

    sql_session.expire_all()

    assert {bc.code for bc in target.barcodes} == {"1111111111", "2222222222"}


def test_deletes_the_source_product(sql_session: Session) -> None:
    alice = _make_user(sql_session)
    source = _make_product(sql_session, bar_code="1111111111")
    target = _make_product(sql_session, bar_code="2222222222")
    source_id = source.id

    merge_products(sql_session, alice, source, target)

    sql_session.expire_all()

    assert sql_session.get(Product, source_id) is None


def test_keeps_targets_own_fields_by_default(sql_session: Session) -> None:
    alice = _make_user(sql_session)
    source = _make_product(sql_session, bar_code="1111111111", name="Cola", price=15, stock=10)
    target = _make_product(sql_session, bar_code="2222222222", name="Pepsi", price=20, stock=5)

    merge_products(sql_session, alice, source, target)

    sql_session.expire_all()

    assert target.name == "Pepsi"
    assert target.price == 20
    assert target.stock == 5


def test_can_edit_the_merged_product(sql_session: Session) -> None:
    alice = _make_user(sql_session)
    source = _make_product(sql_session, bar_code="1111111111", name="Cola", price=15, hidden=True)
    target = _make_product(sql_session, bar_code="2222222222", name="Pepsi", price=20, hidden=False)

    merge_products(
        sql_session,
        alice,
        source,
        target,
        name=source.name,
        price=23,
        hidden=source.hidden,
    )

    sql_session.expire_all()

    assert target.name == "Cola"
    assert target.price == 23
    assert target.hidden is True


def test_can_set_a_custom_stock(sql_session: Session) -> None:
    alice = _make_user(sql_session)
    source = _make_product(sql_session, bar_code="1111111111", stock=10)
    target = _make_product(sql_session, bar_code="2222222222", stock=5)

    merge_products(sql_session, alice, source, target, stock=source.stock + target.stock)

    sql_session.expire_all()

    assert target.stock == 15


@pytest.mark.parametrize("preload", [True, False])
def test_repoints_purchase_history_to_the_target(sql_session: Session, preload: bool) -> None:
    source = _make_product(sql_session, bar_code="1111111111")
    target = _make_product(sql_session, bar_code="2222222222")
    alice = _make_user(sql_session)

    purchase = buy_products(sql_session, [(alice, 1)], [(source, 1)])

    if preload:
        preloaded = set(source.purchases)
        assert len(preloaded) == 1

    merge_products(sql_session, alice, source, target, stock=source.stock + target.stock)

    sql_session.expire_all()

    entry = sql_session.query(PurchaseEntry).filter(PurchaseEntry.purchase_id == purchase.id).one()
    assert entry.product_id == target.id

    xref = sql_session.query(TransactionLogProduct).one()
    assert xref.product_id == target.id


def test_records_logs(sql_session: Session) -> None:
    alice = _make_user(sql_session)
    source = _make_product(sql_session, bar_code="1111111111", name="Cola")
    target = _make_product(sql_session, bar_code="2222222222", name="Pepsi")
    source_id = source.id

    merge_products(
        sql_session,
        alice,
        source,
        target,
        name="Cola",
        stock=source.stock + target.stock - 1,
    )

    sql_session.expire_all()

    merge_log = (
        sql_session.query(ProductLog).filter(ProductLog.type == ProductLogEntryType.MERGE).one()
    )
    assert merge_log.product_id == target.id
    assert merge_log.merged_product_id == source_id

    delete_log = (
        sql_session.query(ProductLog).filter(ProductLog.type == ProductLogEntryType.DELETE).one()
    )
    assert delete_log.merge_ref_id == merge_log.id
    assert delete_log.product_id == source_id

    edit_log = (
        sql_session.query(ProductLog).filter(ProductLog.type == ProductLogEntryType.EDIT).one()
    )
    assert edit_log.merge_ref_id == merge_log.id
    assert edit_log.product_id == target.id
    assert edit_log.name == "Cola"
    assert edit_log.price is None
    assert edit_log.hidden is None

    adjustment_log = (
        sql_session.query(TransactionLog)
        .filter(TransactionLog.type == TransactionLogEntryType.ADJUST_STOCK)
        .one()
    )
    assert adjustment_log.merge_ref_id == merge_log.id
    assert [(u.user, u.amount) for u in adjustment_log.users] == [(alice, None)]


def test_no_change_implies_no_edit_log(sql_session: Session) -> None:
    alice = _make_user(sql_session)
    source = _make_product(sql_session, bar_code="1111111111")
    target = _make_product(sql_session, bar_code="2222222222")

    merge_products(sql_session, alice, source, target)

    sql_session.expire_all()

    assert (
        sql_session.query(ProductLog).filter(ProductLog.type == ProductLogEntryType.EDIT).count()
        == 0
    )


def test_no_stock_change_implies_no_transaction_log(sql_session: Session) -> None:
    alice = _make_user(sql_session)
    source = _make_product(sql_session, bar_code="1111111111", stock=0)
    target = _make_product(sql_session, bar_code="2222222222", stock=5)

    merge_products(sql_session, alice, source, target)

    sql_session.expire_all()

    assert target.stock == 5
    assert sql_session.query(TransactionLog).count() == 0


def test_summed_stock_is_not_logged(sql_session: Session) -> None:
    alice = _make_user(sql_session)
    source = _make_product(sql_session, bar_code="1111111111", stock=10)
    target = _make_product(sql_session, bar_code="2222222222", stock=5)

    merge_products(sql_session, alice, source, target, stock=15)

    sql_session.expire_all()

    assert target.stock == 15
    assert sql_session.query(TransactionLog).count() == 0


def _stock_adjustment(sql_session: Session) -> int:
    log = (
        sql_session.query(TransactionLog)
        .filter(TransactionLog.type == TransactionLogEntryType.ADJUST_STOCK)
        .one()
    )
    return log.products.pop().amount


def test_keeping_target_stock_is_logged(sql_session: Session) -> None:
    alice = _make_user(sql_session)
    source = _make_product(sql_session, bar_code="1111111111", stock=10)
    target = _make_product(sql_session, bar_code="2222222222", stock=5)

    merge_products(sql_session, alice, source, target)

    sql_session.expire_all()

    assert target.stock == 5
    assert _stock_adjustment(sql_session) == -10


def test_custom_stock_is_logged(sql_session: Session) -> None:
    alice = _make_user(sql_session)
    source = _make_product(sql_session, bar_code="1111111111", stock=10)
    target = _make_product(sql_session, bar_code="2222222222", stock=5)

    merge_products(sql_session, alice, source, target, stock=12)

    sql_session.expire_all()

    assert target.stock == 12
    assert _stock_adjustment(sql_session) == -3


@pytest.mark.parametrize("choice", ["source", "target", "sum", "custom"])
def test_log_sum_matches_stock(sql_session: Session, choice: str) -> None:
    alice = _make_user(sql_session)
    source = _make_product(sql_session, bar_code="1111111111", stock=0)
    target = _make_product(sql_session, bar_code="2222222222", stock=0)
    add_stock(sql_session, [alice], [(source, 10, 100), (target, 5, 50)], total_price=150)
    buy_products(sql_session, [(alice, 1)], [(source, 2), (target, 1)])

    stock = {
        "source": source.stock,
        "target": target.stock,
        "sum": source.stock + target.stock,
        "custom": 3,
    }[choice]
    merge_products(sql_session, alice, source, target, stock=stock)

    sql_session.expire_all()

    logged = sum(
        x.amount
        for x in sql_session.query(TransactionLogProduct).filter(
            TransactionLogProduct.product_id == target.id,
        )
    )
    assert target.stock == stock
    assert logged == stock


def test_freed_barcode_after_merge_stays_freed(sql_session: Session) -> None:
    alice = _make_user(sql_session)
    source = _make_product(sql_session, bar_code="1111111111")
    target = _make_product(sql_session, bar_code="2222222222")

    merge_products(sql_session, alice, source, target)

    sql_session.expire_all()

    assert {bc.code for bc in target.barcodes} == {"1111111111", "2222222222"}


def test_rejects_merging_a_product_into_itself(sql_session: Session) -> None:
    alice = _make_user(sql_session)
    product = _make_product(sql_session)

    with pytest.raises(ValueError, match="itself"):
        merge_products(sql_session, alice, product, product)


def test_rejects_empty_name(sql_session: Session) -> None:
    alice = _make_user(sql_session)
    source = _make_product(sql_session, bar_code="1111111111")
    target = _make_product(sql_session, bar_code="2222222222")

    with pytest.raises(ValueError, match="Name cannot be empty"):
        merge_products(sql_session, alice, source, target, name="")


def test_rejects_non_positive_price(sql_session: Session) -> None:
    alice = _make_user(sql_session)
    source = _make_product(sql_session, bar_code="1111111111")
    target = _make_product(sql_session, bar_code="2222222222")

    with pytest.raises(ValueError, match="Price must be positive"):
        merge_products(sql_session, alice, source, target, price=0)


def test_rejects_too_long_name(sql_session: Session) -> None:
    alice = _make_user(sql_session)
    source = _make_product(sql_session, bar_code="1111111111")
    target = _make_product(sql_session, bar_code="2222222222")

    with pytest.raises(ValueError, match="Name must be at most"):
        merge_products(sql_session, alice, source, target, name="x" * (Product.name_length + 1))
