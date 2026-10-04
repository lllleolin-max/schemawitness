"""Opt-in application work and storage bounds for one release review.

Units count explicit application operations, not CPU instructions, elapsed time,
or recursive work inside jsonschema. Input traversal has separate bounds.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class BatchLimits:
    max_work: int = 100_000
    max_input_nodes: int = 100_000
    max_input_bytes: int = 8_000_000
    max_cache_entries: int = 2000
    max_cache_bytes: int = 8_000_000
    max_result_bytes: int = 16_000_000

    def __post_init__(self):
        for key, value in vars(self).items():
            minimum = 0 if key == "max_work" else 1
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(key + " must be an integer >= " + str(minimum))


class BatchWorkLimit(RuntimeError):
    """Raised before an operation would exceed the shared work budget."""


class BatchInputLimit(RuntimeError):
    pass


class WorkBudget:
    def __init__(self, limits):
        self.limits = limits
        self.used = 0
        self.by_kind = {}
        self.halted = None

    def charge(self, kind):
        if self.halted or self.used >= self.limits.max_work:
            self.halted = self.halted or "batch_work_limit"
            raise BatchWorkLimit(self.halted)
        self.used += 1
        self.by_kind[kind] = self.by_kind.get(kind, 0) + 1

    def halt(self, reason):
        self.halted = reason
        raise BatchWorkLimit(reason)
