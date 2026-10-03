"""Installed-package API review with concrete witnesses as regression fixtures."""
from pathlib import Path
from schemawitness import loads, dumps, review

root = Path(__file__).resolve().parent
result = review(loads((root / "release.json").read_text(encoding="utf-8")))
assert result["decision"] == "BLOCK"
assert result["counts"] == {"COMPATIBLE": 2, "BREAKING": 2, "UNKNOWN": 0, "INVALID": 0}
for operation in result["operations"]:
    for direction in ("request", "response"):
        check = operation[direction]
        print(dumps({"operation": operation["id"], "direction": direction,
                     "status": check["status"], "wire": check["wire"]}))
print("release=BLOCK; two verified wire fixtures available for maintainer review")
