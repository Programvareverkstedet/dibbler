import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product
from dibbler.queries import search_product


def _make_product(
    sql_session: Session,
    bar_code: str,
    name: str,
    hidden: bool = False,
) -> Product:
    product = Product(bar_code, name, 10, hidden=hidden)
    sql_session.add(product)
    sql_session.flush()
    return product


def test_search_product_matches_exact_bar_code(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1234567890", "Pepsi")

    result = search_product("1234567890", sql_session)

    assert result is pepsi


def test_search_product_matches_exact_name(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1234567890", "Pepsi")

    result = search_product("Pepsi", sql_session)

    assert result is pepsi


def test_search_product_exact_match_ignores_case(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1234567890", "Pepsi")

    result = search_product("pepsi", sql_session)

    assert result is pepsi


def test_search_product_escapes_percent(sql_session: Session) -> None:
    _make_product(sql_session, "1111111111", "50XX Off")

    result = search_product("50% Off", sql_session)

    assert result == []


def test_search_product_escapes_underscore(sql_session: Session) -> None:
    _make_product(sql_session, "1111111111", "AxB")

    result = search_product("A_B", sql_session)

    assert result == []


def test_search_product_returns_partial_matches(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    pepsi_zero = _make_product(sql_session, "2222222222", "Pepsi Zero")
    _make_product(sql_session, "3333333333", "Chips")

    result = search_product("Pep", sql_session)

    assert isinstance(result, list)
    assert set(result) == {pepsi, pepsi_zero}


def test_search_product_returns_empty_list_for_no_match(sql_session: Session) -> None:
    _make_product(sql_session, "1234567890", "Pepsi")

    result = search_product("nonexistent", sql_session)

    assert result == []


def test_search_product_partial_matches_bar_code(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1234567890", "Pepsi")

    result = search_product("34567", sql_session)

    assert result == [pepsi]


def test_search_product_includes_hidden_by_default(sql_session: Session) -> None:
    hidden_product = _make_product(sql_session, "1234567890", "Pepsi", hidden=True)

    result = search_product("Pepsi", sql_session)

    assert result is hidden_product


def test_search_product_visible_only_excludes_hidden_exact_match(sql_session: Session) -> None:
    _make_product(sql_session, "1234567890", "Pepsi", hidden=True)

    result = search_product("Pepsi", sql_session, find_hidden_products=False)

    assert result == []


def test_search_product_visible_only_excludes_hidden_partial_match(sql_session: Session) -> None:
    _make_product(sql_session, "1234567890", "Pepsi", hidden=True)

    result = search_product("Pep", sql_session, find_hidden_products=False)

    assert result == []


def test_search_product_visible_only_exact_match_ignores_case(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1234567890", "Pepsi", hidden=False)

    result = search_product("pepsi", sql_session, find_hidden_products=False)

    assert result is pepsi


def test_search_product_visible_only_finds_hidden_by_bar_code(sql_session: Session) -> None:
    hidden_product = _make_product(sql_session, "1234567890", "Pepsi", hidden=True)

    result = search_product("1234567890", sql_session, find_hidden_products=False)

    assert result is hidden_product


def test_search_product_rejects_empty_string(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        search_product("", sql_session)
