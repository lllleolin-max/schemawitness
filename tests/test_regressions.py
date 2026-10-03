import unittest
from unittest.mock import patch
from schemawitness import compare, loads, dumps, Limits
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

    def test_wire_budget_bounds_successful_serializations(self):
        schema = {"type": "integer"}
        for _ in range(5):
            schema = {"type": "array", "minItems": 4, "maxItems": 4, "items": schema}
        encoded_sizes = []

        def observing_encoder(value, **kwargs):
            text = dumps(value, **kwargs)
            encoded_sizes.append(len(text.encode("utf-8")))
            return text

        with patch("schemawitness.engine.dumps", side_effect=observing_encoder):
            result = compare(schema, False, limits=Limits(max_document_bytes=1000, max_instance_units=4))
        self.assertEqual(result.status, "UNKNOWN")
        self.assertTrue(encoded_sizes)
        self.assertLessEqual(max(encoded_sizes), 1000, "encoder allocated an oversized complete wire before enforcing its limit")
        shared = [0]
        for _ in range(12):
            shared = [shared] * 16
        with self.assertRaises(ValueError):
            dumps(shared, max_bytes=64)
        self.assertEqual(loads(dumps("汉字\n", max_bytes=32)), "汉字\n")
        self.assertEqual(compare({"const": "x" * 1001}, True, limits=Limits(max_document_bytes=1000)).status, "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
