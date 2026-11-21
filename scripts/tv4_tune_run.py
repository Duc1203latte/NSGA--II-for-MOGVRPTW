"""Chạy song song các cấu hình tuning bằng runner của TV1 (mỗi tiến trình một instance x cấu hình x seed).

    python -m scripts.tv4_tune_run --exp tv4_tune --configs baseline dp_every_eval ... \
        --seeds 100 101 102 103 104 --jobs 12

Mỗi tiến trình có OMP_NUM_THREADS = MKL_NUM_THREADS = OPENBLAS_NUM_THREADS = 1. Log ở
results/<exp>/logs/<instance>_<cấu hình>_seed<seed>.log. Seed tuning (100-104) khác bộ báo cáo (0-9).
"""
from __future__ import annotations
import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from scripts.tv4_tune_configs import overrides
from src.instance import ROOT, load_config
from src.runner import results_root

INSTANCES = [("C102", 25), ("R201", 50)]


def job(exp: str, name: str, n: int, config: str, seed: int, logdir) -> tuple[str, int]:
    cmd = [sys.executable, "-u", "-m", "src.runner", "run", "--exp", exp, "--config", config,
           "--instance", name, "--n", str(n), "--seeds", str(seed)]
    for o in overrides(config):
        cmd += ["--set", o]
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               PYTHONIOENCODING="utf-8", PYTHONPATH=str(ROOT))
    log = logdir / f"{name}-{n}_{config}_seed{seed}.log"
    with open(log, "w", encoding="utf-8") as f:
        rc = subprocess.call(cmd, cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT)
    return f"{name}-{n} {config} seed {seed}", rc


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True)
    ap.add_argument("--configs", nargs="+", required=True)
    ap.add_argument("--seeds", nargs="+", type=int, required=True)
    ap.add_argument("--jobs", type=int, default=12)
    args = ap.parse_args()
    logdir = results_root(load_config()) / args.exp / "logs"
    logdir.mkdir(parents=True, exist_ok=True)
    # việc dài (dp chấm mọi cá thể, R201-50) chạy trước để cân tải
    jobs = [(n, nm, c, s) for c in args.configs for (nm, n) in INSTANCES for s in args.seeds]
    jobs.sort(key=lambda j: (j[2] != "dp_every_eval", j[0] != 50))
    t0, failed = time.perf_counter(), []
    with ThreadPoolExecutor(args.jobs) as pool:
        futs = [pool.submit(job, args.exp, nm, n, c, s, logdir) for n, nm, c, s in jobs]
        for fu in futs:
            label, rc = fu.result()
            if rc != 0:
                failed.append(label)
    print(f"xong {len(jobs)} việc trong {time.perf_counter() - t0:.0f} s; lỗi: {failed or 'không'}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
