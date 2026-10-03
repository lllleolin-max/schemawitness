import unittest
from schemawitness import compare, loads
from jsonschema import Draft202012Validator


class ReviewRegressions(unittest.TestCase):
    def test_dialect_like_keys_inside_literals(self):
        old = {"type": "object"}
        new = {"const": {"$schema": "literal data, not a dialect"}}
        result = compare(old, new)
        self.assertEqual(result.status, "BREAKING")
        value = loads(result.wire)
        self.assertTrue(Draft202012Validator(old).is_valid(value))
        self.assertFalse(Draft202012Validator(new).is_valid(value), result.to_dict())
        literal = {"const": {"$schema": "literal", "nested": {"$schema": "also data"}}}
        removed = {"const": {}}
        r = compare(literal, removed)
        self.assertEqual(r.status, "BREAKING")
        self.assertTrue(Draft202012Validator(literal).is_valid(loads(r.wire)))
        self.assertFalse(Draft202012Validator(removed).is_valid(loads(r.wire)))


if __name__ == "__main__":
    unittest.main()
