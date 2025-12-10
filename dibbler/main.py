import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from dibbler.conf import config_db_string, load_config
from dibbler.lib.check_db_health import check_db_health

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
subparsers.add_parser("loop", help="Run the dibbler loop")
subparsers.add_parser("create-db", help="Create the database")
subparsers.add_parser("slabbedasker", help="Find out who is slabbedasker")
subparsers.add_parser("seed-data", help="Fill with mock data")
subparsers.add_parser("transaction-log", help="Print transaction log")


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

    engine = create_engine(config_db_string())

    sql_session = Session(
        engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
        close_resets_only=True,
    )

    check_db_health(
        engine,
        verify_table_existence=args.subcommand != "create-db",
    )

    if args.subcommand == "loop":
        import dibbler.subcommands.loop as loop

        loop.main(sql_session)

    elif args.subcommand == "create-db":
        import dibbler.subcommands.makedb as makedb

        makedb.main(engine)

    elif args.subcommand == "slabbedasker":
        import dibbler.subcommands.slabbedasker as slabbedasker

        slabbedasker.main(sql_session)

    elif args.subcommand == "seed-data":
        import dibbler.subcommands.seed_test_data as seed_test_data

        seed_test_data.main(sql_session)

    elif args.subcommand == "transaction-log":
        import dibbler.subcommands.transaction_log as transaction_log

        transaction_log.main()


if __name__ == "__main__":
    main()
