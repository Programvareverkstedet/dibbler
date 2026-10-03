import re
from datetime import datetime
from typing import Any

from sqlalchemy import insert, literal, select, update
from sqlalchemy.orm import Session

from dibbler.models import (
    Product,
    ProductBarcode,
    ProductLog,
    ProductMergedBarcode,
    ProductMergedTransaction,
    PurchaseEntry,
    TransactionLog,
    TransactionLogProduct,
    TransactionLogUser,
    User,
)
from dibbler.models.enums import ProductLogEntryType, TransactionLogEntryType

UNSET: Any = object()


def merge_products(
    sql_session: Session,
    user: User,
    source: Product,
    target: Product,
    name: str = UNSET,
    price: int = UNSET,
    hidden: bool = UNSET,
    stock: int = UNSET,
) -> Product:
    if source.id == target.id:
        raise ValueError("Cannot merge a product into itself.")

    if name is not UNSET and not name:
        raise ValueError("Name cannot be empty.")

    if name is not UNSET and not re.fullmatch(Product.name_re, name):
        raise ValueError("Name has an invalid format.")

    if name is not UNSET and len(name) > Product.name_length:
        raise ValueError(f"Name must be at most {Product.name_length} characters.")

    if price is not UNSET and price <= 0:
        raise ValueError("Price must be positive.")

    merge_log = ProductLog(
        type=ProductLogEntryType.MERGE,
        time=datetime.now(),
        product_id=target.id,
        merged_product_id=source.id,
    )
    sql_session.add(merge_log)
    sql_session.flush()

    # Remember which rows belonged to the source, so that the merge can be undone later.
    sql_session.execute(
        insert(ProductMergedBarcode).from_select(
            ["merge_log_id", "bar_code"],
            select(literal(merge_log.id), ProductBarcode.code).where(
                ProductBarcode.product_id == source.id,
            ),
        ),
    )
    sql_session.execute(
        insert(ProductMergedTransaction).from_select(
            ["merge_log_id", "transaction_log_product_id"],
            select(literal(merge_log.id), TransactionLogProduct.id).where(
                TransactionLogProduct.product_id == source.id,
            ),
        ),
    )

    sql_session.execute(
        update(ProductBarcode)
        .where(ProductBarcode.product_id == source.id)
        .values(product_id=target.id),
    )
    sql_session.expire(source, ["barcodes"])

    sql_session.execute(
        update(PurchaseEntry)
        .where(PurchaseEntry.product_id == source.id)
        .values(product_id=target.id),
    )

    sql_session.expire(source, ["purchases"])

    sql_session.execute(
        update(TransactionLogProduct)
        .where(TransactionLogProduct.product_id == source.id)
        .values(product_id=target.id),
    )

    edited_name = name if name is not UNSET and name != target.name else None
    edited_price = price if price is not UNSET and price != target.price else None
    edited_hidden = hidden if hidden is not UNSET and hidden != target.hidden else None

    if edited_name is not None:
        target.name = edited_name
    if edited_price is not None:
        target.price = edited_price
    if edited_hidden is not None:
        target.hidden = edited_hidden

    if edited_name is not None or edited_price is not None or edited_hidden is not None:
        sql_session.add(
            ProductLog(
                type=ProductLogEntryType.EDIT,
                time=datetime.now(),
                product_id=target.id,
                name=edited_name,
                price=edited_price,
                hidden=edited_hidden,
                merge_ref_id=merge_log.id,
            ),
        )

    logged_stock = target.stock + source.stock
    if stock is UNSET:
        stock = target.stock
    target.stock = stock

    if stock != logged_stock:
        diff = stock - logged_stock

        header = TransactionLog(
            type=TransactionLogEntryType.ADJUST_STOCK,
            time=datetime.now(),
            merge_ref_id=merge_log.id,
        )
        sql_session.add(header)
        sql_session.add(
            TransactionLogUser(
                transaction=header,
                user=user,
            ),
        )
        sql_session.add(
            TransactionLogProduct(
                transaction=header,
                product=target,
                amount=diff,
                price_at_time=target.price,
            ),
        )

    sql_session.add(
        ProductLog(
            type=ProductLogEntryType.DELETE,
            time=datetime.now(),
            product_id=source.id,
            merge_ref_id=merge_log.id,
        ),
    )

    sql_session.delete(source)
    sql_session.flush()

    sql_session.expire_all()

    return target
