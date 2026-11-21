#!/bin/sh
# 사용: sh eval_sqlverdict/score.sh  (저장소 루트에서)
set -u
cd "$(dirname "$0")"
SV="uv run --with sqlverdict==0.1.1 sqlverdict"
mkdir -p results
$SV check golden.yaml > results/check_golden.txt; echo "check golden exit=$?" >> results/check_golden.txt
$SV check golden.yaml --format json > results/check_golden.json
for p in predictions/*.yaml; do
  n=$(basename "$p" .yaml)
  $SV check golden.yaml "$p" --format json > "results/check_$n.json"
  $SV score golden.yaml "$p" --format json -o "results/$n.json"
  $SV score golden.yaml "$p" > "results/$n.txt"
done
$SV score golden.yaml predictions/v3_run1.yaml --baseline results/v0_run1.json --format json -o results/v3_run1_vs_v0_run1.json
$SV score golden.yaml predictions/v3_run1.yaml --baseline results/v0_run1.json > results/v3_run1_vs_v0_run1.txt
