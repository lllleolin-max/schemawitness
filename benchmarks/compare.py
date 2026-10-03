"""Disclosed synthetic corpus, executed shallow baseline and two ablations.

This is not an oasdiff/Pact benchmark. The baseline is deliberately restricted
to root-level directional type/required/enum/numeric checks and assumes safety
when those checks find no change, a common but unsafe hand-review shortcut.
"""
from decimal import Decimal
from time import perf_counter
from schemawitness import compare, dumps


def shallow(old, new, direction):
    source, target = (old, new) if direction == "request" else (new, old)
    if not isinstance(source, dict) or not isinstance(target, dict):
        return "COMPATIBLE" if source == target or source is False or target is True else "BREAKING"
    if not set(target.get("required", [])) <= set(source.get("required", [])):
        return "BREAKING"
    if "enum" in source and "enum" in target and any(v not in target["enum"] for v in source["enum"]):
        return "BREAKING"
    for keyword in ("minimum", "exclusiveMinimum"):
        if keyword in target and (keyword not in source or target[keyword] > source[keyword]):
            return "BREAKING"
    for keyword in ("maximum", "exclusiveMaximum"):
        if keyword in target and (keyword not in source or target[keyword] < source[keyword]):
            return "BREAKING"
    a, b = source.get("type"), target.get("type")
    if a != b and b is not None and (a, b) != ("integer", "number"):
        return "BREAKING"
    return "COMPATIBLE"


def cases():
    yield "required-request", {"type": "object"}, {"type": "object", "required": ["id"]}, "request", "BREAKING"
    yield "required-response", {"type": "object", "required": ["id"]}, {"type": "object"}, "response", "BREAKING"
    yield "nested-number", {"type": "object", "properties": {"n": {"type": "integer"}}}, {"type": "object", "properties": {"n": {"type": "integer", "minimum": 5}}}, "request", "BREAKING"
    yield "array-items", {"type": "array", "items": {"type": "number"}}, {"type": "array", "items": {"minimum": 0}}, "request", "BREAKING"
    yield "extra-properties", {"type": "object"}, {"type": "object", "additionalProperties": False}, "request", "BREAKING"
    yield "reference-sibling", {"$defs": {"N": {"type": "integer"}}, "$ref": "#/$defs/N", "minimum": 1}, {"$defs": {"N": {"type": "integer", "minimum": 3}}, "$ref": "#/$defs/N", "minimum": 1}, "request", "BREAKING"
    yield "integer-widen", {"type": "integer"}, {"type": "number"}, "request", "COMPATIBLE"
    yield "unsatisfiable-source", {"type": "number", "minimum": 2, "maximum": 1}, False, "request", "COMPATIBLE"
    yield "empty-array", {"type": "array", "items": False}, {"type": "array", "maxItems": 0}, "request", "COMPATIBLE"
    yield "boolean-number-enum", {"enum": [True, 1]}, {"enum": [1]}, "request", "BREAKING"
    yield "precise-decimal", {"const": Decimal("9007199254740993.000000000000000001")}, {"maximum": Decimal("9007199254740993")}, "request", "BREAKING"
    yield "unsupported-pattern", {"type": "string", "pattern": "^x$"}, {"type": "string"}, "request", "UNKNOWN"


def main():
    totals = {"full_correct": 0, "shallow_correct": 0, "search_only_correct": 0, "proof_only_correct": 0}
    start = perf_counter()
    rows = []
    for name, old, new, direction, expected in cases():
        full = compare(old, new, direction=direction)
        search_only = compare(old, new, direction=direction, prove=False)
        proof_only = compare(old, new, direction=direction, search=False)
        baseline = shallow(old, new, direction)
        assert full.status == expected, (name, full.to_dict())
        for key, actual in (("full_correct", full.status), ("shallow_correct", baseline),
                            ("search_only_correct", search_only.status), ("proof_only_correct", proof_only.status)):
            totals[key] += actual == expected
        rows.append({"case": name, "expected": expected, "full": full.status, "shallow": baseline,
                     "search_only": search_only.status, "proof_only": proof_only.status,
                     "wire": full.wire, "generated_candidates": full.metrics.get("generated_candidates", 0)})
    print(dumps({"synthetic": True, "not_an_incumbent_benchmark": True, "rows": rows,
                 "totals": totals, "case_count": len(rows), "elapsed_seconds": perf_counter() - start}))


if __name__ == "__main__":
    main()
