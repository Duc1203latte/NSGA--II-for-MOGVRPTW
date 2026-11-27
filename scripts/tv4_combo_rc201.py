"""Thoi gian chay tuan tu mot run all_on (init_smart + local_search + diversity sde k=1 + dp polish K=10) o n = 100
tren RC201, 1 seed, n_gen theo config.yaml, de TV1 lap ngan sach cac lan chay cuoi. Do bang time.process_time (CPU) va
time.perf_counter (tuong). Chay khi may it viec khac. Them --config all_on_every_eval de do chay DP moi lan cham.

    python -m scripts.tv4_combo_rc201 [--config all_on] [--seed 100]"""
from __future__ import annotations
import argparse
import time

from scripts.tv4_tune_configs import overrides
from src import nsga2
from src.instance import load_config, load_instance
from src.runner import apply_overrides


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="all_on")
    ap.add_argument("--seed", type=int, default=100)
    args = ap.parse_args()
    cfg = apply_overrides(load_config(), overrides(args.config))
    inst = load_instance("RC201", 100, cfg)
    c0, w0 = time.process_time(), time.perf_counter()
    r = nsga2.run(inst, cfg, args.seed)
    print(f"RC201-100 {args.config} seed {args.seed}: CPU {time.process_time() - c0:.1f} s, "
          f"wall {time.perf_counter() - w0:.1f} s, n_gen {cfg['nsga2']['n_gen']}, n_evals {r['n_evals']}, "
          f"n_dp_calls {r['n_dp_calls']}, front {len(r['front'])}, feasible_front {r['feasible_frac_front']:.2f}")


if __name__ == "__main__":
    main()
