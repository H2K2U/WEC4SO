# WEC — Water‑Energy Calculations for HPP Reservoir Operation

> **A Python toolkit for long‑term optimisation of hydroelectric reservoir drawdown/fill cycles**

---

## Table of contents

1. [Motivation](#motivation)
2. [Theoretical background](#theoretical-background)
3. [Software architecture](#software-architecture)
4. [Installation](#installation)
5. [Quick start](#quick-start)
6. [Testing](#testing)
7. [Roadmap](#roadmap)
8. [Citing & bibliography](#citing--bibliography)
9. [License](#license)

---

## Motivation

Hydropower plants (HPPs) with annual storage reservoirs play a pivotal role in load–following,
frequency regulation and renewables integration.
Planning an **optimal discharge/fill schedule** that maximises generation while respecting
hydrological and market constraints is therefore an evergreen research and industrial topic.
This repository offers a compact yet extensible reference implementation of a
**month‑by‑month reservoir simulation and optimisation engine** backed by the curricula of
Novosibirsk State Technical University.


## Theoretical background

The mathematical formulation follows the classical long‑term HPP scheduling problem
— maximise annual energy **W** subject to:

* reservoir mass balance;
* head dependency on storage curve **H(V)**;
* power equation `N = 8.5 · Q · H / 1000` MW;
* bounds on forebay levels (NRL ≤ Z₍вб₎ ≤ UМО) and environmental releases;
* installed capacity limit *N\_inst*.

The implementation is inspired by course material and examples from the following
textbooks:

| Ref  | Title                                                                                                                       | Scope                                                                           |
| ---- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| \[1] | **Филиппова Т.А., Сидоркин Ю.М., Русина А.Г.**<br>*Оптимизация режимов электростанций и энергосистем*, 3‑е изд., НГТУ, 2018 | General optimisation of power‑system operation fileciteturn1file0L1-L20     |
| \[2] | **Секретарев Ю.А. и др.** *Основы расчётов гидроэнергетических режимов ГЭС в энергосистеме*, НГТУ, 2020                     | Hydrological‑energy calculations & dispatch curves fileciteturn1file3L1-L20 |

> The code examples in this repository reproduce, in a programmatic way, the
> manual step‑by‑step calculations found in \[2] (Chs. 4–6) and extend them with
> optimisation heuristics advocated in \[1] (Ch. 9).

## Software architecture

```text
wec/
├─ constants.py                # domain‑wide constants
├─ domain/                     # pure data models
│   ├─ geometry.py             # Geometry dataclass
│   ├─ static_levels.py        # StaticLevels (+ installed_capacity)
│   └─ hydrological_series.py  # HydrologicalSeries
├─ core/                       # business logic
│   ├─ interpolation.py        # Interpolator protocol + default impl.
│   ├─ formulas.py             # reusable hydraulic / energy formulas
│   ├─ month_selector.py       # automatic regime labelling & rotation
│   └─ reservoir_simulator.py  # forward simulation & heuristics
├─ facade/
│   └─ analyzer.py             # WECAnalyzer – single class to import
├─ visualization/              # matplotlib helpers (optional)
│   └─ plots.py
└─ __init__.py                 # re‑exports for end‑users
cli/
└─ demo.py                     # reproducible example (see below)
```

### Extending the toolkit

* Add new optimisation strategies in `core/` without touching `facade/`.
* Plug alternative interpolators (e.g. monotone splines) by implementing
  `Interpolator`.
* Swap plotting backend by replacing functions in `visualization/`.

## Installation

```bash
# clone repo
$ git clone https://github.com/your‑org/wec.git && cd wec

# create venv (recommended)
$ python -m venv .venv && source .venv/bin/activate

# editable install for development
$ pip install -e .[dev]
```

> **Dependencies**: `numpy`, `pandas`, `matplotlib` (all MIT/BSD licenses).

## Quick start

```bash
$ python cli/demo.py
```

The script will:

1. build dataclass instances from sample input;
2. label months, rotate hydrological year, simulate reservoir;
3. print a tidy `pandas` table and show three illustrative charts:

   * domestic inflow distribution;
   * guaranteed capacity curve;
   * reservoir forebay elevation trajectory.

Feel free to replace the sample inflow series with your own CSV data.

## Testing

Unit tests live under **`tests/`** and rely on **pytest**:

```bash
$ pytest -q
```

A minimal dataset in `tests/fixtures/` guarantees ≤ 0.5 s runtime.

## Roadmap

* ⚙️  Replace greedy heuristics with MILP solver (Pyomo / CBC).
* 📈  Add LiveCharts‑like interactive dashboard via Plotly.
* 🌐  Publish REST API (FastAPI) for remote scenario runs.

## Citing & bibliography

If you use *WEC* in academic research, please cite the relevant textbooks
(\[1]‑\[4]) alongside the GitHub repository DOI (zenodo badge forthcoming).

## License

**MIT License** — free for academic and commercial use.  See `LICENSE` for details.
