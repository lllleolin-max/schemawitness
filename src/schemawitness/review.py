"""Batch an API review into a fail-closed release decision."""
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import math
from .engine import compare, Result
from .model import Limits
from .wire import dumps, WireError, WireLimitError
from .budget import BatchLimits, BatchInputLimit, BatchWorkLimit, WorkBudget


def _shape_error(manifest, limits):
    # Complete structural validation precedes normalization and core work.
    if not isinstance(manifest, dict) or len(manifest) != 1 or set(manifest) != {"operations"} or not isinstance(manifest["operations"], list) or not manifest["operations"]:
        return {"code": "invalid_manifest", "message": "expected nonempty operations array"}
    if len(manifest["operations"]) > limits.max_nodes:
        return {"code": "manifest_limit", "message": "too many operations"}
    ids = set()
    for i, operation in enumerate(manifest["operations"]):
        if not isinstance(operation, dict) or len(operation) != 3 or set(operation) != {"id", "request", "response"}:
            return {"code": "invalid_manifest", "path": f"/operations/{i}", "message": "operation needs exactly id/request/response"}
        identity = operation["id"]
        if not isinstance(identity, str) or not identity or identity in ids:
            return {"code": "invalid_manifest", "path": f"/operations/{i}/id", "message": "id must be a unique nonempty string"}
        ids.add(identity)
        for direction in ("request", "response"):
            pair = operation[direction]
            if not isinstance(pair, dict) or len(pair) != 2 or set(pair) != {"old", "new"}:
                return {"code": "invalid_manifest", "path": f"/operations/{i}/{direction}", "message": "pair needs exactly old/new schemas"}
    return None


def _input_size(manifest, limits, batch_limits):
    nodes, active = 0, set()

    def visit(value, depth=0):
        nonlocal nodes
        nodes += 1
        if nodes > batch_limits.max_input_nodes or depth > limits.max_depth * 2 + 4:
            raise BatchInputLimit("input node/depth budget exhausted")
        if isinstance(value, bool) or value is None:
            return
        if isinstance(value, int):
            # Check before decimal string conversion (including Python's cap).
            if value.bit_length() > limits.max_number_digits * 4:
                raise BatchInputLimit("input numeric digit budget exhausted")
            if len(Decimal(value).as_tuple().digits) > limits.max_number_digits:
                raise BatchInputLimit("input numeric digit budget exhausted")
        elif isinstance(value, Decimal):
            if not value.is_finite():
                raise WireError("non-finite JSON number")
            parts = value.as_tuple()
            if len(parts.digits) > limits.max_number_digits or abs(parts.exponent) > limits.max_number_exponent:
                raise BatchInputLimit("input numeric digit/exponent budget exhausted")
        elif isinstance(value, float):
            if not math.isfinite(value):
                raise WireError("non-finite JSON number")
        elif isinstance(value, str):
            if len(value) > batch_limits.max_input_bytes:
                raise BatchInputLimit("input string budget exhausted")
        elif isinstance(value, (dict, list)):
            if id(value) in active:
                raise WireError("cyclic JSON input")
            active.add(id(value))
            if isinstance(value, dict):
                for key, child in value.items():
                    if not isinstance(key, str):
                        raise WireError("object keys must be strings")
                    visit(key, depth + 1)
                    visit(child, depth + 1)
            else:
                for child in value:
                    visit(child, depth + 1)
            active.remove(id(value))
        else:
            raise WireError("value must be JSON-compatible")

    visit(manifest)
    size = len(dumps(manifest, max_bytes=batch_limits.max_input_bytes,
                     max_depth=limits.max_depth * 2 + 4))
    return nodes, size


def _schema_identity(value):
    """Full original document identity: type + exact wire spelling, not equality.

    Booleans, integers, Decimal coefficients/exponents and float spellings are
    distinct. Keys are sorted; arrays retain order; local reference targets and
    encoded pointer spellings remain inside the document identity.
    """
    digest = sha256()

    def put(token):
        token = token.encode("ascii")
        digest.update(str(len(token)).encode("ascii") + b":" + token)

    def visit(v):
        if isinstance(v, dict):
            put("object")
            put(str(len(v)))
            for key in sorted(v):
                put(dumps(key))
                visit(v[key])
        elif isinstance(v, list):
            put("array")
            put(str(len(v)))
            for child in v:
                visit(child)
        else:
            kind = "null" if v is None else "bool" if isinstance(v, bool) else "int" if isinstance(v, int) else "decimal" if isinstance(v, Decimal) else "float" if isinstance(v, float) else "string"
            put(kind)
            put(dumps(v))

    visit(value)
    return digest.hexdigest()


