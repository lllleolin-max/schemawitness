import unittest
from decimal import Decimal
from schemawitness import compare, independent_validate, Limits, dumps, loads, review


class DirectionalTests(unittest.TestCase):
    def witness(self, old, new, direction="request"):
        r = compare(old, new, direction=direction)
        self.assertEqual(r.status, "BREAKING", r.to_dict())
        transported = loads(r.wire)
        source, target = (old, new) if direction == "request" else (new, old)
        self.assertTrue(independent_validate(source, transported)["valid"])
        self.assertFalse(independent_validate(target, transported)["valid"])
        self.assertTrue(r.validation["after_wire_roundtrip"])
        return r

    def test_required_request_response(self):
        optional = {"type": "object", "properties": {"id": {"type": "integer"}}}
        required = {**optional, "required": ["id"]}
        self.assertEqual(self.witness(optional, required).witness, {})
        self.assertEqual(self.witness(required, optional, "response").witness, {})
        self.assertEqual(compare(required, optional).status, "COMPATIBLE")
        self.assertEqual(compare(optional, required, direction="response").status, "COMPATIBLE")

    def test_nested_and_extra_properties(self):
        base = {"type": "object", "required": ["payload"], "properties": {"payload": {"type": "object", "properties": {"count": {"type": "integer"}}}}}
        new = loads(dumps(base))
        new["properties"]["payload"]["properties"]["count"]["minimum"] = 3
        self.witness(base, new)
        self.witness({"type": "object"}, {"type": "object", "additionalProperties": False})
        self.assertEqual(compare({"type": "object", "properties": {"x": False}, "additionalProperties": False},
                                 {"type": "object", "additionalProperties": False}).status, "COMPATIBLE")

    def test_arrays(self):
        self.witness({"type": "array", "items": {"type": "integer"}},
                     {"type": "array", "items": {"type": "integer", "minimum": 0}})
        self.witness({"type": "array"}, {"type": "array", "minItems": 1})
        self.assertEqual(compare({"type": "array", "items": False}, {"type": "array", "maxItems": 0}).status, "COMPATIBLE")
        self.assertEqual(compare({"type": "array", "minItems": 1, "items": False}, False).status, "COMPATIBLE")

    def test_numeric_enum_and_types(self):
        self.witness({"type": "number", "minimum": 0}, {"type": "number", "exclusiveMinimum": 0})
        self.witness({"enum": [True, 1]}, {"enum": [1]})
        self.assertEqual(compare({"const": Decimal("1.0")}, {"type": "integer"}).status, "COMPATIBLE")
        self.assertEqual(compare({"type": "integer", "exclusiveMinimum": Decimal("1.1")},
                                 {"type": "integer", "minimum": 2}).status, "COMPATIBLE")
        self.assertEqual(compare({"type": "number", "minimum": 1, "exclusiveMaximum": 1}, False).status, "COMPATIBLE")
        self.witness({"const": Decimal("9007199254740993.000000000000000001")},
                     {"maximum": Decimal("9007199254740993")})
        self.assertEqual(compare({"type": ["null", "string"]}, {"type": "string"}).status, "BREAKING")

    def test_ref_siblings_allof(self):
        old = {"$defs": {"x": {"type": "integer"}}, "$ref": "#/$defs/x", "minimum": 0}
        new = {"$defs": {"x": {"type": "integer"}}, "$ref": "#/$defs/x", "minimum": 2}
        self.witness(old, new)
        self.assertEqual(compare({"allOf": [{"type": "integer"}, {"minimum": 5}]},
                                 {"type": "number", "minimum": 2}).status, "COMPATIBLE")
        self.assertEqual(compare({"$defs": {"x": {"type": "integer"}}, "$ref": "#/$defs/x", "type": "string"}, False).status, "COMPATIBLE")

    def test_unknown_invalid_limits(self):
        for keyword, value in (("anyOf", [{"type": "integer"}, {"type": "string"}]), ("pattern", "^x$")):
            r = compare({keyword: value}, True)
            self.assertEqual(r.status, "UNKNOWN")
            self.assertEqual(r.diagnostics[0]["code"], "unsupported_keyword")
        self.assertEqual(compare({"$ref": "https://example.com/schema"}, True).status, "UNKNOWN")
        self.assertEqual(compare({"$ref": "#"}, True).status, "UNKNOWN")
        self.assertEqual(compare({"$schema": "http://json-schema.org/draft-07/schema#"}, True).status, "UNKNOWN")
        self.assertEqual(compare({"type": "potato"}, True).status, "INVALID")
        self.assertEqual(compare({"enum": [1, Decimal("1.0")]}, True).status, "INVALID")
        r = compare({"type": "string", "minLength": 500}, {"const": "x"}, limits=Limits(max_instance_units=10))
        self.assertEqual(r.status, "UNKNOWN")
        self.assertTrue(r.metrics["search_truncated"])
        self.assertEqual(compare({"minimum": Decimal("1E1025")}, True).status, "UNKNOWN")

    def test_batch_and_ablation(self):
        manifest = {"operations": [{"id": "POST /orders", "request": {"old": {"type": "integer"}, "new": {"type": "number"}},
                                    "response": {"old": {"type": "object", "required": ["id"]}, "new": {"type": "object"}}}]}
        r = review(manifest)
        self.assertEqual(r["decision"], "BLOCK")
        self.assertEqual(r["counts"]["BREAKING"], 1)
        self.assertEqual(compare({"type": "integer"}, {"type": "number"}, prove=False, search=False).status, "UNKNOWN")
        self.assertEqual(compare({"minimum": 0}, {"minimum": 2}, search=False).status, "UNKNOWN")

    def test_wire(self):
        d = Decimal("123456789012345678901234567890.000000000000000001")
        self.assertEqual(loads(dumps(d)), d)
        for text in ('{"x":1,"x":2}', 'NaN', 'Infinity'):
            with self.assertRaises(ValueError):
                loads(text)


if __name__ == "__main__":
    unittest.main()
