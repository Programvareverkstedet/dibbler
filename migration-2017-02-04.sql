ALTER TABLE pvv_vv.products RENAME TO products_old;
CREATE TABLE pvv_vv.products
(
    product_id serial,
    bar_code character varying(13) NOT NULL,
    name character varying(45),
    price integer,
    stock integer NOT NULL,
    CONSTRAINT product_pkey PRIMARY KEY (product_id),
    CONSTRAINT barcode_unique UNIQUE (bar_code)
)

INSERT INTO pvv_vv.products (bar_code, name, price, stock)
    SELECT bar_code, name, price, stock FROM products_old;

ALTER TABLE pvv_vv.purchase_entries RENAME TO purchase_entries_old;
ALTER TABLE pvv_vv.purchase_entries_old
    RENAME CONSTRAINT purchase_entries_pkey TO purchase_entries_old_pkey;
ALTER TABLE pvv_vv.purchase_entries_old
    RENAME CONSTRAINT purchase_entries_purchase_id_fkey TO purchase_entries_old_purchase_id_fkey;
ALTER TABLE pvv_vv.purchase_entries_old
    RENAME CONSTRAINT purchase_entries_product_bar_code_fkey TO purchase_entries_old_product_bar_code_fkey;

CREATE TABLE pvv_vv.purchase_entries
(
    id serial,
    purchase_id integer,
    product_id integer,
    amount integer,
    CONSTRAINT purchase_entries_pkey PRIMARY KEY (id),
    CONSTRAINT purchase_entries_product_id_fkey FOREIGN KEY (product_id)
        REFERENCES pvv_vv.products (product_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT purchase_entries_purchase_id_fkey FOREIGN KEY (purchase_id)
        REFERENCES pvv_vv.purchases (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);
INSERT INTO purchase_entries (id, purchase_id, product_id, amount)
    SELECT peo.id, peo.purchase_id, p.product_id, peo.amount
        FROM purchase_entries_old AS peo
            JOIN products AS p ON p.bar_code = peo.product_bar_code;
ALTER TABLE pvv_vv.transactions
    ADD COLUMN penalty integer DEFAULT 1;
DROP TABLE products_old;
DROP TABLE purchase_entries_old;
