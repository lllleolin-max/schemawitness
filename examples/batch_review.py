"""Offline synthetic SDK batch: reuse checks, preserve evidence, fail closed."""
from copy import deepcopy
from schemawitness import BatchLimits, dumps, review

old = {"type": "number", "minimum": 0}
new = {"type": "number", "exclusiveMinimum": 0}
manifest = {"operations": [{"id": "synthetic-" + str(i), "request": {"old": old, "new": new},
                            "response": {"old": old, "new": new}} for i in range(3)]}
before = deepcopy(manifest)
report = review(manifest, batch_limits=BatchLimits(max_work=1000))
assert report["counts"] == {"COMPATIBLE": 3, "BREAKING": 3, "UNKNOWN": 0, "INVALID": 0}
assert report["batch"]["core_compare_calls"] == 2
assert report["operations"][2]["request"]["wire"] == "0"
assert report["operations"][2]["request"]["batch"]["operation_id"] == "synthetic-2"
limited = review(manifest, batch_limits=BatchLimits(max_work=1))
assert limited["decision"] == "BLOCK" and limited["counts"]["UNKNOWN"] == 6
assert manifest == before
print(dumps({"full": report["counts"], "core_compare_calls": report["batch"]["core_compare_calls"],
             "cache_hits": report["batch"]["cache_hits"], "limited": limited["counts"],
             "decision": limited["decision"], "input_unchanged": True}))
