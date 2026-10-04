"""Bounded boundary-guided search. Exhaustion is not an inclusion proof."""
from decimal import Decimal
from fractions import Fraction
from .model import Shape, accepts, atom, empty, integer_bounds
from .wire import value_key, bounded_wire_size


def decimal_fraction(q):
    """Convert a finite decimal rational without a Decimal context roundoff."""
    denominator = q.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    if denominator != 1:
        raise ValueError("non-decimal candidate")
    places = max(twos, fives)
    scaled = q.numerator * 2 ** (places - twos) * 5 ** (places - fives)
    digits = str(abs(scaled))
    return Decimal((int(scaled < 0), tuple(int(c) for c in digits), -places))


class Search:
    def __init__(self, limits, _budget=None):
        self.limits, self.generated, self.truncated = limits, 0, False
        self.candidate_bytes, self.limit_reasons = 0, set()
        self._budget = _budget

    def truncate(self, reason):
        self.truncated = True
        self.limit_reasons.add(reason)

    def candidates(self, source, target, depth=0):
        seen = set()
        for value in self._values(source, target, depth):
            if self._budget is not None:
                self._budget.charge("candidate")
            size = bounded_wire_size(value, self.limits.max_document_bytes)
            if size > self.limits.max_document_bytes:
                self.truncate("candidate_wire_bytes")
                continue
            if self.candidate_bytes + size > self.limits.max_total_candidate_bytes:
                self.truncate("cumulative_candidate_bytes")
                return
            self.candidate_bytes += size
            key = value_key(value)
            if key in seen or not accepts(source, value):
                continue
            seen.add(key)
            self.generated += 1
            if self.generated > self.limits.max_candidates:
                self.truncate("candidate_count")
                return
            yield value

    def child_values(self, source, target, depth):
        if depth > self.limits.max_depth or empty(source):
            return []
        values = []
        for value in self.candidates(source, target, depth):
            values.append(value)
            if len(values) >= 32:
                self.truncate("child_variants")
                break
        return values

    def _values(self, s, t, depth):
        if self._budget is not None:
            self._budget.charge("search")
        if depth > self.limits.max_depth:
            self.truncate("search_depth")
            return
        if s.enum is not None:
            yield from s.enum
            return
        if s == Shape() and t == Shape():
            yield from (None, False, True, -1, 0, 1, Decimal("0.5"), "", "x", [], {})
            return
        if t.enum is not None:
            yield from t.enum
        for kind in ("null", "boolean", "integer", "real", "string", "array", "object"):
            if kind not in s.types:
                continue
            if kind == "null":
                yield None
            if kind == "boolean":
                yield False
                yield True
            if kind in {"integer", "real"}:
                numbers = {Fraction(0), Fraction(1), Fraction(-1), Fraction(1, 2), Fraction(-1, 2)}
                for bound in (s.low, s.high, t.low, t.high):
                    if bound:
                        q = bound[0]
                        epsilon = Fraction(1, q.denominator * 10)
                        numbers.update((q, q - epsilon, q + epsilon, q - 1, q + 1))
                if s.low and s.high:
                    numbers.add((s.low[0] + s.high[0]) / 2)
                if kind == "integer":
                    lo, hi = integer_bounds(s)
                    numbers.update(Fraction(x) for x in (lo, hi) if x is not None)
                    numbers.update(Fraction(q.numerator // q.denominator) for q in list(numbers))
                    numbers.update(Fraction(-(-q.numerator // q.denominator)) for q in list(numbers))
                for q in sorted(numbers):
                    value = q.numerator if q.denominator == 1 else decimal_fraction(q)
                    if atom(value) == kind:
                        yield value
            if kind == "string":
                sizes = {0, 1, s.min_length, t.min_length, max(0, t.min_length - 1)}
                for n in (s.max_length, t.max_length):
                    if n is not None:
                        sizes.update((n, n + 1))
                for n in sorted(sizes):
                    if n > self.limits.max_instance_units:
                        self.truncate("string_length")
                    else:
                        yield "x" * n
            if kind == "array":
                values = self.child_values(s.item(), t.item(), depth + 1)
                sizes = {0, 1, s.min_items, t.min_items, max(0, t.min_items - 1)}
                for n in (s.max_items, t.max_items):
                    if n is not None:
                        sizes.update((n, n + 1))
                for n in sorted(sizes):
                    if n > self.limits.max_instance_units:
                        self.truncate("array_length")
                    elif n == 0:
                        yield []
                    elif values:
                        yield [values[0]] * n
                        for value in values[1:]:
                            yield [value] + [values[0]] * (n - 1)
            if kind == "object":
                if len(s.required) > self.limits.max_instance_units:
                    self.truncate("object_properties")
                    continue
                base, options = {}, {}
                for key in sorted(s.required):
                    vals = self.child_values(s.prop(key), t.prop(key), depth + 1)
                    if not vals:
                        break
                    base[key], options[key] = vals[0], vals
                else:
                    yield base
                    extra = "__schemawitness_extra__"
                    while extra in s.props or extra in t.props or extra in s.required or extra in t.required:
                        extra += "_"
                    for key in [*sorted(s.props.keys() | t.props.keys()), extra]:
                        vals = options.get(key)
                        if vals is None:
                            vals = self.child_values(s.prop(key), t.prop(key), depth + 1)
                        for value in vals:
                            if len(base) + (key not in base) > self.limits.max_instance_units:
                                self.truncate("object_properties")
                                break
                            yield {**base, key: value}
