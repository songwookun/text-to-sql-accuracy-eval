import argparse
import csv
import json
import time
from collections import Counter
from datetime import date
from pathlib import Path

from google.genai import errors

from text2sql.llm import MODEL, generate_sql
from text2sql.prompt import build_prompt
from text2sql.scorer import score

ROOT = Path(__file__).resolve().parent
FIELDS = ["date", "run", "id", "level", "trap", "question", "pred_sql", "label", "detail", "failure_type"]
# 무료 티어 분당 5회
CALL_INTERVAL = 13  


class DailyQuotaExceeded(Exception):
    pass


def call_llm(question: str, version: str) -> str:
    while True:
        try:
            return generate_sql(build_prompt(question, version))
        except errors.ClientError as e:
            if e.code != 429:
                raise
            if "PerDay" in str(e):
                raise DailyQuotaExceeded from e
            time.sleep(60)


def load_done(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as f:
        return [r for r in csv.DictReader(f) if r["label"] != "api_error"]


def save(path: Path, rows: list[dict]):
    rows.sort(key=lambda x: (int(x["run"]), x["id"]))
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v0")
    ap.add_argument("--runs", type=int, default=2)
    args = ap.parse_args()

    golden = [json.loads(line) for line in (ROOT / "golden.jsonl").read_text().splitlines()]
    out = ROOT / "runs" / f"{args.version}.csv"
    rows = load_done(out)
    done = {(int(r["run"]), r["id"]) for r in rows}

    try:
        for r in range(1, args.runs + 1):
            for g in golden:
                if (r, g["id"]) in done:
                    continue
                try:
                    sql = call_llm(g["question"], args.version)
                    v = score(g["sql"], sql)
                    label, detail = v.label, v.detail
                except DailyQuotaExceeded:
                    raise
                # API 실패는 LLM 오답과 분리
                except Exception as e:
                    sql, label, detail = "", "api_error", f"{type(e).__name__}: {e}"
                rows.append({
                    "date": f"{date.today()}", "run": r, "id": g["id"], "level": g["level"],
                    "trap": g["trap"] or "", "question": g["question"], "pred_sql": sql,
                    "label": label, "detail": detail, "failure_type": "",
                })
                # 중간에 끊겨도 한도 쓴 결과는 남김
                save(out, rows)  
                print(f"[{args.version} r{r}] {g['id']} L{g['level']} {label}", flush=True)
                time.sleep(CALL_INTERVAL)
    except DailyQuotaExceeded:
        print("\n하루 한도 도달 → 저장 후 중단. 내일 같은 명령으로 이어서 실행")

    save(out, rows)

    total = args.runs * len(golden)
    print(f"\nmodel={MODEL}  saved → {out.relative_to(ROOT)}  ({len(rows)}/{total})")
    for r in range(1, args.runs + 1):
        c = Counter(x["label"] for x in rows if int(x["run"]) == r)
        print(f"run {r}: " + "  ".join(f"{k}={c[k]}" for k in ["correct", "silent_wrong", "error", "api_error"]))


if __name__ == "__main__":
    main()
