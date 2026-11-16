"""Deterministic single-bus dispatch research prototype. All quantities per interval."""
from dataclasses import dataclass
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix

@dataclass(frozen=True)
class Battery:
    capacity_kwh: float = 10.0
    power_kw: float = 4.0
    efficiency: float = 0.95  # one-way efficiency, not round-trip
    initial_fraction: float = 0.5
    throughput_eur_kwh: float = 0.005

    def validate(self):
        values = (self.capacity_kwh, self.power_kw, self.efficiency,
                  self.initial_fraction, self.throughput_eur_kwh)
        if not all(np.isfinite(values)) or self.capacity_kwh < 0 or self.power_kw < 0:
            raise ValueError('Battery capacity/power must be finite and nonnegative')
        if not 0 < self.efficiency <= 1 or not 0 <= self.initial_fraction <= 1:
            raise ValueError('Invalid efficiency or initial fraction')
        if self.throughput_eur_kwh <= 0:
            raise ValueError('Positive throughput penalty required')


def solve(load, pv, price, carbon, battery=Battery(), carbon_price=0.0, hours=1.0):
    """Minimize grid bill + battery throughput proxy + carbon valuation.

    load, pv: kWh per interval; price: EUR/kWh; carbon: kgCO2e/kWh;
    carbon_price: EUR/kgCO2e; hours: interval duration. No exports allowed.
    """
    battery.validate()
    arrays = [np.asarray(x, dtype=float) for x in (load, pv, price, carbon)]
    if any(x.ndim != 1 or len(x) == 0 for x in arrays):
        raise ValueError('Inputs must be nonempty one-dimensional arrays')
    n = len(arrays[0])
    if any(len(x) != n or not np.all(np.isfinite(x)) or np.any(x < 0) for x in arrays):
        raise ValueError('Inputs must have equal length, finite nonnegative values')
    if not np.isfinite(hours) or hours <= 0 or not np.isfinite(carbon_price) or carbon_price < 0:
        raise ValueError('Invalid interval or carbon price')
    load, pv, price, carbon = arrays
    # Blocks: grid, charge, discharge, curtailment, state-of-charge after interval.
    objective = np.zeros(5*n)
    objective[:n] = price + carbon_price*carbon
    objective[n:3*n] = battery.throughput_eur_kwh
    # Only 8*n equality coefficients are nonzero. Avoid quadratic
    # memory growth for longer horizons; HiGHS accepts sparse constraints.
    matrix = lil_matrix((2*n+1, 5*n), dtype=float)
    rhs = np.zeros(2*n+1)
    for t in range(n):
        matrix[t, t] = 1
        matrix[t, n+t] = -1
        matrix[t, 2*n+t] = 1
        matrix[t, 3*n+t] = -1
        rhs[t] = load[t] - pv[t]
        matrix[n+t, 4*n+t] = 1
        matrix[n+t, n+t] = -battery.efficiency
        matrix[n+t, 2*n+t] = 1/battery.efficiency
        if t:
            matrix[n+t, 4*n+t-1] = -1
        else:
            rhs[n+t] = battery.capacity_kwh*battery.initial_fraction
    matrix[-1, -1] = 1
    rhs[-1] = battery.capacity_kwh*battery.initial_fraction
    matrix = matrix.tocsr()
    bounds = ([(0, None)]*n + [(0, battery.power_kw*hours)]*(2*n)
              + [(0, float(v)) for v in pv] + [(0, battery.capacity_kwh)]*n)
    result = linprog(objective, A_eq=matrix, b_eq=rhs, bounds=bounds, method='highs')
    if not result.success:
        raise RuntimeError(f'Optimization failed: {result.message}')
    grid, charge, discharge, curtailed, soc = result.x.reshape(5, n)
    return {
        'dispatch': dict(grid=grid.tolist(), charge=charge.tolist(),
                         discharge=discharge.tolist(), curtailed=curtailed.tolist(), soc=soc.tolist()),
        'metrics': {
            'grid_kwh': float(grid.sum()), 'grid_bill_eur': float(grid @ price),
            'operational_grid_kgco2e': float(grid @ carbon),
            'throughput_cost_proxy_eur': float((charge.sum()+discharge.sum())*battery.throughput_eur_kwh),
            'objective_eur': float(result.fun), 'curtailed_kwh': float(curtailed.sum()),
            'maximum_equality_residual': float(np.abs(matrix @ result.x-rhs).max()),
        },
    }


def synthetic_day():
    """Invented pedagogical profiles: not measurements, forecasts, or French tariffs."""
    t = np.arange(24)
    load = 1.2 + 1.6*np.exp(-((t-19)/3)**2) + 0.7*np.exp(-((t-8)/2)**2)
    pv = np.maximum(0, 4*np.sin(np.pi*(t-6)/12))
    price = np.where((t >= 17) & (t <= 21), 0.35, 0.18)
    carbon = np.where((t >= 17) & (t <= 21), 0.35, 0.12)
    return load, pv, price, carbon


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('results'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    inputs = synthetic_day()
    scenarios = {
        'grid_only': (inputs[0], np.zeros(24), inputs[2], inputs[3], Battery(0, 0), 0),
        'solar_only': (*inputs, Battery(0, 0), 0),
        'solar_battery_cost': (*inputs, Battery(), 0),
        'solar_battery_carbon': (*inputs, Battery(), 0.2),
    }
    results = {name: solve(*params) for name, params in scenarios.items()}
    (args.output/'summary.json').write_text(json.dumps(results, indent=2)+'\n')
    with (args.output/'dispatch.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['scenario', 'hour', 'load_kwh', 'pv_kwh', 'grid_kwh', 'charge_kwh', 'discharge_kwh', 'curtailed_kwh', 'soc_kwh'])
        for name, result in results.items():
            for t in range(24):
                writer.writerow([name, t, scenarios[name][0][t], scenarios[name][1][t],
                                 *[result['dispatch'][key][t] for key in ('grid','charge','discharge','curtailed','soc')]])
    for name, result in results.items():
        m = result['metrics']
        print(f"{name:26s} bill={m['grid_bill_eur']:.2f} EUR | grid emissions={m['operational_grid_kgco2e']:.2f} kgCO2e")

if __name__ == '__main__':
    main()
