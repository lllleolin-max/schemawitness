import importlib
from copy import deepcopy
import unittest
from unittest.mock import patch
from schemawitness import BatchLimits, Limits, review

module = importlib.import_module('schemawitness.review')


def manifest(old=True, new=True, count=2):
    pair = {'old': old, 'new': new}
    return {'operations': [{'id': str(i), 'request': pair, 'response': pair} for i in range(count)]}


class BatchDepthTests(unittest.TestCase):
    def test_legal_high_depth_returns_controlled_unknown_without_core_work(self):
        schema = True
        for _ in range(1100):
            schema = {'items': schema}
        m = manifest(schema, True, 1)
        # An iterative identity walk checks nonmutation without making the
        # regression harness itself depend on deep equality or deepcopy.
        chain = []
        current = schema
        while isinstance(current, dict):
            chain.append((id(current), tuple(current)))
            current = current['items']
        self.assertIs(current, True)
        limits = Limits(max_depth=2000)
        default = review(m, limits=limits)
        self.assertEqual(default['status'], 'INVALID')
        with patch.object(module, 'compare', side_effect=AssertionError('no core call after input recursion')):
            result = review(m, limits=limits, batch_limits=BatchLimits())
        self.assertEqual((result['status'], result['decision']), ('UNKNOWN', 'BLOCK'))
        self.assertEqual(result['counts']['UNKNOWN'], 2)
        self.assertEqual(result['batch']['halted'], 'batch_recursion_limit')
        self.assertEqual(result['batch']['core_compare_calls'], 0)
        current, after = schema, []
        while isinstance(current, dict):
            after.append((id(current), tuple(current)))
            current = current['items']
        self.assertEqual(chain, after)
        self.assertIs(current, True)

    def test_real_deep_witness_copy_cache_and_result_return(self):
        nested = []
        for _ in range(80):
            nested = [nested]
        m = manifest({'const': nested}, False)
        before = deepcopy(m)
        plain = review(m, limits=Limits(max_depth=200))
        result = review(m, limits=Limits(max_depth=200), batch_limits=BatchLimits())
        self.assertEqual(result['counts'], plain['counts'])
        self.assertEqual(result['counts']['BREAKING'], 2)
        self.assertEqual(result['batch']['core_compare_calls'], 2)
        self.assertEqual(result['batch']['cache_hits'], 2)
        for actual, expected in zip(result['operations'], plain['operations']):
            for direction in ('request', 'response'):
                without_metadata = actual[direction].copy()
                without_metadata.pop('batch')
                self.assertEqual(without_metadata, expected[direction])
        result['operations'][0]['request']['witness'][0].append('mutated result')
        self.assertEqual(result['operations'][1]['request']['witness'], nested)
        self.assertEqual(m, before)

    def test_owned_identity_and_copy_stack_failures_drop_certificates(self):
        m = manifest()
        with patch.object(module, '_schema_identity', side_effect=RecursionError('identity depth')):
            result = review(m, batch_limits=BatchLimits())
        self.assertEqual(result['counts']['UNKNOWN'], 4)
        self.assertEqual(result['batch']['core_compare_calls'], 0)
        for failure_call in (1, 2, 5):  # store, initial return, cached return
            calls = 0
            def copy_boundary(value):
                nonlocal calls
                calls += 1
                if calls == failure_call:
                    raise RecursionError('copy depth')
                return deepcopy(value)
            with patch.object(module, 'deepcopy', side_effect=copy_boundary):
                result = review(m, batch_limits=BatchLimits())
            self.assertEqual(result['decision'], 'BLOCK')
            self.assertEqual(result['batch']['halted'], 'batch_recursion_limit')
            self.assertGreater(result['counts']['UNKNOWN'], 0)
            for op in result['operations']:
                for direction in ('request', 'response'):
                    r = op[direction]
                    if not r['batch']['evaluated']:
                        self.assertEqual(r['status'], 'UNKNOWN')
                        self.assertEqual(r['proof'], [])
                        self.assertIsNone(r['wire'])
        self.assertEqual(m, manifest())

    def test_unrelated_internal_exceptions_are_not_suppressed(self):
        for error in (RuntimeError('engine bug'), RecursionError('core bug')):
            with patch.object(module, 'compare', side_effect=error):
                with self.assertRaises(type(error)):
                    review(manifest(), batch_limits=BatchLimits())
        with patch.object(module, 'deepcopy', side_effect=RuntimeError('copy bug')):
            with self.assertRaises(RuntimeError):
                review(manifest(), batch_limits=BatchLimits())

    def test_result_conversion_stack_limit_is_controlled_at_that_boundary(self):
        class DeepResult:
            def to_dict(self):
                raise RecursionError('result conversion depth')
        with patch.object(module, 'compare', return_value=DeepResult()):
            result = review(manifest(), batch_limits=BatchLimits())
        self.assertEqual(result['counts']['UNKNOWN'], 4)
        self.assertEqual(result['batch']['halted'], 'batch_recursion_limit')
        self.assertEqual(result['batch']['core_compare_calls'], 1)
        self.assertEqual(result['batch']['cache_entries'], 0)


if __name__ == '__main__':
    unittest.main()
