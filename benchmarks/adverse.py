"""Executed honest UNKNOWN boundaries, not selected happy-path cases."""
from decimal import Decimal
from schemawitness import compare, Limits, dumps

cases = [
    ("unproved-equivalent-empty-array", {"type": "array", "items": False}, {"const": []}, Limits()),
    ("candidate-length-budget", {"type": "string", "minLength": 500}, {"const": "x"}, Limits(max_instance_units=10)),
    ("numeric-range-budget", {"minimum": Decimal("1E1025")}, True, Limits()),
    ("unsupported-combinator", {"anyOf": [{"type": "integer"}, {"type": "string"}]}, True, Limits()),
]
for name, old, new, limits in cases:
    result = compare(old, new, limits=limits)
    assert result.status == "UNKNOWN", (name, result.to_dict())
    assert result.wire is None
    print(dumps({"case": name, "status": result.status, "diagnostics": result.diagnostics, "metrics": result.metrics}))
