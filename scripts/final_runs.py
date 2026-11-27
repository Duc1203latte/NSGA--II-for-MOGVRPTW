"""Giai đoạn 4: chạy cấu hình cuối và baseline trên 9 instance Solomon của bài báo và case29,
rồi tổng hợp kết quả thành một file CSV.

Cấu hình (các nhóm I, L, D, P định nghĩa trong scripts/ablation.py):
    baseline : NSGA-II gốc, mọi cờ cải tiến tắt
    IDP      : cấu hình cuối = init_smart + diversity (SDE k = 1, tắt archive) + dp_split polish (K = 10)
    ILDP     : IDP + local_search; mạnh nhất nếu so theo số thế hệ nhưng tốn 3.4-7.8 lần số lần
               đánh giá, nên chỉ chạy ở 200 thế hệ để tham khảo

    python -m scripts.final_runs run --exp final_g200 --seeds 0-19 --configs baseline,IDP,ILDP
    python -m scripts.final_runs run --exp final_g1000 --seeds 0-9 --configs baseline,IDP --set nsga2.n_gen=1000
    python -m scripts.final_runs summarize final_g200 final_g1000

Kết quả thô: results/<exp>/<instance>/<cấu hình>/seed_XX.pkl (chạy lại thì bỏ qua seed đã có).
Tổng hợp: results/final_summary.csv, mỗi dòng một (thí nghiệm, instance, cấu hình).
"""
from __future__ import annotations
import argparse
import pickle
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from scipy.stats import ranksums
from scripts.ablation import GROUPS, parse_seeds
from src.instance import load_config
from src.runner import analyze, apply_overrides, results_root, run_config

# Chín instance bài báo dùng (ở 100 khách bài báo đổi RC202 thành RC201) và case thực tế
INSTANCES = [("C102", 25), ("R201", 25), ("RC202", 25), ("C102", 50), ("R201", 50), ("RC202", 50),
             ("C102", 100), ("R201", 100), ("RC201", 100), ("case29", 29)]
CONFIGS = {
    "baseline": [],
    "IDP": GROUPS["I"] + GROUPS["D"] + GROUPS["P"],
    "ILDP": GROUPS["I"] + GROUPS["L"] + GROUPS["D"] + GROUPS["P"],
}
METRICS = ["HV", "IGD", "SP", "DM", "n_points", "f1_min", "f2_min", "f3_max", "n_evals", "runtime_s"]

def _job(args):
    exp, name, n, config_name, cfg, seed = args
    run_config(exp, config_name, name, n, cfg, [seed])
    return f"{name}-{n} / {config_name} / seed {seed}"

def run(exp: str, configs: list[str], seeds: list[int], overrides: list[str], workers: int) -> None:
    base_cfg = apply_overrides(load_config(), overrides)
    jobs = [(exp, name, n, c, apply_overrides(base_cfg, CONFIGS[c]), s)
            for name, n in INSTANCES for c in configs for s in seeds]
    # việc nặng chạy trước (có local search, rồi instance lớn) để các tiến trình kết thúc gần nhau
    jobs.sort(key=lambda j: (j[3] != "ILDP", -j[2]))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for i, done in enumerate(pool.map(_job, jobs), 1):
            if i % 50 == 0 or i == len(jobs):
                print(f"[{i}/{len(jobs)}] xong {done}", flush=True)

def feasible_fraction(exp: str, inst: str, config_name: str, cfg: dict) -> float:
    """Tỉ lệ nhỏ nhất (qua các seed) lời giải trên front không vượt đội xe."""
    fracs = []
    for path in sorted((results_root(cfg) / exp / inst / config_name).glob("seed_*.pkl")):
        with open(path, "rb") as f:
            r = pickle.load(f)
        fracs.append(float((r["CV"][r["front"]] == 0).mean()))
    return min(fracs)

def summarize(exps: list[str]) -> pd.DataFrame:
    cfg = load_config()
    rows = []
    for exp in exps:
        for name, n in INSTANCES:
            inst = f"{name}-{n}"
            per_run = analyze(exp, inst, cfg)["per_run"]
            base = per_run[per_run.config == "baseline"]
            for c in per_run.config.unique():
                r = per_run[per_run.config == c]
                row = {"exp": exp, "instance": inst, "config": c, "n_seeds": len(r)}
                for m in METRICS:
                    row[f"{m}_mean"] = r[m].mean()
                    row[f"{m}_std"] = r[m].std(ddof=1)
                for m in ("HV", "IGD"):          # Wilcoxon rank-sum so với baseline cùng thí nghiệm
                    row[f"p_{m}"] = np.nan if c == "baseline" else ranksums(r[m], base[m]).pvalue
                # giá trị tốt nhất qua các run, để đặt cạnh cột "min/max" của bài báo
                row["f1_best"], row["f2_best"], row["f3_best"] = r.f1_min.min(), r.f2_min.min(), r.f3_max.max()
                row["feasible_min"] = feasible_fraction(exp, inst, c, cfg)
                rows.append(row)
    out = pd.DataFrame(rows)
    path = results_root(cfg) / "final_summary.csv"
    out.to_csv(path, index=False, encoding="utf-8")
    print(f"Đã lưu {path}")
    return out

def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Giai đoạn 4: chạy và tổng hợp kết quả cuối")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run")
    p_run.add_argument("--exp", required=True)
    p_run.add_argument("--configs", default="baseline,IDP", help=f"chọn trong {list(CONFIGS)}")
    p_run.add_argument("--seeds", required=True, help="ví dụ 0-19 hoặc 0,1,2")
    p_run.add_argument("--set", action="append", default=[], metavar="KHOÁ=GIÁ_TRỊ",
                       help="ghi đè cho mọi cấu hình, ví dụ nsga2.n_gen=1000")
    p_run.add_argument("--workers", type=int, default=16)
    p_sum = sub.add_parser("summarize")
    p_sum.add_argument("exps", nargs="+", help="tên các thí nghiệm, ví dụ final_g200 final_g1000")
    args = ap.parse_args(argv)

    if args.cmd == "run":
        configs = [c.strip() for c in args.configs.split(",")]
        unknown = set(configs) - set(CONFIGS)
        if unknown:
            raise ValueError(f"cấu hình không có: {sorted(unknown)}; chỉ nhận {list(CONFIGS)}")
        run(args.exp, configs, parse_seeds(args.seeds), args.set, args.workers)
    else:
        summarize(args.exps)

if __name__ == "__main__":
    main()
