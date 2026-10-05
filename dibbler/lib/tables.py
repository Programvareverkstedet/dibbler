from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Sequence

MAX_SCREEN_SIZE = 80
SEPARATOR = " | "


@dataclass(frozen=True)
class TableColumn:
    header: str
    """Human-readable name of the column"""

    width: int
    """Width of the column in characters"""

    align: Literal["left", "right"] = "left"
    """Alignment of the column"""

    truncate: bool = False
    """Whether to truncate values longer than `width`"""

    def __post_init__(self) -> None:
        assert len(self.header) <= self.width, (
            f"Header {self.header} is wider than its column ({self.width})"
        )

    def format(self, value: object) -> str:
        text = str(value)
        if self.truncate:
            text = text[: self.width]
        if self.align == "right":
            return text.rjust(self.width)
        return text.ljust(self.width)


class Table:
    """
    An ASCII table that renders one line at a time, meant for use with `streaming_pager`.
    """

    def __init__(self, *columns: TableColumn) -> None:
        self.columns = columns
        assert self.width <= MAX_SCREEN_SIZE, (
            f"Table is {self.width} characters wide, wider than the screen ({MAX_SCREEN_SIZE})"
        )

    @property
    def width(self) -> int:
        return sum(c.width for c in self.columns) + len(SEPARATOR) * (len(self.columns) - 1)

    def row(self, *values: object) -> str:
        cells = (c.format(v) for c, v in zip(self.columns, values, strict=True))
        return SEPARATOR.join(cells).rstrip() + "\n"

    def header(self) -> str:
        return self.row(*(c.header for c in self.columns))

    def hline(self, char: str = "-") -> str:
        return char * self.width + "\n"

    def render(
        self,
        rows: Iterable[Sequence[object]],
        *,
        hline: bool = True,
        footer: Callable[[], Sequence[object]] | None = None,
    ) -> Iterator[str]:
        yield self.header()
        if hline:
            yield self.hline()
        for row in rows:
            yield self.row(*row)
        if footer is not None:
            yield self.hline()
            yield self.row(*footer())
