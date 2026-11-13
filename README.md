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

### 골든셋 밖 검증: "예정일보다 늦게 배송된 주문 비율은?"

실험이 끝난 뒤 데모(V3)에 정의되지 않은 지표를 물어봤습니다.

- 모델의 해석: "배송 완료된 주문 중 실제 배송일이 예정일보다 늦은 주문의 비율" — **의도와 정확히 같음**
- 결과: **8.11%** — 에러 없음, lint 경고 없음
- 실제: **6.77%**. 예정일 컬럼은 시각 없이 날짜만(`00:00:00`) 들어 있는데, 시각이 있는 배송일과 그대로 비교해서 **예정일 당일에 도착한 1,292건을 "지연"으로 셈** → 지연율이 약 20% 부풀려짐

해석 문장도 맞고, 실행도 되고, 정적 검사도 통과했지만 숫자가 틀렸습니다. V0에서 본 것과 같은 패턴이 골든셋 밖에서도 재현됐습니다. 예시를 하나 더 넣는 대신 "예정일은 날짜만 있음"(데이터 특징)과 "지연 = 날짜 기준 비교"(업무 정의) 두 줄을 적어야 같은 개념이 들어간 질문 전체가 고쳐집니다.

### 실무에 적용하려면

데이터에 관한 모든 것을 프롬프트에 넣을 수는 없습니다. 이 실험에서 얻은 결론을 실무 구조로 옮기면 다음과 같습니다.

1. **자주 쓰는 지표부터 정의한다.** 실제 질문은 매출·주문 수·고객 수·지연율 같은 지표 수십 개에 몰립니다. 이 실험에서는 정의 4개로 60% → 100%가 됐습니다. 이 정의는 대시보드에도 필요한, 원래 정해 둬야 하는 것입니다.
2. **데이터 특징은 자동으로 뽑는다.** 컬럼별 샘플 값·형식·NULL 비율을 프로파일링해 프롬프트에 붙이면, "날짜만 들어 있는 컬럼" 같은 함정을 사람이 일일이 찾지 않아도 됩니다.
3. **정의 밖 질문은 모른다고 하거나 되묻는다.** 그럴듯한 오답보다 "이 지표는 정의돼 있지 않아 이렇게 해석했습니다, 맞나요?"가 낫습니다. 정의된 지표 안에서만 SQL을 조립하는 시맨틱 레이어(dbt Semantic Layer, Cube 등)가 이 방향의 극단입니다.
4. **틀린 사례를 골든셋에 쌓는다.** 오답이 나올 때마다 정의를 추가하고 그 문항을 골든셋에 넣어 두면, 프롬프트나 모델을 바꿀 때 다시 틀리는지 자동으로 확인할 수 있습니다.

```
지표 정의 → 서비스 → 오답 발견 → 정의·데이터 특징 추가 → 골든셋에 문항 추가 → (회귀 검증) → …
```

### 데모에 구현한 실무 장치

위 네 가지를 데모(`api.py`, `web/`)에 실제로 넣었습니다. **실험용 V0~V3 프롬프트는 그대로 두고** 데모에만 덧붙이므로 실험 결과는 재현됩니다.

| | 장치 | 동작 |
|---|---|---|
| A | 업무 정의 확장 (`catalog.DEMO_TERMS`) | 배송 지연·객단가·재구매·취소율·이탈·비율 단위 정의를 프롬프트에 추가. 정의 추가 = dict 한 줄 |
| B | 데이터 프로파일링 (`text2sql/profile.py`) | 컬럼별 타입·NULL 비율·값 목록·날짜 형식을 DB에서 자동 추출. "99% 이상 00:00:00이면 날짜만"(서머타임 흔적 85건 허용) |
| C | 정의 밖 지표 표시 | 모델이 SQL 위에 `-- 정의 밖: 고객 이탈률`로 스스로 보고 → 화면에 "해석을 확인하세요" 경고 |
| D | 피드백 → 회귀 셋 | 화면 "틀렸어요" → 올바른 SQL 저장(실행 검증 후 `regression.jsonl`) → `regress.py`가 데모 조건으로 재채점 |

**루프가 실제로 한 바퀴 돈 기록 — R001 "고객 이탈률은?"**

