import sys
from datetime import datetime
from typing import TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from dibbler.lib.pager import streaming_pager
from dibbler.lib.render_transaction_log import render_transaction_log
from dibbler.lib.sql_helpers import iter_in_chunks
from dibbler.models import Product, User
from dibbler.queries import transaction_log_query

UserOrProduct = TypeVar("UserOrProduct", User, Product)


def _find(
    sql_session: Session,
    model: type[UserOrProduct],
    name_column: InstrumentedAttribute[str],
    id_or_name: str,
) -> UserOrProduct:
    """Find user or product by id or name."""
    if id_or_name.isdecimal() and (found := sql_session.get(model, int(id_or_name))):
        return found

    matches = sql_session.scalars(
        select(model).where(func.lower(name_column) == id_or_name.lower()),
    ).all()

    kind = model.__name__.lower()
    if not matches:
        sys.exit(f"No {kind} with id or name {id_or_name!r}")
    if len(matches) > 1:
        sys.exit(f"Multiple {kind}s are named {id_or_name!r}, use the id instead")
    return matches[0]


def main(
    sql_session: Session,
    user: str | None = None,
    product: str | None = None,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
    limit: int | None = None,
    reverse: bool = False,
) -> None:
    query = transaction_log_query(
        user=_find(sql_session, User, User.name, user) if user is not None else None,
        product=(
            _find(sql_session, Product, Product.name, product) if product is not None else None
        ),
        after_time=after_time,
        before_time=before_time,
        limit=limit,
        newest_first=not reverse,
    )
    lines = render_transaction_log(iter_in_chunks(sql_session, query))

    streaming_pager(lines)
