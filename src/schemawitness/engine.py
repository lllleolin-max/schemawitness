"""Public directional comparison and independent post-transport evidence."""
from dataclasses import dataclass, field, asdict
from decimal import Decimal
from fractions import Fraction
from jsonschema import Draft202012Validator, validators
from jsonschema.exceptions import SchemaError
from referencing import Registry
from referencing.exceptions import NoSuchResource
from .model import Compiler, Limits, SchemaIssue, prove_subset
from .search import Search
from .wire import dumps, loads, WireError, WireLimitError


def _integer(checker, value):
    return not isinstance(value, bool) and isinstance(value, (int, Decimal)) and Fraction(value).denominator == 1


ExactValidator = validators.extend(Draft202012Validator, type_checker=
    Draft202012Validator.TYPE_CHECKER.redefine("integer", _integer))


def _no_network(uri):
    raise NoSuchResource(ref=uri)


def _validator_instance(value):
    # Same mathematical JSON value, with integral Decimals represented as ints.
    # This survives jsonschema's dialect-specific validator switching for refs
    # into arbitrary schema-shaped locations, without changing ANY schema data.
    if isinstance(value, Decimal) and Fraction(value).denominator == 1:
        return int(value)
    if isinstance(value, dict):
        return {k: _validator_instance(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_validator_instance(v) for v in value]
    return value


def _meta_schema(value):
    if isinstance(value, Decimal) and value == value.to_integral_value():
        return int(value)
    if isinstance(value, dict):
        return {k: _meta_schema(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_meta_schema(v) for v in value]
    return value


def independent_validate(schema, value):
    validator = ExactValidator(schema, registry=Registry(retrieve=_no_network))
    errors = sorted(validator.iter_errors(_validator_instance(value)), key=lambda e: (str(list(e.path)), str(list(e.schema_path))))
    return {"valid": not errors, "errors": [{"instance_path": list(e.path),
            "schema_path": list(e.schema_path), "keyword": e.validator} for e in errors[:8]]}


@dataclass
class Result:
    status: str
    direction: str
    inclusion: str
    proof: list = field(default_factory=list)
    witness: object = None
    wire: str | None = None
    validation: dict = field(default_factory=dict)
    diagnostics: list = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


def _preflight(value, limits, path="", depth=0, count=None):
    if count is None:
        count = [0]
    count[0] += 1
    if count[0] > limits.max_nodes * 10 or depth > limits.max_depth * 2:
        raise SchemaIssue("resource_limit", path, "input tree exceeds resource limit")
    if isinstance(value, (int, Decimal)) and not isinstance(value, bool):
        decimal = Decimal(value)
        if not decimal.is_finite():
            raise WireError("non-finite JSON number")
        if len(decimal.as_tuple().digits) > limits.max_number_digits or abs(decimal.as_tuple().exponent) > limits.max_number_exponent:
            raise SchemaIssue("unsupported_numeric_range", path,
                              "numeric literal exceeds configured digit/exponent limits; never rounded")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise WireError("object keys must be strings")
            _preflight(child, limits, path + "/" + key.replace("~", "~0").replace("/", "~1"), depth + 1, count)
    if isinstance(value, list):
        for i, child in enumerate(value):
            _preflight(child, limits, path + "/" + str(i), depth + 1, count)
    if isinstance(value, str) and len(value) > limits.max_document_bytes:
        raise SchemaIssue("resource_limit", path, "string exceeds document budget")


def compare(old, new, *, direction="request", limits=None, prove=True, search=True):
    """Compare JSON-compatible schemas. COMPATIBLE requires a sufficient proof.

    Request checks old <= new. Response checks new <= old. BREAKING always has
    independently validated evidence AFTER exact serialization and reparsing.
    """
    if direction not in {"request", "response"}:
        raise ValueError("direction must be request or response")
    limits = limits or Limits()
    result = Result("UNKNOWN", direction, "old_subset_new" if direction == "request" else "new_subset_old")
    try:
        _preflight(old, limits, "/old")
        _preflight(new, limits, "/new")
        old = loads(dumps(old, max_bytes=limits.max_document_bytes, max_depth=limits.max_depth * 2), max_bytes=limits.max_document_bytes)
        new = loads(dumps(new, max_bytes=limits.max_document_bytes, max_depth=limits.max_depth * 2), max_bytes=limits.max_document_bytes)
        for label, schema in (("old", old), ("new", new)):
            _preflight(schema, limits, "/" + label)
            try:
                Draft202012Validator.check_schema(_meta_schema(schema))
            except SchemaError as exc:
                raise SchemaIssue("invalid_schema", "/" + label + "/" + "/".join(str(p) for p in exc.path),
                                  "invalid 2020-12 schema: " + exc.message) from exc
        oc, nc = Compiler(old, limits), Compiler(new, limits)
        os, ns = oc.compile(), nc.compile()
        result.metrics["normalized_nodes"] = oc.nodes + nc.nodes
    except SchemaIssue as exc:
        result.status = "INVALID" if exc.code.startswith("invalid_") else "UNKNOWN"
        result.diagnostics.append(exc.diagnostic())
        return result
    except WireLimitError as exc:
        result.diagnostics.append({"code": "resource_limit", "path": "", "message": str(exc)})
        return result
    except (WireError, RecursionError, TypeError, ValueError) as exc:
        result.status = "INVALID"
        result.diagnostics.append({"code": "invalid_json", "path": "", "message": str(exc)})
        return result
    source, target = (os, ns) if direction == "request" else (ns, os)
    source_schema, target_schema = (old, new) if direction == "request" else (new, old)
    trace = []
    if prove and prove_subset(source, target, trace):
        result.status, result.proof = "COMPATIBLE", trace
        result.metrics["proof_steps"] = len(trace)
        return result
    result.metrics["proof_steps"] = len(trace)
    if search:
        engine = Search(limits)
        for candidate in engine.candidates(source, target):
            try:
                wire = dumps(candidate, max_bytes=limits.max_document_bytes, max_depth=limits.max_depth * 2)
                transported = loads(wire, max_bytes=limits.max_document_bytes)
                sv = independent_validate(source_schema, transported)
                tv = independent_validate(target_schema, transported)
            except (ValueError, RecursionError) as exc:
                if len(result.diagnostics) < 8:
                    result.diagnostics.append({"code": "validation_limit", "path": "", "message": str(exc)})
                continue
            if sv["valid"] and not tv["valid"]:
                result.status, result.witness, result.wire = "BREAKING", transported, wire
                result.validation = {"source": sv, "target": tv, "validator": "jsonschema.Draft202012Validator; exact Decimal integer semantics and equivalent integral representation", "after_wire_roundtrip": True}
                break
        result.metrics.update({"generated_candidates": min(engine.generated, limits.max_candidates), "search_truncated": engine.truncated})
    if result.status == "UNKNOWN":
        result.diagnostics.append({"code": "inclusion_unproved", "path": "", "message":
                                   "sufficient inclusion rules did not prove compatibility; bounded search found no certified witness"})
    return result
