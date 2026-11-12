"""Chạy thí nghiệm và phân tích kết quả.

Hai bước tách riêng:
  run     : chạy một cấu hình trên một instance với nhiều seed, lưu kết quả THÔ của từng seed.
  analyze : đọc mọi cấu hình của một thí nghiệm trên một instance, tính chỉ số, xuất CSV.

Tách như vậy vì reference set và cận chuẩn hoá phụ thuộc mọi cấu hình: thêm cấu hình mới thì
chỉ cần analyze lại (vài giây), không phải chạy lại thuật toán.

Mọi cấu hình trong CÙNG một thí nghiệm phải giải CÙNG một bài toán (cùng mô hình, chỉ khác
thuật toán). Đổi satisfaction_time (hay chi phí, khí thải, dữ liệu) là đổi bài toán, phải tách
thành thí nghiệm khác; analyze sẽ báo lỗi nếu trộn. split_rule thuộc thuật toán, so sánh được.

Ví dụ:
  python -m src.runner run --exp ops_arrival --config ox --instance C102 --n 25
  python -m src.runner run --exp ops_arrival --config obx --instance C102 --n 25 --set nsga2.crossover=obx
  python -m src.runner analyze --exp ops_arrival --instance C102-25

Kết quả nằm ở results/<thí nghiệm>/<instance>/<cấu hình>/seed_XX.pkl
"""
from __future__ import annotations
import argparse
import copy
import itertools
import pickle
import time
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from scipy.stats import ranksums
from src.instance import ROOT, load_config, load_instance
from src.metrics import evaluate_front, hv_history, normalization_bounds, reference_set, sc
from src.nsga2 import run as run_nsga2

METRICS = ["HV", "IGD", "SP", "DM", "n_points"]
# Các khoá config định nghĩa bài toán. Hai cấu hình khác nhau ở đây thì không so sánh được.
MODEL_KEYS = ["cost", "speed_kmh", "emission", "satisfaction_time", "solomon", "case29"]

def apply_overrides(cfg: dict, overrides: list[str]) -> dict:
    cfg = copy.deepcopy(cfg)
    for item in overrides:
        if "=" not in item:
            raise ValueError(f"--set cần dạng khoá=giá_trị, nhận {item!r}")
        key, value = item.split("=", 1)
        *path, last = key.split(".")
        node = cfg
        for k in path:
            if not isinstance(node, dict) or k not in node:
                raise KeyError(f"config không có khoá {key!r}")
            node = node[k]
        if not isinstance(node, dict) or last not in node:
            raise KeyError(f"config không có khoá {key!r}")
        node[last] = yaml.safe_load(value)
    return cfg

def results_root(cfg: dict) -> Path:
    path = Path(cfg["experiment"]["results_dir"])
    return path if path.is_absolute() else ROOT / path

def run_config(exp: str, config_name: str, name: str, n: int, cfg: dict,
               seeds: list[int], overwrite: bool = False) -> Path:
    inst = load_instance(name, n, cfg)
    out_dir = results_root(cfg) / exp / inst.name / config_name
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "config_used.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
    for seed in seeds:
        path = out_dir / f"seed_{seed:02d}.pkl"
        if path.exists() and not overwrite:
            print(f"  seed {seed:2d}: đã có, bỏ qua")
            continue
        t0 = time.perf_counter()
        res = run_nsga2(inst, cfg, seed)
        res["runtime_s"] = time.perf_counter() - t0
        res["instance"] = inst.name
        res["config_name"] = config_name
        with open(path, "wb") as f:
            pickle.dump(res, f)
        front = res["F"][res["front"]]
        print(f"  seed {seed:2d}: {res['runtime_s']:5.1f} s   f1 min {front[:, 0].min():9.1f}   "
              f"f2 min {front[:, 1].min():7.1f}   f3 max {1 - front[:, 2].min():.4f}")
    return out_dir

