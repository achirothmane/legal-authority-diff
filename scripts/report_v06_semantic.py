import json
import sys
from pathlib import Path


report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
bench = report["benchmark"]
lex = report["lexical"]
sem = report["semantic"]
cmp = report["comparison"]

assert bench["name"] == "semantic-v0.6-heldout", bench
assert bench["pairs"] == 20, bench
assert bench["labels"] == {"supported": 10, "unsupported": 10}, bench
assert bench["no_tuning_protocol"] is True, bench

print("V0.6 SEMANTIC HELD-OUT BENCHMARK: COMPLETE")
print(f"pairs: {bench['pairs']}")
print(
    "lexical: "
    f"TP={lex['counts']['tp']} TN={lex['counts']['tn']} "
    f"FP={lex['counts']['fp']} FN={lex['counts']['fn']} "
    f"accuracy={lex['metrics']['accuracy']:.3f}"
)
print(
    "semantic: "
    f"TP={sem['counts']['tp']} TN={sem['counts']['tn']} "
    f"FP={sem['counts']['fp']} FN={sem['counts']['fn']} "
    f"accuracy={sem['metrics']['accuracy']:.3f}"
)
print(f"semantic model: {sem['model']}")
print(f"fixed_by_semantic: {cmp['fixed_by_semantic']}")
print(f"broken_by_semantic: {cmp['broken_by_semantic']}")
print(f"same_wrong: {cmp['same_wrong']}")

for row in sem["rows"]:
    if not row["correct"]:
        print(
            f"SEMANTIC_MISS {row['pair_id']} "
            f"expected={row['expected_support']} "
            f"predicted={row['predicted_support']} "
            f"score={row['score']:.3f} citation={row['citation']}"
        )
