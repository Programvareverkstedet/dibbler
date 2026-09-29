from datetime import datetime
from typing import NamedTuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from dibbler.models import TransactionLog, User

from .user_product_stats import user_product_stats_query


class UserInfo(NamedTuple):
    last_activity: datetime | None
    products_bought: int
    products_added: int


def user_info(
    sql_session: Session,
    user: User,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
) -> UserInfo:
    """
    Retrieve various information about a user.

    - `last_activity` is the last time the user was active according to trx logs.
    - `products_{bought,added}` are the total amount of items bought/added ever.
    - `after_time` is inclusive and `before_time` is exclusive.
    """

    if after_time is not None and before_time is not None and after_time > before_time:
        raise ValueError("after_time cannot be after before_time.")

    optional_conditions = [
        after_time is not None and TransactionLog.time >= after_time,
        before_time is not None and TransactionLog.time < before_time,
    ]
    conditions = [condition for condition in optional_conditions if not isinstance(condition, bool)]

    last_activity = (
        select(func.max(TransactionLog.time))
        .where(TransactionLog.users.any(user=user), *conditions)
        .scalar_subquery()
    )

    stats = user_product_stats_query(
        user=user,
        after_time=after_time,
        before_time=before_time,
    ).subquery()

    query = select(
        last_activity,
        func.coalesce(func.sum(stats.c.bought), 0),
        func.coalesce(func.sum(stats.c.added), 0),
    ).select_from(stats)

    return UserInfo(*sql_session.execute(query).one())
