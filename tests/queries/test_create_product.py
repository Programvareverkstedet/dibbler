import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product
from dibbler.queries import create_product


def test_create_product_persists_a_queryable_product(sql_session: Session) -> None:
    product = create_product(sql_session, "1234567890", "Cola", 15, stock=10, hidden=True)

    sql_session.expire_all()

    fetched = sql_session.get(Product, product.product_id)
    assert fetched is not None
    assert fetched.bar_code == "1234567890"
    assert fetched.name == "Cola"
    assert fetched.price == 15
    assert fetched.stock == 10
    assert fetched.hidden is True


def test_create_product_defaults_to_zero_stock_and_not_hidden(sql_session: Session) -> None:
    product = create_product(sql_session, "1234567890", "Cola", 15)

    sql_session.expire_all()

    assert product.stock == 0
    assert product.hidden is False


def test_create_product_rejects_empty_bar_code(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="Bar code cannot be empty"):
        create_product(sql_session, "", "Cola", 15)


def test_create_product_rejects_empty_name(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="Name cannot be empty"):
        create_product(sql_session, "1234567890", "", 15)


def test_create_product_rejects_non_positive_price(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="Price must be positive"):
        create_product(sql_session, "1234567890", "Cola", 0)


def test_create_product_rejects_non_digit_bar_code(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="digits only"):
        create_product(sql_session, "123abc", "Cola", 15)
