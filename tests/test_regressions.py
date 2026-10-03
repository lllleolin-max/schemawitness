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

    def test_json_pointer_array_indices_are_not_python_indices(self):
        for pointer in ("#/allOf/-1", "#/allOf/00", "#/allOf/+0"):
            schema = {"allOf": [{"type": "integer"}], "$ref": pointer}
            result = compare(schema, {"type": "number"})
            self.assertEqual(result.status, "INVALID", (pointer, result.to_dict()))
            self.assertEqual(result.diagnostics[0]["code"], "invalid_reference")
        for pointer in ("#/$defs/a~2", "#/$defs/a%ZZ"):
            schema = {"$defs": {"a~2": True, "a%ZZ": True}, "$ref": pointer}
            self.assertEqual(compare(schema, True).status, "INVALID")
        schema = {"$defs": {"a/b~c": {"type": "integer"}}, "$ref": "#%2F$defs%2Fa~1b~0c"}
        self.assertEqual(compare(schema, {"type": "number"}).status, "COMPATIBLE")
        loop = {"$defs": {"a": {"$ref": "#%2F$defs%2Fa"}}, "$ref": "#/$defs/a"}
        self.assertEqual(compare(loop, True).diagnostics[0]["code"], "recursive_reference")


if __name__ == "__main__":
    unittest.main()
