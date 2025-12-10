from datetime import datetime

from sqlalchemy import BindParameter, bindparam
from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, User

# NOTE: This absolutely needs a cache, else we can't stop recursing until we know all owners for all products...
#
# Since we know that the non-owned products will not get renowned by the user by other means,
# we can just check for ownership on the products that have an ADD_PRODUCT transaction for the user.
# between now and the cached time.
#
# However, the opposite way is more difficult. The cache will store which products are owned by which users,
# but we still need to check if the user passes out of ownership for the item, without needing to check past
# the cache time. Maybe we also need to store the queue number(s) per user/product combo in the cache? What if
# a user has products multiple places in the queue, interleaved with other users?


def user_products(
    sql_session: Session,
    user: User,
    use_cache: bool = True,
    until_time: BindParameter[datetime] | datetime | None = None,
    until_transaction: Transaction | None = None,
    until_inclusive: bool = True,
) -> list[tuple[Product, int]]:
    """
    Returns the list of products owned by the user, along with how many of each product they own.
    """

    if user.id is None:
        raise ValueError("User must be persisted in the database.")

    if not (until_time is None or until_transaction is None):
        raise ValueError("Cannot filter by both until_time and until_transaction.")

    if isinstance(until_time, datetime):
        until_time = BindParameter("until_time", value=until_time)

    if isinstance(until_transaction, Transaction):
        if until_transaction.id is None:
            raise ValueError("until_transaction must be persisted in the database.")
        until_transaction_id = bindparam("until_transaction_id", value=until_transaction.id)
    else:
        until_transaction_id = None

    raise NotImplementedError("Not implemented yet, needs caching system first.")
