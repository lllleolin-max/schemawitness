import tracemalloc
import unittest
from schemawitness import BatchLimits, review


class MalformedShapeResources(unittest.TestCase):
    def test_extra_keys_are_rejected_before_allocating_a_key_set(self):
        # The caller's input allocation is outside the review's memory scope.
        # This catches an extra O(number-of-invalid-keys) set allocation.
        operation = {"id": "synthetic", "request": {"old": True, "new": True},
                     "response": {"old": True, "new": True}}
        operation.update({"extra_" + str(i): None for i in range(100_000)})
        tracemalloc.start()
        try:
            result = review({"operations": [operation]}, batch_limits=BatchLimits(max_input_nodes=20))
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertEqual(result["status"], "INVALID")
        self.assertEqual(result["operations"], [])
        self.assertLess(peak, 100_000)
