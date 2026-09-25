import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product
from dibbler.queries import edit_product


def _make_product(sql_session: Session) -> Product:
    product = Product("1234567890", "Cola", 15, stock=10, hidden=False)
    sql_session.add(product)
    sql_session.flush()
    return product


def test_edit_product_updates_only_the_given_fields(sql_session: Session) -> None:
    product = _make_product(sql_session)

    edit_product(sql_session, product, name="Pepsi", price=20, bar_code="0987654321", hidden=True)

    sql_session.expire_all()

    assert product.name == "Pepsi"
    assert product.price == 20
    assert product.bar_code == "0987654321"
    assert product.hidden is True


def test_edit_product_leaves_product_untouched_when_nothing_is_passed(sql_session: Session) -> None:
    product = _make_product(sql_session)

    edit_product(sql_session, product)

    sql_session.expire_all()

    assert product.name == "Cola"
    assert product.price == 15
    assert product.bar_code == "1234567890"
    assert product.hidden is False


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


def test_edit_product_rejects_empty_bar_code(sql_session: Session) -> None:
    product = _make_product(sql_session)

    with pytest.raises(ValueError, match="Bar code cannot be empty"):
        edit_product(sql_session, product, bar_code="")


def test_edit_product_rejects_non_positive_price(sql_session: Session) -> None:
    product = _make_product(sql_session)

    with pytest.raises(ValueError, match="Price must be positive"):
        edit_product(sql_session, product, price=0)
