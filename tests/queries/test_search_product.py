from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import Product
from dibbler.queries import search_product


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

# Should not be able to find hidden products
def test_search_product_hidden_products(sql_session: Session) -> None:
    pass

# Should be able to find hidden products if specified
def test_search_product_find_hidden_products(sql_session: Session) -> None:
    pass

# Should be able to find hidden products by barcode despite not specified
def test_search_product_hidden_products_by_barcode(sql_session: Session) -> None:
    pass
