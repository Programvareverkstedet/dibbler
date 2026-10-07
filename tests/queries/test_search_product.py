import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product
from dibbler.queries import search_product


def _make_products(sql_session: Session) -> dict[str, Product]:
    products = [
        Product("1234567890", "Pepsi", 10),
        Product("2222222222", "Pepsi Zero", 10),
        Product("3333333333", "Chips", 10),
        Product("4444444444", "Secret Cola", 10, hidden=True),
        Product("5555555555", "50XX Off", 10),
        Product("6666666666", "AxB", 10),
        Product("7777777777", "50% Off", 10),
        Product("8888888888", "A_B", 10),
    ]
    sql_session.add_all(products)
    sql_session.flush()
    return {product.name: product for product in products}


@pytest.mark.parametrize(
    ("query", "find_hidden_products", "expected"),
    [
        pytest.param("nonexistent", True, set(), id="no-match"),

        pytest.param("1234567890", True, "Pepsi", id="exact-barcode"),
        pytest.param("34567", True, {"Pepsi"}, id="partial-barcode"),

        pytest.param("Pepsi", True, "Pepsi", id="exact-name"),
        pytest.param("pepsi", True, "Pepsi", id="exact-name-ignores-case"),
        pytest.param("Pep", True, {"Pepsi", "Pepsi Zero"}, id="partial-name"),
        pytest.param("50%", True, {"50% Off"}, id="name-with-percent"),
        pytest.param("A_", True, {"A_B"}, id="name-with-underscore"),

        pytest.param("Secret Cola", True, "Secret Cola", id="hidden-exact-name"),
        pytest.param("Secret", True, {"Secret Cola"}, id="hidden-partial-name"),
        pytest.param("pepsi", False, "Pepsi", id="visible-only-exact-name-ignores-case"),
        pytest.param("Pep", False, {"Pepsi", "Pepsi Zero"}, id="visible-only-partial-name"),
        pytest.param("Secret Cola", False, set(), id="visible-only-hidden-exact-name"),
        pytest.param("Secret", False, set(), id="visible-only-hidden-partial-name"),
        pytest.param("4444444444", False, "Secret Cola", id="visible-only-hidden-barcode"),
    ],
)  # fmt: skip
def test_search_product(
    sql_session: Session,
    query: str,
    find_hidden_products: bool,
    expected: str | set[str],
) -> None:
    products = _make_products(sql_session)

    result = search_product(sql_session, query, find_hidden_products=find_hidden_products)

    if isinstance(expected, str):
        assert result is products[expected]
    else:
        assert isinstance(result, list)
        assert {product.name for product in result} == expected


def test_search_product_rejects_empty_string(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        search_product(sql_session, "")
