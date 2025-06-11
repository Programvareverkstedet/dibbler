from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from dibbler.models import Product


def search_product(
    string: str,
    session: Session,
    find_hidden_products=True,
) -> Product | list[Product]:
    if find_hidden_products:
        exact_match = (
            session.query(Product)
            .filter(or_(Product.bar_code == string, Product.name == string))
            .first()
        )
    else:
        exact_match = (
            session.query(Product)
            .filter(
                or_(
                    Product.bar_code == string,
                    and_(Product.name == string, not Product.hidden),
                )
            )
            .first()
        )
    if exact_match:
        return exact_match
    if find_hidden_products:
        product_list = (
            session.query(Product)
            .filter(
                or_(
                    Product.bar_code.ilike(f"%{string}%"),
                    Product.name.ilike(f"%{string}%"),
                )
            )
            .all()
        )
    else:
        product_list = (
            session.query(Product)
            .filter(
                or_(
                    Product.bar_code.ilike(f"%{string}%"),
                    and_(Product.name.ilike(f"%{string}%"), not Product.hidden),
                )
            )
            .all()
        )
    return product_list
