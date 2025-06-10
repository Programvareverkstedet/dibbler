from sqlalchemy import MetaData
from sqlalchemy.orm import (
    DeclarativeBase,
    declared_attr,
)
from sqlalchemy.orm.collections import (
    InstrumentedDict,
    InstrumentedList,
    InstrumentedSet,
)


def _pascal_case_to_snake_case(name: str) -> str:
    return "".join(["_" + i.lower() if i.isupper() else i for i in name]).lstrip("_")


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return _pascal_case_to_snake_case(cls.__name__)

    def __repr__(self) -> str:
        columns = ", ".join(
            f"{k}={repr(v)}"
            for k, v in self.__dict__.items()
            if not any(
                [
                    k.startswith("_"),
                    # Ensure that we don't try to print out the entire list of
                    # relationships, which could create an infinite loop
                    isinstance(v, Base),
                    isinstance(v, InstrumentedList),
                    isinstance(v, InstrumentedSet),
                    isinstance(v, InstrumentedDict),
                ]
            )
        )
        return f"<{self.__class__.__name__}({columns})>"
