#!/usr/bin/python

import codecs
import io
import random
import sys
import traceback
from pathlib import Path
from signal import (
    SIG_IGN,
    SIGQUIT,
    SIGTSTP,
)
from signal import (
    signal as set_signal_handler,
)
from time import ctime, time_ns

from sqlalchemy.orm import Session

from ..conf import config
from ..lib.syslog import get_syslog_logger
from ..menus import (
    AddProductMenu,
    AddStockMenu,
    AddUserMenu,
    AdjustCreditMenu,
    AdjustStockMenu,
    BalanceMenu,
    BuyMenu,
    CleanupStockMenu,
    EditProductMenu,
    EditUserMenu,
    FAQMenu,
    MainMenu,
    Menu,
    MergeProductsMenu,
    PrintLabelMenu,
    ProductListMenu,
    ProductPopularityMenu,
    ProductRevenueMenu,
    ProductSearchMenu,
    ShowUserMenu,
    TransactionLogMenu,
    TransferMenu,
    UserListMenu,
    UsersByDepositsMenu,
    UsersByRestockingMenu,
    UsersBySpendingMenu,
    UsersByWithdrawalsMenu,
)

try:
    from .._version import commit_id, version
except ImportError:
    commit_id = None
    version = None

random.seed()

logger = get_syslog_logger()

CRASHDUMP_DIR = Path("/var/lib/dibbler/crashdumps")

_QUESTION_MARK_CODEC_ERROR_HANDLER_ID = "dibbler-question-mark"


def _replace_with_question_mark(error: UnicodeError) -> tuple[str, int]:
    if not isinstance(error, UnicodeDecodeError):
        raise error

    undecodable_byte = error.object[error.start : error.end]
    as_latin1 = undecodable_byte.decode("iso8859-1")
    logger.warning(
        "Replaced undecodable stdin bytes with '?': %r%s",
        undecodable_byte,
        f" ({as_latin1})" if as_latin1.isprintable() else "",
    )

    return "?", error.end


codecs.register_error(
    _QUESTION_MARK_CODEC_ERROR_HANDLER_ID,
    _replace_with_question_mark,
)


def write_crashdump(exception: BaseException) -> Path:
    CRASHDUMP_DIR.mkdir(parents=True, exist_ok=True)
    crashdump_path = CRASHDUMP_DIR / f"crashdump_{time_ns()}.log"
    with crashdump_path.open("x") as f:
        f.write(f"Dibbler crashdump @ {ctime()}\n")
        if version is not None:
            f.write(
                f"Dibbler version {version}, commit {commit_id if commit_id else '<unknown>'}\n",
            )
        f.write("\n")
        traceback.print_exception(exception, file=f)
    return crashdump_path


def main(sql_session: Session) -> None:
    logger.info(
        "Starting dibbler loop"
        + (f" (version {version}, commit {commit_id or '<unknown>'})" if version else ""),
    )

    if isinstance(sys.stdin, io.TextIOWrapper):
        sys.stdin.reconfigure(errors=_QUESTION_MARK_CODEC_ERROR_HANDLER_ID)

    if not config["general"]["stop_allowed"]:
        set_signal_handler(SIGQUIT, SIG_IGN)

    if not config["general"]["stop_allowed"]:
        set_signal_handler(SIGTSTP, SIG_IGN)

    main_menu = MainMenu(
        sql_session,
        items=[
            BuyMenu(sql_session),
            ProductListMenu(sql_session),
            ShowUserMenu(sql_session),
            UserListMenu(sql_session),
            AdjustCreditMenu(sql_session),
            TransferMenu(sql_session),
            AddStockMenu(sql_session),
            Menu(
                "Add/edit",
                sql_session,
                items=[
                    AddUserMenu(sql_session),
                    EditUserMenu(sql_session),
                    AddProductMenu(sql_session),
                    EditProductMenu(sql_session),
                    MergeProductsMenu(sql_session),
                    AdjustStockMenu(sql_session),
                    CleanupStockMenu(sql_session),
                ],
            ),
            ProductSearchMenu(sql_session),
            TransactionLogMenu(sql_session),
            Menu(
                "Statistics",
                sql_session,
                items=[
                    ProductPopularityMenu(sql_session),
                    ProductRevenueMenu(sql_session),
                    UsersBySpendingMenu(sql_session),
                    UsersByRestockingMenu(sql_session),
                    UsersByDepositsMenu(sql_session),
                    UsersByWithdrawalsMenu(sql_session),
                    BalanceMenu(sql_session),
                ],
            ),
            FAQMenu(sql_session),
            PrintLabelMenu(sql_session),
        ],
        exit_msg="happy happy joy joy",
        exit_confirm_msg="Really quit Dibbler?",
    )
    if not config["general"]["quit_allowed"]:
        main_menu.exit_disallowed_msg = (
            "You can check out any time you like, but you can never leave."
        )
    while True:
        # noinspection PyBroadException
        try:
            main_menu.execute()
        except KeyboardInterrupt:
            print("")
            print("Interrupted.")
        except Exception as e:
            print("Something went wrong.")
            print(f"{type(e)}: {e}")
            if config["general"]["show_tracebacks"]:
                traceback.print_tb(e.__traceback__)

            logger.error(
                "Unhandled exception in main loop: %s: %s",
                type(e).__name__,
                e,
                exc_info=e,
            )
            try:
                crashdump_path = write_crashdump(e)
            except OSError as crashdump_error:
                print(f"Could not write crash dump: {crashdump_error}")
                logger.error("Could not write crash dump: %s", crashdump_error)
            else:
                logger.info("Wrote crash dump to %s", crashdump_path)
        else:
            break
        print("Restarting main menu.")
        try:
            main_menu.sql_session.reset()
        except:  # noqa: S110
            pass
