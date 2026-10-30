import sqlite3
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")
DB = Path("data/olist.db")

TABLES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "product_category_name_translation": "product_category_name_translation.csv",
}


def load():
    DB.unlink(missing_ok=True)
    conn = sqlite3.connect(DB)
    for table, filename in TABLES.items():
        df = pd.read_csv(RAW / filename, encoding="utf-8-sig")
        df.to_sql(table, conn, index=False)
        print(f"{table:<35} {len(df):>8,}")
    conn.close()


if __name__ == "__main__":
    load()
