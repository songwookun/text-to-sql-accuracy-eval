"""legacy_labels.json + results/*.json → 비교.md

실행: uv run --with sqlverdict==0.1.0 python eval_sqlverdict/report.py  (build.py, score.sh 다음)
"""
import json
from pathlib import Path

import yaml

D = Path(__file__).resolve().parent
RUNS = [f"v{v}_run{r}" for v in range(4) for r in (1, 2)]
ABBR = {"correct": "C", "correct_approx": "A", "extra_columns": "X", "silent_wrong": "W", "error": "E"}

golden = {i["id"]: i for i in yaml.safe_load(open(D / "golden.yaml", encoding="utf-8"))["items"]}
preds = {n: {i["id"]: i for i in yaml.safe_load(open(D / "predictions" / f"{n}.yaml", encoding="utf-8"))["items"]}
         for n in RUNS}
sv = {n: json.load(open(D / "results" / f"{n}.json", encoding="utf-8")) for n in RUNS}
sv_items = {n: {i["id"]: i for i in sv[n]["items"]} for n in RUNS}
legacy = {(f"{x['version']}_run{x['run']}", x["id"]): x for x in json.load(open(D / "legacy_labels.json", encoding="utf-8"))}
check = json.load(open(D / "results" / "check_golden.json", encoding="utf-8"))
base = json.load(open(D / "results" / "v3_run1_vs_v0_run1.json", encoding="utf-8"))


def head(res, k=3):
    return f"columns={res['columns']}, rows({len(res['rows'])})={res['rows'][:k]}"


def rel(a, b):
    return abs(a - b) / abs(a) if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a else None


L = []
w = L.append
w("# sqlverdict 0.1.0 재채점 비교\n")
w("- 기존 판정: `runs/v*.csv`의 label (현재 `text2sql/scorer.py`로 다시 채점해도 160행 모두 동일: "
  + str(all(x["csv_label"] == x["scorer_now"] for x in legacy.values())) + ")")
w("- sqlverdict: `uv run --with sqlverdict==0.1.0 sqlverdict score` (기본 tolerance 0.001)")
w("- 재현: `uv run --with sqlverdict==0.1.0 python eval_sqlverdict/build.py` → `sh eval_sqlverdict/score.sh` → "
  "`uv run --with sqlverdict==0.1.0 python eval_sqlverdict/report.py`\n")

w("## 1. 판정이 다른 행 (기존 correct 여부 ≠ sqlverdict correct 여부)\n")
w("원인 칸은 **추정**. 근거는 실제 값.\n")
w("| run | id | 기존 | sqlverdict | 근거(실제 값) | 추정 원인 |")
w("|---|---|---|---|---|---|")
diff_rows = []
for n in RUNS:
    for q in golden:
        old, new = legacy[(n, q)]["csv_label"], sv_items[n][q]["label"]
        if (old == "correct") == (new == "correct") and not (old != "correct" and new != "silent_wrong"):
            continue
        diff_rows.append((n, q))
        exp, got = golden[q]["expected"], preds[n][q].get("result")
        ev = f"정답 {head(exp)} / 예측 {head(got) if got else preds[n][q]['error']}"
        r = [rel(a, b) for er, gr in zip(exp["rows"], got["rows"] if got else []) for a, b in zip(er, gr)]
        r = [x for x in r if x]
        if r:
            ev += f" / 최대 상대오차 {max(r):.4%}"
        guess = {
            "correct_approx": "정답·예측 중 한쪽만 ROUND(…, 2). 기존 scorer는 양쪽을 소수 2자리로 반올림해 같게 봄, "
                              "sqlverdict는 반올림 없이 상대오차 0.1% 안이면 correct_approx",
            "extra_columns": "예측이 SELECT *로 컬럼이 더 많음. 기존 scorer는 빈 결과끼리 `[] == []`라 컬럼 수를 못 봄",
        }.get(new, "")
        w(f"| {n} | {q} | {old} | {new} | {ev} | {guess} |")
w(f"\n→ 160행 중 {len(diff_rows)}행. 기존 silent_wrong 16행은 sqlverdict에서도 모두 silent_wrong.\n")

