import argparse
import sys

from dibbler.conf import DEFAULT_CONFIG_PATH, config, default_config_path_submissive_and_readable

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


def main():
    args = parser.parse_args()

    if args.config is not None:
        config.read(args.config)
    elif default_config_path_submissive_and_readable():
        config.read(DEFAULT_CONFIG_PATH)
    else:
        print("Could not read config file, it was neither provided nor readable in default location", file=sys.stderr)

    if args.subcommand == "loop":
        import dibbler.subcommands.loop as loop

        loop.main()

    elif args.subcommand == "create-db":
        import dibbler.subcommands.makedb as makedb

        makedb.main()

    elif args.subcommand == "slabbedasker":
        import dibbler.subcommands.slabbedasker as slabbedasker

        slabbedasker.main()

    elif args.subcommand == "seed-data":
        import dibbler.subcommands.seed_test_data as seed_test_data

        seed_test_data.main()


if __name__ == "__main__":
    main()
