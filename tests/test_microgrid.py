import unittest
import numpy as np
from microgrid import Battery, solve, synthetic_day

class DispatchTests(unittest.TestCase):
    def test_no_assets(self):
        r=solve([2,3],[0,0],[.2,.4],[.1,.2],Battery(0,0))
        self.assertAlmostEqual(r['metrics']['grid_bill_eur'],1.6)
        self.assertAlmostEqual(r['metrics']['operational_grid_kgco2e'],.8)

    def test_solar_curtailment(self):
        r=solve([1],[3],[.2],[.1],Battery(0,0))
        self.assertAlmostEqual(r['dispatch']['curtailed'][0],2)
        self.assertAlmostEqual(r['metrics']['grid_kwh'],0)

    def test_conservation_and_bounds(self):
        load,pv,p,c=synthetic_day(); b=Battery(); r=solve(load,pv,p,c,b)
        d={k:np.array(v) for k,v in r['dispatch'].items()}
        np.testing.assert_allclose(d['grid']+pv+d['discharge'],load+d['charge']+d['curtailed'],atol=1e-8)
        previous=np.r_[b.capacity_kwh*b.initial_fraction,d['soc'][:-1]]
        np.testing.assert_allclose(d['soc'],previous+b.efficiency*d['charge']-d['discharge']/b.efficiency,atol=1e-8)
        self.assertAlmostEqual(d['soc'][-1],b.capacity_kwh*b.initial_fraction)
        self.assertTrue(np.all(d['soc'] >= -1e-8)); self.assertTrue(np.all(d['soc'] <= b.capacity_kwh+1e-8))
        self.assertLess(r['metrics']['maximum_equality_residual'],1e-8)

    def test_cost_optimum_no_worse_than_no_storage(self):
        data=synthetic_day()
        self.assertLessEqual(solve(*data)['metrics']['objective_eur'],solve(*data,Battery(0,0))['metrics']['objective_eur']+1e-8)

    def test_carbon_valuation(self):
        data=([1,1],[0,0],[.1,.1],[.9,.1]); b=Battery(2,2,1,0)
        # Initial zero disallows borrowing energy from the future.
        r=solve(*data,b,carbon_price=1)
        self.assertAlmostEqual(r['dispatch']['grid'][0],1)

    def test_conflicting_carbon_and_price(self):
        data=([1,1],[0,0],[.1,.3],[.9,.1]); b=Battery(2,2,1,0)
        cheap=solve(*data,b)
        clean=solve(*data,b,carbon_price=1)
        self.assertLess(cheap['metrics']['grid_bill_eur'],clean['metrics']['grid_bill_eur'])
        self.assertLess(clean['metrics']['operational_grid_kgco2e'],cheap['metrics']['operational_grid_kgco2e'])

    def test_half_hour_power_limit(self):
        r=solve([0,4],[0,0],[.1,1],[0,0],Battery(4,2,1,0),hours=.5)
        self.assertLessEqual(max(r['dispatch']['charge']),1+1e-8)
        self.assertLessEqual(max(r['dispatch']['discharge']),1+1e-8)

    def test_bad_inputs(self):
        for data in [([1],[0,0],[1],[1]),([1],[0],[-1],[1]),([float('nan')],[0],[1],[1])]:
            with self.assertRaises(ValueError): solve(*data)
        with self.assertRaises(ValueError): solve([1],[0],[1],[1],Battery(efficiency=0))

if __name__ == '__main__': unittest.main()
