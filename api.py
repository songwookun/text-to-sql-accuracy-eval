import json
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from google.genai import errors
from pydantic import BaseModel, Field

from text2sql.catalog import terms_prompt
from text2sql.executor import QueryTimeout, query
from text2sql.guard import UnsafeSQLError, guard
from text2sql.lint import lint
from text2sql.llm import MODEL, generate_sql
from text2sql.profile import profile_columns
from text2sql.prompt import build_prompt

load_dotenv()

ROOT = Path(__file__).resolve().parent
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v3")  # 실험 결과 보고 확정
MOCK_LLM = os.getenv("MOCK_LLM") == "1"  # 1이면 Gemini 대신 골든셋 SQL 사용 (한도 절약)

GOLDEN = {
    g["question"]: g["sql"]
    for g in map(json.loads, (ROOT / "golden.jsonl").read_text().splitlines())
}
# 데모 전용: 해석 한 줄 + 순위 근거 값. 실험(run.py) 조건과 분리
DEMO_RULES = """## Output rules
- First line: a SQL comment in Korean saying how you read the question, e.g. -- 해석: 배송 완료 주문 기준, 상품 개수로 셈
- When ranking or picking top/bottom items, also return the value used for ranking.
- Give every computed column a short snake_case alias."""
MOCK_FALLBACK = "SELECT order_status, COUNT(*) AS orders FROM orders GROUP BY order_status ORDER BY orders DESC"


def demo_extra() -> str:
    return "\n\n".join([DEMO_RULES, terms_prompt(), profile_columns()])


app =FastAPI(title="text-to-sql demo")


def split_interpretation(sql: str) -> tuple[str, str]:
    lines = sql.strip().splitlines()
    if lines and lines[0].lstrip().startswith("--"):
        note = lines[0].lstrip()[2:].strip().removeprefix("해석:").strip()
        return note, "\n".join(lines[1:]).strip()
    return "", sql.strip()


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class AskResponse(BaseModel):
    question: str
    sql: str = ""
    interpretation: str = ""
    warnings: list[str] = []
    columns: list[str] = []
    rows: list[list] = []
    error: str | None = None
    error_type: str | None = None
    model: str
    version: str
    mock: bool


@app.get("/api/health")
def health():
    return {"ok": True, "model": MODEL, "version": PROMPT_VERSION, "mock": MOCK_LLM}


@app.get("/api/examples")
def examples():
    return list(GOLDEN)[:8]


@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest):
    q = req.question.strip()
    res = AskResponse(question=q, model="mock" if MOCK_LLM else MODEL, version=PROMPT_VERSION, mock=MOCK_LLM)

    try:
        raw = GOLDEN.get(q, MOCK_FALLBACK) if MOCK_LLM else generate_sql(build_prompt(q, PROMPT_VERSION, demo_extra()))
        res.interpretation, res.sql = split_interpretation(raw)
    except errors.ClientError as e:
        res.error_type = "quota" if e.code == 429 else "llm"
        if e.code != 429:
            res.error = str(e)
        elif "PerDay" in str(e):
            res.error = "오늘 Gemini 무료 한도(하루 20회)를 다 썼어요. 한도가 초기화된 뒤 다시 시도해주세요."
        else:
            res.error = "Gemini 분당 한도를 넘었어요. 1분 뒤 다시 시도해주세요."
        return res
    except errors.ServerError:
        res.error_type, res.error = "llm", "Gemini 서버가 바빠요. 잠시 후 다시 시도해주세요."
        return res

    res.warnings = [i.message for i in lint(res.sql, q)]  # 차단 X, 경고만
    try:
        res.columns, rows = query(guard(res.sql))
        res.rows = [list(r) for r in rows]
    except UnsafeSQLError as e:
        res.error_type, res.error = "unsafe", f"안전검사에서 막혔어요: {e}"
    except QueryTimeout:
        res.error_type, res.error = "timeout", "쿼리가 10초를 넘겨 중단했어요."
    except sqlite3.Error as e:
        res.error_type, res.error = "sql", f"SQL 실행 오류: {e}"
    return res
