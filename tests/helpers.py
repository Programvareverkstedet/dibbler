from datetime import datetime, timedelta

from dibbler.models import Transaction


def assign_times(
    transactions: list[Transaction],
    start_time: datetime = datetime(2024, 1, 1, 0, 0, 0),
    delta: timedelta = timedelta(minutes=1),
) -> None:
    """Assigns datetimes to a list of transactions starting from start_time and incrementing by delta."""
    current_time = start_time
    for transaction in transactions:
        transaction.time = current_time
        current_time += delta


def assert_id_order_similar_to_time_order(transactions: list[Transaction]) -> None:
    """Asserts that the order of transaction IDs is similar to the order of their timestamps."""
    sorted_by_time = sorted(transactions, key=lambda t: t.time)
    sorted_by_id = sorted(transactions, key=lambda t: t.id)

    for t1, t2 in zip(sorted_by_time, sorted_by_id, strict=False):
        assert t1.id == t2.id or t1.time == t2.time, (
            f"Transaction ID order does not match time order:\n"
            f"ID {t1.id} at time {t1.time}\n"
            f"ID {t2.id} at time {t2.time}"
        )
