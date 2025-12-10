from dibbler.db import Session
from dibbler.lib.render_transaction_log import render_transaction_log
from dibbler.queries import transaction_log


def main() -> None:
    sql_session = Session()

    result = transaction_log(sql_session)
    rendered = render_transaction_log(result)

    print(rendered)


if __name__ == "__main__":
    main()
