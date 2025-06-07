import random

from sqlalchemy.orm import Session

from ..menus.main import DibblerCli

def main(sql_session: Session):
    random.seed()

    DibblerCli.run_with_safe_exit_wrapper(sql_session)

    exit(0)
