_TREE_CHARS = {
    "normal": {
        "vertical": "│  ",
        "branch": "├─ ",
        "last": "└─ ",
        "empty": "   ",
    },
    "ascii": {
        "vertical": "|   ",
        "branch": "|-- ",
        "last": "`-- ",
        "empty": "    ",
    },
}

assert set(_TREE_CHARS["normal"].keys()) == set(_TREE_CHARS["ascii"].keys())
assert all(len(v) == 3 for v in _TREE_CHARS["normal"].values())
assert all(len(v) == 4 for v in _TREE_CHARS["ascii"].values())


def render_tree(
    tree: list[str | list],
    ascii_only: bool = False,
) -> str:
    """
    Render a tree structure as a string.

    Each item in the `tree` list can be either a string (a leaf node)
    or another list (a subtree).

    When `ascii_only` is `True`, only ASCII characters are used for drawing the tree.

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
    |-- root
    |   |-- child1
    |   |   |-- grandchild1
    |   |   `-- grandchild2
    |   `-- child2
    `-- root2
    ```
    """

    result: list[str] = []
    for index, item in enumerate(tree):
        is_last = index == len(tree) - 1
        item_lines = _render_tree_line(item, is_last, ascii_only)
        result.extend(item_lines)
    return "\n".join(result)


def _render_tree_line(
    item: str | list,
    is_last: bool,
    ascii_only: bool,
    prefix: str = "",
) -> list[str]:
    chars = _TREE_CHARS["ascii"] if ascii_only else _TREE_CHARS["normal"]
    lines: list[str] = []

    if isinstance(item, str):
        line_prefix = chars["last"] if is_last else chars["branch"]
        item_lines = item.splitlines()
        for line_index, line in enumerate(item_lines):
            if line_index == 0:
                lines.append(f"{prefix}{line_prefix}{line}")
            else:
                lines.append(f"{prefix}{chars['vertical']}{line}")

    elif isinstance(item, list):
        new_prefix = prefix + (chars["empty"] if is_last else chars["vertical"])
        for sub_index, sub_item in enumerate(item):
            sub_is_last = sub_index == len(item) - 1
            sub_lines = _render_tree_line(sub_item, sub_is_last, ascii_only, new_prefix)
            lines.extend(sub_lines)
    else:
        raise ValueError("Item must be either a string or a list.")

    return lines
