import argparse
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from dibbler.conf import load_config, config_db_string

parser = argparse.ArgumentParser()

parser.add_argument(
    "-c",
    "--config",
    help="Path to the config file",
    type=Path,
    metavar="FILE",
    required=False,
)

subparsers = parser.add_subparsers(
    title="subcommands",
    dest="subcommand",
    required=True,
)
subparsers.add_parser("loop", help="Run the dibbler loop")
subparsers.add_parser("create-db", help="Create the database")
subparsers.add_parser("slabbedasker", help="Find out who is slabbedasker")
subparsers.add_parser("seed-data", help="Fill with mock data")


def main():
    args = parser.parse_args()

    load_config(args.config)

    engine = create_engine(config_db_string())
    sql_session = Session(engine)

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


if __name__ == "__main__":
    main()
