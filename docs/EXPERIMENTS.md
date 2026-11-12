# A reproducible sensitivity experiment

## Question

For one invented day, how do capacity, inverter power, efficiency and a monetary
carbon valuation change optimal dispatch? These are **operational trade-offs**,
not a recommendation to buy a battery.

## Run

```sh
python sensitivity.py --capacities 0 5 10 20 --powers 2 4 \
  --efficiencies 0.9 0.95 --carbon-prices 0 0.2 --output results/sweep
```

This creates 32 cases. The default command creates 24. Each row is a Cartesian
combination, so some no-storage cases are intentionally duplicates. Every case
starts and ends with an empty battery. This differs from `microgrid.py`'s default
50% initial SOC: use like-for-like boundaries when comparing results.

## Read the outputs

- `sensitivity.csv`: flat metrics suitable for a spreadsheet or plotting tool.
- `sensitivity.json`: same rows plus exact inputs, assumptions, no-storage
  baselines, Python/NumPy/SciPy versions and synthetic-data provenance.
- `grid_bill_reduction_eur`: no-storage bill minus scenario bill. Negative means
  the scenario costs more on the grid bill, which can occur under carbon weighting.
- `grid_emissions_reduction_kgco2e`: difference in modeled grid-related emissions.
  This is not a lifecycle or real-world avoided-emissions claim.
- `objective_reduction_eur`: improvement against a no-storage baseline evaluated
  using the **same** carbon price and throughput convention. Do not rank this
  column across different carbon valuations as if it were a common objective.
- `maximum_equality_residual`: numerical conservation check, not proof that the
  physical model or invented assumptions describe a real installation.

One-way efficiency 0.95 means round-trip efficiency 0.9025. Power values are kW;
capacity and interval flows are kWh. In the Python API, `hours` controls conversion
of inverter power to interval energy. Never resample kWh as if it were kW.

## Validation expectations

With all else fixed and zero initial/final SOC, adding capacity expands the
feasible set. The optimized objective should not increase, up to numerical
tolerance. A zero-capacity case must match its no-storage baseline. The objective
must decompose into grid bill + throughput proxy + monetized grid emissions.
Tests enforce these properties. Equal objectives can still have different dispatch
schedules due to multiple optima; compare metrics and constraints, not exact flow
vectors across solver versions.

## What to investigate next

Change one factor at a time before interpreting a full grid. Look for saturation:
more storage may have little value once inverter power or available solar becomes
binding. To discuss investment, first introduce licensed measured multi-season
data, uncertainty, capital and replacement costs, degradation, tariff rules and
an independent review. Do not multiply one synthetic day's savings by 365 and
present it as a forecast or payback estimate.
