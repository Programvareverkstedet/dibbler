import argparse
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from dibbler.conf import config

parser = argparse.ArgumentParser()

parser.add_argument(
    "-c",
    "--config",
    help="Path to the config file",
    type=str,
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


def _get_database_url_from_config() -> str:
    """Get the database URL from the configuration."""
    url = config.get("database", "url")
    if url is not None:
        return url

    url_file = config.get("database", "url_file")
    if url_file is not None:
        with Path(url_file).open() as file:
            return file.read().strip()

    raise ValueError("No database URL found in configuration.")


def _connect_to_database(url: str, **engine_args) -> Session:
    try:
        engine = create_engine(url, **engine_args)
        sql_session = Session(engine)
    except Exception as err:
        print("Error: could not connect to database.")
        print(err)
        exit(1)

    print(f"Debug: Connected to database at '{url}'")
    return sql_session


def main():
    args = parser.parse_args()
    config.read(args.config)

    database_url = _get_database_url_from_config()
    sql_session = _connect_to_database(
      database_url,
      echo=config.getboolean("database", "echo_sql", fallback=False),
    )

    if args.subcommand == "loop":
        import dibbler.subcommands.loop as loop

        loop.main(sql_session)

    elif args.subcommand == "create-db":
        import dibbler.subcommands.makedb as makedb

        makedb.main(sql_session)

    elif args.subcommand == "slabbedasker":
        import dibbler.subcommands.slabbedasker as slabbedasker

        slabbedasker.main(sql_session)

    elif args.subcommand == "seed-data":
        import dibbler.subcommands.seed_test_data as seed_test_data

        seed_test_data.main(sql_session)


if __name__ == "__main__":
    main()
