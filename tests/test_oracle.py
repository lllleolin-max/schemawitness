"""Independent finite-domain oracle checks the sufficient proof, not the search.

Instances are enumerated independently and evaluated by jsonschema. An oracle
cannot prove the infinite calculus; it falsifies unsound positives in this grid.
"""
import itertools
import unittest
from schemawitness import compare, independent_validate


class FiniteOracle(unittest.TestCase):
    def test_all_pairs(self):
        primitives = [None, False, True, -1, 0, 1, 2, "", "x"]
        instances = primitives + [[], *[[v] for v in primitives], *[[a, b] for a, b in itertools.product([-1, 0, 1], repeat=2)]]
        instances += [{}, *[{k: v} for k, v in itertools.product(["x", "y", "z"], primitives)],
                      *[{"x": a, "y": b} for a, b in itertools.product([-1, 0, False], repeat=2)]]
        schemas = [True, False, {}, {"type": "integer"}, {"type": "number", "minimum": 0},
                   {"type": "integer", "exclusiveMinimum": 0, "maximum": 1},
                   {"type": "number", "minimum": 2, "maximum": 1}, {"enum": [True, 0, ""]},
                   {"type": "string", "minLength": 1}, {"type": "array", "items": False},
                   {"type": "array", "items": {"type": "integer"}, "maxItems": 1},
                   {"type": "array", "items": {"minimum": 0}, "minItems": 1},
                   {"type": "object", "properties": {"x": {"type": "integer"}}, "additionalProperties": False},
                   {"type": "object", "properties": {"x": False}},
                   {"type": "object", "required": ["x"]},
                   {"type": "object", "required": ["x"], "properties": {"x": False}},
                   {"type": "object", "additionalProperties": {"type": "integer"}}]
        valid = [[independent_validate(s, v)["valid"] for v in instances] for s in schemas]
        for i, j in itertools.product(range(len(schemas)), repeat=2):
            r = compare(schemas[i], schemas[j])
            if r.status == "COMPATIBLE":
                self.assertFalse(any(a and not b for a, b in zip(valid[i], valid[j])), (schemas[i], schemas[j], r.to_dict()))
            if r.status == "BREAKING":
                self.assertTrue(independent_validate(schemas[i], r.witness)["valid"])
                self.assertFalse(independent_validate(schemas[j], r.witness)["valid"])


if __name__ == "__main__":
    unittest.main()
