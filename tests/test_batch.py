import copy
from decimal import Decimal
import importlib
import random
import unittest
from unittest.mock import patch
from jsonschema import Draft202012Validator
from schemawitness import BatchLimits, Limits, compare, dumps, loads, review

review_module = importlib.import_module("schemawitness.review")
engine = importlib.import_module("schemawitness.engine")
validation = importlib.import_module("schemawitness.validation")


def manifest(pairs):
    return {"operations": [{"id": str(i), "request": {"old": old, "new": new},
                            "response": {"old": old, "new": new}}
                           for i, (old, new) in enumerate(pairs)]}


class BatchReviewTests(unittest.TestCase):
    def test_complete_validation_before_any_comparison(self):
        m = manifest([(True, True)] * 2)
        m["operations"][-1]["id"] = "0"
        for batch in (None, BatchLimits()):
            with patch.object(review_module, "compare", side_effect=AssertionError("core work before complete validation")):
                self.assertEqual(review(m, batch_limits=batch)["status"], "INVALID")
        m["operations"][-1]["id"] = "1"
        m["operations"][-1]["response"]["extra"] = 1
        with patch.object(review_module, "compare", side_effect=AssertionError("core work")):
            self.assertEqual(review(m, batch_limits=BatchLimits())["status"], "INVALID")

    def test_repeated_pairs_keep_direction_and_detached_results(self):
        old = {"type": "object"}
        new = {"type": "object", "required": ["x"]}
        m = manifest([(old, new)] * 100)
        before = copy.deepcopy(m)
        with patch.object(review_module, "compare", wraps=compare) as core:
            result = review(m, batch_limits=BatchLimits())
        self.assertEqual(core.call_count, 2)
        self.assertEqual(result["batch"]["cache_hits"], 198)
        self.assertEqual(result["operations"][0]["request"]["status"], "BREAKING")
        self.assertEqual(result["operations"][0]["response"]["status"], "COMPATIBLE")
        for i, op in enumerate(result["operations"]):
            for direction in ("request", "response"):
                self.assertEqual(op[direction]["batch"]["operation_id"], str(i))
                self.assertEqual(op[direction]["batch"]["direction"], direction)
        result["operations"][0]["request"]["validation"]["source"]["valid"] = None
        result["operations"][0]["response"]["proof"].clear()
        self.assertTrue(result["operations"][1]["request"]["validation"]["source"]["valid"])
        self.assertTrue(result["operations"][1]["response"]["proof"])
        self.assertEqual(m, before)
        old["required"] = ["x"]
        changed = review(m, batch_limits=BatchLimits())
        self.assertEqual(changed["operations"][0]["request"]["status"], "COMPATIBLE")
        self.assertEqual(changed["batch"]["core_compare_calls"], 2)

    def test_identity_preserves_original_numeric_types_and_spelling(self):
        values = [True, 1, Decimal("1"), Decimal("1.0"), 1.0, False, 0, Decimal("-0"), -0.0]
        m = manifest([({"const": value}, True) for value in values])
        r = review(m, batch_limits=BatchLimits())
        self.assertEqual(r["batch"]["core_compare_calls"], 2 * len(values))
        ids = [op["request"]["batch"]["old_identity"] for op in r["operations"]]
        self.assertEqual(len(set(ids)), len(values))
        # Python True == 1 must not upgrade an invalid schema through a cache hit.
        r = review(manifest([({"minLength": 1}, True), ({"minLength": True}, True)]), batch_limits=BatchLimits())
        self.assertEqual(r["operations"][1]["request"]["status"], "INVALID")
        precise = Decimal("9007199254740993.000000000000000001")
        r = review(manifest([({"const": precise}, {"maximum": Decimal("9007199254740993")})] * 2), batch_limits=BatchLimits())
        self.assertEqual(r["operations"][1]["request"]["wire"], str(precise))
        self.assertEqual(loads(r["operations"][1]["request"]["wire"]), precise)

    def test_document_and_encoded_pointer_identity(self):
        old = {"$defs": {"a/b~c": {"const": 1}}, "$ref": "#%2F$defs%2Fa~1b~0c"}
        changed = copy.deepcopy(old)
        changed["$defs"]["a/b~c"]["const"] = 2
        literal = {"$defs": {"%2F": {"const": 3}}, "$ref": "#/$defs/%252F"}
        m = manifest([(old, {"const": 1}), (changed, {"const": 1}), (literal, {"const": 3})])
        r = review(m, batch_limits=BatchLimits())
        self.assertEqual(r["operations"][0]["request"]["status"], "COMPATIBLE")
        self.assertEqual(r["operations"][1]["request"]["status"], "BREAKING")
        self.assertEqual(r["operations"][2]["request"]["status"], "COMPATIBLE")
        self.assertEqual(r["batch"]["core_compare_calls"], 6)
        self.assertGreater(r["batch"]["work_by_kind"]["backend_reference_lookup"], 0)

    def test_unknown_and_backend_failure_cannot_be_cached_as_allow(self):
        m = manifest([({"$ref": "https://example.invalid/no-network"}, True)] * 2)
        with patch.object(validation, "_no_network", side_effect=AssertionError("network")):
            r = review(m, batch_limits=BatchLimits())
        self.assertEqual(r["counts"]["UNKNOWN"], 4)
        self.assertEqual(r["decision"], "BLOCK")
        with patch.object(validation, "_resolver", side_effect=TypeError("injected backend failure")):
            r = review(manifest([(True, True)] * 2), batch_limits=BatchLimits())
        self.assertEqual(r["counts"]["UNKNOWN"], 4)
        self.assertEqual(r["batch"]["cache_hits"], 2)
        for op in r["operations"]:
            for d in ("request", "response"):
                self.assertEqual(op[d]["proof"], [])
                self.assertIsNone(op[d]["wire"])

    def test_actual_work_and_exact_boundary(self):
        m = manifest([({"type": "string", "minLength": 500}, {"const": "x"})])
        limits = Limits(max_instance_units=16, max_candidates=20)
        normal = review(m, limits=limits, batch_limits=BatchLimits())
        work = normal["batch"]["work_used"]
        self.assertEqual(work, sum(normal["batch"]["work_by_kind"].values()))
        for delta in (-1, 0, 1):
            r = review(m, limits=limits, batch_limits=BatchLimits(max_work=work + delta))
            self.assertLessEqual(r["batch"]["work_used"], work + delta)
            if delta < 0:
                self.assertEqual(r["operations"][-1]["response"]["status"], "UNKNOWN")
                self.assertEqual(r["operations"][-1]["response"]["diagnostics"][0]["code"], "batch_work_limit")
                self.assertIsNone(r["operations"][-1]["response"]["wire"])
            else:
                for d in ("request", "response"):
                    value = r["operations"][0][d].copy()
                    value.pop("batch")
                    self.assertEqual(value, compare(m["operations"][0][d]["old"], m["operations"][0][d]["new"], direction=d, limits=limits).to_dict())

    def test_distinct_operations_share_work_and_remaining_are_unknown(self):
        m = manifest([({"type": "string", "minLength": 500 + i}, {"const": "x"}) for i in range(100)])
        r = review(m, limits=Limits(max_instance_units=16), batch_limits=BatchLimits(max_work=80))
        self.assertEqual(len(r["operations"]), 100)
        self.assertEqual(r["batch"]["work_used"], 80)
        self.assertLess(r["batch"]["core_compare_calls"], 200)
        self.assertEqual(r["decision"], "BLOCK")
        halted = False
        for op in r["operations"]:
            for d in ("request", "response"):
                value = op[d]
                if not value["batch"]["evaluated"]:
                    halted = True
                if halted:
                    self.assertEqual(value["status"], "UNKNOWN")
                    self.assertEqual(value["proof"], [])
                    self.assertIsNone(value["wire"])
        self.assertTrue(halted)
        r = review(manifest([(True, True)]), batch_limits=BatchLimits(max_work=0))
        self.assertEqual(r["batch"]["core_compare_calls"], 0)
        self.assertEqual(r["counts"]["UNKNOWN"], 2)

    def test_storage_input_boundaries_and_invalid_json(self):
        m = manifest([(True, True)] * 2)
        normal = review(m, batch_limits=BatchLimits())
        for field, value in (("max_cache_bytes", normal["batch"]["cache_bytes"]),
                             ("max_input_bytes", normal["batch"]["input_bytes"]),
                             ("max_input_nodes", normal["batch"]["input_nodes"]),
                             ("max_result_bytes", normal["batch"]["result_bytes"])):
            for delta in (-1, 0, 1):
                r = review(m, batch_limits=BatchLimits(**{field: value + delta}))
                self.assertEqual(r["status"], "UNKNOWN" if delta < 0 else "COMPATIBLE", (field, delta, r))
                if field.startswith("max_input") and delta < 0:
                    self.assertEqual(r["batch"]["core_compare_calls"], 0)
        r = review(m, batch_limits=BatchLimits(max_cache_entries=1))
        self.assertEqual(r["batch"]["cache_entries"], 1)
        self.assertEqual(r["operations"][1]["request"]["status"], "UNKNOWN")
        self.assertEqual(review(m, batch_limits=BatchLimits(max_cache_entries=2))["status"], "COMPATIBLE")
        for bad in ({1: True}, {"const": float("nan")}, {"const": Decimal("Infinity")}, {"const": ()}):
            with patch.object(review_module, "compare", side_effect=AssertionError("core work for non-JSON")):
                self.assertEqual(review(manifest([(bad, True)]), batch_limits=BatchLimits())["status"], "INVALID")
        cyclic = {}
        cyclic["const"] = cyclic
        self.assertEqual(review(manifest([(cyclic, True)]), batch_limits=BatchLimits())["status"], "INVALID")
        r = review(manifest([({"const": 10 ** 5000}, True)]), batch_limits=BatchLimits())
        self.assertEqual(r["status"], "UNKNOWN")
        self.assertEqual(r["batch"]["core_compare_calls"], 0)

    def test_multibyte_input_and_cached_witness_budget_boundaries(self):
        old = {"const": {"\u6c49\u03bb\U0001f642": Decimal("0.100000000000000000000000000001")}}
        new = {"const": {"\u6c49\u03bb\U0001f642": Decimal("0.1")}}
        m = manifest([(old, new)] * 2)
        normal = review(m, batch_limits=BatchLimits())
        self.assertEqual(normal["counts"]["BREAKING"], 4)
        self.assertEqual(normal["batch"]["input_bytes"], len(dumps(m)))
        self.assertEqual(normal["batch"]["cache_hits"], 2)
        self.assertTrue(normal["operations"][1]["request"]["wire"].isascii())
        for field, size in (("max_input_bytes", normal["batch"]["input_bytes"]),
                            ("max_cache_bytes", normal["batch"]["cache_bytes"]),
                            ("max_result_bytes", normal["batch"]["result_bytes"])):
            for delta in (-1, 0, 1):
                r = review(m, batch_limits=BatchLimits(**{field: size + delta}))
                if delta < 0:
                    self.assertIsNotNone(r["batch"]["halted"])
                    self.assertEqual(r["operations"][-1]["response"]["status"], "UNKNOWN")
                    self.assertIsNone(r["operations"][-1]["response"]["wire"])
                    self.assertEqual(r["operations"][-1]["response"]["validation"], {})
                else:
                    self.assertIsNone(r["batch"]["halted"])
                    self.assertEqual(r["counts"]["BREAKING"], 4)

    def test_budget_exhausts_before_each_backend_boundary(self):
        m = manifest([(True, True)])
        normal = review(m, batch_limits=BatchLimits())
        for maximum in range(normal["batch"]["work_used"] + 1):
            with patch.object(engine.Draft202012Validator, "check_schema", wraps=engine.Draft202012Validator.check_schema) as meta, \
                 patch.object(validation, "_resolver", wraps=validation._resolver) as roots:
                r = review(m, batch_limits=BatchLimits(max_work=maximum))
            by_kind = r["batch"]["work_by_kind"]
            self.assertEqual(meta.call_count, by_kind.get("backend_meta_schema", 0))
            self.assertEqual(roots.call_count, by_kind.get("backend_reference_root", 0))
            self.assertLessEqual(r["batch"]["work_used"], maximum)
            if maximum < normal["batch"]["work_used"]:
                self.assertEqual(r["decision"], "BLOCK")

    def test_120_single_batch_pairs_with_independent_membership(self):
        rng = random.Random(20261005)
        pairs = []
        for i in range(120):
            a, b = rng.randrange(-5, 6), rng.randrange(-5, 6)
            kind = i % 6
            if kind == 0:
                pair = ({"type": "integer", "minimum": a}, {"type": "number", "minimum": b})
            elif kind == 1:
                pair = ({"type": "string", "minLength": abs(a)}, {"type": "string", "maxLength": abs(b)})
            elif kind == 2:
                pair = ({"type": "array", "items": {"type": "integer", "minimum": a}}, {"type": "array", "items": {"minimum": b}})
            elif kind == 3:
                pair = ({"type": "object", "properties": {"x": {"type": "integer"}}}, {"type": "object", "required": ["x"], "properties": {"x": {"minimum": b}}})
            elif kind == 4:
                pair = ({"allOf": [{"type": "integer"}, {"minimum": a}]}, {"type": "integer", "maximum": b})
            else:
                pair = ({"$defs": {"x": {"type": "integer", "minimum": a}}, "$ref": "#/$defs/x"}, {"type": "number", "minimum": b})
            pairs.append(pair)
        m = manifest(pairs)
        before = copy.deepcopy(m)
        r = review(m, batch_limits=BatchLimits(max_work=1_000_000))
        witnesses = 0
        for (old, new), op in zip(pairs, r["operations"]):
            for direction in ("request", "response"):
                actual = op[direction].copy()
                actual.pop("batch")
                self.assertEqual(actual, compare(old, new, direction=direction).to_dict())
                if actual["status"] == "BREAKING":
                    witnesses += 1
                    # An independent standard validator for this integer-only
                    # fixture family, separate from application validation.
                    import json
                    value = json.loads(actual["wire"])
                    source, target = (old, new) if direction == "request" else (new, old)
                    self.assertTrue(Draft202012Validator(source).is_valid(value))
                    self.assertFalse(Draft202012Validator(target).is_valid(value))
        self.assertGreater(witnesses, 100)
        self.assertEqual(m, before)


if __name__ == "__main__":
    unittest.main()
