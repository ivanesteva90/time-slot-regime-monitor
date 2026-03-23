"""
Quick research pipeline for SPX iron condor backtests.

Features (Phase 1):
- Load CSVs from folders (default: ../data and ../BTM/*).
- Normalize date/time, derive weekday/month.
- Compute core metrics: total profit, trade count, win rate, avg win/loss, expectancy,
  profit factor, max drawdown, longest losing streak.
- Compare sizing variants: fixed 1 contract, fixed 2 contracts, mixed weekday sizing
  (Mon/Thu/Fri = 2; Tue/Wed = 1).
- Equity ladder simulation: 1 contract until equity >= 4000, 2 contracts until equity < 3300.
- Save summary tables to ../outputs.

Run:
  python pipeline.py --inputs ../data ../BTM/rut ../BTM/spx ../BTM/xsp
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd


DATA_COLS = ["Date", "Hora", "P/L"]
WEEKDAY_MAP = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri"}
WEEKDAY_SIZING = {"Mon": 2, "Tue": 1, "Wed": 1, "Thu": 2, "Fri": 2}
EQUITY_UP = 4000
EQUITY_DOWN = 3300


@dataclass
class Trade:
    date: pd.Timestamp
    slot: str
    pl: float
    weekday: str
    month: str


def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in DATA_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name} missing columns {missing}")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Hora"] = df["Hora"].astype(str).str.slice(0, 5)
    df = df.dropna(subset=["Date"])
    df["weekday"] = df["Date"].dt.weekday.map(WEEKDAY_MAP)
    df["month"] = df["Date"].dt.to_period("M").astype(str)
    df["pl"] = pd.to_numeric(df["P/L"], errors="coerce")
    df = df.dropna(subset=["pl"])
    return df[["Date", "Hora", "pl", "weekday", "month"]].rename(columns={"Hora": "slot"})


def longest_losing_streak(values: List[float]) -> int:
    streak = best = 0
    for v in values:
        if v < 0:
            streak += 1
            best = max(best, streak)
        else:
            streak = 0
    return best


def max_drawdown(values: List[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for v in values:
        equity += v
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return max_dd


def core_metrics(series: Iterable[float]) -> Dict[str, float]:
    vals = list(series)
    if not vals:
        return {k: math.nan for k in [
            "total", "count", "win_rate", "avg_win", "avg_loss",
            "expectancy", "profit_factor", "max_dd", "max_losing_streak"
        ]}
    wins = [v for v in vals if v > 0]
    losses = [v for v in vals if v < 0]
    total = sum(vals)
    count = len(vals)
    win_rate = len(wins) / count
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    expectancy = total / count
    profit_factor = (sum(wins) / -sum(losses)) if losses else float("inf")
    dd = max_drawdown(vals)
    streak = longest_losing_streak(vals)
    return {
        "total": total,
        "count": count,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
        "profit_factor": profit_factor,
        "max_dd": dd,
        "max_losing_streak": streak,
    }


def apply_size(df: pd.DataFrame, size: int) -> pd.Series:
    return df["pl"] * size


def apply_weekday_mix(df: pd.DataFrame) -> pd.Series:
    sizes = df["weekday"].map(WEEKDAY_SIZING).fillna(1)
    return df["pl"] * sizes


def apply_equity_ladder(df: pd.DataFrame) -> pd.Series:
    equity = 0.0
    out = []
    current_size = 1
    for v in df["pl"]:
        out.append(v * current_size)
        equity += v * current_size
        if equity >= EQUITY_UP:
            current_size = 2
        if equity < EQUITY_DOWN:
            current_size = 1
    return pd.Series(out, index=df.index)


def summarize_variant(name: str, series: pd.Series, base_df: pd.DataFrame) -> Dict[str, object]:
    m = core_metrics(series.tolist())
    return {
        "variant": name,
        "total": m["total"],
        "count": m["count"],
        "win_rate": m["win_rate"],
        "avg_win": m["avg_win"],
        "avg_loss": m["avg_loss"],
        "expectancy": m["expectancy"],
        "profit_factor": m["profit_factor"],
        "max_dd": m["max_dd"],
        "max_losing_streak": m["max_losing_streak"],
        "span_start": base_df["Date"].min(),
        "span_end": base_df["Date"].max(),
    }


def process_file(path: Path) -> pd.DataFrame:
    df = load_csv(path)
    df = df.sort_values(["Date", "slot"]).reset_index(drop=True)
    variants = []
    variants.append(summarize_variant("size_1", apply_size(df, 1), df))
    variants.append(summarize_variant("size_2", apply_size(df, 2), df))
    variants.append(summarize_variant("weekday_mix", apply_weekday_mix(df), df))
    variants.append(summarize_variant("equity_ladder", apply_equity_ladder(df), df))
    out = pd.DataFrame(variants)
    out.insert(0, "file", path.name)
    return out


def find_inputs(directories: List[Path]) -> List[Path]:
    inputs: List[Path] = []
    for d in directories:
        if not d.exists():
            continue
        for p in d.rglob("*.csv"):
            inputs.append(p)
    return sorted(inputs)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="SPX IC research pipeline (Phase 1)")
    parser.add_argument(
        "--inputs",
        nargs="*",
        type=Path,
        default=[Path("../data"), Path("../BTM")],
        help="Folders to scan for CSVs (default: ../data and ../BTM)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("../outputs/summary_variants.csv"),
        help="Output CSV path (default: ../outputs/summary_variants.csv)"
    )
    args = parser.parse_args(argv)

    inputs = find_inputs(args.inputs)
    if not inputs:
        print("No CSV files found in", [str(p) for p in args.inputs], file=sys.stderr)
        return 1

    summaries = []
    errors = []
    for path in inputs:
        try:
            summaries.append(process_file(path))
            print(f"Processed {path}")
        except Exception as exc:  # noqa: BLE001
            errors.append((path, exc))
            print(f"Error {path}: {exc}", file=sys.stderr)

    if summaries:
        result = pd.concat(summaries, ignore_index=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(args.output, index=False)
        print(f"\nSaved summary to {args.output}")
    else:
        print("No valid datasets processed.", file=sys.stderr)

    if errors:
        print("\nErrors:", file=sys.stderr)
        for path, exc in errors:
            print(f"- {path}: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
