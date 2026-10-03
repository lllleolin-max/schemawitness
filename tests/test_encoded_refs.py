"""Encoded-reference integration probes include actual search and console paths."""
from copy import deepcopy
from decimal import Decimal
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import json
import subprocess
import sys
import sysconfig
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import quote
from jsonschema import Draft202012Validator
from referencing.exceptions import Unresolvable
from schemawitness import compare, independent_validate, dumps, loads
from schemawitness.cli import main

DIALECT = "https://json-schema.org/draft/2020-12/schema"


def schema(ref, minimum=0):
    return {"$defs": {"N": {"type": "integer", "minimum": minimum}}, "$ref": ref}


class EncodedReferenceTests(unittest.TestCase):
    def test_encoded_target_source_and_response_siblings(self):
        for ref in ("#/$defs/N", "#%2F$defs%2FN", "#%2f%24defs%2fN"):
            target = schema(ref)
            r = compare(True, target)
            self.assertEqual(r.status, "BREAKING", r.to_dict())
            self.assertEqual(r.wire, "null")
            self.assertTrue(independent_validate(True, loads(r.wire))["valid"])
            self.assertFalse(Draft202012Validator(schema("#/$defs/N")).is_valid(loads(r.wire)))
            old = {**schema(ref), "minimum": 1}
            new = {"type": "integer", "minimum": 2}
            for a, b, direction in ((old, new, "request"), (new, old, "response")):
                result = compare(a, b, direction=direction)
                self.assertEqual(result.status, "BREAKING", result.to_dict())
                self.assertEqual(loads(result.wire), 1)
                self.assertTrue(result.validation["source"]["valid"])
                self.assertFalse(result.validation["target"]["valid"])
            self.assertEqual(compare(old, {"type": "number", "minimum": 0}).status, "COMPATIBLE")

    def test_percent_tilde_and_unicode_are_decoded_once(self):
        keys = ("%2F", "%", "a/b~c", "数/值~%", "~1", "#?", "")
        for key in keys:
            token = key.replace("~", "~0").replace("/", "~1")
            pointer = "/$defs/" + token
            encoded = "#" + quote(pointer, safe="")
            target = {"$defs": {key: {"type": "integer", "minimum": 2}}, "$ref": encoded}
            canonical = {"$defs": {key: {"type": "integer", "minimum": 2}}, "$ref": "#" + quote(pointer, safe="/~")}
            for value, expected in ((None, False), (True, False), (1, False), (2, True), (Decimal("2.0"), True), (Decimal("2.1"), False)):
                self.assertIs(independent_validate(target, value)["valid"], expected, (key, value))
                self.assertIs(independent_validate(canonical, value)["valid"], expected)
            result = compare(True, target)
            self.assertEqual(result.status, "BREAKING", (key, result.to_dict()))
        # %252F names the literal %2F key; it must not become the slash key.
        target = {"$defs": {"%2F": {"const": 3}, "/": {"const": 4}}, "$ref": "#%2F$defs%2F%252F"}
        self.assertTrue(independent_validate(target, 3)["valid"])
        self.assertFalse(independent_validate(target, 4)["valid"])

    def test_nested_schema_dialect_switch_and_annotation_targets(self):
        target = {"$defs": {"N": {"$schema": DIALECT, "$ref": "#%2F$defs%2FM", "minimum": 2},
                            "M": {"type": "integer"}}, "$ref": "#%2F$defs%2FN"}
        self.assertTrue(independent_validate(target, Decimal("2.0"))["valid"])
        self.assertFalse(independent_validate(target, Decimal("1.0"))["valid"])
        self.assertFalse(independent_validate(target, Decimal("2.000000000000000001"))["valid"])
        self.assertEqual(compare({"const": Decimal("2.0")}, target, prove=False).status, "UNKNOWN")
        annotation = {"default": {"$schema": DIALECT, "$ref": "#%2F$defs%2FN", "minimum": 1},
                      "$defs": {"N": {"type": "integer"}}, "$ref": "#%2Fdefault"}
        self.assertTrue(independent_validate(annotation, Decimal("1.0"))["valid"])
        self.assertEqual(compare({"const": Decimal("1.0")}, annotation, prove=False).status, "UNKNOWN")
        nested = {"type": "object", "required": ["x"], "properties": {"x": target},
                  "$defs": target["$defs"]}
        self.assertTrue(independent_validate(nested, {"x": Decimal("2.0")})["valid"])
        self.assertEqual(compare({"const": {"x": 1}}, nested).status, "BREAKING")

    def test_literal_values_and_referenced_literal_schema_are_untouched(self):
        literal = {"$ref": "#%2F$defs%2FN", "$schema": "literal", "nested": {"$ref": "#%2Fbad"}}
        constant = {"const": literal}
        original = deepcopy(constant)
        result = compare(constant, False)
        self.assertEqual(result.status, "BREAKING")
        self.assertEqual(loads(result.wire), literal)
        self.assertEqual(constant, original)
        self.assertTrue(Draft202012Validator(constant).is_valid(loads(result.wire)))
        dual_role = {"const": {"$ref": "#%2F$defs%2FO", "type": "object"},
                     "$defs": {"O": {"type": "object"}}, "$ref": "#%2Fconst"}
        result = compare(dual_role, False)
        self.assertEqual(result.status, "BREAKING", result.to_dict())
        self.assertEqual(loads(result.wire), dual_role["const"])
        self.assertTrue(independent_validate(dual_role, loads(result.wire))["valid"])
        self.assertFalse(independent_validate({"const": {}}, loads(result.wire))["valid"])

    def test_cycles_invalid_fragments_and_backend_failure_do_not_certify(self):
        cycle = {"$defs": {"N": {"$ref": "#%2F$defs%2FN"}}, "$ref": "#/$defs/N"}
        self.assertEqual(compare(cycle, True).diagnostics[0]["code"], "recursive_reference")
        for ref in ("#%2F$defs%2F%FF", "#%2F$defs%2Fa~2", "#%2F$defs%2Fa%ZZ"):
            self.assertEqual(compare(schema(ref), True).status, "INVALID")
        encoded = schema("#%2F$defs%2FN")
        with patch("schemawitness.validation.LocalFragmentResolver.lookup", side_effect=Unresolvable(ref="#blocked")):
            direct = independent_validate(encoded, 1)
            self.assertIsNone(direct["valid"])
            for old, new in ((True, encoded), (encoded, True), (encoded, encoded)):
                result = compare(old, new)
                self.assertEqual(result.status, "UNKNOWN")
                self.assertIsNone(result.wire)
                self.assertEqual(result.proof, [])
                self.assertEqual(result.diagnostics[0]["code"], "independent_validator_failure")
            with tempfile.TemporaryDirectory() as name:
                old, new = Path(name)/"old.json", Path(name)/"new.json"
                old.write_text("true", encoding="utf-8")
                new.write_text(dumps(encoded), encoding="utf-8")
                output = StringIO()
                with redirect_stdout(output):
                    self.assertEqual(main([str(old), str(new)]), 2)
                self.assertEqual(loads(output.getvalue())["status"], "UNKNOWN")

    def test_actual_console_source_target_and_direction(self):
        executable = Path(sysconfig.get_path("scripts")) / ("schemawitness.exe" if sys.platform == "win32" else "schemawitness")
        with tempfile.TemporaryDirectory() as name:
            old, new = Path(name)/"old.json", Path(name)/"new.json"
            for ref in ("#/$defs/N", "#%2F$defs%2FN"):
                for a, b, direction, wire in ((True, schema(ref), "request", "null"),
                                               (schema(ref), {"type": "integer", "minimum": 2}, "request", "0"),
                                               ({"type": "integer", "minimum": 2}, schema(ref), "response", "0")):
                    old.write_text(dumps(a), encoding="utf-8"); new.write_text(dumps(b), encoding="utf-8")
                    initial = old.read_bytes(), new.read_bytes()
                    proc = subprocess.run([str(executable), str(old), str(new), "--direction", direction],
                                          capture_output=True, text=True, timeout=10)
                    self.assertEqual(proc.returncode, 1, proc.stderr)
                    self.assertNotIn("Traceback", proc.stderr)
                    report = json.loads(proc.stdout)
                    self.assertEqual(report["status"], "BREAKING")
                    self.assertEqual(report["wire"], wire)
                    self.assertEqual((old.read_bytes(), new.read_bytes()), initial)
                    self.assertTrue(report["validation"]["source"]["valid"])
                    self.assertFalse(report["validation"]["target"]["valid"])