| 단계 | 결과 |
|---|---|
| 화면 질문 | 모델이 "1회 구매 고객 비율"로 직접 정의 → 96.88%, 정의 밖 경고 표시 → "틀렸어요"로 정답(최근 6개월 구매 없음, 59.13%) 저장 |
| 회귀 1차 | **error** — 이번엔 6개월 기준으로 해석했지만 별칭 오타. 같은 프롬프트에서도 해석이 흔들림 |
| 이탈 정의 추가 → 2차 | **silent_wrong** — 로직은 같아졌지만 0.5913 vs 59.13 (단위) |
| "비율은 0~100%" 규칙 추가 → 3차 | **correct** |

정의 하나로 끝나지 않았습니다. "이탈"의 기준 아래에 "비율을 어떤 단위로 쓰는가" 같은 숨은 관례가 하나 더 있었고, 회귀 셋이 그것을 드러냈습니다. 배송 지연율도 A+B 적용 후 같은 질문에 6.77%(정답)로 바뀌었습니다.

### 한계

- **골든셋이 작다 (20문항).** 100%의 95% 신뢰구간 하한이 91%이고, V1~V3 차이는 통계적으로 구분되지 않습니다.
- **천장 효과.** V1에서 이미 만점이라 조인 메모·예시의 효과를 잴 수 없었습니다. 더 어려운 문항(복잡한 조인, 애매한 지표)이 있어야 비교가 가능합니다.
- **정의를 아는 쪽이 채점한다.** V1에 넣은 업무 정의는 정답 SQL을 쓸 때 쓴 정의와 같습니다. 이것은 결함이라기보다 요점입니다 — "정답"은 조직의 정의에 달려 있고, 그 정의를 모델에게 알려 주지 않으면 맞힐 수 없습니다.
- 모델 1개(Gemini Flash), 데이터셋 1개, 무료 티어 한도 때문에 버전당 2회만 반복했습니다.
- **데모 실무 장치는 사례 단위로만 확인했습니다.** 정의 밖 경고는 모델의 자기 보고라 놓칠 수 있고, 피드백은 승인 단계 없이 저장되며, 프로파일의 샘플 값이 LLM으로 전송되므로 실제 회사 데이터라면 민감 컬럼 마스킹이 필요합니다.

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
| `text2sql/catalog.py`, `lint.py` | 테이블 관계·지표 정의(데모용 DEMO_TERMS 포함), 실행 전 위험 패턴 검사 |
| `text2sql/profile.py` | 컬럼 프로파일 자동 추출 (데모 프롬프트용) |
| `run.py` | 실험 실행 (일일 한도에 걸리면 저장 후 중단, 다음 실행 때 이어서) |
| `report.py` | `runs/*.csv` → `runs/report.md` |
| `api.py`, `web/` | 데모: FastAPI + React. 질문 → SQL·해석·정의 밖 경고·lint 경고·결과 표, "틀렸어요" 피드백 |
| `regression.jsonl`, `regress.py` | 실무 피드백 회귀 셋과 재채점 (`runs/regression.csv`) |

### 실행 방법

