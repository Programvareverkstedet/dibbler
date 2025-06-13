from sqlalchemy import and_, literal, or_, select
from sqlalchemy.orm import Session

from dibbler.models import Product


def search_product(
    string: str,
    sql_session: Session,
    find_hidden_products=True,
) -> Product | list[Product]:
    exact_match = sql_session.scalars(
        select(Product).where(
            or_(
                Product.bar_code == string,
                and_(
                    Product.name == string,
                    literal(True) if find_hidden_products else not Product.hidden,
                ),
            )
        )
    ).first()

    if exact_match:
        return exact_match

    product_list = sql_session.scalars(
        select(Product).where(
            or_(
                Product.bar_code.ilike(f"%{string}%"),
                and_(
                    Product.name.ilike(f"%{string}%"),
                    literal(True) if find_hidden_products else not Product.hidden,
                ),
            )
        )
    ).all()

    return list(product_list)
