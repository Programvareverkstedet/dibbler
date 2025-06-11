from sqlalchemy.orm import Session


def test_user_not_allowed_to_transfer_to_self(sql_session: Session) -> None:
    raise NotImplementedError("This test is not implemented yet.")
#     insert_test_data(sql_session)
#     ...

# user1 = sql_session.scalars(select(User).where(User.name == "Test User 1")).one()

# with pytest.raises(ValueError, match="Cannot transfer to self"):
#     user1.transfer(sql_session, user1, 10)  # Attempting to transfer to self
