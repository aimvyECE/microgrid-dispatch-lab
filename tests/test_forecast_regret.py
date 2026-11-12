import unittest
import numpy as np
from microgrid import Battery
from forecast_regret import evaluate, experiment

class ForecastRegretTests(unittest.TestCase):
    def test_perfect_signals_zero_regret(self):
        r = evaluate([1,1], [0,0], [.1,.5], [.2,.3], [.1,.5], [.2,.3])
        self.assertAlmostEqual(r['regret_eur'], 0)

    def test_reversed_tariff_can_lose_money(self):
        r = evaluate([1,1], [0,0], [.5,.1], [0,0], [.1,.5], [0,0], Battery(1,1,1,0,.005))
        self.assertGreater(r['regret_eur'], 0)
        self.assertLess(r['realized_savings_vs_no_storage_eur'], 0)

    def test_no_storage_has_zero_regret(self):
        r = evaluate([1,1], [0,0], [.5,.1], [0,0], [.1,.5], [0,0], Battery(0,0))
        self.assertAlmostEqual(r['regret_eur'], 0)

    def test_invalid_forecast_rejected(self):
        for p in ([.1], [-1,.2], [np.nan,.2]):
            with self.assertRaises(ValueError):
                evaluate([1,1], [0,0], [.5,.1], [0,0], p, [0,0])

    def test_realized_score_has_carbon_and_throughput(self):
        b = Battery(1,1,1,0,.005)
        r = evaluate([1,1], [0,0], [.1,.5], [.2,.4], [.1,.5], [.2,.4], b, .2)
        d = r['planned_dispatch']
        expected = r['realized_grid_bill_eur'] + .2*r['realized_grid_emissions_kgco2e'] + .005*(sum(d['charge'])+sum(d['discharge']))
        self.assertAlmostEqual(expected, r['realized_objective_eur'])

    def test_synthetic_cases_feasible_and_reproducible(self):
        e = experiment()
        self.assertEqual(e, experiment())
        for case in e['cases'].values():
            d = case['planned_dispatch']; inputs = e['actual_inputs']
            for t in range(24):
                self.assertAlmostEqual(d['grid'][t]+inputs['pv'][t]+d['discharge'][t], inputs['load'][t]+d['charge'][t]+d['curtailed'][t])
            self.assertAlmostEqual(d['soc'][-1], 0)
            self.assertGreaterEqual(case['regret_eur'], 0)
