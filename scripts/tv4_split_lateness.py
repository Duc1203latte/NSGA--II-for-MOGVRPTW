"""Do muc tre/som/so xe/f1/f3 duoi ba quy tac tach tuyen (capacity, capacity_time, DP), khong chay tien hoa.
  A) 200 hoan vi ngau nhien (default_rng(0)) tren C102-25, R201-50, C102-100.
  B) quan the cuoi cua cac run baseline tv4_main (seed 0-9), tach lai tung hoan vi bang ca ba quy tac.
Chay: python -m scripts.tv4_split_lateness [--out results/tv4_main/split_lateness.md]"""
from __future__ import annotations

import argparse
import pickle
import warnings
from pathlib import Path

import numpy as np

from src.decoder import evaluate_routes_detail, split_capacity_time, split_greedy
from src.improvements.dp_split import objective_scales, split_dp
from src.instance import load_config, load_instance
from src.runner import results_root

RULES = ("capacity", "capacity_time", "dp")
KEYS = ("F4", "late_min", "early_min", "n_vehicles", "f1", "f3")
W = np.array([1 / 3, 1 / 3, 1 / 3])


def routes_for(rule, perm, inst, scales):
    if rule == "capacity":
        return split_greedy(perm, inst)
    if rule == "capacity_time":
        return split_capacity_time(perm, inst)
    return split_dp(perm, inst, W, scales)


def measure(perms, inst, scales):
    out = {}
    for rule in RULES:
        rows = []
        for p in perms:
            d = evaluate_routes_detail(routes_for(rule, p, inst, scales), inst)
            feas = inst.fleet_size is None or d["n_vehicles"] <= inst.fleet_size
            rows.append([d[k] for k in KEYS] + [float(feas)])
        out[rule] = np.array(rows, dtype=float)
    return out


def table(label, res, inst):
    fl = "khong gioi han" if inst.fleet_size is None else str(inst.fleet_size)
    lines = [f"**{label}** (fleet_size = {fl}; moi o: TB ± do lech chuan)", "",
             "| Quy tac | F4 (phat) | late_min | early_min | So xe | f1 | f3 | Kha thi doi xe |",
             "|---|---|---|---|---|---|---|---|"]
    for rule in RULES:
        a = res[rule]
        cells = [f"{a[:, i].mean():.4g} ± {a[:, i].std(ddof=1):.3g}" for i in range(len(KEYS))]
        lines.append(f"| {rule} | " + " | ".join(cells) + f" | {a[:, -1].mean():.2f} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    cfg = load_config()
    parts = []
    warnings.simplefilter("ignore")
    for name, n in (("C102", 25), ("R201", 50), ("C102", 100)):
        inst = load_instance(name, n, cfg)
        scales = objective_scales(inst)
        rng = np.random.default_rng(0)
        perms = [list(rng.permutation(np.arange(1, inst.n + 1))) for _ in range(200)]
        parts.append(table(f"{name}-{n}, 200 hoan vi ngau nhien", measure(perms, inst, scales), inst))
    root = results_root(cfg) / "tv4_main"
    for name, n in (("C102", 25), ("R201", 50)):
        inst = load_instance(name, n, cfg)
        scales = objective_scales(inst)
        perms = []
        for f in sorted((root / f"{name}-{n}" / "baseline").glob("seed_*.pkl")):
            perms += [list(map(int, p)) for p in pickle.load(open(f, "rb"))["pop"]]
        parts.append(table(f"{name}-{n}, quan the cuoi baseline ({len(perms)} hoan vi, seed 0-9)",
                           measure(perms, inst, scales), inst))
    text = "\n\n".join(parts)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
