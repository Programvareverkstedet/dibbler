from sqlalchemy.orm import Session

from dibbler.models import Product
from dibbler.queries import search_product


def insert_test_data(sql_session: Session) -> list[Product]:
    products = [
        Product("1234567890123", "Test Product A"),
        Product("2345678901234", "Test Product B"),
        Product("3456789012345", "Another Product"),
        Product("4567890123456", "Hidden Product", hidden=True),
    ]

    sql_session.add_all(products)
    sql_session.commit()

    return products


def test_search_product_no_products(sql_session: Session) -> None:
    result = search_product("Nonexistent Product", sql_session)

    assert isinstance(result, list)

    assert len(result) == 0


def test_search_product_name_exact_match(sql_session: Session) -> None:
    insert_test_data(sql_session)

    result = search_product("Test Product A", sql_session)
    assert isinstance(result, Product)
    assert result.bar_code == "1234567890123"


def test_search_product_name_partial_match(sql_session: Session) -> None:
    insert_test_data(sql_session)

    result = search_product("Test Product", sql_session)
    assert isinstance(result, list)
    assert len(result) == 2
    names = {product.name for product in result}
    assert names == {"Test Product A", "Test Product B"}


def test_search_product_name_no_match(sql_session: Session) -> None:
    insert_test_data(sql_session)

    result = search_product("Nonexistent", sql_session)
    assert isinstance(result, list)
    assert len(result) == 0


def test_search_product_barcode_exact_match(sql_session: Session) -> None:
    products = insert_test_data(sql_session)

    product = products[1]  # Test Product B

    result = search_product(product.bar_code, sql_session)
    assert isinstance(result, Product)
    assert result.name == product.name


# Should not be able to find hidden products
def test_search_product_hidden_products(sql_session: Session) -> None:
    insert_test_data(sql_session)
    result = search_product("Hidden Product", sql_session)
    assert isinstance(result, list)
    assert len(result) == 0


# Should be able to find hidden products if specified
def test_search_product_find_hidden_products(sql_session: Session) -> None:
    insert_test_data(sql_session)
    result = search_product("Hidden Product", sql_session, find_hidden_products=True)
    assert isinstance(result, Product)
    assert result.name == "Hidden Product"


# Should be able to find hidden products by barcode despite not specified
def test_search_product_hidden_products_by_barcode(sql_session: Session) -> None:
    products = insert_test_data(sql_session)
    hidden_product = products[3]  # Hidden Product

    result = search_product(hidden_product.bar_code, sql_session)
    assert isinstance(result, Product)
    assert result.name == "Hidden Product"
