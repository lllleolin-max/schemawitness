"""Batch an API review into a fail-closed release decision."""
from .engine import compare
from .model import Limits


def review(manifest, *, limits=None):
    limits = limits or Limits()
    invalid = {"status": "INVALID", "decision": "BLOCK", "operations": [], "diagnostics": []}
    if not isinstance(manifest, dict) or set(manifest) != {"operations"} or not isinstance(manifest["operations"], list) or not manifest["operations"]:
        invalid["diagnostics"] = [{"code": "invalid_manifest", "message": "expected nonempty operations array"}]
        return invalid
    if len(manifest["operations"]) > limits.max_nodes:
        invalid["diagnostics"] = [{"code": "manifest_limit", "message": "too many operations"}]
        return invalid
    ids, results = set(), []
    for i, operation in enumerate(manifest["operations"]):
        if not isinstance(operation, dict) or set(operation) != {"id", "request", "response"}:
            invalid["diagnostics"] = [{"code": "invalid_manifest", "path": f"/operations/{i}", "message": "operation needs exactly id/request/response"}]
            return invalid
        identity = operation["id"]
        if not isinstance(identity, str) or not identity or identity in ids:
            invalid["diagnostics"] = [{"code": "invalid_manifest", "path": f"/operations/{i}/id", "message": "id must be a unique nonempty string"}]
            return invalid
        ids.add(identity)
        entry = {"id": identity}
        for direction in ("request", "response"):
            pair = operation[direction]
            if not isinstance(pair, dict) or set(pair) != {"old", "new"}:
                invalid["diagnostics"] = [{"code": "invalid_manifest", "path": f"/operations/{i}/{direction}", "message": "pair needs exactly old/new schemas"}]
                return invalid
            entry[direction] = compare(pair["old"], pair["new"], direction=direction, limits=limits).to_dict()
        results.append(entry)
    counts = {s: sum(e[d]["status"] == s for e in results for d in ("request", "response"))
              for s in ("COMPATIBLE", "BREAKING", "UNKNOWN", "INVALID")}
    status = next((s for s in ("INVALID", "BREAKING", "UNKNOWN") if counts[s]), "COMPATIBLE")
    return {"status": status, "decision": "ALLOW" if status == "COMPATIBLE" else "BLOCK",
            "counts": counts, "operations": results, "diagnostics": []}
