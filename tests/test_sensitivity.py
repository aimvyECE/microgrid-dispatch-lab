import unittest
import numpy as np
from sensitivity import sweep
from microgrid import Battery, solve, synthetic_day


class SensitivityTests(unittest.TestCase):
    def test_count_and_reproducibility(self):
        result = sweep(*synthetic_day())
        self.assertEqual(len(result['scenarios']), 24)
        self.assertEqual(result, sweep(*synthetic_day()))
        self.assertEqual(result['inputs']['load_kwh'], synthetic_day()[0].tolist())

    def test_zero_capacity_matches_baseline(self):
        result = sweep(*synthetic_day(), capacities=[0])
        for row in result['scenarios']:
            self.assertAlmostEqual(row['objective_reduction_eur'], 0)
            self.assertAlmostEqual(row['grid_bill_reduction_eur'], 0)

    def test_more_capacity_cannot_worsen_objective(self):
        rows = sweep(*synthetic_day(), capacities=[0, 5, 10, 20], powers=[4],
                     efficiencies=[.95], carbon_prices=[.2])['scenarios']
        for a, b in zip(rows, rows[1:]):
            self.assertLessEqual(b['objective_eur'], a['objective_eur'] + 1e-8)

    def test_matching_baseline_valuation(self):
        result = sweep(*synthetic_day(), capacities=[5], powers=[4],
                       efficiencies=[.95], carbon_prices=[1])
        expected = solve(*synthetic_day(), Battery(0, 0, initial_fraction=0), carbon_price=1)['metrics']
        self.assertEqual(result['baselines_by_carbon_price']['1'], expected)
        row = result['scenarios'][0]
        self.assertAlmostEqual(row['objective_reduction_eur'], expected['objective_eur']-row['objective_eur'])

    def test_reject_invalid_axes(self):
        for key, values in [('capacities', []), ('capacities', [-1]), ('powers', [float('inf')]),
                            ('efficiencies', [0]), ('efficiencies', [1.1]), ('carbon_prices', [-1])]:
            with self.subTest(key=key, values=values), self.assertRaises(ValueError):
                sweep(*synthetic_day(), **{key: values})

    def test_generator_inputs_not_consumed_between_runs(self):
        data = synthetic_day()
        a = sweep(*(iter(v) for v in data))
        b = sweep(*data)
        self.assertEqual(a, b)

    def test_objective_decomposition(self):
        rows = sweep(*synthetic_day())['scenarios']
        for row in rows:
            expected = row['grid_bill_eur'] + row['throughput_cost_proxy_eur'] + row['carbon_price_eur_kgco2e']*row['operational_grid_kgco2e']
            self.assertAlmostEqual(row['objective_eur'], expected)
            self.assertLess(row['maximum_equality_residual'], 1e-7)

if __name__ == '__main__':
    unittest.main()
