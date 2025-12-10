import pytest
from sqlalchemy.orm import Session


@pytest.mark.skip(reason="Not yet implemented")
def test_joint_buy_product_missing_product(sql_session: Session) -> None: ...


@pytest.mark.skip(reason="Not yet implemented")
def test_joint_buy_product_missing_user(sql_session: Session) -> None: ...


@pytest.mark.skip(reason="Not yet implemented")
def test_joint_buy_product_out_of_stock(sql_session: Session) -> None: ...


@pytest.mark.skip(reason="Not yet implemented")
def test_joint_buy_product(sql_session: Session) -> None: ...


@pytest.mark.skip(reason="Not yet implemented")
def test_joint_buy_product_duplicate_user(sql_session: Session) -> None: ...


@pytest.mark.skip(reason="Not yet implemented")
def test_joint_buy_product_non_involved_instigator(sql_session: Session) -> None: ...