def load_runs(exp_dir: Path) -> dict[str, list[dict]]:
    """Đọc mọi seed của mọi cấu hình trong thư mục results/<thí nghiệm>/<instance>."""
    runs = {}
    for config_dir in sorted(p for p in exp_dir.iterdir() if p.is_dir()):
        files = sorted(config_dir.glob("seed_*.pkl"))
        if files:
            runs[config_dir.name] = []
            for path in files:
                with open(path, "rb") as f:
                    runs[config_dir.name].append(pickle.load(f))
    return runs

def check_same_problem(exp_dir: Path, config_names: list[str]) -> None:
    models = {}
    for name in config_names:
        with open(exp_dir / name / "config_used.yaml", encoding="utf-8") as f:
            used = yaml.safe_load(f)
        models[name] = {k: used[k] for k in MODEL_KEYS}
    first = config_names[0]
    for name in config_names[1:]:
        diff = [k for k in MODEL_KEYS if models[name][k] != models[first][k]]
        if diff:
            raise ValueError(f"cấu hình {name!r} khác {first!r} ở {diff}: đây là hai bài toán khác nhau, "
                             f"không so sánh được. Hãy chạy chúng ở hai thí nghiệm (--exp) riêng.")

def front_of(res: dict) -> np.ndarray:
    return res["F"][res["front"]]

def analyze(exp: str, instance_name: str, cfg: dict) -> dict[str, pd.DataFrame]:
    exp_dir = results_root(cfg) / exp / instance_name
    runs = load_runs(exp_dir)
    if not runs:
        raise FileNotFoundError(f"không có kết quả trong {exp_dir}")
    check_same_problem(exp_dir, list(runs))
    ref_point = cfg["metrics"]["hv_ref_point"]
    all_fronts = [front_of(r) for rs in runs.values() for r in rs]
    ref = reference_set(all_fronts)
    bounds = normalization_bounds(all_fronts)

    # Chỉ số của từng run
    rows = []
    for config_name, rs in runs.items():
        for r in rs:
            F = front_of(r)
            m = evaluate_front(F, ref, bounds, ref_point)
            rows.append({
                "config": config_name, "seed": r["seed"], **m,
                "f1_min": F[:, 0].min(), "f2_min": F[:, 1].min(), "f3_max": 1 - F[:, 2].min(),
                "n_evals": r["n_evals"], "runtime_s": r["runtime_s"],
            })
    per_run = pd.DataFrame(rows)

    # Trung bình ± độ lệch chuẩn, cộng hệ số tương quan Pearson giữa ba mục tiêu trên front gộp
    summary = per_run.groupby("config").agg(["mean", "std"])
    summary.columns = [f"{a}_{b}" for a, b in summary.columns]
    summary = summary.drop(columns=["seed_mean", "seed_std"])
    for config_name, rs in runs.items():
        pts = np.vstack([front_of(r) for r in rs])
        pts = pts * np.array([1, 1, -1]) + np.array([0, 0, 1])     # đổi cột 3 về f3 thật
        with np.errstate(invalid="ignore", divide="ignore"):   # mục tiêu không đổi thì ra NaN
            c = np.corrcoef(pts, rowvar=False)
        summary.loc[config_name, ["corr_f1_f2", "corr_f1_f3", "corr_f2_f3"]] = c[0, 1], c[0, 2], c[1, 2]

    # So từng cặp cấu hình: p-value rank-sum trên HV, SC trung bình theo seed ghép cặp
    pair_rows = []
    for a, b in itertools.combinations(runs, 2):
        hv_a = per_run.loc[per_run.config == a, "HV"].to_numpy()
        hv_b = per_run.loc[per_run.config == b, "HV"].to_numpy()
        fa = {r["seed"]: front_of(r) for r in runs[a]}
        fb = {r["seed"]: front_of(r) for r in runs[b]}
        common = sorted(fa.keys() & fb.keys())
        pair_rows.append({
            "A": a, "B": b,
            "HV_A": hv_a.mean(), "HV_B": hv_b.mean(),
            "p_HV": ranksums(hv_a, hv_b).pvalue,
            "SC_A_B": np.mean([sc(fa[s], fb[s]) for s in common]),
            "SC_B_A": np.mean([sc(fb[s], fa[s]) for s in common]),
        })
    pairwise = pd.DataFrame(pair_rows)

    # Đường hội tụ: HV trung bình qua các thế hệ
    convergence = pd.DataFrame({
        config_name: np.mean([hv_history(r["history"], bounds, ref_point) for r in rs], axis=0)
        for config_name, rs in runs.items()
    })
    convergence.index.name = "generation"

    out = {"per_run": per_run, "summary": summary, "pairwise": pairwise, "convergence": convergence}
    for key, df in out.items():
        df.to_csv(exp_dir / f"{key}.csv", encoding="utf-8")
    return out

