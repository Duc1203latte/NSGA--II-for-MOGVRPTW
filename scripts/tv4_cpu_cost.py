"""Chi phí CPU tuần tự (serial-equivalent) của từng cấu hình tuning, tương đối so với baseline.

Chạy từng cấu hình trong CÙNG một tiến trình, lần lượt, đo bằng time.process_time (thời gian CPU của
tiến trình, ít bị ảnh hưởng bởi việc máy bận hơn thời gian tường), trên các seed tuning, n_gen theo
config.yaml. Chạy khi không có việc song song khác thì số liệu sạch nhất.

    python -m scripts.tv4_cpu_cost --exp tv4_tune --configs baseline dp_every_eval ... --seeds 100 101
Ghi results/<exp>/cpu_cost.csv (instance, config, cpu_s trung bình mỗi run, relative = so với baseline).
"""
from __future__ import annotations
import argparse
import time

import pandas as pd

from scripts.tv4_tune_configs import overrides
from scripts.tv4_tune_run import INSTANCES
from src import nsga2
from src.instance import load_config, load_instance
from src.runner import apply_overrides, results_root


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True)
    ap.add_argument("--configs", nargs="+", required=True)
    ap.add_argument("--seeds", nargs="+", type=int, required=True)
    args = ap.parse_args()
    base_cfg = load_config()
    rows = []
    for name, n in INSTANCES:
        for config in args.configs:
            cfg = apply_overrides(base_cfg, overrides(config))
            inst = load_instance(name, n, cfg)
            t = time.process_time()
            for seed in args.seeds:
                nsga2.run(inst, cfg, seed)
            cpu = (time.process_time() - t) / len(args.seeds)
            rows.append({"instance": f"{name}-{n}", "config": config, "cpu_s": cpu})
            print(f"{name}-{n:<4d} {config:22s} {cpu:7.2f} s CPU/run", flush=True)
    df = pd.DataFrame(rows)
    out = results_root(base_cfg) / args.exp / "cpu_cost.csv"
    if out.exists():   # gộp với lần đo trước: dòng mới thay dòng cũ cùng (instance, config)
        old = pd.read_csv(out)[["instance", "config", "cpu_s"]]
        df = pd.concat([old, df]).drop_duplicates(["instance", "config"], keep="last")
    base = df[df.config == "baseline"].set_index("instance").cpu_s
    df["relative"] = df.apply(lambda r: r.cpu_s / base[r.instance], axis=1)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8")
    print(f"ghi {out}")


if __name__ == "__main__":
    main()
