from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import Product
from dibbler.queries.search_product import search_product


def test_search_product_no_products(sql_session: Session) -> None:
    pass


def test_search_product_name_exact_match(sql_session: Session) -> None:
    pass


def test_search_product_name_partial_match(sql_session: Session) -> None:
    pass


def test_search_product_name_no_match(sql_session: Session) -> None:
    pass


def test_search_product_barcode_exact_match(sql_session: Session) -> None:
    pass


def test_search_product_hidden_products(sql_session: Session) -> None:
    pass


def test_search_product_find_hidden_products(sql_session: Session) -> None:
    pass
