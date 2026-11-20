"""golden.jsonl·runs/v*.csv → sqlverdict 입력(YAML) 생성. DB는 읽기 전용.

실행: uv run --with sqlverdict==0.1.0 python eval_sqlverdict/build.py
"""
import csv
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from text2sql import executor, scorer  # noqa: E402
from text2sql.executor import QueryTimeout, query  # noqa: E402
from text2sql.guard import UnsafeSQLError, guard  # noqa: E402

if not executor.DB_PATH.exists():
    sys.exit(f"DB 없음: {executor.DB_PATH} — 만들지 않고 중단")

# why 초안 (trap 문항만, 사람 검증 전). 숫자는 2026-11-20 DB 실측
WHY = {
    "Q17": "order_payments는 주문당 결제 행이 여러 개일 수 있음(1:N). 결제 테이블을 직접 조인하면 "
           "item 행이 결제 행 수만큼 복제돼 404,020.72 → 632,719.07로 부풂. IN 서브쿼리로 주문만 거르고 "
           "매출=delivered 주문의 SUM(price)",
    "Q18": "customer_id는 주문마다 새로 발급됨. 사람 단위는 customer_unique_id. "
           "2018년 COUNT(DISTINCT customer_unique_id)=52,749 vs customer_id=54,011",
    "Q19": "사내 정의 매출 = order_status='delivered' 주문의 SUM(order_items.price), 배송비 제외. "
           "필터 없이 price만 6,155,806.98, price+freight 7,142,672.43, 정답 5,962,902.01",
    "Q20": "주문 데이터는 2016-09-04 ~ 2018-10-17. 2019년 주문은 없으므로 빈 결과가 정답",
}


def run_sql(sql):
    cols, rows = query(sql)
    return {"columns": cols, "rows": [list(r) for r in rows]}


def build_golden():
    items = []
    for line in (ROOT / "golden.jsonl").read_text(encoding="utf-8").splitlines():
        g = json.loads(line)
        rows = scorer.run_gold(g["sql"])  # 1,000행 초과 검사 재사용
        cols, _ = query(g["sql"])
        it = {
            "id": g["id"],
            "question": g["question"],
            "level": f"L{g['level']}",          # 1 → L1 (sqlverdict 형식)
            "trap": g["trap"] or "none",        # null → none
            "verified": True,
            "ordered": scorer.is_ordered(g["sql"]),
            "gold_sql": g["sql"],
            "expected": {"columns": cols, "rows": [list(r) for r in rows]},
        }
        if g["id"] in WHY:
            it["why"] = WHY[g["id"]]
        if g["trap"] == "empty_ok":
            it["empty_ok"] = True
        items.append(it)
    doc = {"dialect": "sqlite", "snapshot": date.today().isoformat(), "items": items}
    dump(doc, OUT / "golden.yaml")
    return {it["id"]: it for it in items}


def predict(pred_sql):
    try:
        return {"result": run_sql(guard(pred_sql, scorer.MAX_ROWS))}
    except (UnsafeSQLError, QueryTimeout, sqlite3.Error) as e:
        return {"error": f"{type(e).__name__}: {e}"}


def build_predictions():
    (OUT / "predictions").mkdir(exist_ok=True)
    legacy = []
    for v in range(4):
        rows = list(csv.DictReader(open(ROOT / "runs" / f"v{v}.csv", encoding="utf-8")))
        for r in sorted({x["run"] for x in rows}):
            items = []
            for x in (x for x in rows if x["run"] == r):
                items.append({"id": x["id"], "pred_sql": x["pred_sql"], **predict(x["pred_sql"])})
                # 기존 판정: CSV 기록값 + 현재 scorer로 다시 채점한 값
                gold = json.loads(next(l for l in (ROOT / "golden.jsonl").read_text(encoding="utf-8").splitlines()
                                       if json.loads(l)["id"] == x["id"]))["sql"]
                now = scorer.score(gold, x["pred_sql"])
                legacy.append({"version": f"v{v}", "run": int(r), "id": x["id"],
                               "csv_label": x["label"], "failure_type": x["failure_type"],
                               "scorer_now": now.label, "scorer_detail": now.detail})
            dump({"run_name": f"v{v}_run{r}", "dialect": "sqlite", "items": items},
                 OUT / "predictions" / f"v{v}_run{r}.yaml")
    (OUT / "legacy_labels.json").write_text(json.dumps(legacy, ensure_ascii=False, indent=1), encoding="utf-8")


def dump(doc, path):
    path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=1000), encoding="utf-8")
    print("생성:", path.relative_to(ROOT))


if __name__ == "__main__":
    build_golden()
    build_predictions()
