# Text-to-SQL Accuracy Eval

**[한국어](#한국어) · [English](#english)**

> **한 줄 결론:** LLM이 쓴 SQL에서 위험한 건 에러가 아니라 *에러 없이 틀린 숫자*다. 이를 막은 건 더 많은 힌트나 예시가 아니라 **"매출이 무엇인가" 같은 업무 정의를 명시하는 것**이었다.
>
> **TL;DR:** The real danger in LLM-written SQL is not errors but *numbers that are wrong without any error*. What fixed it was not more hints or examples, but **writing down business definitions such as "what counts as revenue."**

---

## 한국어

### 이 프로젝트가 전달하려는 것

"자연어로 물으면 SQL을 짜 주는 LLM, 그 숫자를 믿어도 되는가?"를 감이 아니라 **측정**으로 답한 실험입니다.

1. **Text-to-SQL의 실패는 조용하다.** 기본 프롬프트(V0)의 오답 16건은 **전부 정상 실행**됐고 그럴듯한 숫자를 냈습니다(error 0건). 사용자는 틀렸다는 걸 알 방법이 없습니다.
2. **틀린 이유는 SQL 실력이 아니라 정의의 부재였다.** 오답의 75%(12/16)는 "매출"을 결제 금액으로 계산하거나, 배송 완료 조건을 빼는 등 **업무 용어 해석 차이**였습니다. 모델은 문법적으로 완벽한 SQL을 썼고, 단지 우리 회사의 "매출"을 몰랐을 뿐입니다.
3. **정의를 적어 주자 문제가 거의 사라졌다.** 컬럼 설명 + 업무 용어 정의(V1)만으로 정확도가 **60% → 100%**가 됐습니다. 그 뒤에 추가한 조인 주의사항(V2)·예시(V3)는 측정 가능한 개선을 만들지 못했습니다(천장 효과).

즉 Text-to-SQL을 실무에 들이려면 **좋은 모델·프롬프트 기교보다 먼저, 지표 정의를 문서화하고 정답셋으로 검증하는 체계**가 필요하다는 것이 이 프로젝트의 메시지입니다.

### 실험 설계

| 항목 | 내용 |
|---|---|
| 데이터 | [Kaggle Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) → SQLite 8개 테이블 (읽기 전용) |
| 모델 | `gemini-3.5-flash`, `temperature=0` |
| 골든셋 | 한국어 질문 20개 (`golden.jsonl`), 난이도 L1~L4. L4는 함정 문항(업무 용어, 1:N 중복 조인, 고객 ID, 빈 결과) |
| 기준일 | 2018-08-31 ("지난달" 같은 상대 날짜 해석용) |
| 반복 | 버전마다 2회 × 20문항 = 40회. 같은 조건에서 결과가 흔들리는지도 확인 |
| 채점 | **실행 결과 비교(Execution Accuracy)**. SQL 문장이 아니라 결과 집합을 비교. 별칭 무시, 정답에 `ORDER BY`가 없으면 순서 무시, 소수 둘째 자리 반올림 |

프롬프트 버전 — 한 번에 하나씩만 추가 (`text2sql/prompt.py`)

| 버전 | 추가한 것 |
|---|---|
| V0 | `CREATE TABLE` 스키마 + 기준일 |
| V1 | + 컬럼 설명, 코드값 뜻, **업무 용어 정의** (매출 = 배송 완료 주문의 `SUM(price)`, 고객 수 = `customer_unique_id` 기준 등) |
| V2 | + 조인 키, 1:N 조인 주의 메모 |
| V3 | + 검증된 질문–SQL 예시 3개 (골든셋과 겹치지 않음) |

판정: `correct` / `error`(실행 실패, 눈에 보임) / **`silent_wrong`(실행은 됐는데 결과가 다름 — 핵심 지표)**

### 결과

버전별 정확도 (40회 합산, 전체 표는 [`runs/report.md`](runs/report.md))

| 버전 | 정답률 | 95% CI | silent_wrong | error | 회차 간 일치 |
|---|---|---|---|---|---|
| V0 | **60%** (24/40) | 45–74% | 16 | 0 | 90% |
| V1 | **100%** (40/40) | 91–100% | 0 | 0 | 100% |
| V2 | 95% (38/40) | 83–99% | 2 | 0 | 90% |
| V3 | 100% (40/40) | 91–100% | 0 | 0 | 100% |

난이도별 — V0은 조인·업무 용어가 들어간 L3에서 무너짐

| 버전 | L1 | L2 | L3 | L4 |
|---|---|---|---|---|
| V0 | 100% | 67% | **20%** | 50% |
| V1 | 100% | 100% | 100% | 100% |
| V2 | 100% | 92% | 90% | 100% |
| V3 | 100% | 100% | 100% | 100% |

실패 유형 (전체 18건)

| 유형 | 건수 | 대표 사례 |
|---|---|---|
| `revenue_def` | 6 | "2017년 매출은?" → V0는 `SUM(payment_value)`(배송비 포함, 취소 주문 포함). 정답 5,962,902 vs 생성 7,249,747 (+22%) |
| `missing_filter` | 6 | "판매자 주별 매출" → 배송 완료 조건 누락으로 SP 매출 8,509,511 → 8,753,396 |
| `missing_column` | 5 | 순위는 맞는데 개수 컬럼을 빼먹음 (V2의 2건도 이 유형) |
| `dup_count` | 1 | 리뷰가 2개인 주문을 두 번 셈 (`COUNT` vs `COUNT(DISTINCT)`), 421 → 422 |

### 처음 세운 가설은 맞았나

| 가설 | 결과 |
|---|---|
| 조인 3개 이상·업무 용어가 들어가면 정확도가 떨어진다 | ✅ V0 L3 20%, 업무 용어 함정 0% |
| 컬럼 설명·조인 관계·예시를 하나씩 넣을 때마다 오른다 | ❌ **V1 한 번에 100%**. V2·V3의 효과는 이 골든셋으로는 측정 불가 |
| 가장 위험한 실패는 에러 없이 틀린 SQL이다 | ✅ V0 오답 16/16이 `silent_wrong`, error 0 |

추가 관찰
- **V2의 오답 2건은 프롬프트 탓이 아니라 비결정성.** `temperature=0`인데도 서로 다른 회차·문항에서 개수 컬럼을 빼먹었고, 같은 문항이 다른 회차에선 정답이었습니다. 컬럼 하나 차이를 허용하는 "너그러운 채점"으로는 V1~V3 모두 100%.
- **정적 검사(lint)로 조용한 오답을 실행 전에 잡을 수 있다.** 테이블 관계·지표 정의를 담은 `catalog.py`를 기준으로 1:N 중복 조인, 지표 식 위반, 필터 누락을 검사한 결과 V0 진짜 오답 13/13 탐지, 정답 오탐 0건. 단, 규칙을 V0 오답을 보고 만들었으므로 탐지율은 과대평가돼 있습니다.

### 한계

- **골든셋이 작다 (20문항).** 100%의 95% 신뢰구간 하한이 91%이고, V1~V3 차이는 통계적으로 구분되지 않습니다.
- **천장 효과.** V1에서 이미 만점이라 조인 메모·예시의 효과를 잴 수 없었습니다. 더 어려운 문항(복잡한 조인, 애매한 지표)이 있어야 비교가 가능합니다.
- **정의를 아는 쪽이 채점한다.** V1에 넣은 업무 정의는 정답 SQL을 쓸 때 쓴 정의와 같습니다. 이것은 결함이라기보다 요점입니다 — "정답"은 조직의 정의에 달려 있고, 그 정의를 모델에게 알려 주지 않으면 맞힐 수 없습니다.
- 모델 1개(Gemini Flash), 데이터셋 1개, 무료 티어 한도 때문에 버전당 2회만 반복했습니다.

### 구성

```
[한국어 질문] + [프롬프트 V0~V3] → Gemini → SQL → guard(안전검사) → SQLite(읽기 전용) 실행 → 결과
                                                                              │
                          [정답 SQL] → SQLite 실행 → 결과 ──────────────────→ 비교 → runs/vN.csv
```

| 파일 | 역할 |
|---|---|
| `text2sql/prompt.py` | 버전별 프롬프트 조립 (V0~V3) |
| `text2sql/llm.py` | Gemini 호출, 코드블록 제거 |
| `text2sql/guard.py` | sqlglot으로 단일 SELECT만 허용, 허용 테이블 확인, `LIMIT` 강제 |
| `text2sql/executor.py` | 읽기 전용 연결 + 실행 시간 제한 |
| `text2sql/scorer.py` | 실행 결과 비교 채점 (엄격 / 너그러운) |
| `text2sql/catalog.py`, `lint.py` | 테이블 관계·지표 정의, 실행 전 위험 패턴 검사 |
| `run.py` | 실험 실행 (일일 한도에 걸리면 저장 후 중단, 다음 실행 때 이어서) |
| `report.py` | `runs/*.csv` → `runs/report.md` |
| `api.py`, `web/` | 데모: FastAPI + React. 질문 → SQL·해석·lint 경고·결과 표 |

### 실행 방법

```bash
uv sync
# Kaggle Olist CSV를 data/raw/에 넣은 뒤
uv run python load_db.py
cp .env.example .env            # GEMINI_API_KEY 입력

uv run python run.py --version v1   # 실험 (--runs 기본 2)
uv run python report.py             # runs/report.md 갱신
uv run pytest                       # 테스트 99개

# 데모
uv run uvicorn api:app --reload     # :8000
cd web && npm install && npm run dev
```

데모는 `PROMPT_VERSION=v3`(기본값)을 씁니다. V1과 정확도는 같지만, 회차 간 일치도 100%이고 1:N 조인 주의와 예시가 들어 있어 골든셋 밖의 자유 질문에 더 안전하다고 판단했습니다.

---

## English

### What this project is about

An experiment that answers *"Can we trust the numbers when an LLM writes SQL from a natural-language question?"* by **measuring** it instead of guessing.

1. **Text-to-SQL fails silently.** All 16 wrong answers from the baseline prompt (V0) **ran without error** and returned plausible numbers (0 execution errors). A user would have no way to tell.
2. **The cause was missing definitions, not SQL skill.** 75% of failures (12/16) came from **interpreting business terms differently** — computing "revenue" from payment amounts, or dropping the "delivered only" condition. The model wrote syntactically perfect SQL; it simply didn't know what *our* "revenue" means.
3. **Writing the definitions down almost eliminated the problem.** Adding column notes and business-term definitions (V1) took accuracy from **60% to 100%**. Join notes (V2) and few-shot examples (V3) added afterwards produced no measurable gain (ceiling effect).

The message: before better models or prompt tricks, putting Text-to-SQL into practice requires **documented metric definitions and a golden set to verify against.**

### Setup

| Item | Detail |
|---|---|
| Data | [Kaggle Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) → 8 SQLite tables (read-only) |
| Model | `gemini-3.5-flash`, `temperature=0` |
| Golden set | 20 Korean questions (`golden.jsonl`), levels L1–L4. L4 = trap questions (business terms, 1:N duplicate joins, customer IDs, empty result) |
| Reference date | 2018-08-31 (for relative dates like "last month") |
| Repetition | 2 runs × 20 questions = 40 per version, also checking run-to-run stability |
| Scoring | **Execution accuracy** — compare result sets, not SQL text. Aliases ignored, row order ignored unless the gold SQL has `ORDER BY`, floats rounded to 2 decimals |

Prompt versions — one addition at a time (`text2sql/prompt.py`)

| Version | Adds |
|---|---|
| V0 | `CREATE TABLE` schema + reference date |
| V1 | + column notes, code values, **business-term definitions** (revenue = `SUM(price)` of delivered orders, customers = distinct `customer_unique_id`, …) |
| V2 | + join keys, warning about 1:N joins |
| V3 | + 3 verified question–SQL examples (disjoint from the golden set) |

Labels: `correct` / `error` (execution failed — visible) / **`silent_wrong` (ran fine, wrong result — the key metric)**

### Results

Accuracy by version (40 runs each; full tables in [`runs/report.md`](runs/report.md))

| Version | Accuracy | 95% CI | silent_wrong | error | Run-to-run agreement |
|---|---|---|---|---|---|
| V0 | **60%** (24/40) | 45–74% | 16 | 0 | 90% |
| V1 | **100%** (40/40) | 91–100% | 0 | 0 | 100% |
| V2 | 95% (38/40) | 83–99% | 2 | 0 | 90% |
| V3 | 100% (40/40) | 91–100% | 0 | 0 | 100% |

By level — V0 collapses at L3 (joins + business terms)

| Version | L1 | L2 | L3 | L4 |
|---|---|---|---|---|
| V0 | 100% | 67% | **20%** | 50% |
| V1 | 100% | 100% | 100% | 100% |
| V2 | 100% | 92% | 90% | 100% |
| V3 | 100% | 100% | 100% | 100% |

Failure types (18 total)

| Type | Count | Example |
|---|---|---|
| `revenue_def` | 6 | "Revenue in 2017?" → V0 used `SUM(payment_value)` (includes shipping and canceled orders). Expected 5,962,902 vs got 7,249,747 (+22%) |
| `missing_filter` | 6 | "Revenue by seller state" → missing the delivered filter; SP 8,509,511 → 8,753,396 |
| `missing_column` | 5 | Correct ranking but the count column was omitted (both V2 failures) |
| `dup_count` | 1 | Orders with two reviews counted twice (`COUNT` vs `COUNT(DISTINCT)`), 421 → 422 |

### Did the hypotheses hold?

| Hypothesis | Outcome |
|---|---|
| Accuracy drops with 3+ joins or business terms | ✅ V0: 20% on L3, 0% on business-term traps |
| Each added context (columns → joins → examples) raises accuracy step by step | ❌ **V1 alone reached 100%.** V2/V3 effects can't be measured with this golden set |
| The most dangerous failure is SQL that runs but is wrong | ✅ 16/16 V0 failures were `silent_wrong`, 0 errors |

Additional observations
- **V2's two failures look like nondeterminism, not the prompt.** Even at `temperature=0`, a count column was dropped on different runs and questions, while the same question passed on the other run. With lenient scoring (allowing a missing column), V1–V3 are all 100%.
- **Static checks can catch silent errors before execution.** A lint pass driven by `catalog.py` (table relationships and metric definitions) flags 1:N fan-out joins, metric-expression violations and missing filters: 13/13 genuine V0 errors detected, 0 false positives on correct answers. Since the rules were written after seeing V0's failures, the detection rate is optimistic.

### Limitations

- **Small golden set (20 questions).** The lower bound of the 95% CI at 100% is 91%; V1–V3 are not statistically distinguishable.
- **Ceiling effect.** V1 already scores 100%, so the value of join notes and examples could not be measured. Harder questions (complex joins, ambiguous metrics) are needed.
- **The grader knows the definitions.** The business definitions in V1 are the same ones used to write the gold SQL. That is less a flaw than the point: the "right answer" depends on the organization's definitions, and a model cannot get it right unless it is told them.
- One model (Gemini Flash), one dataset, and only 2 runs per version due to free-tier quotas.

### Structure

```
[Korean question] + [prompt V0–V3] → Gemini → SQL → guard → SQLite (read-only) → result
                                                                       │
                       [gold SQL] → SQLite → result ─────────────────→ compare → runs/vN.csv
```

| File | Role |
|---|---|
| `text2sql/prompt.py` | Builds the prompt for each version (V0–V3) |
| `text2sql/llm.py` | Gemini call, strips code fences |
| `text2sql/guard.py` | sqlglot: single SELECT only, allowed tables, enforced `LIMIT` |
| `text2sql/executor.py` | Read-only connection + query timeout |
| `text2sql/scorer.py` | Execution-result scoring (strict / lenient) |
| `text2sql/catalog.py`, `lint.py` | Table relationships & metric definitions, pre-execution risk checks |
| `run.py` | Runs the experiment (saves and stops on daily quota, resumes next time) |
| `report.py` | `runs/*.csv` → `runs/report.md` |
| `api.py`, `web/` | Demo: FastAPI + React. Question → SQL, interpretation, lint warnings, result table |

### Usage

```bash
uv sync
# put the Kaggle Olist CSVs in data/raw/
uv run python load_db.py
cp .env.example .env            # set GEMINI_API_KEY

uv run python run.py --version v1   # experiment (--runs defaults to 2)
uv run python report.py             # refresh runs/report.md
uv run pytest                       # 99 tests

# demo
uv run uvicorn api:app --reload     # :8000
cd web && npm install && npm run dev
```

The demo uses `PROMPT_VERSION=v3` (default). It ties V1 on accuracy, but had 100% run-to-run agreement and includes the 1:N join warning and examples, which should make it safer for free-form questions outside the golden set.
