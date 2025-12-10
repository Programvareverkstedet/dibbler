from dibbler.lib.render_tree import render_tree
from dibbler.models import Transaction, TransactionType
from dibbler.models.Transaction import EXPECTED_FIELDS


def render_transaction_log(transaction_log: list[Transaction]) -> str:
    """
    Renders a transaction log as a pretty, human-readable string.
    """

    aggregated_log = _aggregate_joint_transactions(transaction_log)

    lines = []
    for transaction in aggregated_log:
        if isinstance(transaction, list):
            inner_lines = []
            lines.append(_render_transaction(transaction[0]))
            for sub_transaction in transaction[1:]:
                line = _render_transaction(sub_transaction)
                inner_lines.append(line)
            lines.append(inner_lines)
        else:
            line = _render_transaction(transaction)
            lines.append(line)

    return render_tree(lines)


def _aggregate_joint_transactions(
    transactions: list[Transaction],
) -> list[Transaction | list[Transaction]]:
    aggregated: list[Transaction | list[Transaction]] = []

    i = 0
    while i < len(transactions):
        current = transactions[i]

        # The aggregation is running backwards, so it will hit JOINT transactions first
        if current.type_ == TransactionType.JOINT:
            joint_transactions = [current]
            j = i
            while j < len(transactions):
                j += 1
                next_transaction = transactions[j]
                if next_transaction.type_ == TransactionType.JOINT_BUY_PRODUCT:
                    joint_transactions.append(next_transaction)
                else:
                    break
            aggregated.append(joint_transactions)
            i = j  # Skip processed transactions
        elif current.type_ == TransactionType.JOINT:
            # Empty joint transaction?
            i += 1
            continue
        else:
            aggregated.append(current)
            i += 1
    return aggregated


def _render_transaction(transaction: Transaction) -> str:
    match transaction.type_:
        case TransactionType.ADD_PRODUCT:
            line = f"ADD_PRODUCT({transaction.id}, {transaction.user.name}"
            for field in EXPECTED_FIELDS[TransactionType.ADD_PRODUCT]:
                value = getattr(transaction, field)
                line += f", {field}={value}"
            line += ")"
        case TransactionType.BUY_PRODUCT:
            line = f"BUY_PRODUCT({transaction.id}, {transaction.user.name}"
            for field in EXPECTED_FIELDS[TransactionType.BUY_PRODUCT]:
                value = getattr(transaction, field)
                line += f", {field}={value}"
            line += ")"
        case TransactionType.ADJUST_STOCK:
            line = f"ADJUST_STOCK({transaction.id}, {transaction.user.name}"
            for field in EXPECTED_FIELDS[TransactionType.ADJUST_STOCK]:
                value = getattr(transaction, field)
                line += f", {field}={value}"
            line += ")"
        case TransactionType.ADJUST_PENALTY:
            line = f"ADJUST_PENALTY({transaction.id}, {transaction.user.name}"
            for field in EXPECTED_FIELDS[TransactionType.ADJUST_PENALTY]:
                value = getattr(transaction, field)
                line += f", {field}={value}"
            line += ")"
        case TransactionType.ADJUST_INTEREST:
            line = f"ADJUST_INTEREST({transaction.id}, {transaction.user.name}"
            for field in EXPECTED_FIELDS[TransactionType.ADJUST_INTEREST]:
                value = getattr(transaction, field)
                line += f", {field}={value}"
            line += ")"
        case TransactionType.ADJUST_BALANCE:
            line = f"ADJUST_BALANCE({transaction.id}, {transaction.user.name}"
            for field in EXPECTED_FIELDS[TransactionType.ADJUST_BALANCE]:
                value = getattr(transaction, field)
                line += f", {field}={value}"
            line += ")"
        case TransactionType.JOINT:
            line = f"JOINT({transaction.id}, {transaction.user.name}"
            for field in EXPECTED_FIELDS[TransactionType.JOINT]:
                value = getattr(transaction, field)
                line += f", {field}={value}"
            line += ")"
        case TransactionType.JOINT_BUY_PRODUCT:
            line = f"JOINT_BUY_PRODUCT({transaction.id}, {transaction.user.name}"
            for field in EXPECTED_FIELDS[TransactionType.JOINT_BUY_PRODUCT]:
                value = getattr(transaction, field)
                line += f", {field}={value}"
            line += ")"
        case _:
            line = (
                f"UNKNOWN[{transaction.type_}](id={transaction.id}, user_id={transaction.user_id})"
            )
    return line
