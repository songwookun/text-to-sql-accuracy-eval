import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LABELS = ["correct", "silent_wrong", "error"]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    mid = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return mid - half, mid + half


def pct(k: int, n: int) -> str:
    return f"{k / n:.0%} ({k}/{n})" if n else "—"


def load_runs() -> dict[str, list[dict]]:
    runs = {}
    for path in sorted((ROOT / "runs").glob("v*.csv")):
        with path.open() as f:
            runs[path.stem] = [r for r in csv.DictReader(f) if r["label"] in LABELS]
    return runs


def table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def main():
    golden = [json.loads(line) for line in (ROOT / "golden.jsonl").read_text().splitlines()]
    expected = len(golden) * 2
    runs = load_runs()
    if not runs:
        print("runs/*.csv 없음")
        return

    out = ["## 버전별 정확도 (전체 회차 합산)"]
    rows = []
    for v, rs in runs.items():
        c = Counter(r["label"] for r in rs)
        lo, hi = wilson(c["correct"], len(rs))
        rows.append([v, f"{len(rs)}/{expected}", pct(c["correct"], len(rs)), f"{lo:.0%}–{hi:.0%}",
                     pct(c["silent_wrong"], len(rs)), pct(c["error"], len(rs))])
    out.append(table(["버전", "진행", "correct", "95% CI", "silent_wrong", "error"], rows))

    out.append("\n## 난이도별 정답률")
    levels = sorted({g["level"] for g in golden})
    rows = []
    for v, rs in runs.items():
        by = defaultdict(list)
        for r in rs:
            by[int(r["level"])].append(r["label"] == "correct")
        rows.append([v] + [pct(sum(by[l]), len(by[l])) for l in levels])
    out.append(table(["버전"] + [f"L{l}" for l in levels], rows))

    traps = sorted({g["trap"] for g in golden if g["trap"]})
    out.append("\n## 함정 문항 (L4)")
    rows = []
    for v, rs in runs.items():
        by = defaultdict(list)
        for r in rs:
            if r["trap"]:
                by[r["trap"]].append(r["label"] == "correct")
        rows.append([v] + [pct(sum(by[t]), len(by[t])) for t in traps])
    out.append(table(["버전"] + traps, rows))

    out.append("\n## 회차 간 일관성 (같은 문항, run1 vs run2 라벨 일치)")
    rows = []
    for v, rs in runs.items():
        by = defaultdict(dict)
        for r in rs:
            by[r["id"]][r["run"]] = r["label"]
        pairs = [d for d in by.values() if len(d) == 2]
        same = sum(len(set(d.values())) == 1 for d in pairs)
        rows.append([v, pct(same, len(pairs))])
    out.append(table(["버전", "일치"], rows))

    out.append("\n## 실패 문항")
    rows = []
    for v, rs in runs.items():
        for r in rs:
            if r["label"] != "correct":
                rows.append([v, f"r{r['run']}", r["id"], r["trap"] or "", r["label"],
                             r["failure_type"] or "(미분류)", r["detail"][:60].replace("|", "/")])
    out.append(table(["버전", "회차", "문항", "함정", "라벨", "실패유형", "상세"], rows) if rows else "없음")

    types = Counter(r["failure_type"] or "(미분류)" for rs in runs.values() for r in rs if r["label"] != "correct")
    if types:
        out.append("\n## 실패 유형 분포")
        out.append(table(["유형", "건수"], [[t, str(n)] for t, n in types.most_common()]))

    text = "\n".join(out)
    (ROOT / "runs" / "report.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
