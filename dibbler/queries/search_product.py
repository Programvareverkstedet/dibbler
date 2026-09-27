from sqlalchemy import and_, not_, or_
from sqlalchemy.orm import Session

from dibbler.models import Product


def search_product(
    string: str,
    sql_session: Session,
    find_hidden_products: bool = True,
) -> Product | list[Product] | None:
    assert sql_session is not None

    if not string:
        raise ValueError("Search string cannot be empty.")

    if find_hidden_products:
        exact_match = (
            sql_session.query(Product)
            .filter(or_(Product.bar_code == string, Product.name == string))
            .first()
        )
    else:
        exact_match = (
            sql_session.query(Product)
            .filter(
                or_(
                    Product.bar_code == string,
                    and_(
                        Product.name == string,
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
                    Product.bar_code.ilike(f"%{string}%"),
                    Product.name.ilike(f"%{string}%"),
                ),
            )
            .all()
        )
    else:
        product_list = (
            sql_session.query(Product)
            .filter(
                or_(
                    Product.bar_code.ilike(f"%{string}%"),
                    and_(
                        Product.name.ilike(f"%{string}%"),
                        not_(Product.hidden),
                    ),
                ),
            )
            .all()
        )
    return product_list
