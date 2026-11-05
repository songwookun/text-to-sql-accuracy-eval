## 버전별 정확도 (전체 회차 합산)
| 버전 | 진행 | correct | 95% CI | silent_wrong | error |
|---|---|---|---|---|---|
| v0 | 33/40 | 64% (21/33) | 47%–78% | 36% (12/33) | 0% (0/33) |

## 난이도별 정답률
| 버전 | L1 | L2 | L3 | L4 |
|---|---|---|---|---|
| v0 | 100% (10/10) | 73% (8/11) | 14% (1/7) | 40% (2/5) |

## 함정 문항 (L4)
| 버전 | biz_term | dup_join | empty_ok | unique_id |
|---|---|---|---|---|
| v0 | 0% (0/1) | 0% (0/2) | 100% (1/1) | 100% (1/1) |

## 회차 간 일관성 (같은 문항, run1 vs run2 라벨 일치)
| 버전 | 일치 |
|---|---|
| v0 | 85% (11/13) |

## 실패 문항
| 버전 | 회차 | 문항 | 함정 | 라벨 | 실패유형 | 상세 |
|---|---|---|---|---|---|---|
| v0 | r1 | Q08 |  | silent_wrong | dup_count | expected [('approved', 1), ('canceled', 421), ('created', 2) |
| v0 | r1 | Q11 |  | silent_wrong | revenue_def | expected [('2018-01', 924645.0), ('2018-02', 826437.13), ('2 |
| v0 | r1 | Q12 |  | silent_wrong | missing_filter | expected [('health_beauty', 755724.5), ('watches_gifts', 687 |
| v0 | r1 | Q13 |  | silent_wrong | missing_column | expected [('bed_bath_table', 5235), ('health_beauty', 4204), |
| v0 | r1 | Q14 |  | silent_wrong | missing_filter | expected [('SP', 8509511.46), ('PR', 1232096.99), ('MG', 977 |
| v0 | r1 | Q16 |  | silent_wrong | missing_filter | expected [(755724.5,)], got [(772238.15,)] |
| v0 | r1 | Q17 | dup_join | silent_wrong | revenue_def | expected [(404020.72,)], got [(343013.19,)] |
| v0 | r1 | Q19 | biz_term | silent_wrong | revenue_def | expected [(5962902.01,)], got [(7249746.73,)] |
| v0 | r2 | Q07 |  | silent_wrong | missing_column | expected [('bed_bath_table', 3029), ('sports_leisure', 2867) |
| v0 | r2 | Q12 |  | silent_wrong | missing_filter | expected [('health_beauty', 755724.5), ('watches_gifts', 687 |
| v0 | r2 | Q13 |  | silent_wrong | missing_column | expected [('bed_bath_table', 5235), ('health_beauty', 4204), |
| v0 | r2 | Q17 | dup_join | silent_wrong | revenue_def | expected [(404020.72,)], got [(343013.19,)] |

## 실패 유형 분포
| 유형 | 건수 |
|---|---|
| revenue_def | 4 |
| missing_filter | 4 |
| missing_column | 3 |
| dup_count | 1 |
