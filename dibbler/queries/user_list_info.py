from collections.abc import Iterator
from datetime import datetime
from typing import NamedTuple

from sqlalchemy import Integer, Select, case, func, select
from sqlalchemy.orm import Session

from dibbler.lib.sql_helpers import DEFAULT_STREAMING_ITER_CHUNK_SIZE, iter_rows_in_chunks
from dibbler.models import TransactionLog, TransactionLogProduct, TransactionLogUser, User
from dibbler.models.enums import TransactionLogEntryType


class UserListInfo(NamedTuple):
    user: User
    products_bought: int
    products_added: int
    last_activity: datetime | None


def user_list_info_query() -> Select[tuple[User, int, int, datetime | None]]:
    # A user appearing several times in the same trx should only count it once.
    trx_users = (
        select(TransactionLogUser.transaction_log_id, TransactionLogUser.user_id)
        .distinct()
        .subquery()
    )

    activity = (
        select(
            trx_users.c.user_id,
            func.max(TransactionLog.time).label("last_activity"),
        )
        .join(TransactionLog, TransactionLog.id == trx_users.c.transaction_log_id)
        .group_by(trx_users.c.user_id)
        .subquery()
    )

    bought = func.sum(
        case(
            (
                TransactionLog.type == TransactionLogEntryType.BUY_PRODUCT,
                -TransactionLogProduct.amount,
            ),
            else_=0,
        ),
        type_=Integer,
    )
    added = func.sum(
        case(
            (
                TransactionLog.type == TransactionLogEntryType.ADD_PRODUCT,
                TransactionLogProduct.amount,
            ),
            else_=0,
        ),
        type_=Integer,
    )

    totals = (
        select(
            trx_users.c.user_id,
            bought.label("bought"),
            added.label("added"),
        )
        .join(TransactionLog, TransactionLog.id == trx_users.c.transaction_log_id)
        .join(TransactionLogProduct, TransactionLogProduct.transaction_log_id == TransactionLog.id)
        .where(
            TransactionLog.type.in_(
                [TransactionLogEntryType.BUY_PRODUCT, TransactionLogEntryType.ADD_PRODUCT],
            ),
        )
        .group_by(trx_users.c.user_id)
        .subquery()
    )

    return (
        select(
            User,
            func.coalesce(totals.c.bought, 0),
            func.coalesce(totals.c.added, 0),
            activity.c.last_activity,
        )
        .outerjoin(totals, totals.c.user_id == User.id)
        .outerjoin(activity, activity.c.user_id == User.id)
        .order_by(User.name)
    )


def user_list_info(sql_session: Session) -> list[UserListInfo]:
    """Retrieve all users with their products bought/added counts and last activity."""
    return [UserListInfo(*row) for row in sql_session.execute(user_list_info_query())]


def user_list_info_stream(
    sql_session: Session,
    chunk_size: int = DEFAULT_STREAMING_ITER_CHUNK_SIZE,
) -> Iterator[UserListInfo]:
    """Streaming variant of `user_list_info`, which fetches `chunk_size` users at a time."""
    query = user_list_info_query()
    return (UserListInfo(*row) for row in iter_rows_in_chunks(sql_session, query, chunk_size))
