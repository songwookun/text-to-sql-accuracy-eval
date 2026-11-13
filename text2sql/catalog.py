# 테이블·연결·지표 정의. lint가 읽고, 실험 끝난 뒤 프롬프트 생성(①)·SQL 조립(③)에도 쓸 예정

TABLES = {
    "orders": "주문 1건 = 1행",
    "order_items": "주문 안의 상품 1개 = 1행",
    "order_payments": "주문의 결제 수단 1개 = 1행",
    "order_reviews": "주문 리뷰 1개 = 1행",
    "customers": "주문별 고객 = 1행 (customer_unique_id가 실제 사람)",
    "products": "상품 1개 = 1행",
    "sellers": "판매자 1명 = 1행",
    "product_category_name_translation": "카테고리 포르투갈어 → 영어",
}

# (부모 테이블, 부모 키, 자식 테이블, 자식 키): 부모 1행에 자식 여러 행
ONE_TO_MANY = [
    ("orders", "order_id", "order_items", "order_id"),
    ("orders", "order_id", "order_payments", "order_id"),
    ("orders", "order_id", "order_reviews", "order_id"),
    ("customers", "customer_id", "orders", "customer_id"),
    ("products", "product_id", "order_items", "product_id"),
    ("sellers", "seller_id", "order_items", "seller_id"),
    ("product_category_name_translation", "product_category_name", "products", "product_category_name"),
]

METRICS = {
    "revenue": {
        "keywords": ["매출", "revenue"],
        "agg": "SUM",
        "column": ("order_items", "price"),
        "filter": ("orders", "order_status", "delivered"),
    },
}

# 데모 전용 업무 정의 (실험 V0~V3 프롬프트엔 안 들어감)
DEMO_TERMS = {
    "Late delivery (배송 지연)": "delivered orders where date(order_delivered_customer_date) > date(order_estimated_delivery_date). Compare dates, not timestamps.",
    "Average order value (객단가)": "revenue / number of orders, both over delivered orders.",
    "Repeat customer (재구매 고객)": "customer_unique_id with 2 or more distinct order_id.",
    "Cancellation rate (취소율)": "COUNT(DISTINCT order_id) with order_status = 'canceled' / COUNT(DISTINCT order_id) of all orders.",
}


def terms_prompt() -> str:
    return "## More business terms\n" + "\n".join(f"- {k}: {v}" for k, v in DEMO_TERMS.items())
