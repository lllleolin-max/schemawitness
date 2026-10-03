"""Resource probes bound preprocessing, not only post-search wire transport."""
import unittest
from unittest.mock import patch
from schemawitness import compare, Limits, dumps
from schemawitness.wire import value_key, bounded_wire_size


class SearchResourceTests(unittest.TestCase):
    def test_oversized_shared_values_never_reach_unbounded_dedup_keys(self):
        schema = {"type": "integer"}
        for _ in range(5):
            schema = {"type": "array", "minItems": 4, "maxItems": 4, "items": schema}

        def guarded_key(value):
            dumps(value, max_bytes=1000)
            return value_key(value)

        with patch("schemawitness.search.value_key", side_effect=guarded_key):
            result = compare(schema, False, limits=Limits(max_document_bytes=1000, max_instance_units=4))
        self.assertEqual(result.status, "UNKNOWN")
        self.assertTrue(result.metrics["search_truncated"])
        self.assertIn("candidate_wire_bytes", result.metrics["search_limit_reasons"])
        shared = [0]
        for _ in range(12):
            shared = [shared] * 16
        self.assertEqual(bounded_wire_size(shared, 64), 65)

    def test_cumulative_budget_and_size_oracle(self):
        for v in [None, 1, "汉字", [1, {"x": "\\n"}], {"a": [True, False]}, [[[]]]]:
            self.assertEqual(bounded_wire_size(v, 1000), len(dumps(v)))
        result = compare({"type": "string", "minLength": 20}, {"const": "x"},
                         limits=Limits(max_total_candidate_bytes=10))
        self.assertEqual(result.status, "UNKNOWN")
        self.assertIn("cumulative_candidate_bytes", result.metrics["search_limit_reasons"])
        self.assertLessEqual(result.metrics["candidate_bytes"], 10)
