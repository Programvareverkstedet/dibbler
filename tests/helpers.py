from datetime import datetime, timedelta

from dibbler.models import TransactionLog


def assign_times(
    entries: list[TransactionLog],
    start_time: datetime = datetime(2024, 1, 1, 0, 0, 0),
    delta: timedelta = timedelta(minutes=1),
) -> None:
    """Assigns datetimes to a list of log entries starting from start_time and incrementing by delta."""
    current_time = start_time
    for entry in entries:
        entry.time = current_time
        current_time += delta


def assert_id_order_similar_to_time_order(entries: list[TransactionLog]) -> None:
    """Asserts that the order of entry IDs is similar to the order of their timestamps."""
    sorted_by_time = sorted(entries, key=lambda e: e.time)
    sorted_by_id = sorted(entries, key=lambda e: e.id)

    for e1, e2 in zip(sorted_by_time, sorted_by_id, strict=False):
        assert e1.id == e2.id or e1.time == e2.time, (
            f"Entry ID order does not match time order:\n"
            f"ID {e1.id} at time {e1.time}\n"
            f"ID {e2.id} at time {e2.time}"
        )
