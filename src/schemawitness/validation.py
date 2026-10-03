"""Independent jsonschema evaluation with a URI-fragment transport adapter.

The adapter adjusts only the URI passed to dependency lookup, not the schema
tree or instance data. All assertion evaluation and pointer target lookup remain
in jsonschema/referencing. In particular, literal $ref/$schema keys stay intact.
"""
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from types import SimpleNamespace
from urllib.parse import quote, unquote
import re
from jsonschema import Draft202012Validator, validators
from referencing import Registry
from referencing.exceptions import NoSuchResource, Unresolvable
from referencing.jsonschema import DRAFT202012


def _integer(checker, value):
    return not isinstance(value, bool) and isinstance(value, (int, Decimal)) and Fraction(value).denominator == 1


ExactValidator = validators.extend(Draft202012Validator, type_checker=
    Draft202012Validator.TYPE_CHECKER.redefine("integer", _integer))


def _no_network(uri):
    raise NoSuchResource(ref=uri)


@dataclass(frozen=True)
class LocalFragmentResolver:
    """Preserve RFC 6901 fragment interpretation through validator evolution.

    referencing 0.37 classifies a raw fragment before percent decoding; an
    encoded leading slash is consequently mistaken for an anchor. Re-encode
    the decoded pointer with literal separators before delegating. Escaping
    percent signs again preserves exactly ONE decode, including literal %2F.
    The resolver is passed through jsonschema's _resolver integration field;
    this private constructor seam is covered by installed-dependency tests.
    """
    delegate: object

    def lookup(self, ref):
        if isinstance(ref, str) and ref.startswith("#"):
            if re.search(r"%(?![0-9A-Fa-f]{2})", ref):
                raise Unresolvable(ref=ref)
            pointer = unquote(ref[1:], errors="strict")
            if not pointer or pointer.startswith("/"):
                if re.search(r"~(?![01])", pointer):
                    raise Unresolvable(ref=ref)
                ref = "#" + quote(pointer, safe="/~", encoding="utf-8", errors="strict")
        resolved = self.delegate.lookup(ref)
        return SimpleNamespace(contents=resolved.contents,
                               resolver=LocalFragmentResolver(resolved.resolver))

    def in_subresource(self, subresource):
        return LocalFragmentResolver(self.delegate.in_subresource(subresource))

    def dynamic_scope(self):
        return self.delegate.dynamic_scope()


def _validator_instance(value):
    # Equivalent mathematical JSON values survive jsonschema's class switching.
    # No source/target schema or any literal schema data is modified.
    if isinstance(value, Decimal) and Fraction(value).denominator == 1:
        return int(value)
    if isinstance(value, dict):
        return {k: _validator_instance(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_validator_instance(v) for v in value]
    return value


def _resolver(schema):
    registry = Registry(retrieve=_no_network)
    return registry, LocalFragmentResolver(registry.resolver_with_root(DRAFT202012.create_resource(schema)))


def _failure(exc):
    return {"code": "independent_validator_failure",
            "message": "independent dependency could not evaluate the schema: " + type(exc).__name__}


def check_reference_lookup(schema, references):
    """Exercise independent target lookup before any inclusion certificate.

    Compiler metadata supplies only encountered URI spellings; target lookup
    uses the original document and the independent dependency, not its resolved
    targets or normalized constraints. This also detects backend failures on
    proof-only paths instead of discovering them only during witness search.
    """
    try:
        _, resolver = _resolver(schema)
        for ref in sorted(references):
            resolver.lookup(ref)
    except (Unresolvable, RecursionError, UnicodeError, TypeError, AttributeError) as exc:
        return _failure(exc)
    return None


def independent_validate(schema, value):
    """Evaluate a transported value. valid=None means dependency failure.

    Consumers must require valid is True/False for membership evidence; None
    is an unresolved evaluation, never evidence that a target rejects a value.
    """
    try:
        registry, resolver = _resolver(schema)
        validator = ExactValidator(schema, registry=registry, _resolver=resolver)
        errors = sorted(validator.iter_errors(_validator_instance(value)),
                        key=lambda e: (str(list(e.path)), str(list(e.schema_path))))
    except (Unresolvable, RecursionError, UnicodeError, TypeError, AttributeError) as exc:
        return {"valid": None, "errors": [], "diagnostics": [_failure(exc)]}
    return {"valid": not errors, "errors": [{"instance_path": list(e.path),
            "schema_path": list(e.schema_path), "keyword": e.validator} for e in errors[:8]]}
