from collections.abc import Iterable, Iterator
from datetime import date
from textwrap import fill

from dibbler.models import TransactionLog
from dibbler.models.enums import TransactionLogEntryType

# NOTE: ikik, this code is not very beautiful, nor very readable.
#       if you came over this and gasped audibly, feel free to refactor.

_TREE_CHARS = {
    "normal": {
        "vertical": "│  ",
        "branch": "├─ ",
        "last": "└─ ",
        "empty": "   ",
    },
    "ascii": {
        "vertical": "|  ",
        "branch": "|- ",
        "last": "`- ",
        "empty": "   ",
    },
}

assert len({frozenset(charset) for charset in _TREE_CHARS.values()}) == 1
assert all(len({len(piece) for piece in charset.values()}) == 1 for charset in _TREE_CHARS.values())


def _tree_chars(ascii_only: bool) -> dict[str, str]:
    return _TREE_CHARS["ascii"] if ascii_only else _TREE_CHARS["normal"]


def _render_tree_items(
    items: list[str | list],
    chars: dict[str, str],
    prefix: str,
    closed: bool,
) -> list[str]:
    lines: list[str] = []
    for index, item in enumerate(items):
        if isinstance(item, list):
            is_last = closed and index == len(items) - 1
            child_prefix = prefix + (chars["empty"] if is_last else chars["vertical"])
            lines.extend(_render_tree_items(item, chars, child_prefix, closed=True))

        else:
            has_children = index + 1 < len(items) and isinstance(items[index + 1], list)
            last_index = index + 1 if has_children else index
            is_last = closed and last_index == len(items) - 1

            corner = chars["last"] if is_last else chars["branch"]
            trunk = chars["empty"] if is_last else chars["vertical"]
            first, *rest = item.split("\n")
            lines.append(f"{prefix}{corner}{first}")
            lines.extend(f"{prefix}{trunk}{line}" for line in rest)
    return lines


def render_tree(
    tree: list[str | list],
    *,
    ascii_only: bool = False,
    more_follows: bool = False,
    trailing_newline: bool = False,
) -> str:
    """
    Render a tree structure as a string.

    Each item in the `tree` list can be either a string (a leaf node)
    or another list (the children of the preceding string).
    A string may span multiple lines, the continuation lines are drawn along the trunk.

    - When `ascii_only` is set, only ASCII characters are used for drawing the tree.
    - If `more_follow` is set, the bottom will be rendered as a T branch instead of a corner.
    - Trailing newline does exactly what you expect it to do.

    Example:

    ```python
        tree = [
            "root",
            [
                "child1",
                [
                    "grandchild1",
                    "grandchild2",
                ],
                "child2",
            ],
            "root2",
        ]
        print(render_tree(tree, ascii_only=False))
    ```

    Output:

    ```
    ├─ root
    │  ├─ child1
    │  │  ├─ grandchild1
    │  │  └─ grandchild2
    │  └─ child2
    └─ root2
    ```

    Example with ASCII only:

    ```python
        print(render_tree(tree, ascii_only=True))
    ```

    Output:

    ```
    |- root
    |  |- child1
    |  |  |- grandchild1
    |  |  `- grandchild2
    |  `- child2
    `- root2
    ```
    """
    lines = _render_tree_items(tree, _tree_chars(ascii_only), "", closed=not more_follows)
    return "\n".join(lines) + ("\n" if trailing_newline and lines else "")


def _flag_last(items: Iterable[TransactionLog]) -> Iterator[tuple[TransactionLog, bool]]:
    iterator = iter(items)
    previous = next(iterator, None)
    if previous is None:
        return
    for item in iterator:
        yield previous, False
        previous = item
    yield previous, True


def _render_separator(label: str, ascii_only: bool, width: int = 30) -> str:
    chars = _tree_chars(ascii_only)
    trunk, dash = chars["branch"][:2]
    return f"{trunk}{dash}{dash} {label} ".ljust(width, dash) + dash * 3


def _render_header(entry: TransactionLog) -> str:
    line = f"{entry.time:%H:%M:%S} {entry.type.display_name()}"
    if entry.merge_ref_id is not None:
        line += " (PART OF PRODUCT MERGE)"
    return line


def _day_label(above: date | None, below: date, divider: str) -> str:
    label = f"v {below:%Y-%m-%d}"
    if above is not None:
        label = f"^ {above:%Y-%m-%d} {divider} {label}"
    return label


def _wrap(text: str, width: int, hanging: int = 2) -> str:
    return fill(
        text,
        width=max(width, hanging + 1),
        subsequent_indent=" " * hanging,
        break_on_hyphens=False,
    )


def _render_children(entry: TransactionLog, width: int) -> list[str]:
    """The description, users and products of an entry, each wrapped to `width`."""
    children = []

    if entry.description:
        prefix = "description: "
        children.append(_wrap(prefix + entry.description, width, hanging=len(prefix)))

    for user in sorted(entry.users, key=lambda u: (u.user.name, u.id)):
        line = f"user {user.user.name}: credit_diff={-user.amount:+}"
        if user.penalty not in (None, 1):
            line += f", penalty={user.penalty}"
        children.append(_wrap(line, width))

    for product in sorted(entry.products, key=lambda p: (p.product.name, p.id)):
        name = product.product.name
        if entry.type == TransactionLogEntryType.ADJUST_STOCK:
            line = f"{product.amount:+}stk {name}"
        else:
            line = f"{abs(product.amount)}stk {product.price_at_time}kr {name}"
        children.append(_wrap(line, width))

    return children


def render_transaction_log(
    transaction_log: Iterable[TransactionLog],
    ascii_only: bool = False,
    width: int = 80,
) -> Iterator[str]:
    chars = _tree_chars(ascii_only)
    trunk = chars["vertical"][0]
    indent = len(chars["branch"])
    current_day = None

    for entry, is_last in _flag_last(transaction_log):
        day = entry.time.date()
        if day != current_day:
            if current_day is not None:
                yield f"{trunk}\n"
            label = _day_label(current_day, day, trunk)
            yield f"{_render_separator(label, ascii_only)}\n{trunk}\n"
            current_day = day

        yield render_tree(
            [
                _wrap(_render_header(entry), width - indent),
                _render_children(entry, width - 2 * indent),
            ],
            ascii_only=ascii_only,
            more_follows=not is_last,
            trailing_newline=True,
        )
