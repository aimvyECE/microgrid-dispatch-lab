"""Reproducible parameter sweeps, not investment or capacity-sizing advice."""
import argparse
import csv
import json
import platform
from itertools import product
from pathlib import Path

import numpy as np
import scipy
from microgrid import Battery, solve, synthetic_day


def _values(values, name, *, positive=False, maximum=None):
    values = list(values)
    if not values or any(not np.isfinite(v) or v < 0 or (positive and v == 0)
                         or (maximum is not None and v > maximum) for v in values):
        raise ValueError(f'{name} must be nonempty, finite and within supported bounds')
    return values


def sweep(load, pv, price, carbon, capacities=(0, 5, 10), powers=(2, 4),
          efficiencies=(0.9, 0.95), carbon_prices=(0, 0.2), hours=1.0):
    """Cartesian sweep with empty initial/final storage and matched no-storage baseline.

    Baseline is revalued at each carbon price. Objective differences must not be
    compared across different carbon valuations. All flows are kWh per interval.
    """
    capacities = _values(capacities, 'capacities')
    powers = _values(powers, 'powers')
    efficiencies = _values(efficiencies, 'efficiencies', positive=True, maximum=1)
    carbon_prices = _values(carbon_prices, 'carbon_prices')
    # Materialize iterables once, so repeated scenarios use exactly the same data.
    inputs = tuple(np.asarray(list(v), dtype=float) for v in (load, pv, price, carbon))
    rows = []
    baselines = {}
    for valuation in carbon_prices:
        baselines[valuation] = solve(*inputs, Battery(0, 0, initial_fraction=0),
                                    carbon_price=valuation, hours=hours)['metrics']
    for capacity, power, efficiency, valuation in product(capacities, powers, efficiencies, carbon_prices):
        battery = Battery(capacity, power, efficiency, initial_fraction=0)
        result = solve(*inputs, battery, carbon_price=valuation, hours=hours)
        metrics = result['metrics']
        baseline = baselines[valuation]
        rows.append({
            'capacity_kwh': capacity, 'power_kw': power, 'one_way_efficiency': efficiency,
            'carbon_price_eur_kgco2e': valuation, **metrics,
            'grid_bill_reduction_eur': baseline['grid_bill_eur'] - metrics['grid_bill_eur'],
            'grid_emissions_reduction_kgco2e': baseline['operational_grid_kgco2e'] - metrics['operational_grid_kgco2e'],
            'objective_reduction_eur': baseline['objective_eur'] - metrics['objective_eur'],
        })
    return {
        'schema_version': 1,
        'assumptions': {'hours_per_interval': hours, 'initial_and_final_soc_fraction': 0,
                        'throughput_eur_kwh': Battery().throughput_eur_kwh,
                        'no_capital_costs': True, 'perfect_foresight': True},
        'inputs': dict(zip(('load_kwh', 'pv_kwh', 'price_eur_kwh', 'carbon_kgco2e_kwh'),
                           (v.tolist() for v in inputs))),
        'environment': {'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__},
        'baselines_by_carbon_price': {str(k): v for k, v in baselines.items()},
        'scenarios': rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('results/sensitivity'))
    parser.add_argument('--capacities', nargs='+', type=float, default=[0, 5, 10])
    parser.add_argument('--powers', nargs='+', type=float, default=[2, 4])
    parser.add_argument('--efficiencies', nargs='+', type=float, default=[0.9, 0.95])
    parser.add_argument('--carbon-prices', nargs='+', type=float, default=[0, 0.2])
    args = parser.parse_args()
    try:
        result = sweep(*synthetic_day(), capacities=args.capacities, powers=args.powers,
                       efficiencies=args.efficiencies, carbon_prices=args.carbon_prices)
    except ValueError as exc:
        parser.error(str(exc))
    result['data_provenance'] = 'synthetic_day(): invented 24-hour pedagogical profiles, not measurements'
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'sensitivity.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    with (args.output / 'sensitivity.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(result['scenarios'][0]))
        writer.writeheader()
        writer.writerows(result['scenarios'])
    print(f"Wrote {len(result['scenarios'])} synthetic scenarios to {args.output}")


if __name__ == '__main__':
    main()
