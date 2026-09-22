import json
import sys
from pathlib import Path


report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

benchmark = report["benchmark"]
counts = report["counts"]
metrics = report["metrics"]
dist = report["score_distribution"]
rows = report["rows"]

assert benchmark["pairs"] == 20, benchmark
assert benchmark["labels"] == {"supported": 10, "unsupported": 10}, benchmark
assert counts["total"] == 20, counts

print("V0.5 REAL CLAIM-CITATION BENCHMARK: COMPLETE")
print(f"model: {report['model']}")
print(f"threshold: {report['threshold']}")
print(
    "confusion: "
    f"TP={counts['tp']} TN={counts['tn']} "
    f"FP={counts['fp']} FN={counts['fn']}"
)
print(
    "metrics: "
    f"accuracy={metrics['accuracy']:.3f} "
    f"precision={metrics['precision']:.3f} "
    f"recall={metrics['recall']:.3f} "
    f"fpr={metrics['false_positive_rate']:.3f} "
    f"fnr={metrics['false_negative_rate']:.3f}"
)
print(
    "scores: "
    f"supported_mean={dist['supported_mean']} "
    f"unsupported_mean={dist['unsupported_mean']}"
)

mistakes = [row for row in rows if not row["correct"]]
print(f"misclassifications: {len(mistakes)}")
for row in mistakes:
    print(
        f"- {row['pair_id']} claim={row['claim_id']} "
        f"expected={row['expected_support']} "
        f"predicted={row['predicted_support']} "
        f"score={row['score']:.3f} "
        f"citation={row['citation']}"
    )
