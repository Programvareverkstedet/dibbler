import argparse
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from dibbler.conf import config_db_string, load_config
from dibbler.lib.check_db_health import check_db_health


def _parse_time(string: str) -> datetime:
    try:
        return datetime.fromisoformat(string)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid time {string}") from None


parser = argparse.ArgumentParser()

parser.add_argument(
    "-c",
    "--config",
    help="Path to the config file",
    type=Path,
    metavar="FILE",
    required=False,
)

parser.add_argument(
    "-V",
    "--version",
    help="Show program version",
    action="store_true",
    default=False,
)

subparsers = parser.add_subparsers(
    title="subcommands",
    dest="subcommand",
)
subparsers.add_parser("verify-config", help="Statically verify the config file")
subparsers.add_parser("loop", help="Run the dibbler loop")
subparsers.add_parser("create-db", help="Create the database")
subparsers.add_parser("slabbedasker", help="Find out who is slabbedasker")
subparsers.add_parser("seed-data", help="Fill with mock data")
transaction_log_parser = subparsers.add_parser("transaction-log", help="Print transaction log")
transaction_log_parser.add_argument(
    "-n",
    "--limit",
    help="Only show the N most recent entries",
    type=int,
    metavar="NUM",
)
transaction_log_parser.add_argument(
    "--after",
    help="Only show entries after this date (e.g. 2024-01-31)",
    type=_parse_time,
    metavar="DATE",
)
transaction_log_parser.add_argument(
    "--before",
    help="Only show entries before this date (e.g. 2024-01-31)",
    type=_parse_time,
    metavar="DATE",
)
transaction_log_parser.add_argument(
    "--reverse",
    help="Show the oldest entries at the top",
    action="store_true",
)
_transaction_log_subject = transaction_log_parser.add_mutually_exclusive_group()
_transaction_log_subject.add_argument(
    "--user",
    help="Only show entries involving this user (name or id)",
    metavar="USER",
)
_transaction_log_subject.add_argument(
    "--product",
    help="Only show entries involving this product (name or id)",
    metavar="PRODUCT",
)


def main() -> None:
    args = parser.parse_args()

    if args.version:
        from ._version import commit_id, version

        print(f"Dibbler version {version}, commit {commit_id if commit_id else '<unknown>'}")
        return

    if not args.subcommand:
        parser.print_help()
        sys.exit(1)

    load_config(args.config)

    if args.subcommand == "verify-config":
        return

    engine = create_engine(config_db_string())

    if args.subcommand == "create-db":
        import dibbler.subcommands.makedb as makedb

        makedb.main(engine)
        return

    sql_session = Session(
        engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
        close_resets_only=True,
    )

    check_db_health(engine, verify_table_existence=True)

    if args.subcommand == "loop":
        import dibbler.subcommands.loop as loop

        loop.main(sql_session)

    elif args.subcommand == "slabbedasker":
        import dibbler.subcommands.slabbedasker as slabbedasker

        slabbedasker.main(sql_session)

    elif args.subcommand == "seed-data":
        import dibbler.subcommands.seed_test_data as seed_test_data

        seed_test_data.main(sql_session)

    elif args.subcommand == "transaction-log":
        import dibbler.subcommands.transaction_log as transaction_log

        transaction_log.main(
            sql_session,
            user=args.user,
            product=args.product,
            after_time=args.after,
            before_time=args.before,
            limit=args.limit,
            reverse=args.reverse,
        )


if __name__ == "__main__":
    main()
