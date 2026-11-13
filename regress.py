import csv
import json
import time
from collections import Counter
from datetime import date

from google.genai import errors

from api import PROMPT_VERSION, REGRESSION, ROOT, demo_extra, split_comments
from run import CALL_INTERVAL
from text2sql.llm import generate_sql
from text2sql.prompt import build_prompt
from text2sql.scorer import score

OUT = ROOT / "runs" / "regression.csv"
FIELDS = ["date", "id", "question", "pred_sql", "label", "detail"]


def main():
    items = [json.loads(l) for l in REGRESSION.read_text().splitlines()] if REGRESSION.exists() else []
    rows = []
    for i, it in enumerate(items):
        if i:
            time.sleep(CALL_INTERVAL)
        try:
            _, sql = split_comments(generate_sql(build_prompt(it["question"], PROMPT_VERSION, demo_extra())))
        except errors.ClientError as e:
            if e.code != 429:
                raise
            print("Gemini 한도 도달 → 여기까지만 채점")
            break
        v = score(it["sql"], sql)
        rows.append({"date": f"{date.today()}", "id": it["id"], "question": it["question"],
                     "pred_sql": sql, "label": v.label, "detail": v.detail})
        print(f"[{it['id']}] {v.label}  {it['question']}", flush=True)

    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    c = Counter(r["label"] for r in rows)
    print(f"\n{PROMPT_VERSION}+demo  correct {c['correct']}/{len(items)}  silent_wrong={c['silent_wrong']} error={c['error']}  → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
