import argparse

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
    title='subcommands',
    dest='subcommand',
    required=True,
)
subparsers.add_parser(
    'loop',
    help='Run the dibbler loop'
)
subparsers.add_parser(
    'create-db',
    help='Create the database'
)
subparsers.add_parser(
    'slabbedasker',
    help='Find out who is slabbedasker'
)

def main():
    args = parser.parse_args()
    config.read(args.config)

    if args.subcommand == 'loop':
      import dibbler.text_based as text_based
      text_based.main()

    elif args.subcommand == 'create-db':
      import dibbler.scripts.makedb as makedb
      makedb.main()

    elif args.subcommand == 'slabbedasker':
      import dibbler.scripts.slabbedasker as slabbedasker
      slabbedasker.main()


if __name__ == "__main__":
    main()