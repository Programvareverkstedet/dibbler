from typing import Any

import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, ProductLog
from dibbler.models.enums import ProductLogEntryType
from dibbler.queries import create_product, edit_product


def _make_product(sql_session: Session) -> Product:
    return create_product(sql_session, "1234567890", "Cola", 15)


def test_edit_product_updates_only_the_given_fields(sql_session: Session) -> None:
    product = _make_product(sql_session)

    edit_product(sql_session, product, name="Pepsi", price=20, hidden=True)

    sql_session.expire_all()

    assert product.name == "Pepsi"
    assert product.price == 20
    assert {bc.code for bc in product.barcodes} == {"1234567890"}
    assert product.hidden is True


def test_edit_product_records_an_edit_log_entry_with_only_touched_fields(
    sql_session: Session,
) -> None:
    product = _make_product(sql_session)

    edit_product(sql_session, product, price=20)

    sql_session.expire_all()

    log = sql_session.query(ProductLog).filter(ProductLog.type == ProductLogEntryType.EDIT).one()
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


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        pytest.param({}, "Nothing to edit", id="nothing"),
        pytest.param({"hidden": False}, "Nothing to edit", id="same-hidden"),

        pytest.param({"name": ""}, "Name cannot be empty", id="empty-name"),
        pytest.param({"name": "Cola"}, "Nothing to edit", id="same-name"),
        pytest.param({"name": "Pep\nsi"}, "Name has an invalid format", id="invalid-chars-name"),
        pytest.param({"name": "x" * (Product.name_length + 1)}, "Name must be at most", id="too-long-name"),

        pytest.param({"price": 15}, "Nothing to edit", id="same-price"),
        pytest.param({"price": 0}, "Price must be positive", id="non-positive-price"),
        pytest.param({"price": -1}, "Price must be positive", id="negative-price"),
        pytest.param({"name": "Pepsi", "price": 0}, "Price must be positive", id="valid-name-invalid-price"),
    ],
)  # fmt: skip
def test_invariants(sql_session: Session, kwargs: dict[str, Any], error: str) -> None:
    product = _make_product(sql_session)

    with pytest.raises(ValueError, match=error):
        edit_product(sql_session, product, **kwargs)

    sql_session.expire_all()

    assert (product.name, product.price, product.hidden) == ("Cola", 15, False)
