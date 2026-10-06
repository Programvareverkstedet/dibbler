from sqlalchemy import and_, not_, or_
from sqlalchemy.orm import Session

from dibbler.models import Product, ProductBarcode

_LIKE_ESCAPE_CHAR = "\\"


def search_product(
    sql_session: Session,
    string: str,
    find_hidden_products: bool = True,
) -> Product | list[Product] | None:
    assert sql_session is not None

    if not string:
        raise ValueError("Search string cannot be empty.")

    escaped = (
        string.replace(_LIKE_ESCAPE_CHAR, _LIKE_ESCAPE_CHAR * 2)
        .replace("%", f"{_LIKE_ESCAPE_CHAR}%")
        .replace("_", f"{_LIKE_ESCAPE_CHAR}_")
    )

    if find_hidden_products:
        exact_match = (
            sql_session.query(Product)
            .filter(
                or_(
                    Product.barcodes.any(ProductBarcode.code == string),
                    Product.name.ilike(escaped, escape=_LIKE_ESCAPE_CHAR),
                ),
            )
            .first()
        )
    else:
        exact_match = (
            sql_session.query(Product)
            .filter(
                or_(
                    Product.barcodes.any(ProductBarcode.code == string),
                    and_(
                        Product.name.ilike(escaped, escape=_LIKE_ESCAPE_CHAR),
                        not_(Product.hidden),
                    ),
                ),
            )
            .first()
        )

    if exact_match:
        return exact_match

    if find_hidden_products:
        product_list = (
            sql_session.query(Product)
            .filter(
                or_(
                    Product.barcodes.any(
                        ProductBarcode.code.ilike(f"%{escaped}%", escape=_LIKE_ESCAPE_CHAR),
                    ),
                    Product.name.ilike(f"%{escaped}%", escape=_LIKE_ESCAPE_CHAR),
                ),
            )
            .all()
        )
    else:
        product_list = (
            sql_session.query(Product)
            .filter(
                or_(
                    Product.barcodes.any(
                        ProductBarcode.code.ilike(f"%{escaped}%", escape=_LIKE_ESCAPE_CHAR),
                    ),
                    and_(
                        Product.name.ilike(f"%{escaped}%", escape=_LIKE_ESCAPE_CHAR),
                        not_(Product.hidden),
                    ),
                ),
            )
            .all()
        )

    return product_list