```bash
uv sync
# Kaggle Olist CSV를 data/raw/에 넣은 뒤
uv run python load_db.py
cp .env.example .env            # GEMINI_API_KEY 입력

uv run python run.py --version v1   # 실험 (--runs 기본 2)
uv run python report.py             # runs/report.md 갱신
uv run python regress.py            # 회귀 셋 재채점 (문항 수만큼 호출)
uv run pytest                       # 테스트 110개

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

### Beyond the golden set: "What share of orders arrived after the estimated date?"

After the experiment, we asked the demo (V3) about a metric that was never defined.

- Model's interpretation: "share of delivered orders whose actual delivery date is later than the estimated date" — **exactly the intent**
- Result: **8.11%** — no error, no lint warning
- Actual: **6.77%**. The estimated-date column holds dates only (`00:00:00`), but it was compared directly with the delivery timestamp, so **1,292 orders delivered on the estimated day were counted as late** — inflating the late rate by about 20%

The interpretation was right, the query ran, and the static check passed — yet the number was wrong. The same pattern seen in V0 reappeared outside the golden set. Instead of adding another example, two lines fix every question involving this concept: "the estimated date has no time part" (data quirk) and "late = compare by date" (business definition).

### Applying this in practice

You cannot put everything about the data into a prompt. Turning these findings into a working setup looks like this:

1. **Define the metrics people actually ask about.** Real questions cluster around a few dozen metrics — revenue, orders, customers, late rate. Here, 4 definitions took accuracy from 60% to 100%. These are definitions a dashboard needs anyway.
2. **Extract data quirks automatically.** Profiling each column (sample values, format, null ratio) and attaching it to the prompt catches traps like "date-only column" without humans hunting for them.
3. **Say "I don't know" or ask back outside the definitions.** "This metric isn't defined, so I read it as X — is that right?" beats a plausible wrong number. A semantic layer (dbt Semantic Layer, Cube, …) that only assembles SQL from defined metrics is the far end of this approach.
4. **Grow the golden set from failures.** Each wrong answer becomes a new definition plus a new golden question, so any later prompt or model change is automatically checked for regressions.

```
define metrics → serve → find a wrong answer → add definition / data quirk → add golden question → (regression check) → …
```

### Practical safeguards built into the demo

The four ideas above are implemented in the demo (`api.py`, `web/`). **The experiment prompts V0–V3 are untouched** — everything is appended only for the demo, so the experiment stays reproducible.

| | Safeguard | What it does |
|---|---|---|
| A | More business definitions (`catalog.DEMO_TERMS`) | Late delivery, average order value, repeat customer, cancellation rate, churn, and rate units added to the prompt. Adding a definition = one dict line |
| B | Data profiling (`text2sql/profile.py`) | Per-column type, null ratio, value list and date format extracted from the DB. "≥99% at 00:00:00 → date only" (tolerates 85 DST-shifted rows) |
| C | Flag undefined metrics | The model self-reports `-- 정의 밖: <metric>` above the SQL → the UI shows "check the interpretation" |
| D | Feedback → regression set | UI "this is wrong" → corrected SQL saved after execution check (`regression.jsonl`) → `regress.py` re-scores under demo conditions |

**One full turn of the loop — R001 "What is the customer churn rate?"**

| Step | Outcome |
|---|---|
| Asked in the UI | Model defined churn as "customers with one purchase" → 96.88%, undefined-metric warning shown → corrected answer (no purchase in last 6 months, 59.13%) saved |
| Regression run 1 | **error** — this time it used the 6-month rule but mistyped an alias. Same prompt, different interpretation |
| Add churn definition → run 2 | **silent_wrong** — same logic, but 0.5913 vs 59.13 (units) |
| Add "rates as 0–100%" rule → run 3 | **correct** |

One definition was not enough: beneath "churn" sat another unwritten convention — how rates are expressed — and the regression set surfaced it. The late-delivery question also returned the correct 6.77% after A+B.

### Limitations

- **Small golden set (20 questions).** The lower bound of the 95% CI at 100% is 91%; V1–V3 are not statistically distinguishable.
- **Ceiling effect.** V1 already scores 100%, so the value of join notes and examples could not be measured. Harder questions (complex joins, ambiguous metrics) are needed.
- **The grader knows the definitions.** The business definitions in V1 are the same ones used to write the gold SQL. That is less a flaw than the point: the "right answer" depends on the organization's definitions, and a model cannot get it right unless it is told them.
- One model (Gemini Flash), one dataset, and only 2 runs per version due to free-tier quotas.
- **The demo safeguards were checked case by case only.** Undefined-metric flags rely on the model's self-report and can be missed, feedback is saved without an approval step, and profile sample values are sent to the LLM — real company data would need masking of sensitive columns.

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
| `text2sql/catalog.py`, `lint.py` | Table relationships & metric definitions (incl. demo DEMO_TERMS), pre-execution risk checks |
| `text2sql/profile.py` | Automatic column profile (for the demo prompt) |
| `run.py` | Runs the experiment (saves and stops on daily quota, resumes next time) |
| `report.py` | `runs/*.csv` → `runs/report.md` |
| `api.py`, `web/` | Demo: FastAPI + React. Question → SQL, interpretation, undefined-metric and lint warnings, result table, "this is wrong" feedback |
| `regression.jsonl`, `regress.py` | Regression set from user feedback and its re-scoring (`runs/regression.csv`) |

### Usage

```bash
uv sync
# put the Kaggle Olist CSVs in data/raw/
uv run python load_db.py
cp .env.example .env            # set GEMINI_API_KEY

uv run python run.py --version v1   # experiment (--runs defaults to 2)
uv run python report.py             # refresh runs/report.md
uv run python regress.py            # re-score the regression set (one call per item)
uv run pytest                       # 110 tests

# demo
uv run uvicorn api:app --reload     # :8000
cd web && npm install && npm run dev
```

The demo uses `PROMPT_VERSION=v3` (default). It ties V1 on accuracy, but had 100% run-to-run agreement and includes the 1:N join warning and examples, which should make it safer for free-form questions outside the golden set.
