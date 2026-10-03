"""Intersection normalization and a deliberately sufficient inclusion calculus."""
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from urllib.parse import unquote
import re
from .wire import value_key

ATOMS = frozenset({"null", "boolean", "integer", "real", "string", "array", "object"})
DIALECT = "https://json-schema.org/draft/2020-12/schema"


@dataclass(frozen=True)
class Limits:
    max_nodes: int = 2000
    max_depth: int = 32
    max_candidates: int = 2000
    max_instance_units: int = 128
    max_number_digits: int = 256
    max_number_exponent: int = 1024
    max_document_bytes: int = 1_000_000
    max_total_candidate_bytes: int = 8_000_000

    def __post_init__(self):
        for key, value in vars(self).items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(key + " must be a positive integer")


class SchemaIssue(ValueError):
    def __init__(self, code, path, message):
        self.code, self.path, self.message = code, path, message
        super().__init__(message)

    def diagnostic(self):
        result = {"code": self.code, "path": self.path, "message": self.message}
        if hasattr(self, "schema"):
            result["schema"] = self.schema
        return result


@dataclass
class Shape:
    types: frozenset = ATOMS
    enum: tuple | None = None
    low: tuple | None = None       # (Fraction, exclusive)
    high: tuple | None = None
    min_length: int = 0
    max_length: int | None = None
    min_items: int = 0
    max_items: int | None = None
    items: "Shape | None" = None
    props: dict = field(default_factory=dict)
    required: frozenset = frozenset()
    additional: "Shape | None" = None

    def prop(self, key):
        return self.props.get(key, self.additional or Shape())

    def item(self):
        return self.items or Shape()


def tighter(a, b, lower):
    if a is None:
        return b
    if b is None:
        return a
    if a[0] == b[0]:
        return (a[0], a[1] or b[1])
    return max(a, b) if lower else min(a, b)


def smaller(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return min(a, b)


def meet(a, b):
    enums = a.enum if b.enum is None else b.enum if a.enum is None else tuple(
        v for v in a.enum if value_key(v) in {value_key(x) for x in b.enum})
    props = {k: meet(a.prop(k), b.prop(k)) for k in a.props.keys() | b.props.keys()}
    return Shape(a.types & b.types, enums, tighter(a.low, b.low, True),
                 tighter(a.high, b.high, False), max(a.min_length, b.min_length),
                 smaller(a.max_length, b.max_length), max(a.min_items, b.min_items),
                 smaller(a.max_items, b.max_items), meet(a.item(), b.item())
                 if a.items is not None or b.items is not None else None,
                 props, a.required | b.required,
                 meet(a.additional or Shape(), b.additional or Shape())
                 if a.additional is not None or b.additional is not None else None)


def atom(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, Decimal)):
        return "integer" if Fraction(value).denominator == 1 else "real"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


def accepts(s, value, _memo=None):
    if s == Shape():
        return True
    if _memo is None:
        _memo = {}
    pair = (id(s), id(value))
    if isinstance(value, (list, dict)) and pair in _memo:
        return _memo[pair]
    kind = atom(value)
    if kind not in s.types or (s.enum is not None and
            value_key(value) not in {value_key(v) for v in s.enum}):
        return False
    if kind in {"integer", "real"}:
        n = Fraction(value)
        return not ((s.low and (n < s.low[0] or (n == s.low[0] and s.low[1]))) or
                    (s.high and (n > s.high[0] or (n == s.high[0] and s.high[1]))))
    if kind == "string":
        return len(value) >= s.min_length and (s.max_length is None or len(value) <= s.max_length)
    if kind == "array":
        result = len(value) >= s.min_items and (s.max_items is None or len(value) <= s.max_items) and all(
            accepts(s.item(), v, _memo) for v in value)
        _memo[pair] = result
        return result
    if kind == "object":
        result = s.required <= value.keys() and all(accepts(s.prop(k), v, _memo) for k, v in value.items())
        _memo[pair] = result
        return result
    return True


