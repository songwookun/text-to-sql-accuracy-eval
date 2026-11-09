## 버전별 정확도 (전체 회차 합산)
| 버전 | 진행 | correct | 95% CI | 너그러운 correct | silent_wrong | error |
|---|---|---|---|---|---|---|
| v0 | 40/40 | 60% (24/40) | 45%–74% | 68% (27/40) | 40% (16/40) | 0% (0/40) |
| v1 | 40/40 | 100% (40/40) | 91%–100% | 100% (40/40) | 0% (0/40) | 0% (0/40) |
| v2 | 8/40 | 88% (7/8) | 53%–98% | 100% (8/8) | 12% (1/8) | 0% (0/8) |

너그러운 correct: 컬럼 수만 다르고 겹치는 컬럼 값·순서는 같은 경우까지 정답 (예: 순위는 맞는데 개수 컬럼 누락)

## 난이도별 정답률
| 버전 | L1 | L2 | L3 | L4 |
|---|---|---|---|---|
| v0 | 100% (10/10) | 67% (8/12) | 20% (2/10) | 50% (4/8) |
| v1 | 100% (10/10) | 100% (12/12) | 100% (10/10) | 100% (8/8) |
| v2 | 100% (5/5) | 67% (2/3) | — | — |

## 함정 문항 (L4)
| 버전 | biz_term | dup_join | empty_ok | unique_id |
|---|---|---|---|---|
| v0 | 0% (0/2) | 0% (0/2) | 100% (2/2) | 100% (2/2) |
| v1 | 100% (2/2) | 100% (2/2) | 100% (2/2) | 100% (2/2) |
| v2 | — | — | — | — |

## 회차 간 일관성 (같은 문항, run1 vs run2 라벨 일치)
| 버전 | 일치 |
|---|---|
| v0 | 90% (18/20) |
| v1 | 100% (20/20) |
| v2 | — |

## 실패 문항
| 버전 | 회차 | 문항 | 함정 | 라벨 | 너그러운 | 실패유형 | 상세 |
|---|---|---|---|---|---|---|---|
| v0 | r1 | Q08 |  | silent_wrong |  | dup_count | expected [('approved', 1), ('canceled', 421), ('created', 2) |
| v0 | r1 | Q11 |  | silent_wrong |  | revenue_def | expected [('2018-01', 924645.0), ('2018-02', 826437.13), ('2 |
| v0 | r1 | Q12 |  | silent_wrong |  | missing_filter | expected [('health_beauty', 755724.5), ('watches_gifts', 687 |
| v0 | r1 | Q13 |  | silent_wrong | ✓ | missing_column | expected [('bed_bath_table', 5235), ('health_beauty', 4204), |
| v0 | r1 | Q14 |  | silent_wrong |  | missing_filter | expected [('SP', 8509511.46), ('PR', 1232096.99), ('MG', 977 |
| v0 | r1 | Q16 |  | silent_wrong |  | missing_filter | expected [(755724.5,)], got [(772238.15,)] |
| v0 | r1 | Q17 | dup_join | silent_wrong |  | revenue_def | expected [(404020.72,)], got [(343013.19,)] |
| v0 | r1 | Q19 | biz_term | silent_wrong |  | revenue_def | expected [(5962902.01,)], got [(7249746.73,)] |
| v0 | r2 | Q07 |  | silent_wrong | ✓ | missing_column | expected [('bed_bath_table', 3029), ('sports_leisure', 2867) |
| v0 | r2 | Q11 |  | silent_wrong |  | revenue_def | expected [('2018-01', 924645.0), ('2018-02', 826437.13), ('2 |
| v0 | r2 | Q12 |  | silent_wrong |  | missing_filter | expected [('health_beauty', 755724.5), ('watches_gifts', 687 |
| v0 | r2 | Q13 |  | silent_wrong | ✓ | missing_column | expected [('bed_bath_table', 5235), ('health_beauty', 4204), |
| v0 | r2 | Q14 |  | silent_wrong |  | missing_filter | expected [('SP', 8509511.46), ('PR', 1232096.99), ('MG', 977 |
| v0 | r2 | Q16 |  | silent_wrong |  | missing_filter | expected [(755724.5,)], got [(772238.15,)] |
| v0 | r2 | Q17 | dup_join | silent_wrong |  | revenue_def | expected [(404020.72,)], got [(343013.19,)] |
| v0 | r2 | Q19 | biz_term | silent_wrong |  | revenue_def | expected [(5962902.01,)], got [(7249746.73,)] |
| v2 | r1 | Q07 |  | silent_wrong | ✓ | missing_column | expected [('bed_bath_table', 3029), ('sports_leisure', 2867) |

## 실패 유형 분포
| 유형 | 건수 |
|---|---|
| revenue_def | 6 |
| missing_filter | 6 |
| missing_column | 4 |
| dup_count | 1 |

## lint 탐지 (실행 전 정적 검사)
| 버전 | 진짜 오답 중 탐지 | 정답인데 경고(오탐) |
|---|---|---|
| v0 | 100% (13/13) | 0% (0/24) |
| v1 | — | 0% (0/40) |
| v2 | — | 0% (0/7) |

진짜 오답 = 너그러운 채점으로도 틀린 것. 주의: 규칙을 V0 오답을 보고 만들었으므로 V0 탐지율은 과대평가
