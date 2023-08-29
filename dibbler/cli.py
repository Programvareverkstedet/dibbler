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

def main():
    args = parser.parse_args()
    config.read(args.config)

    import dibbler.text_based as text_based

    text_based.main()

if __name__ == "__main__":
    main()