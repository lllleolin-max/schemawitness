"""Exact JSON transport. No Decimal-to-float conversions."""
from decimal import Decimal
import json
import math


class WireError(ValueError):
    pass


def dumps(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise WireError("non-finite number")
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise WireError("non-finite number")
        return json.dumps(value, allow_nan=False)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True)
    if isinstance(value, list):
        return "[" + ",".join(dumps(v) for v in value) + "]"
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        return "{" + ",".join(dumps(k) + ":" + dumps(value[k]) for k in sorted(value)) + "}"
    raise WireError("value must be JSON-compatible; keys must be strings")


def loads(text, *, max_bytes=1_000_000):
    if len(text.encode("utf-8")) > max_bytes:
        raise WireError("document exceeds byte limit")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise WireError("duplicate object key: " + key)
            result[key] = value
        return result

    def constant(value):
        raise WireError("invalid JSON number: " + value)

    try:
        return json.loads(text, parse_float=Decimal, parse_constant=constant,
                          object_pairs_hook=pairs)
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise WireError(str(exc)) from exc


def value_key(value):
    """JSON Schema equality: boolean != number; numeric spelling is irrelevant."""
    from fractions import Fraction
    if value is None:
        return ("null",)
    if isinstance(value, bool):
        return ("boolean", value)
    if isinstance(value, (int, Decimal)):
        return ("number", Fraction(value))
    if isinstance(value, str):
        return ("string", value)
    if isinstance(value, list):
        return ("array", tuple(value_key(v) for v in value))
    return ("object", tuple((k, value_key(v)) for k, v in sorted(value.items())))