def _unknown(direction, code):
    result = Result("UNKNOWN", direction, "old_subset_new" if direction == "request" else "new_subset_old")
    result.diagnostics = [{"code": code, "path": "", "message": "shared batch bound exhausted; no certificate was retained"}]
    return result.to_dict()


def review(manifest, *, limits=None, batch_limits=None):
    """Default: original per-direction bounds. BatchLimits opts into sharing.

    The cache is private to this call, never crosses a trust domain or manifest,
    and stores detached results. Caller mutation during a call is unsupported;
    inputs and returned results are not mutated by the review.
    """
    limits = limits or Limits()
    if batch_limits is not None and not isinstance(batch_limits, BatchLimits):
        raise TypeError("batch_limits must be BatchLimits or None")
    invalid = {"status": "INVALID", "decision": "BLOCK", "operations": [], "diagnostics": []}
    error = _shape_error(manifest, limits)
    if error:
        invalid["diagnostics"] = [error]
        return invalid
    budget = WorkBudget(batch_limits) if batch_limits is not None else None
    cache, cache_bytes, result_bytes = {}, 0, 0
    stats = {"core_compare_calls": 0, "cache_hits": 0, "input_nodes": 0, "input_bytes": 0}
    if budget is not None:
        try:
            stats["input_nodes"], stats["input_bytes"] = _input_size(manifest, limits, batch_limits)
        except (BatchInputLimit, WireLimitError):
            budget.halted = "batch_input_limit"
        except WireError as exc:
            invalid["diagnostics"] = [{"code": "invalid_json", "message": str(exc)}]
            return invalid
    results = []
    for operation in manifest["operations"]:
        entry = {"id": operation["id"]}
        for direction in ("request", "response"):
            pair = operation[direction]
            if budget is None:
                entry[direction] = compare(pair["old"], pair["new"], direction=direction, limits=limits).to_dict()
                continue
            old_id = new_id = None
            cache_hit = False
            try:
                budget.charge("cache_lookup")
                old_id, new_id = _schema_identity(pair["old"]), _schema_identity(pair["new"])
                key = (direction, old_id, new_id)
                if key in cache:
                    result = cache[key]
                    cache_hit = True
                    stats["cache_hits"] += 1
                else:
                    if len(cache) >= batch_limits.max_cache_entries:
                        budget.halt("batch_cache_limit")
                    stats["core_compare_calls"] += 1
                    result = compare(pair["old"], pair["new"], direction=direction, limits=limits, _budget=budget).to_dict()
                    if budget.halted:
                        raise BatchWorkLimit(budget.halted)
                    budget.charge("cache_store")
                    size = len(dumps(result)) + len(direction) + 128
                    if cache_bytes + size > batch_limits.max_cache_bytes:
                        budget.halt("batch_cache_limit")
                    cache[key] = deepcopy(result)
                    cache_bytes += size
                size = len(dumps(result))
                if result_bytes + size > batch_limits.max_result_bytes:
                    budget.halt("batch_result_limit")
                result_bytes += size
                result = deepcopy(result)
            except BatchWorkLimit:
                result = _unknown(direction, budget.halted)
            result["batch"] = {"operation_id": operation["id"], "direction": direction,
                               "old_identity": old_id, "new_identity": new_id,
                               "cache_hit": cache_hit, "evaluated": not bool(budget.halted)}
            entry[direction] = result
        results.append(entry)
    counts = {s: sum(e[d]["status"] == s for e in results for d in ("request", "response"))
              for s in ("COMPATIBLE", "BREAKING", "UNKNOWN", "INVALID")}
    status = next((s for s in ("INVALID", "BREAKING", "UNKNOWN") if counts[s]), "COMPATIBLE")
    report = {"status": status, "decision": "ALLOW" if status == "COMPATIBLE" else "BLOCK",
              "counts": counts, "operations": results, "diagnostics": []}
    if budget is not None:
        report["batch"] = {**stats, "work_used": budget.used, "work_by_kind": dict(budget.by_kind),
                           "limits": vars(batch_limits).copy(), "cache_entries": len(cache),
                           "cache_bytes": cache_bytes, "result_bytes": result_bytes,
                           "halted": budget.halted}
    return report
