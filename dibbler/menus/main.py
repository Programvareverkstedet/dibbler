import sys
import signal
import traceback

from sqlalchemy import (
    event,
)
from sqlalchemy.orm import Session

from libdib.repl import (
    NumberedCmd,
    InteractiveItemSelector,
    prompt_yes_no,
)

from dibbler.conf import config

class DibblerCli(NumberedCmd):
    def __init__(self, sql_session: Session):
        super().__init__()
        self.sql_session = sql_session
        self.sql_session_dirty = False

        @event.listens_for(self.sql_session, "after_flush")
        def mark_session_as_dirty(*_):
            self.sql_session_dirty = True
            self.prompt_header = "(unsaved changes)"

        @event.listens_for(self.sql_session, "after_commit")
        @event.listens_for(self.sql_session, "after_rollback")
        def mark_session_as_clean(*_):
            self.sql_session_dirty = False
            self.prompt_header = None

    # TODO: move to libdib.repl
    @classmethod
    def run_with_safe_exit_wrapper(cls, sql_session: Session):
        tool = cls(sql_session)

        if not config.getboolean("general", "stop_allowed"):
            signal.signal(signal.SIGQUIT, signal.SIG_IGN)

        if not config.getboolean("general", "stop_allowed"):
            signal.signal(signal.SIGTSTP, signal.SIG_IGN)

        while True:
            try:
                tool.cmdloop()
            except KeyboardInterrupt:
                if not tool.sql_session_dirty:
                    exit(0)
                try:
                    print()
                    if prompt_yes_no(
                        "Are you sure you want to exit without saving?", default=False
                    ):
                        raise KeyboardInterrupt
                except KeyboardInterrupt:
                    if tool.sql_session is not None:
                        tool.sql_session.rollback()
                    exit(0)
            except Exception:
                print("Something went wrong.")
                print(f"{sys.exc_info()[0]}: {sys.exc_info()[1]}")
                if config.getboolean("general", "show_tracebacks"):
                    traceback.print_tb(sys.exc_info()[2])

    def default(self, maybe_barcode: str):
        raise NotImplementedError(
            "This command is not implemented yet. Please use the numbered commands instead."
        )

    def do_buy(self, arg: str):
        ...

    def do_product_list(self, arg: str):
        ...

    def do_show_user(self, arg: str):
        ...

    def do_user_list(self, arg: str):
        ...

    def do_adjust_credit(self, arg: str):
        ...

    def do_transfer(self, arg: str):
        ...

    def do_add_stock(self, arg: str):
        ...

    def do_add_edit(self, arg: str):
        ...
        # AddEditMenu(self.sql_session).cmdloop()

    def do_product_search(self, arg: str):
        ...

    def do_statistics(self, arg: str):
        ...

    def do_faq(self, arg: str):
        ...

    def do_print_label(self, arg: str):
        ...


    def do_exit(self, _: str):
        if self.sql_session_dirty:
            if prompt_yes_no("Would you like to save your changes?"):
                self.sql_session.commit()
            else:
                self.sql_session.rollback()
        exit(0)

    funcs = {
        0: {
            "f": default,
            "doc": "Choose / Add item with its ISBN",
        },
        1: {
            "f": do_buy,
            "doc": "Buy",
        },
        2: {
            "f": do_product_list,
            "doc": "Product List",
        },
        3: {
            "f": do_show_user,
            "doc": "Show User",
        },
        4: {
            "f": do_user_list,
            "doc": "User List",
        },
        5: {
            "f": do_adjust_credit,
            "doc": "Adjust Credit",
        },
        6: {
            "f": do_transfer,
            "doc": "Transfer",
        },
        7: {
            "f": do_add_stock,
            "doc": "Add Stock",
        },
        8: {
            "f": do_add_edit,
            "doc": "Add/Edit",
        },
        9: {
            "f": do_product_search,
            "doc": "Product Search",
        },
        10: {
            "f": do_statistics,
            "doc": "Statistics",
        },
        11: {
            "f": do_faq,
            "doc": "FAQ",
        },
        12: {
            "f": do_print_label,
            "doc": "Print Label",
        },
        13: {
            "f": do_exit,
            "doc": "Exit",
        },
    }
