from sqlalchemy.orm import declared_attr


class XrefMixin:
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return f"xref_{cls.__name__.lower()}"
