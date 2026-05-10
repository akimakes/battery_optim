# Home Battery Tariff Simulation

This project analyzes whether a home battery can reduce electricity costs under
dynamic aWATTar-style hourly pricing. The current model uses 15-minute house
consumption and market price data.

## Layout

```text
config/default.yaml              Simulation defaults
data/input/data.csv              Synchronized 15-minute input data
data/output/simulations/         Generated simulation results
data/price/                      Raw or converted price data
data/house_consumption/          Raw house consumption exports
scripts/prepare_data.py          Build synchronized input data
scripts/json_to_csv.py           Convert aWATTar JSON exports to CSV
scripts/plot_marketprice.py      Plot historical market prices
run_simulation.py                Run the current rule-based simulation
src/batt/                        Reusable simulation package
tests/                           Future tests
```

## Install

```powershell
& 'C:\Users\aki\AppData\Local\Python\bin\python.exe' -m pip install -r requirements.txt
```

## Run

```powershell
& 'C:\Users\aki\AppData\Local\Python\bin\python.exe' run_simulation.py
```

The runner uses a rule-based controller: charge below a low price threshold and
discharge above a high price threshold.

Battery SOC settings in `config/default.yaml` are fractions of usable capacity:

```yaml
battery:
  capacity_kwh: 5.74
  min_soc_fraction: 0.2
  max_soc_fraction: 0.8
```

Internally these are converted to kWh before the simulation runs. The initial
SOC is fixed at 50% of capacity.

To find better rule parameters, set this in `config/default.yaml`:

```yaml
optimizer:
  enabled: true
```

The optimizer keeps the same rule and searches `low_price_eur_per_kwh` /
`high_price_eur_per_kwh` parameter pairs to maximize `savings_eur`.
Set `optimizer.cpu_cores` in `config/default.yaml` to use multiple CPU cores
for the parameter search.

Monthly plotting is also controlled from `config/default.yaml`:

```yaml
plot:
  enabled: true
  year: 2026
  month: 1
  timezone: Europe/Vienna
  output_file: data/output/simulations/month_plot.png
```

Only the selected month is plotted. The chart includes billable import price,
energy flows, and battery state of charge.

## Test

```powershell
$env:PYTHONPATH='src'
& 'C:\Users\aki\AppData\Local\Python\bin\python.exe' -m unittest discover -s tests
```
