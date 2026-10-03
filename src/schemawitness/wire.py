"""Exact JSON transport. No Decimal-to-float conversions."""
from decimal import Decimal
import json
import math


class WireError(ValueError):
    pass


class WireLimitError(WireError):
    pass


def dumps(value, *, max_bytes=None, max_depth=64):
    """Bound during emission, before allocating an oversized complete wire.

    ensure_ascii makes all emitted text ASCII, so character counts equal bytes.
    The bounded path escapes strings incrementally too.
    """
    pieces, used, active = [], 0, set()

    def emit(token):
        nonlocal used
        if max_bytes is not None and used + len(token) > max_bytes:
            raise WireLimitError("wire exceeds byte limit during serialization")
        pieces.append(token)
        used += len(token)

    def encode(v, depth):
        if depth > max_depth:
            raise WireLimitError("wire exceeds depth limit during serialization")
        if v is None:
            emit("null")
        elif isinstance(v, bool):
            emit("true" if v else "false")
        elif isinstance(v, int):
            emit(str(v))
        elif isinstance(v, Decimal):
            if not v.is_finite():
                raise WireError("non-finite number")
            emit(str(v))
        elif isinstance(v, float):
            if not math.isfinite(v):
                raise WireError("non-finite number")
            emit(json.dumps(v, allow_nan=False))
        elif isinstance(v, str):
            if max_bytes is None:
                emit(json.dumps(v, ensure_ascii=True))
            else:
                emit('"')
                for char in v:
                    emit(json.dumps(char, ensure_ascii=True)[1:-1])
                emit('"')
        elif isinstance(v, (list, dict)):
            if id(v) in active:
                raise WireError("cyclic JSON input")
            active.add(id(v))
            if isinstance(v, list):
                emit("[")
                for i, child in enumerate(v):
                    if i:
                        emit(",")
                    encode(child, depth + 1)
                emit("]")
            else:
                if not all(isinstance(k, str) for k in v):
                    raise WireError("object keys must be strings")
                emit("{")
                for i, key in enumerate(sorted(v)):
                    if i:
                        emit(",")
                    encode(key, depth + 1)
                    emit(":")
                    encode(v[key], depth + 1)
                emit("}")
            active.remove(id(v))
        else:
            raise WireError("value must be JSON-compatible")

    encode(value, 0)
    return "".join(pieces)


def loads(text, *, max_bytes=1_000_000):
    if len(text.encode("utf-8")) > max_bytes:
        raise WireLimitError("document exceeds byte limit")

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
