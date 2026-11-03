import sqlite3

from text2sql.executor import DB_PATH

REFERENCE_DATE = "2018-08-31"

# V1: 컬럼 설명 + 코드값 뜻
COLUMN_NOTES = """## Column notes
- customers.customer_id: issued per order. The same person gets a new customer_id on every order.
- customers.customer_unique_id: the real person. Use this to count customers.
- customers.customer_state / sellers.seller_state: 2-letter Brazilian state code (SP = São Paulo, RJ = Rio de Janeiro, MG = Minas Gerais, ...).
- orders.order_status: one of delivered, shipped, canceled, unavailable, invoiced, processing, created, approved.
- orders.order_purchase_timestamp: when the order was placed, text 'YYYY-MM-DD HH:MM:SS'. Use it for all order date filters.
- order_items.price: item price, excluding shipping. order_items.freight_value: shipping cost of the item.
- order_payments.payment_type: one of credit_card, boleto, voucher, debit_card, not_defined.
- order_payments.payment_value: amount paid with that payment method (includes shipping).
- order_reviews.review_score: integer 1 to 5.
- products.product_category_name: category name in Portuguese (e.g. cama_mesa_banho = bed, bath & table).
- product_category_name_translation: maps product_category_name (Portuguese) to product_category_name_english."""

# V1: 업무 용어 정의
BUSINESS_TERMS = """## Business terms
- Revenue (매출): SUM(order_items.price) over orders with order_status = 'delivered'. Excludes shipping.
- Number of customers (고객 수): COUNT(DISTINCT customers.customer_unique_id).
- Number of orders (주문 수): COUNT(DISTINCT orders.order_id).
- Month (월): strftime('%Y-%m', orders.order_purchase_timestamp)."""

# V2: 조인 관계 + 1:N 주의
JOIN_NOTES = """## Join keys
- orders.customer_id = customers.customer_id
- order_items.order_id = orders.order_id (one order has many items)
- order_payments.order_id = orders.order_id (one order can have many payments)
- order_reviews.order_id = orders.order_id (one order can have more than one review)
- order_items.product_id = products.product_id
- order_items.seller_id = sellers.seller_id
- products.product_category_name = product_category_name_translation.product_category_name

## Caution: 1:N joins
Joining order_items and order_payments in the same query multiplies rows and inflates sums.
Filter by the other table with IN or EXISTS instead of joining both."""

# V3: 검증된 예시 (골든셋과 겹치지 않음)
EXAMPLES = """## Examples
Q: 배송 완료된 주문은 평균 며칠 만에 도착했어?
SQL: SELECT ROUND(AVG(julianday(order_delivered_customer_date) - julianday(order_purchase_timestamp)), 1) FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL

Q: 10개월 이상 할부로 결제된 주문들의 매출은?
SQL: SELECT ROUND(SUM(i.price), 2) FROM orders o JOIN order_items i ON o.order_id = i.order_id WHERE o.order_status = 'delivered' AND o.order_id IN (SELECT order_id FROM order_payments WHERE payment_installments >= 10)

Q: 가구·인테리어 카테고리 상품을 판 판매자는 몇 명이야?
SQL: SELECT COUNT(DISTINCT i.seller_id) FROM order_items i JOIN products p ON i.product_id = p.product_id JOIN product_category_name_translation t ON p.product_category_name = t.product_category_name WHERE t.product_category_name_english = 'furniture_decor'"""


def load_schema() -> str:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
    finally:
        conn.close()
    return "\n\n".join(sql for (sql,) in rows)


VERSIONS = ["v0", "v1", "v2", "v3"]


def build_prompt(question: str, version: str = "v0") -> str:
    level = VERSIONS.index(version)
    parts = [
        "You are a SQLite expert. Write one SQLite query that answers the question.",
        f"Today is {REFERENCE_DATE}. Resolve relative dates like 'last month' from this date.",
        "Output only the SQL. No explanation.",
        "## Schema\n" + load_schema(),
    ]
    if level >= 1:
        parts += [COLUMN_NOTES, BUSINESS_TERMS]
    if level >= 2:
        parts.append(JOIN_NOTES)
    if level >= 3:
        parts.append(EXAMPLES)
    parts.append(f"## Question\n{question}")
    return "\n\n".join(parts)
