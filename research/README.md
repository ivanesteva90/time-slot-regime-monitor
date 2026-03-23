# Research Pipeline (Phase 1)

Quick CLI to process SPX IC backtest CSVs and output summary metrics for sizing variants.

Run from this folder:
```
python src/pipeline.py --inputs ../data ../BTM
```

Outputs:
- `../outputs/summary_variants.csv` with variants:
  - `size_1` (1 contrato)
  - `size_2` (2 contratos)
  - `weekday_mix` (L/J/V = 2; M/X = 1)
  - `equity_ladder` (4000↑ → 2; 3300↓ → 1)

Metrics per variant: total profit, trades, win rate, avg win/loss, expectancy, profit factor, max drawdown, longest losing streak, span start/end.

Data sources:
- `../data/*.csv`
- `../BTM/rut|spx|xsp/*.csv` (carpetas creadas para separar por subyacente)
