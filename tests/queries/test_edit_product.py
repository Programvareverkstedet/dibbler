import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, ProductLog
from dibbler.models.enums import ProductLogEntryType
from dibbler.queries import edit_product


def _make_product(sql_session: Session) -> Product:
    product = Product("1234567890", "Cola", 15, stock=10, hidden=False)
    sql_session.add(product)
    sql_session.flush()
    return product


def test_edit_product_updates_only_the_given_fields(sql_session: Session) -> None:
    product = _make_product(sql_session)

    edit_product(sql_session, product, name="Pepsi", price=20, hidden=True)

    sql_session.expire_all()

    assert product.name == "Pepsi"
    assert product.price == 20
    assert {bc.code for bc in product.barcodes} == {"1234567890"}
    assert product.hidden is True


def test_edit_product_rejects_editing_nothing(sql_session: Session) -> None:
    product = _make_product(sql_session)

    with pytest.raises(ValueError, match="Nothing to edit"):
        edit_product(sql_session, product)


def test_edit_product_rejects_resubmitting_the_same_price(sql_session: Session) -> None:
    product = _make_product(sql_session)

    with pytest.raises(ValueError, match="Nothing to edit"):
        edit_product(sql_session, product, price=15)


def test_edit_product_records_an_edit_log_entry_with_only_touched_fields(
    sql_session: Session,
) -> None:
    product = _make_product(sql_session)

    edit_product(sql_session, product, price=20)

    sql_session.expire_all()

    log = sql_session.query(ProductLog).one()
    assert log.type == ProductLogEntryType.EDIT
    assert log.product_id == product.id
    assert log.price == 20
    assert log.name is None
    assert log.hidden is None


def test_edit_product_can_touch_only_hidden(sql_session: Session) -> None:
    product = _make_product(sql_session)

    edit_product(sql_session, product, hidden=True)

    sql_session.expire_all()

    assert product.hidden is True
    assert product.name == "Cola"
    assert product.price == 15


def test_edit_product_does_not_apply_any_change_when_one_field_is_invalid(
    sql_session: Session,
) -> None:
    product = _make_product(sql_session)

    with pytest.raises(ValueError, match="Price must be positive"):
        edit_product(sql_session, product, name="Pepsi", price=0)

    sql_session.expire_all()

    assert product.name == "Cola"
    assert product.price == 15


def test_edit_product_rejects_empty_name(sql_session: Session) -> None:
    product = _make_product(sql_session)

    with pytest.raises(ValueError, match="Name cannot be empty"):
        edit_product(sql_session, product, name="")


def test_edit_product_rejects_non_positive_price(sql_session: Session) -> None:
    product = _make_product(sql_session)

    with pytest.raises(ValueError, match="Price must be positive"):
        edit_product(sql_session, product, price=0)