w("## 2. 실행별 요약\n")
w("| run | 기존 correct | sv correct | correct_approx | extra_columns | silent_wrong | error | sv accuracy |")
w("|---|---|---|---|---|---|---|---|")
for n in RUNS:
    s = sv[n]["summary"]
    oc = sum(legacy[(n, q)]["csv_label"] == "correct" for q in golden)
    w(f"| {n} | {oc}/20 | {s['correct']} | {s['correct_approx']} | {s['extra_columns']} | {s['silent_wrong']} "
      f"| {s['error']} | {s['accuracy']} |")
w("\nsqlverdict의 accuracy는 `correct / 채점수`라 correct_approx·extra_columns가 오답 쪽으로 빠짐.\n")

w("## 3. 문항 × 버전 × 회차 (기존/sqlverdict)\n")
w("C=correct, A=correct_approx, X=extra_columns, W=silent_wrong, E=error. 다른 칸은 **굵게**.\n")
w("| id | trap | " + " | ".join(RUNS) + " |")
w("|---|---|" + "---|" * len(RUNS))
for q, g in golden.items():
    cells = []
    for n in RUNS:
        c = f"{ABBR[legacy[(n, q)]['csv_label']]}/{ABBR[sv_items[n][q]['label']]}"
        cells.append(f"**{c}**" if (n, q) in diff_rows else c)
    w(f"| {q} | {g['trap']} | " + " | ".join(cells) + " |")

w("\n## 4. --baseline 비교 (v3_run1, 기준 v0_run1)\n")
w(f"- regressions: {base['regressions'] or '없음'}")
w(f"- improvements: {base['improvements']}")
w(f"- warnings: {base['warnings'] or '없음'}")
w("- 기존 판정으로 보면 v0_run1 오답 8개(Q08 Q11 Q12 Q13 Q14 Q16 Q17 Q19)가 v3_run1에서 모두 정답 → improvements와 일치\n")

w("## 5. 골든셋 check 결과 (고치지 않음)\n")
w(f"- error {check['summary']['error']}개 · warn {check['summary']['warn']}개")
for i in check["issues"]:
    w(f"  - [{i['severity']}] {i['id']}: {i['message']}")
w("- 예측 파일 8개 check: " + ", ".join(
    f"{n} error {json.load(open(D / 'results' / f'check_{n}.json'))['summary']['error']}" for n in RUNS))

w("\n## 6. 변환 규칙 · why 초안\n")
w("- level: `1` → `L1` (sqlverdict는 L1~L4 문자열만 허용, 값은 그대로)")
w("- trap: `null` → `none`, 나머지 그대로")
w("- ordered: `scorer.is_ordered(gold_sql)` (정답 SQL에 ORDER BY 유무)")
w("- verified: 전부 true / empty_ok: Q20만 true / snapshot: 2026-11-20")
w("- expected: gold_sql을 `text2sql.executor.query`로 실행(읽기 전용, `scorer.run_gold`의 1,000행 검사 통과)")
w("- 예측: pred_sql → `guard(pred_sql, 1000)` → `executor.query`. 실행 에러는 `error: \"<예외명>: <메시지>\"` "
  "(이번 데이터엔 에러 0건). pred_sql은 원문(guard 전) 저장\n")
w("**why 초안 문항 (사람 검증 전, golden.yaml엔 verified: true로 들어가 있음)**\n")
for q, g in golden.items():
    if g.get("why"):
        w(f"- {q} ({g['trap']}): {g['why']}")
w("\ntrap=none 16문항은 why를 쓰지 않음 (sqlverdict 규칙상 필수 아님).")

w("\n## 7. sqlverdict 버그·개선점\n")
w("이번 재채점에서 찾은 항목. 수정은 [sqlverdict](https://github.com/songwookun/sqlverdict)에서 진행.\n")
w("- 버그: 이름 매칭 + 위치 대체가 섞이면 남는 컬럼이 있어도 `missing_columns`로 silent_wrong (판정 틀림)")
w("- 버그: 1행 결과면 항상 \"값이 정확히 N배\" 힌트 + 조인·필터 원인 단정 (힌트 틀림, 이번 Q17·Q19)")
w("- 확인 필요: empty_ok 문항에서 양쪽 0행인데 컬럼이 더 많으면 extra_columns (이번 Q20)")
w("- 확인 필요: correct_approx가 accuracy에선 오답, --baseline에선 regression으로 집계 (이번 Q03·Q09)")

(D / "비교.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("생성: eval_sqlverdict/비교.md")