def integer_bounds(s):
    lo = None if s.low is None else -(-s.low[0].numerator // s.low[0].denominator)
    hi = None if s.high is None else s.high[0].numerator // s.high[0].denominator
    if s.low and s.low[1] and s.low[0].denominator == 1:
        lo += 1
    if s.high and s.high[1] and s.high[0].denominator == 1:
        hi -= 1
    return lo, hi


def empty_kind(s, kind):
    if kind not in s.types:
        return True
    if s.enum is not None:
        return not any(atom(v) == kind and accepts(s, v) for v in s.enum)
    if kind in {"integer", "real"}:
        if s.low and s.high:
            if s.low[0] > s.high[0] or (s.low[0] == s.high[0] and (s.low[1] or s.high[1])):
                return True
            if kind == "real" and s.low[0] == s.high[0] and s.low[0].denominator == 1:
                return True
        if kind == "integer":
            lo, hi = integer_bounds(s)
            return lo is not None and hi is not None and lo > hi
    if kind == "string":
        return s.max_length is not None and s.min_length > s.max_length
    if kind == "array":
        return (s.max_items is not None and s.min_items > s.max_items) or (s.min_items > 0 and empty(s.item()))
    if kind == "object":
        return any(empty(s.prop(k)) for k in s.required)
    return False


def empty(s):
    return all(empty_kind(s, kind) for kind in s.types)


class Compiler:
    annotations = {"title", "description", "default", "examples", "deprecated", "readOnly", "writeOnly", "$comment"}
    supported = {"$schema", "$defs", "$ref", "allOf", "type", "enum", "const", "minimum", "maximum",
                 "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength", "properties", "required",
                 "additionalProperties", "items", "minItems", "maxItems"} | annotations

    def __init__(self, root, limits):
        self.root, self.limits, self.nodes = root, limits, 0

    def compile(self, schema=None, path="", stack=(), depth=0):
        if schema is None:
            schema = self.root
        self.nodes += 1
        if self.nodes > self.limits.max_nodes or depth > self.limits.max_depth:
            raise SchemaIssue("resource_limit", path, "schema expansion exceeds node/depth limit")
        if isinstance(schema, bool):
            return Shape() if schema else Shape(types=frozenset())
        if not isinstance(schema, dict):
            raise SchemaIssue("invalid_schema", path, "schema must be an object or boolean")
        for keyword in sorted(schema):
            if keyword not in self.supported:
                raise SchemaIssue("unsupported_keyword", path + "/" + keyword, "unsupported assertion or vocabulary: " + keyword)
        if "$schema" in schema and schema["$schema"] != DIALECT:
            raise SchemaIssue("unsupported_dialect", path + "/$schema", "only explicit 2020-12 dialect is supported")
        s = Shape()
        if "type" in schema:
            names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
            allowed = {"null", "boolean", "integer", "number", "string", "array", "object"}
            if not names or any(not isinstance(n, str) or n not in allowed for n in names) or len(set(names)) != len(names):
                raise SchemaIssue("invalid_schema", path + "/type", "type must contain unique supported JSON types")
            s.types = frozenset(x for n in names for x in ({"integer", "real"} if n == "number" else {n}))
        for keyword in ("enum", "const"):
            if keyword in schema:
                values = schema[keyword] if keyword == "enum" else [schema[keyword]]
                if not isinstance(values, list) or not values:
                    raise SchemaIssue("invalid_schema", path + "/" + keyword, "enum must be a nonempty array")
                if len(values) > self.limits.max_nodes:
                    raise SchemaIssue("resource_limit", path + "/" + keyword, "enum exceeds node limit")
                keys = [value_key(v) for v in values]
                if keyword == "enum" and len(set(keys)) != len(keys):
                    raise SchemaIssue("invalid_schema", path + "/enum", "enum contains equal JSON values")
                s = meet(s, Shape(enum=tuple(values)))
        for keyword in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"):
            if keyword in schema:
                value = schema[keyword]
                if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
                    raise SchemaIssue("invalid_schema", path + "/" + keyword, "bound must be a number")
                bound = (Fraction(value), keyword.startswith("exclusive"))
                if keyword in {"minimum", "exclusiveMinimum"}:
                    s.low = tighter(s.low, bound, True)
                else:
                    s.high = tighter(s.high, bound, False)
        for keyword, attr in (("minLength", "min_length"), ("maxLength", "max_length"),
                              ("minItems", "min_items"), ("maxItems", "max_items")):
            if keyword in schema:
                v = schema[keyword]
                if isinstance(v, bool) or not isinstance(v, (int, Decimal)) or Fraction(v).denominator != 1 or v < 0:
                    raise SchemaIssue("invalid_schema", path + "/" + keyword, "size bound must be a nonnegative integer")
                setattr(s, attr, int(v))
        if "required" in schema:
            req = schema["required"]
            if not isinstance(req, list) or any(not isinstance(v, str) for v in req) or len(set(req)) != len(req):
                raise SchemaIssue("invalid_schema", path + "/required", "required must be unique strings")
            s.required = frozenset(req)
        if "properties" in schema:
            if not isinstance(schema["properties"], dict):
                raise SchemaIssue("invalid_schema", path + "/properties", "properties must be an object")
            s.props = {k: self.compile(v, path + "/properties/" + k.replace("~", "~0").replace("/", "~1"), stack, depth + 1)
                       for k, v in sorted(schema["properties"].items())}
        for keyword, attr in (("additionalProperties", "additional"), ("items", "items")):
            if keyword in schema:
                setattr(s, attr, self.compile(schema[keyword], path + "/" + keyword, stack, depth + 1))
        if "$ref" in schema:
            ref = schema["$ref"]
            if not isinstance(ref, str) or not ref.startswith("#"):
                raise SchemaIssue("unsupported_reference", path + "/$ref", "only same-document JSON Pointer references are supported")
            if re.search(r"%(?![0-9A-Fa-f]{2})", ref):
                raise SchemaIssue("invalid_reference", path + "/$ref", "invalid percent escape in reference")
            try:
                pointer = unquote(ref[1:], errors="strict")
            except UnicodeError as exc:
                raise SchemaIssue("invalid_reference", path + "/$ref", "reference fragment is not valid UTF-8") from exc
            if pointer and not pointer.startswith("/"):
                raise SchemaIssue("unsupported_reference", path + "/$ref", "anchors are unsupported; use a JSON Pointer fragment")
            if re.search(r"~(?![01])", pointer):
                raise SchemaIssue("invalid_reference", path + "/$ref", "invalid JSON Pointer tilde escape")
            target = self.root
            try:
                for part in pointer[1:].split("/") if pointer else []:
                    key = part.replace("~1", "/").replace("~0", "~")
                    if isinstance(target, list):
                        if not re.fullmatch(r"0|[1-9][0-9]*", key):
                            raise ValueError("invalid array index token")
                        target = target[int(key)]
                    else:
                        target = target[key]
            except (KeyError, IndexError, ValueError, TypeError) as exc:
                raise SchemaIssue("invalid_reference", path + "/$ref", "reference target does not exist: " + ref) from exc
            if id(target) in stack:
                raise SchemaIssue("recursive_reference", path + "/$ref", "recursive references are not supported")
            s = meet(s, self.compile(target, pointer, stack + (id(target),), depth + 1))
        if "allOf" in schema:
            values = schema["allOf"]
            if not isinstance(values, list) or not values:
                raise SchemaIssue("invalid_schema", path + "/allOf", "allOf must be a nonempty array")
            for i, child in enumerate(values):
                s = meet(s, self.compile(child, path + "/allOf/" + str(i), stack, depth + 1))
        return s


def prove_subset(source, target, trace, path="", depth=0):
    """Sound sufficient rules only; False means 'not proved', never 'breaking'."""
    if source == target or target == Shape():
        trace.append({"path": path, "rule": "identical-normal-form" if source == target else "universal-target"})
        return True
    if empty(source):
        trace.append({"path": path, "rule": "empty-source"})
        return True
    if source.enum is not None:
        valid = [v for v in source.enum if accepts(source, v)]
        ok = all(accepts(target, v) for v in valid)
        if ok:
            trace.append({"path": path, "rule": "finite-enum", "valid_values": len(valid)})
        return ok
    for kind in sorted(source.types):
        if empty_kind(source, kind):
            continue
        if kind not in target.types:
            return False
        if target.enum is not None:
            finite = [None] if kind == "null" else [False, True] if kind == "boolean" else None
            if finite is None or not all(accepts(target, v) for v in finite):
                return False
            continue
        if kind == "integer":
            sl, sh = integer_bounds(source)
            tl, th = integer_bounds(target)
            if (tl is not None and (sl is None or sl < tl)) or (th is not None and (sh is None or sh > th)):
                return False
        if kind == "real":
            if target.low and (not source.low or source.low[0] < target.low[0] or
                               (source.low[0] == target.low[0] and target.low[1] and not source.low[1])):
                return False
            if target.high and (not source.high or source.high[0] > target.high[0] or
                                (source.high[0] == target.high[0] and target.high[1] and not source.high[1])):
                return False
        if kind == "string":
            if source.min_length < target.min_length or (target.max_length is not None and
                    (source.max_length is None or source.max_length > target.max_length)):
                return False
        if kind == "array":
            source_max = 0 if empty(source.item()) else source.max_items
            if source.min_items < target.min_items or (target.max_items is not None and
                    (source_max is None or source_max > target.max_items)):
                return False
            if source_max != 0 and not prove_subset(source.item(), target.item(), trace, path + "/items", depth + 1):
                return False
        if kind == "object":
            if not target.required <= source.required:
                return False
            for key in sorted(source.props.keys() | target.props.keys()):
                if not prove_subset(source.prop(key), target.prop(key), trace, path + "/properties/" + key.replace("~", "~0").replace("/", "~1"), depth + 1):
                    return False
            if not prove_subset(source.additional or Shape(), target.additional or Shape(), trace,
                                path + "/additionalProperties", depth + 1):
                return False
    trace.append({"path": path, "rule": "product-inclusion", "types": sorted(source.types)})
    return True