def print_report(out: dict[str, pd.DataFrame]) -> None:
    s = out["summary"]
    print("\nTrung bình ± độ lệch chuẩn theo cấu hình:")
    for config_name, row in s.iterrows():
        cells = "   ".join(f"{m} {row[m + '_mean']:.4f} ± {row[m + '_std']:.4f}" for m in METRICS[:4])
        print(f"  {config_name:20s} {cells}")
    print("\nTương quan Pearson trên front gộp (NaN: mục tiêu đó không đổi trên cả front):")
    print(s[["corr_f1_f2", "corr_f1_f3", "corr_f2_f3"]].round(3).to_string())
    if len(out["pairwise"]):
        print("\nSo từng cặp (p-value rank-sum trên HV):")
        print(out["pairwise"].round(4).to_string(index=False))
    conv = out["convergence"]
    marks = [g for g in (0, len(conv) // 4, len(conv) // 2, 3 * len(conv) // 4, len(conv) - 1)]
    print("\nHV trung bình qua các thế hệ:")
    print(conv.iloc[marks].round(4).to_string())

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Chạy và phân tích thí nghiệm NSGA-II")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="chạy một cấu hình trên một instance")
    p_run.add_argument("--exp", required=True, help="tên thí nghiệm, ví dụ baseline")
    p_run.add_argument("--config", required=True, help="tên cấu hình, ví dụ arrival")
    p_run.add_argument("--instance", required=True, help="C102, R201, RC202, RC201 hoặc case29")
    p_run.add_argument("--n", type=int, required=True, help="số khách")
    p_run.add_argument("--set", action="append", default=[], metavar="KHOÁ=GIÁ_TRỊ",
                       help="ghi đè config, dùng được nhiều lần, ví dụ --set nsga2.crossover=obx")
    p_run.add_argument("--seeds", help="danh sách seed, ví dụ 0,1,2; mặc định lấy từ config")
    p_run.add_argument("--overwrite", action="store_true", help="chạy lại cả seed đã có file")
    p_an = sub.add_parser("analyze", help="tính chỉ số cho mọi cấu hình của một thí nghiệm")
    p_an.add_argument("--exp", required=True)
    p_an.add_argument("--instance", required=True, help="tên thư mục instance, ví dụ C102-25")

    args = parser.parse_args(argv)
    base_cfg = load_config()

    if args.command == "run":
        cfg = apply_overrides(base_cfg, args.set)
        seeds = [int(s) for s in args.seeds.split(",")] if args.seeds else cfg["experiment"]["seeds"]
        print(f"{args.exp} / {args.instance}-{args.n} / {args.config}   ghi đè: {args.set or 'không'}")
        out_dir = run_config(args.exp, args.config, args.instance, args.n, cfg, seeds, args.overwrite)
        print(f"Đã lưu vào {out_dir}")
    else:
        print_report(analyze(args.exp, args.instance, base_cfg))

if __name__ == "__main__":
    main()
