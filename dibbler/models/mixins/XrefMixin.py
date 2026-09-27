from sqlalchemy.orm import declared_attr

from dibbler.lib.helpers import pascal_case_to_snake_case


class XrefMixin:
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return f"xref_{pascal_case_to_snake_case(cls.__name__)}"
