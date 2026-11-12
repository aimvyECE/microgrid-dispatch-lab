"""Price/carbon forecast stress tests, holding demand and PV known exactly."""
from dataclasses import asdict
import argparse
import json
from pathlib import Path
import numpy as np
import scipy
from microgrid import Battery, solve, synthetic_day


def evaluate(load, pv, actual_price, actual_carbon, forecast_price,
             forecast_carbon, battery=Battery(), carbon_price=0.0, hours=1.0):
    """Compare a forecast-optimal fixed schedule with a hindsight lower bound.

    Demand/PV are identical in both optimizations. Only price/carbon signals
    are uncertain; this is NOT closed-loop control or load/PV forecast repair.
    Regret includes throughput and the SAME carbon valuation for both schedules.
    """
    planned = solve(load, pv, forecast_price, forecast_carbon, battery, carbon_price, hours)
    hindsight = solve(load, pv, actual_price, actual_carbon, battery, carbon_price, hours)
    # solve validates each vector, but the two horizons must also match.
    if len(planned['dispatch']['grid']) != len(hindsight['dispatch']['grid']):
        raise ValueError('Forecast and realized horizons must match')
    grid = np.array(planned['dispatch']['grid'])
    bill = float(grid @ np.array(actual_price))
    emissions = float(grid @ np.array(actual_carbon))
    realized = bill + emissions*carbon_price + planned['metrics']['throughput_cost_proxy_eur']
    bound = hindsight['metrics']['objective_eur']
    regret = realized - bound
    if regret < -1e-7:
        raise RuntimeError('Negative regret exceeds numerical tolerance')
    no_storage = solve(load, pv, actual_price, actual_carbon,
                       Battery(0, 0, battery.efficiency, 0, battery.throughput_eur_kwh),
                       carbon_price, hours)
    return {
        'planned_dispatch': planned['dispatch'],
        'hindsight_dispatch': hindsight['dispatch'],
        'forecast_objective_eur': planned['metrics']['objective_eur'],
        'realized_grid_bill_eur': bill,
        'realized_grid_emissions_kgco2e': emissions,
        'realized_objective_eur': realized,
        'hindsight_objective_eur': bound,
        'regret_eur': max(0.0, regret),
        'realized_savings_vs_no_storage_eur': no_storage['metrics']['objective_eur'] - realized,
        'no_storage_objective_eur': no_storage['metrics']['objective_eur'],
    }


def experiment():
    load, pv, price, carbon = synthetic_day()
    battery = Battery(initial_fraction=0)
    cases = {
        'perfect_signals': (price, carbon),
        'flat_signals': (np.full(24, price.mean()), np.full(24, carbon.mean())),
        'peak_announced_4h_early': (np.roll(price, -4), np.roll(carbon, -4)),
        'peak_announced_4h_late': (np.roll(price, 4), np.roll(carbon, 4)),
    }
    return {
        'scope': 'Synthetic deterministic stress cases, not probability-weighted forecasts or expected savings. Demand/PV perfectly known. No real controller.',
        'versions': {'numpy': np.__version__, 'scipy': scipy.__version__},
        'battery': asdict(battery), 'carbon_price_eur_kg': 0.2, 'interval_hours': 1,
        'actual_inputs': dict(load=load.tolist(), pv=pv.tolist(), price=price.tolist(), carbon=carbon.tolist()),
        'cases': {name: {'forecast_price': p.tolist(), 'forecast_carbon': c.tolist(),
                         **evaluate(load, pv, price, carbon, p, c, battery, 0.2)}
                  for name, (p, c) in cases.items()},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('results/forecast_regret.json'))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(experiment(), indent=2, allow_nan=False)+'\n')
